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
const processInputs = new Map()
const processTokens = new Map()
const rootsByInput = new Map()
// URL取り込み元の音声を、分離・採譜の派生成果物と区別して保持する。
// 同じ入力の再分離時は元音声だけ残し、入力切替・終了時にはすべて削除する。
const sourceRootsByInput = new Map()

const MAX_CAPTURE_BYTES = 8 * 1024 * 1024
const MAX_DOWNLOADED_BYTES = 4 * 1024 * 1024 * 1024
const MAX_STDERR_CHARS = 64 * 1024
const ENGINE_TIMEOUT_MS = pu.boundedPositiveInt(
  process.env.EARPIPE_ENGINE_TIMEOUT_MS, 6 * 60 * 60 * 1000, 1000, 24 * 60 * 60 * 1000,
)
const DOWNLOAD_TIMEOUT_MS = pu.boundedPositiveInt(
  process.env.EARPIPE_DOWNLOAD_TIMEOUT_MS, 45 * 60 * 1000, 1000, 6 * 60 * 60 * 1000,
)
const MAX_ACTIVE_PROCESSES = pu.boundedPositiveInt(
  process.env.EARPIPE_MAX_ACTIVE_PROCESSES, 2, 1, 8,
)

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

  // ローカル固定UIから外部ページへ遷移・新規ウィンドウ生成させない。
  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith('file:')) event.preventDefault()
  })

  // macOSはウィンドウを閉じてもプロセスが残るため、閉じた時点で一時成果物と
  // 長時間子プロセスを必ず解放する。
  mainWindow.on('closed', () => {
    cleanupAllResources()
    mainWindow = null
  })
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

// 3.17/3.18: 終了時に残留プロセスをkillし、一時ディレクトリを再帰削除

function killProcessTree(proc, signal = 'SIGKILL') {
  if (!proc || !proc.pid) return
  if (process.platform === 'win32') {
    try {
      const killer = spawn('taskkill', ['/pid', String(proc.pid), '/T', '/F'], { windowsHide: true })
      killer.on('error', () => { try { proc.kill(signal) } catch { /* already gone */ } })
    } catch {
      try { proc.kill(signal) } catch { /* already gone */ }
    }
    return
  }
  try {
    process.kill(-proc.pid, signal)
  } catch {
    try { proc.kill(signal) } catch { /* already gone */ }
  }
}

function waitForProcessClose(proc, timeoutMs = 5000) {
  if (!proc || proc.exitCode !== null) return Promise.resolve(true)
  return new Promise((resolve) => {
    let done = false
    const finish = (closed) => {
      if (done) return
      done = true
      clearTimeout(timer)
      resolve(closed)
    }
    const timer = setTimeout(() => finish(false), timeoutMs)
    timer.unref?.()
    proc.once('close', () => finish(true))
  })
}

function cleanupAllResources() {
  for (const proc of activeProcesses) {
    killProcessTree(proc, 'SIGKILL')
  }
  activeProcesses.clear()
  processInputs.clear()
  processTokens.clear()
  for (const root of generatedRoots) {
    try { fs.rmSync(root, { recursive: true, force: true }) } catch { /* best effort */ }
  }
  generatedRoots.clear()
  rootsByInput.clear()
  sourceRootsByInput.clear()
  separationCache.clear()
  primaryMusicxmlByInput.clear()
}

app.on('before-quit', cleanupAllResources)

function registerRoot(root, inputPath = null) {
  generatedRoots.add(root)
  if (inputPath) {
    if (!rootsByInput.has(inputPath)) rootsByInput.set(inputPath, new Set())
    rootsByInput.get(inputPath).add(root)
  }
  return root
}

function associateRoot(root, inputPath) {
  if (!root || !inputPath) return
  if (!rootsByInput.has(inputPath)) rootsByInput.set(inputPath, new Set())
  rootsByInput.get(inputPath).add(root)
}

