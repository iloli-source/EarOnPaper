const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const fs = require('fs')
const os = require('os')
const { pathToFileURL } = require('url')
const pu = require('./platform-utils')

const ENGINE_DIR = path.resolve(__dirname, '../spike/ear-pipeline')
// 3.2: OS別候補から実在するPythonを解決(POSIX固定をやめWindows/構成差に対応)
const PYTHON = pu.resolveExecutable(pu.pythonCandidates(ENGINE_DIR))

// 3.17/3.18: 生成した一時ディレクトリと採譜子プロセスを追跡し、終了時に片付ける
const generatedRoots = new Set()
const activeProcesses = new Set()

// 分離済みステムwavのキャッシュ: inputPath -> { dir, stems: {name: wavPath} }。
// 分離(Demucs)は重いので1入力につき1回だけ実行し、選ばれた楽器だけ後段で採譜する。
const separationCache = new Map()

// 採譜済み中間物のキャッシュ: inputPath -> MusicXML パス(#116)。
// 追加形式(簡譜/度数/移動ド等)を出す際、音声からのフル再採譜(Demucs+basic-pitch)を
// やり直さず、この採譜済み MusicXML から render サブコマンドで高速生成するために保持する。
const primaryMusicxmlByInput = new Map()

// 抽出楽器のメタ(表示順)。6-stem(htdemucs_6s)でギター/ピアノを分離して個別提示する。
// drums(非音程)と other(残差)は除外。ギターをデフォルト先頭にしTABを持たせる。
// ※ピアノは分離品質が実験的(音漏れ多め)だが、選択肢として提示する。
const INSTRUMENTS = [
  { id: 'guitar', label: 'ギター', hasTab: true },
  { id: 'piano', label: 'ピアノ', hasTab: false },
  { id: 'vocals', label: 'ボーカル', hasTab: false },
  { id: 'bass', label: 'ベース', hasTab: false },
]

let mainWindow

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#0d0d0f',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      // sandbox:true(既定・セキュア)を維持する。preload はローカルモジュールを require
      // しない(basenameForDisplay をインライン化し、file URL はメイン側で生成)ため、
      // サンドボックス下でも壊れない。以前 sandbox 未指定で preload が
      // require('./platform-utils') に失敗し window.earpipe が公開されなかった(#61)。
      sandbox: true,
    },
  })

  // E2E テスト起動時(env EARPAPER_E2E=1)のみ ?e2e=1 を付与。これにより
  // renderer 側のテストフック(window.__earpipeTest)は本番では一切生えない。
  const loadOpts = process.env.EARPAPER_E2E === '1' ? { query: { e2e: '1' } } : undefined
  mainWindow.loadFile(path.join(__dirname, 'renderer/index.html'), loadOpts)
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

// 3.17/3.18: 終了時に残留プロセスをkillし、一時ディレクトリを再帰削除
app.on('before-quit', () => {
  for (const proc of activeProcesses) {
    try { proc.kill() } catch { /* already gone */ }
  }
  activeProcesses.clear()
  for (const root of generatedRoots) {
    try { fs.rmSync(root, { recursive: true, force: true }) } catch { /* best effort */ }
  }
  generatedRoots.clear()
})

// 管理下(アプリ生成物)の判定: いずれかの一時ルート配下かつ許可拡張子(3.14/3.15/3.20)
function isOwnedOutput(filePath) {
  for (const root of generatedRoots) {
    if (pu.isManagedOutput(root, filePath)) return true
  }
  return false
}

// 生成物3種すべてが通常ファイルかつ0バイト超であることを確認(3.8: 偽成功の防止)
async function ensureOutputs(paths) {
  for (const p of Object.values(paths)) {
    let st
    try {
      st = await fs.promises.stat(p)
    } catch {
      throw new Error(`出力ファイルが生成されませんでした: ${pu.basenameForDisplay(p)}`)
    }
    if (!st.isFile() || st.size <= 0) {
      throw new Error(`出力ファイルが不正です(空/非ファイル): ${pu.basenameForDisplay(p)}`)
    }
  }
}

