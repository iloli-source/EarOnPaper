'use strict'

const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')

const appDir = path.resolve(__dirname, '..')
const mainSource = fs.readFileSync(path.join(appDir, 'main.js'), 'utf8')
const rendererSource = fs.readFileSync(path.join(appDir, 'renderer', 'app.js'), 'utf8')

test('URL取り込み元は再分離直前に保持し、陳腐化結果は解放する', () => {
  assert.match(mainSource, /associateSourceRoot\(dlDir, filePath\)/)
  assert.match(mainSource, /await releaseInputResources\(inputPath, \{ preserveSource: true \}\)/)
  assert.match(rendererSource, /requestId !== urlGeneration[\s\S]*releaseInput\(imported\.path\)/)
})

test('必須成果物検証の失敗でもステム出力ルートを削除する', () => {
  assert.match(
    mainSource,
    /await ensureOutputs\(paths\)[\s\S]*catch \(err\) \{[\s\S]*removeRoot\(outDir\)[\s\S]*throw err/,
  )
})


test('進捗イベントは処理トークンで別ジョブ混入を拒否する', () => {
  const preloadSource = fs.readFileSync(path.join(appDir, 'preload.js'), 'utf8')
  assert.match(mainSource, /sender\.send\('transcribe-progress', \{ token: safeToken, line \}\)/)
  assert.match(preloadSource, /ipcRenderer\.invoke\('transcribe-stem'[\s\S]*progressToken/)
  assert.match(rendererSource, /payload\.token !== expectedToken/)
  assert.match(rendererSource, /importUrl\(url, progressToken\)/)
  assert.match(rendererSource, /separateAudio\(filePath, progressToken\)/)
})


test('新しい入力は古いURL取得プロセスをトークンで停止する', () => {
  const preloadSource = fs.readFileSync(path.join(appDir, 'preload.js'), 'utf8')
  assert.match(mainSource, /ipcMain\.handle\('cancel-operation'/)
  assert.match(mainSource, /processTokens\.get\(proc\) === safeToken/)
  assert.match(preloadSource, /cancelOperation: \(token\)/)
  assert.match(rendererSource, /await cancelActiveUrlOperation\(\)/)
  assert.match(rendererSource, /activeUrlOperationToken = progressToken/)
})


test('入力切替は子プロセスの停止完了を待ってから次工程へ進む', () => {
  assert.match(mainSource, /function waitForProcessClose\(proc, timeoutMs = 5000\)/)
  assert.match(mainSource, /const closed = await Promise\.all\(stopping\)/)
  assert.match(mainSource, /await releaseInputResources\(inputPath, \{ preserveSource: true \}\)/)
})