function associateSourceRoot(root, inputPath) {
  associateRoot(root, inputPath)
  if (!root || !inputPath) return
  if (!sourceRootsByInput.has(inputPath)) sourceRootsByInput.set(inputPath, new Set())
  sourceRootsByInput.get(inputPath).add(root)
}

function removeRoot(root) {
  if (!root) return
  try { fs.rmSync(root, { recursive: true, force: true }) } catch { /* best effort */ }
  generatedRoots.delete(root)
  for (const [input, roots] of rootsByInput) {
    roots.delete(root)
    if (roots.size === 0) rootsByInput.delete(input)
  }
  for (const [input, roots] of sourceRootsByInput) {
    roots.delete(root)
    if (roots.size === 0) sourceRootsByInput.delete(input)
  }
}

async function releaseInputResources(inputPath, { preserveSource = false } = {}) {
  if (!inputPath) return
  const stopping = []
  for (const proc of [...activeProcesses]) {
    if (processInputs.get(proc) === inputPath) {
      stopping.push(waitForProcessClose(proc))
      killProcessTree(proc, 'SIGKILL')
    }
  }
  if (stopping.length > 0) {
    const closed = await Promise.all(stopping)
    if (closed.some((ok) => !ok)) throw new Error('実行中プロセスを安全に停止できませんでした')
  }
  const roots = rootsByInput.get(inputPath)
  const sourceRoots = sourceRootsByInput.get(inputPath)
  for (const root of pu.selectRootsForRelease(roots, sourceRoots, preserveSource)) {
    removeRoot(root)
  }
  if (!preserveSource) {
    rootsByInput.delete(inputPath)
    sourceRootsByInput.delete(inputPath)
  }
  separationCache.delete(inputPath)
  primaryMusicxmlByInput.delete(inputPath)
}

ipcMain.handle('release-input', async (_, inputPath) => {
  await releaseInputResources(inputPath)
})

ipcMain.handle('cancel-operation', async (_, token) => {
  const safeToken = token == null ? null : String(token).slice(0, 100)
  if (!safeToken) return
  const stopping = []
  for (const proc of [...activeProcesses]) {
    if (processTokens.get(proc) === safeToken) {
      stopping.push(waitForProcessClose(proc))
      killProcessTree(proc, 'SIGKILL')
    }
  }
  if (stopping.length > 0) {
    const closed = await Promise.all(stopping)
    if (closed.some((ok) => !ok)) throw new Error('URL取得プロセスを安全に停止できませんでした')
  }
})

function safeProgress(sender, line, token = null) {
  if (!line || !sender || sender.isDestroyed()) return
  const safeToken = token == null ? null : String(token).slice(0, 100)
  try { sender.send('transcribe-progress', { token: safeToken, line }) } catch { /* renderer closed */ }
}

function boundedTail(current, chunk, max = MAX_STDERR_CHARS) {
  const next = current + chunk
  return next.length > max ? next.slice(-max) : next
}