// ファイル選択ダイアログ
ipcMain.handle('open-file-dialog', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: '音声ファイル', extensions: ['wav', 'mp3', 'flac', 'ogg', 'm4a', 'aiff', 'aif', 'aac', 'opus', 'mp4'] },
      { name: 'すべてのファイル', extensions: ['*'] },
    ],
  })
  return result.canceled ? null : result.filePaths[0]
})

// 保存ダイアログ(3.14: コピー元をアプリ生成物に限定・3.10: 非同期コピー)
ipcMain.handle('save-file', async (_, srcPath, ext, defaultName) => {
  if (!isOwnedOutput(srcPath)) {
    throw new Error('保存できるのはアプリが生成した楽譜ファイルのみです')
  }
  const result = await dialog.showSaveDialog(mainWindow, {
    defaultPath: defaultName || `楽譜.${ext}`,
    filters: [{ name: String(ext).toUpperCase(), extensions: [ext] }],
  })
  if (result.canceled) return null
  await fs.promises.copyFile(srcPath, result.filePath)
  return result.filePath
})

// PDFをOSのデフォルトアプリで開く(3.15: 管理下生成物に限定・3.9: エラー文字列を確認)
ipcMain.handle('open-external', async (_, filePath) => {
  if (!isOwnedOutput(filePath)) {
    throw new Error('開けるのはアプリが生成した楽譜ファイルのみです')
  }
  const errMsg = await shell.openPath(filePath)
  if (errMsg) {
    throw new Error(`ファイルを開けませんでした: ${errMsg}`)
  }
})

// 採譜実行
ipcMain.handle('transcribe', async (event, inputPath, engine = 'auto', title = '') => {
  // 3.16: IPC境界で入力を再検証(拡張子allowlist + 通常ファイル)
  if (!pu.isAllowedAudioInput(inputPath)) {
    throw new Error('対応していない形式です(音声ファイルを選んでください)')
  }
  try {
    const st = fs.statSync(inputPath)
    if (!st.isFile()) throw new Error('not a file')
  } catch {
    throw new Error('入力ファイルが見つからないか、ファイルではありません')
  }

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'earpaper-'))
  generatedRoots.add(tmpDir)  // 3.17: 終了時削除の対象に追跡
  const baseName = path.basename(inputPath, path.extname(inputPath))
  const outMusicxml = path.join(tmpDir, `${baseName}.musicxml`)
  const outPdf = path.join(tmpDir, `${baseName}.pdf`)
  const outMidi = path.join(tmpDir, `${baseName}.mid`)
  const outTab = path.join(tmpDir, `${baseName}.tab.pdf`)  // ギターTAB譜PDF(任意・採譜と同時生成)

  return new Promise((resolve, reject) => {
    // 一旦(2026-07-22 ユーザー指示): ギター/ピアノ抽出モード。
    // Demucsで other ステム(専用ギターステムが無いためギター+ピアノ+その他が混在)を
    // 分離し、poly(多声)で検出する。monoは多声ステムをほぼ拾えない(実測5音)ため poly 必須。
    // TABは --tab-mono で各拍の主旋律1音に絞り、物理的に常に演奏可能な単音TABにする。
    const STEM = 'other'
    const selected = 'poly'
    const args = [
      '-W', 'ignore::RuntimeWarning',
      '-m', 'earpipe.pipeline', 'transcribe', inputPath,
      '-o', outMusicxml,
      '--pdf', outPdf,
      '--midi', outMidi,
      '--tab', outTab,
      '--tab-mono',
      '--stem', STEM,
      '--engine', selected,
    ]
    const safeTitle = pu.clampTitle(title)  // 3.19: 200文字上限
    if (safeTitle) args.push('--title', safeTitle)

    // 3.6: mono以外はbasic-pitch用Pythonを渡すが、実在する場合のみ設定する
    // (存在しないパスの強制でワーカー起動を壊さない。無ければエンジンが自動探索)
    const env = { ...process.env }
    if (selected !== 'mono') {
      const bp = pu.resolveExistingPath(pu.basicPitchPythonCandidates(ENGINE_DIR, env))
      if (bp) env.EARPIPE_BP_PYTHON = bp
    }

    const proc = spawn(PYTHON, args, { cwd: ENGINE_DIR, env })
    activeProcesses.add(proc)  // 3.18: 終了時killの対象に追跡

    let stdout = ''
    let stderr = ''

    proc.stdout.on('data', (chunk) => {
      stdout += chunk.toString()
    })

    proc.stderr.on('data', (chunk) => {
      const line = chunk.toString().trim()
      if (line) {
        stderr += line + '\n'
        event.sender.send('transcribe-progress', line)
      }
    })

    proc.on('close', (code) => {
      activeProcesses.delete(proc)
      if (code !== 0) {
        reject(new Error(`採譜エンジンがエラーで終了しました (code ${code})\n${stderr}`))
        return
      }
      let result
      try {
        result = JSON.parse(stdout)
      } catch {
        reject(new Error('エンジン出力のパースに失敗しました'))
        return
      }
      const paths = { musicxml: outMusicxml, pdf: outPdf, midi: outMidi }
      // PDF埋め込み用の file URL はメイン側(node:url あり)で作る。これにより
      // preload はローカルモジュール require が不要になり sandbox:true を維持できる。
      const pdfUrl = pathToFileURL(outPdf).href
      // 3.8: 成果物の実体(存在・非空)を確認してから成功応答する。
      // TAB譜は任意出力: 生成できていれば paths.tab に載せる(失敗しても本体採譜は成功扱い)。
      ensureOutputs(paths)
        .then(async () => {
          try {
            const tabStat = await fs.promises.stat(outTab)
            if (tabStat.isFile() && tabStat.size > 0) paths.tab = outTab
          } catch { /* TAB は任意: 無ければレンダラ側でボタン非表示 */ }
          // #116: 追加形式の再採譜回避用に採譜済み MusicXML を保持
          primaryMusicxmlByInput.set(inputPath, outMusicxml)
          resolve({ ...result, paths, pdfUrl })
        })
        .catch(reject)
    })

    proc.on('error', (err) => {
      activeProcesses.delete(proc)
      reject(new Error(`Pythonの起動に失敗しました: ${err.message}`))
    })
  })
})

