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

  return new Promise((resolve, reject) => {
    // auto=音源に応じてmono/poly自動選択(既定・#64) / mono / poly のみ許可
    const selected = ['auto', 'mono', 'poly'].includes(engine) ? engine : 'auto'
    const args = [
      '-W', 'ignore::RuntimeWarning',
      '-m', 'earpipe.pipeline', 'transcribe', inputPath,
      '-o', outMusicxml,
      '--pdf', outPdf,
      '--midi', outMidi,
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
      // 3.8: 成果物の実体(存在・非空)を確認してから成功応答する
      ensureOutputs(paths)
        .then(() => resolve({ ...result, paths, pdfUrl }))
        .catch(reject)
    })

    proc.on('error', (err) => {
      activeProcesses.delete(proc)
      reject(new Error(`Pythonの起動に失敗しました: ${err.message}`))
    })
  })
})