function runCapturedProcess(command, args, {
  cwd,
  env,
  inputPath = null,
  operationToken = null,
  timeoutMs = ENGINE_TIMEOUT_MS,
  onProgress = null,
  parseJson = false,
} = {}) {
  if (activeProcesses.size >= MAX_ACTIVE_PROCESSES) {
    return Promise.reject(new Error('別の重い処理が実行中です。完了後に再試行してください'))
  }
  return new Promise((resolve, reject) => {
    let settled = false
    let stdoutBytes = 0
    const stdoutParts = []
    let stderr = ''
    let proc
    let timer = null

    const finish = (fn, value) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      if (proc) {
        activeProcesses.delete(proc)
        processInputs.delete(proc)
        processTokens.delete(proc)
      }
      fn(value)
    }

    try {
      proc = spawn(command, args, {
        cwd, env: env || { ...process.env }, windowsHide: true,
        detached: process.platform !== 'win32',
      })
    } catch (err) {
      reject(err)
      return
    }
    activeProcesses.add(proc)
    if (inputPath) processInputs.set(proc, inputPath)
    if (operationToken != null) processTokens.set(proc, String(operationToken).slice(0, 100))

    timer = setTimeout(() => {
      killProcessTree(proc, 'SIGKILL')
      finish(reject, new Error(`処理が制限時間を超えました (${Math.round(timeoutMs / 60000)}分)`))
    }, timeoutMs)
    timer.unref?.()

    proc.stdout?.on('data', (chunk) => {
      stdoutBytes += chunk.length
      if (stdoutBytes > MAX_CAPTURE_BYTES) {
        killProcessTree(proc, 'SIGKILL')
        finish(reject, new Error('エンジン標準出力が上限を超えました'))
        return
      }
      stdoutParts.push(Buffer.from(chunk))
    })
    proc.stderr?.on('data', (chunk) => {
      const text = chunk.toString()
      stderr = boundedTail(stderr, text)
      if (onProgress) onProgress(text.trim())
    })
    proc.on('error', (err) => finish(reject, err))
    proc.on('close', (code) => {
      if (settled) return
      if (code !== 0) {
        finish(reject, new Error(`プロセスがエラーで終了しました (code ${code})\n${stderr}`))
        return
      }
      const stdout = Buffer.concat(stdoutParts).toString()
      if (!parseJson) {
        finish(resolve, { stdout, stderr })
        return
      }
      try {
        finish(resolve, JSON.parse(stdout))
      } catch {
        finish(reject, new Error('エンジン出力のパースに失敗しました'))
      }
    })
  })
}

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
  const normalizedExt = String(ext || '').replace(/^\./, '').toLowerCase()
  if (!pu.OUTPUT_EXTENSIONS.includes(`.${normalizedExt}`)
      || path.extname(srcPath).toLowerCase() !== `.${normalizedExt}`) {
    throw new Error('保存形式と生成ファイルの形式が一致しません')
  }
  const srcStat = await fs.promises.stat(srcPath)
  if (!srcStat.isFile() || srcStat.size <= 0) throw new Error('保存元ファイルが空か不正です')
  // 初期名はbasename化してパス区切り混入を防ぐ(曲名スネーク名は renderer 側で生成)
  const safeDefault = pu.basenameForDisplay(String(defaultName || ''))
  const result = await dialog.showSaveDialog(mainWindow, {
    defaultPath: safeDefault || `楽譜.${normalizedExt}`,
    filters: [{ name: normalizedExt.toUpperCase(), extensions: [normalizedExt] }],
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
  const st = await fs.promises.stat(filePath)
  if (!st.isFile() || st.size <= 0) throw new Error('ファイルが空か不正です')
  const errMsg = await shell.openPath(filePath)
  if (errMsg) {
    throw new Error(`ファイルを開けませんでした: ${errMsg}`)
  }
})