// ── 楽器分離 → 選択楽器のみ採譜 ────────────────────────────────
// 分離(Demucs)を1回だけ実行して抽出楽器を提示し、ユーザーが選んだ楽器のwavだけを
// 後段で採譜する。全楽器を一括採譜すると重すぎる(1曲10分超)ため、選択オンデマンドにする。

// エンジンをspawnし stdout(JSON) を解析して返す。stderr行は onProgress へ流す。
function runEngineJson(args, env, onProgress) {
  return new Promise((resolve, reject) => {
    const proc = spawn(PYTHON, ['-W', 'ignore::RuntimeWarning', '-m', 'earpipe.pipeline', ...args],
      { cwd: ENGINE_DIR, env: env || { ...process.env } })
    activeProcesses.add(proc)
    let stdout = ''
    let stderr = ''
    proc.stdout.on('data', (c) => { stdout += c.toString() })
    proc.stderr.on('data', (c) => {
      const line = c.toString().trim()
      if (line) { stderr += line + '\n'; if (onProgress) onProgress(line) }
    })
    proc.on('error', (e) => { activeProcesses.delete(proc); reject(new Error(`Pythonの起動に失敗しました: ${e.message}`)) })
    proc.on('close', (code) => {
      activeProcesses.delete(proc)
      if (code !== 0) { reject(new Error(`エンジンがエラーで終了しました (code ${code})\n${stderr}`)); return }
      try { resolve(JSON.parse(stdout)) } catch { reject(new Error('エンジン出力のパースに失敗しました')) }
    })
  })
}

// basic-pitch(poly)用の Python を見つけたら env に設定して返す(auto採譜のpoly経路用)
function bpEnv() {
  const env = { ...process.env }
  const bp = pu.resolveExistingPath(pu.basicPitchPythonCandidates(ENGINE_DIR, env))
  if (bp) env.EARPIPE_BP_PYTHON = bp
  return env
}

