const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const fs = require('fs')
const os = require('os')

const ENGINE_DIR = path.resolve(__dirname, '../spike/ear-pipeline')
const PYTHON = path.join(ENGINE_DIR, '.venv/bin/python')
const PYTHON312 = path.join(ENGINE_DIR, '.venv312/bin/python3.12')

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
    },
  })

  mainWindow.loadFile(path.join(__dirname, 'renderer/index.html'))
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

// ファイル選択ダイアログ
ipcMain.handle('open-file-dialog', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: '音声ファイル', extensions: ['wav', 'mp3', 'flac', 'ogg', 'm4a', 'aiff'] },
    ],
  })
  return result.canceled ? null : result.filePaths[0]
})

// 保存ダイアログ
ipcMain.handle('save-file', async (_, srcPath, ext, defaultName) => {
  const result = await dialog.showSaveDialog(mainWindow, {
    defaultPath: defaultName || `楽譜.${ext}`,
    filters: [{ name: ext.toUpperCase(), extensions: [ext] }],
  })
  if (result.canceled) return null
  fs.copyFileSync(srcPath, result.filePath)
  return result.filePath
})

// PDFをOSのデフォルトアプリで開く
ipcMain.handle('open-external', async (_, filePath) => {
  await shell.openPath(filePath)
})

// 採譜実行
ipcMain.handle('transcribe', async (event, inputPath, engine = 'mono') => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'earpaper-'))
  const baseName = path.basename(inputPath, path.extname(inputPath))
  const outMusicxml = path.join(tmpDir, `${baseName}.musicxml`)
  const outPdf = path.join(tmpDir, `${baseName}.pdf`)
  const outMidi = path.join(tmpDir, `${baseName}.mid`)

  return new Promise((resolve, reject) => {
    const isPoly = engine === 'poly'
    const args = [
      '-m', 'earpipe.pipeline', 'transcribe', inputPath,
      '-o', outMusicxml,
      '--pdf', outPdf,
      '--midi', outMidi,
      '--engine', isPoly ? 'poly' : 'mono',
    ]

    const env = { ...process.env }
    if (isPoly) env.EARPIPE_BP_PYTHON = PYTHON312

    console.log('[earpipe] CMD:', PYTHON, args.join(' '))
    const proc = spawn(PYTHON, args, { cwd: ENGINE_DIR, env })

    let stdout = ''
    let stderr = ''

    proc.stdout.on('data', (chunk) => {
      stdout += chunk.toString()
    })

    proc.stderr.on('data', (chunk) => {
      const line = chunk.toString().trim()
      if (line) {
        stderr += line + '\n'
        // 進捗をレンダラーに送信
        event.sender.send('transcribe-progress', line)
      }
    })

    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`採譜エンジンがエラーで終了しました (code ${code})\n${stderr}`))
        return
      }
      try {
        const result = JSON.parse(stdout)
        resolve({
          ...result,
          paths: {
            musicxml: outMusicxml,
            pdf: outPdf,
            midi: outMidi,
          },
        })
      } catch {
        reject(new Error('エンジン出力のパースに失敗しました'))
      }
    })

    proc.on('error', (err) => {
      reject(new Error(`Pythonの起動に失敗しました: ${err.message}`))
    })
  })
})