// 採譜実行
ipcMain.handle('transcribe', async (event, inputPath, engine = 'auto', title = '', progressToken = null) => {
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
  registerRoot(tmpDir, inputPath)  // 入力単位で追跡し、切替時にも削除
  const baseName = pu.snakeFileStem(path.basename(inputPath, path.extname(inputPath)))
  const outMusicxml = path.join(tmpDir, `${baseName}.musicxml`)
  const outPdf = path.join(tmpDir, `${baseName}.pdf`)
  const outMidi = path.join(tmpDir, `${baseName}.mid`)
  const outTab = path.join(tmpDir, `${baseName}.tab.pdf`)  // ギターTAB譜PDF(任意・採譜と同時生成)
  const outChordChart = path.join(tmpDir, `${baseName}.chord.pdf`)  // コード譜(一次導線・#123/#116)
  const outConfView = path.join(tmpDir, `${baseName}.confview.pdf`)  // 解析ビュー(#121)

  // 一旦(2026-07-22 ユーザー指示): ギター/ピアノ抽出モード。
  const STEM = 'other'
  const selected = pu.normalizeEngine(engine)
  const args = [
    'transcribe', inputPath,
    '-o', outMusicxml,
    '--pdf', outPdf,
    '--midi', outMidi,
    '--tab', outTab,
    '--tab-mono',
    '--chord-chart', outChordChart,
    '--emit', `confview=${outConfView}`,
    '--stem', STEM,
    '--engine', selected,
  ]
  const safeTitle = pu.clampTitle(title)
  if (safeTitle) args.push('--title', safeTitle)

  const env = { ...process.env }
  if (selected !== 'mono') {
    const bp = pu.resolveExistingPath(pu.basicPitchPythonCandidates(ENGINE_DIR, env))
    if (bp) env.EARPIPE_BP_PYTHON = bp
  }

  try {
    const result = await runEngineJson(args, env,
      (line) => safeProgress(event.sender, line, progressToken), inputPath, progressToken)
    const paths = { musicxml: outMusicxml, pdf: outPdf, midi: outMidi }
    await ensureOutputs(paths)
    try {
      const st = await fs.promises.stat(outTab)
      if (st.isFile() && st.size > 0) paths.tab = outTab
    } catch { /* TABは任意 */ }
    let chordChartUrl = null
    try {
      const st = await fs.promises.stat(outChordChart)
      if (st.isFile() && st.size > 0) {
        paths.chordChart = outChordChart
        chordChartUrl = pathToFileURL(outChordChart).href
      }
    } catch { /* 任意 */ }
    let confViewUrl = null
    try {
      const st = await fs.promises.stat(outConfView)
      if (st.isFile() && st.size > 0) {
        paths.confView = outConfView
        confViewUrl = pathToFileURL(outConfView).href
      }
    } catch { /* 任意 */ }
    primaryMusicxmlByInput.set(inputPath, outMusicxml)
    return { ...result, paths, pdfUrl: pathToFileURL(outPdf).href, chordChartUrl, confViewUrl }
  } catch (err) {
    removeRoot(tmpDir)
    throw err
  }
})

// ── 楽器分離 → 選択楽器のみ採譜 ────────────────────────────────
// 分離(Demucs)を1回だけ実行して抽出楽器を提示し、ユーザーが選んだ楽器のwavだけを
// 後段で採譜する。全楽器を一括採譜すると重すぎる(1曲10分超)ため、選択オンデマンドにする。

// エンジンをspawnし stdout(JSON) を解析して返す。stderr行は onProgress へ流す。
async function runEngineJson(args, env, onProgress, inputPath = null, operationToken = null) {
  try {
    return await runCapturedProcess(
      PYTHON,
      ['-W', 'ignore::RuntimeWarning', '-m', 'earpipe.pipeline', ...args],
      { cwd: ENGINE_DIR, env, inputPath, operationToken, onProgress, parseJson: true },
    )
  } catch (err) {
    if (err.code === 'ENOENT') throw new Error(`Pythonの起動に失敗しました: ${err.message}`)
    throw err
  }
}

// basic-pitch(poly)用の Python を見つけたら env に設定して返す(auto採譜のpoly経路用)
function bpEnv() {
  const env = { ...process.env }
  const bp = pu.resolveExistingPath(pu.basicPitchPythonCandidates(ENGINE_DIR, env))
  if (bp) env.EARPIPE_BP_PYTHON = bp
  return env
}