// 分離のみ実行 → 抽出できた楽器一覧を返す(採譜はしない)
ipcMain.handle('separate-audio', async (event, inputPath) => {
  if (!pu.isAllowedAudioInput(inputPath)) {
    throw new Error('対応していない形式です(音声ファイルを選んでください)')
  }
  try {
    if (!fs.statSync(inputPath).isFile()) throw new Error('not a file')
  } catch {
    throw new Error('入力ファイルが見つからないか、ファイルではありません')
  }

  const sepDir = fs.mkdtempSync(path.join(os.tmpdir(), 'earpaper-sep-'))
  generatedRoots.add(sepDir)
  const result = await runEngineJson(
    ['separate', inputPath, '--out-dir', sepDir],
    { ...process.env },  // Demucsは .venv-demucs を規約で自動検出
    (line) => event.sender.send('transcribe-progress', line),
  )
  const stems = result.stems || {}
  separationCache.set(inputPath, { dir: sepDir, stems })
  // 抽出できた melodic 楽器のみ(wavが実在)を、ギター優先の順で返す
  const instruments = INSTRUMENTS
    .filter((it) => stems[it.id])
    .map((it) => ({ id: it.id, label: it.label, hasTab: it.hasTab }))
  if (instruments.length === 0) throw new Error('採譜できる楽器が見つかりませんでした')
  return { instruments }
})

// 選ばれた楽器(ステム)のwavだけを採譜して譜面を返す。分離は再実行しない。
ipcMain.handle('transcribe-stem', async (event, inputPath, stemId, title = '', opts = {}) => {
  const cache = separationCache.get(inputPath)
  if (!cache || !cache.stems[stemId]) {
    throw new Error('分離結果が見つかりません。もう一度ファイルを読み込んでください')
  }
  const wav = cache.stems[stemId]
  const meta = INSTRUMENTS.find((it) => it.id === stemId)
  const hasTab = !!(meta && meta.hasTab)

  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'earpaper-stem-'))
  generatedRoots.add(outDir)
  const outMusicxml = path.join(outDir, `${stemId}.musicxml`)
  const outPdf = path.join(outDir, `${stemId}.pdf`)
  const outMidi = path.join(outDir, `${stemId}.mid`)
  const outTab = path.join(outDir, `${stemId}.tab.pdf`)

  // 分離済みwavを直接採譜(--stem 指定なし=二重分離を避ける)。engine auto。
  // ギター(other)は TAB も単旋律で生成する。
  const args = [
    'transcribe', wav,
    '-o', outMusicxml, '--pdf', outPdf, '--midi', outMidi,
    '--engine', 'auto',
  ]
  if (hasTab) args.push('--tab', outTab, '--tab-mono')
  // 任意上書き(分かる人は指定): BPM範囲/拍子/キー。allowlistで検証してから渡す。
  const o = opts || {}
  if (/^\d+-\d+$/.test(String(o.bpmRange || ''))) args.push('--bpm-range', o.bpmRange)
  if (['4/4', '3/4', '2/4'].includes(o.beat)) args.push('--beat', o.beat)
  if (/^[A-G]#?$/.test(String(o.keyTonic || ''))) {
    args.push('--key', o.keyTonic, '--mode', o.keyMode === 'minor' ? 'minor' : 'major')
  }
  const safeTitle = pu.clampTitle(title)
  if (safeTitle) args.push('--title', `${safeTitle} (${meta.label})`)

  const result = await runEngineJson(args, bpEnv(),
    (line) => event.sender.send('transcribe-progress', line))

  const paths = { musicxml: outMusicxml, pdf: outPdf, midi: outMidi }
  await ensureOutputs(paths)
  if (hasTab) {
    try {
      const st = await fs.promises.stat(outTab)
      if (st.isFile() && st.size > 0) paths.tab = outTab
    } catch { /* TAB は任意 */ }
  }
  const pdfUrl = pathToFileURL(outPdf).href
  const tabUrl = paths.tab ? pathToFileURL(paths.tab).href : null
  // #116: 追加形式の再採譜回避用に採譜済み MusicXML を保持(inputPath基準)
  primaryMusicxmlByInput.set(inputPath, outMusicxml)
  return {
    stem: stemId, label: meta.label,
    n_notes: result.n_notes, engine: result.engine,
    bpm: result.bpm, tuning_offset_cents: result.tuning_offset_cents,
    paths, pdfUrl, tabUrl,
  }
})

