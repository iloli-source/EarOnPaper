'use strict'

// formal/ の TLC 反例を main.js のIPCハンドラで再現する回帰テスト(refs #152)。
// 子プロセスの終了と stat の復帰はハーネスから制御し、実時間待ちはしない。

const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { loadMain } = require('./helpers/main-harness')

function withMain(fn) {
  return async () => {
    const main = loadMain()
    try {
      await fn(main)
    } finally {
      main.dispose()
    }
  }
}

async function separate(main, input) {
  const pending = main.invoke('separate-audio', input, 'sep')
  await Promise.resolve()
  const proc = main.spawned.at(-1)
  proc.succeed()
  await pending
  return proc
}

async function transcribeStem(main, input, stemId) {
  const pending = main.invoke('transcribe-stem', input, stemId, 'Song', {}, `t-${stemId}`)
  main.spawned.at(-1).succeed()
  return pending
}

const isOptionalChordStat = (p) => p.endsWith('_chord.pdf')

test('release-input が採譜後の stat 待ちに割り込んだら、解放済みの結果を成功として返さない', withMain(async (main) => {
  // Arrange: InputLifecycleBugRelease の反例 Start → EngineExit → ReleaseSync → Publish
  const input = main.makeInput()
  await separate(main, input)
  const gate = main.gateStat(isOptionalChordStat)
  const pending = main.invoke('transcribe-stem', input, 'guitar', 'Song', {}, 't1')
  const proc = main.spawned.at(-1)
  const outDir = path.dirname(proc.args[proc.args.indexOf('-o') + 1])
  proc.succeed()
  await gate.reached

  // Act
  await main.invoke('release-input', input)
  gate.release()

  // Assert
  await assert.rejects(pending, /破棄/)
  assert.equal(fs.existsSync(outDir), false)
}))

test('ウィンドウ終了の後始末が採譜後の stat 待ちに割り込んだら、結果を公開しない', withMain(async (main) => {
  // Arrange: InputLifecycleBugCleanup の反例 Start → EngineExit → Cleanup → Publish
  const input = main.makeInput()
  await separate(main, input)
  const gate = main.gateStat(isOptionalChordStat)
  const pending = main.invoke('transcribe-stem', input, 'guitar', 'Song', {}, 't1')
  main.spawned.at(-1).succeed()
  await gate.reached

  // Act
  main.emitApp('before-quit')
  gate.release()

  // Assert
  await assert.rejects(pending, /破棄/)
}))

test('release-input は kill 待ちの間に始まった同じ入力の子プロセスも止める', withMain(async (main) => {
  // Arrange: InputLifecycleBugOrphan の反例 Start(h1) → ReleaseKill → Start(h2) → Close(h1) → ReleaseFinish
  const input = main.makeInput()
  const first = main.invoke('transcribe', input, 'auto', 'Song', 'a')
  const firstProc = main.spawned.at(-1)
  const releasing = main.invoke('release-input', input)
  const second = main.invoke('transcribe', input, 'auto', 'Song', 'b')
  const secondProc = main.spawned.at(-1)
  assert.notEqual(firstProc, secondProc)

  // Act
  firstProc.close(null)
  await assert.rejects(first)
  await new Promise((resolve) => setImmediate(resolve))

  // Assert
  assert.equal(secondProc.killedBy, 'SIGKILL')
  secondProc.close(null)
  await assert.rejects(second)
  await releasing
}))

test('楽器を切り替えて戻した後の追加形式は、表示中の楽器の MusicXML から作る', withMain(async (main) => {
  // Arrange: StemCacheBug の反例 Transcribe(guitar) → Transcribe(piano) → Switch(guitar) → Export
  const input = main.makeInput()
  await separate(main, input)
  const guitar = await transcribeStem(main, input, 'guitar')
  await transcribeStem(main, input, 'piano')
  main.dialog.savePath = path.join(main.workDir, 'out.txt')

  // Act
  const pending = main.invoke('export-extra', input, 'jianpu', null, 'out.txt', 'guitar')
  await new Promise((resolve) => setImmediate(resolve))
  const renderProc = main.spawned.at(-1)
  renderProc.succeed()
  await pending

  // Assert
  assert.equal(renderProc.args[renderProc.args.indexOf('--from-musicxml') + 1], guitar.paths.musicxml)
}))

test('後始末で止められた分離の失敗処理は、後続の分離が登録したキャッシュを消さない', withMain(async (main) => {
  // Arrange: SeparationOwnerBug の反例 A_Start → Cleanup → B_Start → B_Done → A_LateClose
  const input = main.makeInput()
  const first = main.invoke('separate-audio', input, 'a')
  await Promise.resolve()
  const firstProc = main.spawned.at(-1)
  main.emitApp('before-quit')
  await separate(main, input)

  // Act
  firstProc.close(null)
  await assert.rejects(first)

  // Assert
  const result = await transcribeStem(main, input, 'guitar')
  assert.equal(result.stem, 'guitar')
}))

test('子プロセスの一時領域は追跡中ルート配下に置き、release-input で一緒に消える', withMain(async (main) => {
  // Arrange
  const input = main.makeInput()
  const sepProc = await separate(main, input)
  const pending = main.invoke('transcribe-stem', input, 'guitar', 'Song', {}, 't1')
  const proc = main.spawned.at(-1)
  const outDir = path.dirname(proc.args[proc.args.indexOf('-o') + 1])
  const sepDir = sepProc.args[sepProc.args.indexOf('--out-dir') + 1]

  // Act
  const childTmp = proc.options.env.TMPDIR
  proc.succeed()
  await pending

  // Assert: SIGKILL で Python の finally が走らなくても、アプリ側の解放で消える場所にある
  assert.equal(path.dirname(childTmp), outDir)
  assert.equal(proc.options.env.TEMP, childTmp)
  assert.equal(proc.options.env.TMP, childTmp)
  assert.equal(path.dirname(sepProc.options.env.TMPDIR), sepDir)
  assert.equal(fs.statSync(childTmp).isDirectory(), true)
  await main.invoke('release-input', input)
  assert.equal(fs.existsSync(childTmp), false)
}))

test('追加形式のフォールバック再採譜は、終了時に自分の一時ルートを残さない', withMain(async (main) => {
  // Arrange
  const input = main.makeInput()
  main.dialog.savePath = path.join(main.workDir, 'out.txt')

  // Act
  const pending = main.invoke('export-extra', input, 'jianpu', null, 'out.txt', 'guitar')
  await new Promise((resolve) => setImmediate(resolve))
  const proc = main.spawned.at(-1)
  const tmpRoot = path.dirname(proc.args[proc.args.indexOf('-o') + 1])
  proc.succeed()
  await pending

  // Assert
  assert.equal(fs.existsSync(tmpRoot), false)
  assert.equal(fs.existsSync(main.dialog.savePath), true)
}))