// ── URL取り込み(#128・F-006裁定変更 2026-07-23) ─────────────────────
// yt-dlp(ユーザーマシン上でのローカル実行)でURLの音声をm4a化し、既存の
// ファイル入力フローに合流させる。サーバーは一切関与しない(NF-023非衝突)。
// サイト利用規約・楽曲の著作権はユーザー責任(レンダラ側に注意文言を常設)。
ipcMain.handle('import-url', async (event, url, progressToken = null) => {
  if (!pu.isAllowedMediaUrl(url)) {
    throw new Error('URLの形式が正しくないか、ローカルネットワーク宛てのURLです')
  }
  const ytdlp = pu.resolveExecutable(pu.ytDlpCandidates())
  const dlDir = registerRoot(fs.mkdtempSync(path.join(os.tmpdir(), 'earpaper-dl-')))
  const args = pu.buildYtDlpArgs(url, dlDir)
  try {
    const { stdout } = await runCapturedProcess(ytdlp, args, {
      env: { ...process.env },
      timeoutMs: DOWNLOAD_TIMEOUT_MS,
      operationToken: progressToken,
      onProgress: (line) => safeProgress(event.sender, line, progressToken),
    })
    const lines = stdout.trim().split(/\r?\n/).filter(Boolean)
    const reportedPath = lines[lines.length - 1]
    if (!reportedPath) throw new Error('取り込んだ音声ファイルの保存先を取得できませんでした')

    let filePath
    let realRoot
    try {
      filePath = fs.realpathSync.native(reportedPath)
      realRoot = fs.realpathSync.native(dlDir)
    } catch {
      throw new Error('取り込んだ音声ファイルが見つかりませんでした')
    }
    const rel = path.relative(realRoot, filePath)
    const st = fs.statSync(filePath)
    if (rel === '' || rel.startsWith('..') || path.isAbsolute(rel)
        || !pu.isAllowedAudioInput(filePath) || !st.isFile() || st.size <= 0
        || st.size > MAX_DOWNLOADED_BYTES) {
      throw new Error('yt-dlpが管理外または不正なファイルを返しました')
    }
    associateSourceRoot(dlDir, filePath)
    return { path: filePath, title: path.basename(filePath, path.extname(filePath)) }
  } catch (err) {
    removeRoot(dlDir)
    if (err.code === 'ENOENT') {
      const install = process.platform === 'darwin'
        ? 'brew install yt-dlp'
        : process.platform === 'win32'
          ? 'winget install yt-dlp.yt-dlp'
          : 'お使いのLinuxのパッケージ管理機能で yt-dlp をインストール'
      throw new Error(`yt-dlp が見つかりません。${install}してから再試行してください`)
    }
    throw err
  }
})

// 分離のみ実行 → 抽出できた楽器一覧を返す(採譜はしない)
ipcMain.handle('separate-audio', async (event, inputPath, progressToken = null) => {
  if (!pu.isAllowedAudioInput(inputPath)) {
    throw new Error('対応していない形式です(音声ファイルを選んでください)')
  }
  try {
    if (!fs.statSync(inputPath).isFile()) throw new Error('not a file')
  } catch {
    throw new Error('入力ファイルが見つからないか、ファイルではありません')
  }

  // 同じ入力を再処理する場合、旧ステム・譜面・実行中プロセスを先に解放する。
  await releaseInputResources(inputPath, { preserveSource: true })
  const sepDir = registerRoot(fs.mkdtempSync(path.join(os.tmpdir(), 'earpaper-sep-')), inputPath)
  try {
    const result = await runEngineJson(
      ['separate', inputPath, '--out-dir', sepDir],
      { ...process.env },
      (line) => safeProgress(event.sender, line, progressToken),
      inputPath,
      progressToken,
    )
    const rawStems = result.stems || {}
    const stems = {}
    const realRoot = fs.realpathSync.native(sepDir)
    for (const meta of INSTRUMENTS) {
      const candidate = rawStems[meta.id]
      if (!candidate) continue
      try {
        const real = fs.realpathSync.native(candidate)
        const rel = path.relative(realRoot, real)
        const st = fs.statSync(real)
        if (rel !== '' && !rel.startsWith('..') && !path.isAbsolute(rel)
            && path.extname(real).toLowerCase() === '.wav' && st.isFile() && st.size > 0) {
          stems[meta.id] = real
        }
      } catch { /* 不正・欠落ステムは候補から落とす */ }
    }
    separationCache.set(inputPath, { dir: sepDir, stems })
    const instruments = INSTRUMENTS
      .filter((it) => stems[it.id])
      .map((it) => ({ id: it.id, label: it.label, hasTab: it.hasTab }))
    if (instruments.length === 0) throw new Error('採譜できる有効な楽器ステムが見つかりませんでした')
    return { instruments }
  } catch (err) {
    removeRoot(sepDir)
    separationCache.delete(inputPath)
    throw err
  }
})