// ── 詳細（音楽家向け）エクスポート ──────────────────────────────
// 簡譜/リードシート/度数/Nashville/GP5 等の理論系出力を GUI から生成する(#音楽家対象)。
// CLI にしか無かった --format/--analysis 出力を、ユーザーが実際に触れる導線へ露出する。

// key -> { kind, ext }。format=登録形式 / analysis=解析注釈。
const EXTRA_OUTPUTS = {
  jianpu: { kind: 'format', ext: 'txt' },
  leadsheet: { kind: 'format', ext: 'txt' },
  abc: { kind: 'format', ext: 'txt' },
  lilypond: { kind: 'format', ext: 'txt' },
  gp5: { kind: 'format', ext: 'gp5' },
  ust: { kind: 'format', ext: 'ust' },
  movable_do: { kind: 'analysis', ext: 'txt' },
  roman: { kind: 'analysis', ext: 'txt' },
  nashville: { kind: 'analysis', ext: 'txt' },
}

function runEngine(args) {
  return new Promise((resolve, reject) => {
    const proc = spawn(PYTHON, ['-W', 'ignore::RuntimeWarning', '-m', 'earpipe.pipeline', ...args],
      { cwd: ENGINE_DIR, env: { ...process.env } })
    activeProcesses.add(proc)
    let stderr = ''
    proc.stderr.on('data', (d) => { stderr += d.toString() })
    proc.on('error', (e) => { activeProcesses.delete(proc); reject(new Error(`Python起動失敗: ${e.message}`)) })
    proc.on('close', (code) => {
      activeProcesses.delete(proc)
      if (code === 0) resolve()
      else reject(new Error(`採譜エンジンがエラー終了 (code ${code})\n${stderr}`))
    })
  })
}

// 追加出力を1つ生成して保存する。savePath は E2E(EARPAPER_E2E=1)のときだけ引数指定を許し、
// それ以外は必ず保存ダイアログを出す(本番でレンダラが任意パスへ書けないようにする)。
ipcMain.handle('export-extra', async (_, inputPath, key, e2eSavePath) => {
  const spec = EXTRA_OUTPUTS[key]
  if (!spec) throw new Error('対応していない出力形式です')
  if (!pu.isAllowedAudioInput(inputPath)) throw new Error('入力音声が不正です')
  try {
    if (!fs.statSync(inputPath).isFile()) throw new Error('not a file')
  } catch {
    throw new Error('元の音声ファイルが見つかりません')
  }

  let savePath
  if (process.env.EARPAPER_E2E === '1' && e2eSavePath) {
    savePath = e2eSavePath
  } else {
    const res = await dialog.showSaveDialog(mainWindow, {
      defaultPath: `楽譜.${key}.${spec.ext}`,
      filters: [{ name: key, extensions: [spec.ext] }],
    })
    if (res.canceled) return null
    savePath = res.filePath
  }

  const flag = spec.kind === 'format' ? '--format' : '--analysis'
  // #116: 採譜済み中間物(MusicXML)があれば render で再利用し、フル再採譜
  // (Demucs分離+basic-pitch検出)をやり直さない。無い場合のみ音声から再採譜する。
  const cachedXml = primaryMusicxmlByInput.get(inputPath)
  if (cachedXml && fs.existsSync(cachedXml)) {
    await runEngine(['render', '--from-musicxml', cachedXml, flag, `${key}=${savePath}`])
  } else {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'earpaper-x-'))
    generatedRoots.add(tmpDir)
    const tmpXml = path.join(tmpDir, 'base.musicxml')  // lilypond 等は -o(MusicXML)を要する
    await runEngine(['transcribe', inputPath, '-o', tmpXml, flag, `${key}=${savePath}`, '--engine', 'auto'])
  }

  // 生成物の実体(存在・非空)を確認してから成功応答(偽成功防止)
  const st = fs.existsSync(savePath) ? fs.statSync(savePath) : null
  if (!st || !st.isFile() || st.size === 0) {
    throw new Error(`${key} の出力生成に失敗しました`)
  }
  return savePath
})