// 選ばれた楽器(ステム)のwavだけを採譜して譜面を返す。分離は再実行しない。
ipcMain.handle('transcribe-stem', async (event, inputPath, stemId, title = '', opts = {}, progressToken = null) => {
  const meta = INSTRUMENTS.find((it) => it.id === stemId)
  if (!meta) throw new Error('対応していない楽器です')
  const cache = separationCache.get(inputPath)
  if (!cache || !cache.stems[stemId]) {
    throw new Error('分離結果が見つかりません。もう一度ファイルを読み込んでください')
  }
  const wav = cache.stems[stemId]
  let wavStat
  try {
    const realRoot = fs.realpathSync.native(cache.dir)
    const realWav = fs.realpathSync.native(wav)
    const rel = path.relative(realRoot, realWav)
    wavStat = fs.statSync(realWav)
    if (rel === '' || rel.startsWith('..') || path.isAbsolute(rel)
        || !wavStat.isFile() || wavStat.size <= 0 || path.extname(realWav).toLowerCase() !== '.wav') {
      throw new Error('invalid stem')
    }
  } catch {
    throw new Error('分離済み音声が欠落または不正です。もう一度読み込んでください')
  }
  const hasTab = !!meta.hasTab

  const outDir = registerRoot(fs.mkdtempSync(path.join(os.tmpdir(), 'earpaper-stem-')), inputPath)
  // #135追補: 生成ファイル自体を曲名入りスネーク名にする。PDFビューアのDLボタン等、
  // エクスポートボタン以外の保存経路でも初期名に曲名が入るようにする。
  const nameStem = pu.snakeFileStem(pu.clampTitle(title))
  const outMusicxml = path.join(outDir, `${nameStem}_${stemId}.musicxml`)
  const outPdf = path.join(outDir, `${nameStem}_${stemId}_score.pdf`)
  const outMidi = path.join(outDir, `${nameStem}_${stemId}.mid`)
  const outTab = path.join(outDir, `${nameStem}_${stemId}_tab.pdf`)
  const outChordChart = path.join(outDir, `${nameStem}_${stemId}_chord.pdf`)  // #123/#116: コード譜(一次導線)
  const outConfView = path.join(outDir, `${nameStem}_${stemId}_analysis.pdf`)  // #121: 信頼度ハイライト＋波形

  // 分離済みwavを直接採譜(--stem 指定なし=二重分離を避ける)。engine auto。
  // ギター(other)は TAB も単旋律で生成する。コード譜は一次導線として常時生成する。
  const args = [
    'transcribe', wav,
    '-o', outMusicxml, '--pdf', outPdf, '--midi', outMidi,
    '--chord-chart', outChordChart,
    '--emit', `confview=${outConfView}`,
    '--engine', 'auto',
  ]
  if (hasTab) args.push('--tab', outTab, '--tab-mono')
  // 任意上書き(分かる人は指定): BPM範囲/拍子/キー。allowlistで検証してから渡す。
  const o = opts || {}
  const bpmRange = pu.normalizeBpmRange(String(o.bpmRange || ''))
  if (bpmRange) args.push('--bpm-range', bpmRange)
  if (['4/4', '3/4', '2/4'].includes(o.beat)) args.push('--beat', o.beat)
  if (/^[A-G](?:#|b)?$/.test(String(o.keyTonic || ''))) {
    args.push('--key', o.keyTonic, '--mode', o.keyMode === 'minor' ? 'minor' : 'major')
  }
  const safeTitle = pu.clampTitle(title)
  if (safeTitle) args.push('--title', pu.clampTitle(`${safeTitle} (${meta.label})`))

  try {
    const result = await runEngineJson(args, bpEnv(),
      (line) => safeProgress(event.sender, line, progressToken), inputPath, progressToken)

    const paths = { musicxml: outMusicxml, pdf: outPdf, midi: outMidi }
    await ensureOutputs(paths)
    if (hasTab) {
      try {
        const st = await fs.promises.stat(outTab)
        if (st.isFile() && st.size > 0) paths.tab = outTab
      } catch { /* TAB は任意 */ }
    }
    // コード譜(#123)は一次導線。生成できていれば paths/URL に載せる(失敗しても本体は成功)。
    try {
      const cst = await fs.promises.stat(outChordChart)
      if (cst.isFile() && cst.size > 0) paths.chordChart = outChordChart
    } catch { /* コード譜は任意: 無ければレンダラ側でタブ非表示 */ }
    // 解析ビュー(#121: 信頼度ハイライト＋波形)。任意出力。
    try {
      const vst = await fs.promises.stat(outConfView)
      if (vst.isFile() && vst.size > 0) paths.confView = outConfView
    } catch { /* 解析ビューは任意 */ }
    const pdfUrl = pathToFileURL(outPdf).href
    const tabUrl = paths.tab ? pathToFileURL(paths.tab).href : null
    const chordChartUrl = paths.chordChart ? pathToFileURL(paths.chordChart).href : null
    const confViewUrl = paths.confView ? pathToFileURL(paths.confView).href : null
    // #116: 追加形式の再採譜回避用に採譜済み MusicXML を保持(inputPath基準)
    primaryMusicxmlByInput.set(inputPath, outMusicxml)
    return {
      stem: stemId, label: meta.label,
      n_notes: result.n_notes, engine: result.engine,
      bpm: result.bpm, tuning_offset_cents: result.tuning_offset_cents,
      paths, pdfUrl, tabUrl, chordChartUrl, confViewUrl,
    }
  } catch (err) {
    // エンジン成功後でも必須成果物が空・欠落なら、半端な一時成果物を残さない。
    removeRoot(outDir)
    throw err
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

async function runEngine(args, env = { ...process.env }, inputPath = null) {
  try {
    await runCapturedProcess(
      PYTHON,
      ['-W', 'ignore::RuntimeWarning', '-m', 'earpipe.pipeline', ...args],
      { cwd: ENGINE_DIR, env, inputPath },
    )
  } catch (err) {
    if (err.code === 'ENOENT') throw new Error(`Python起動失敗: ${err.message}`)
    throw err
  }
}

// 追加出力を1つ生成して保存する。savePath は E2E(EARPAPER_E2E=1)のときだけ引数指定を許し、
// それ以外は必ず保存ダイアログを出す(本番でレンダラが任意パスへ書けないようにする)。
ipcMain.handle('export-extra', async (_, inputPath, key, e2eSavePath, defaultName) => {
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
    const realTmp = fs.realpathSync.native(os.tmpdir())
    const candidate = path.resolve(e2eSavePath)
    const rel = path.relative(realTmp, candidate)
    if (rel === '' || rel.startsWith('..') || path.isAbsolute(rel)
        || path.extname(candidate).toLowerCase() !== `.${spec.ext}`) {
      throw new Error('E2E保存先は一時ディレクトリ配下の正しい拡張子に限定されます')
    }
    savePath = candidate
  } else {
    const extraDefault = pu.basenameForDisplay(String(defaultName || ''))
    const res = await dialog.showSaveDialog(mainWindow, {
      defaultPath: extraDefault || `楽譜.${key}.${spec.ext}`,
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
    await runEngine(['render', '--from-musicxml', cachedXml, flag, `${key}=${savePath}`],
      { ...process.env }, inputPath)
  } else {
    const tmpDir = registerRoot(fs.mkdtempSync(path.join(os.tmpdir(), 'earpaper-x-')), inputPath)
    const tmpXml = path.join(tmpDir, 'base.musicxml')  // lilypond 等は -o(MusicXML)を要する
    await runEngine(['transcribe', inputPath, '-o', tmpXml, flag, `${key}=${savePath}`, '--engine', 'auto'],
      bpEnv(), inputPath)
  }

  // 生成物の実体(存在・非空)を確認してから成功応答(偽成功防止)
  const st = fs.existsSync(savePath) ? fs.statSync(savePath) : null
  if (!st || !st.isFile() || st.size === 0) {
    throw new Error(`${key} の出力生成に失敗しました`)
  }
  return savePath
})
