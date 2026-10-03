'use strict'

// main.js を Electron 無しで読み込むためのテストハーネス。
// electron / child_process.spawn / process.kill を偽物に差し替え、子プロセスの終了と
// fs.promises.stat の復帰タイミングをテスト側から制御する(実時間の sleep は使わない)。

const { EventEmitter } = require('node:events')
const childProcess = require('node:child_process')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')

const appDir = path.resolve(__dirname, '..', '..')
const mainPath = path.join(appDir, 'main.js')
const electronPath = require.resolve('electron', { paths: [appDir] })
const FAKE_PID_BASE = 9000000

function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
}

function argAfter(args, flag) {
  const i = args.indexOf(flag)
  return i >= 0 ? args[i + 1] : null
}

// 偽エンジン: 引数から出力先を読み取り、成功時は非空の成果物を実際に書き出す。
function outputsOf(args) {
  const outs = ['-o', '--pdf', '--midi', '--tab', '--chord-chart']
    .map((flag) => argAfter(args, flag)).filter(Boolean)
  for (const flag of ['--emit', '--format', '--analysis']) {
    const spec = argAfter(args, flag)
    if (spec) outs.push(spec.slice(spec.indexOf('=') + 1))
  }
  return outs
}

function createFakeProc(pid, command, args, options) {
  const proc = new EventEmitter()
  proc.pid = pid
  proc.exitCode = null
  proc.command = command
  proc.args = args
  proc.options = options
  proc.killedBy = null
  proc.stdout = new EventEmitter()
  proc.stderr = new EventEmitter()
  proc.close = (code) => {
    proc.exitCode = code === null ? 137 : code
    proc.emit('close', code)
  }
  proc.succeed = (json = { n_notes: 1, engine: 'fake' }) => {
    const payload = { ...json }
    const sepDir = argAfter(args, '--out-dir')
    if (sepDir) {
      payload.stems = {}
      for (const stem of ['guitar', 'piano']) {
        const wav = path.join(sepDir, `${stem}.wav`)
        fs.writeFileSync(wav, 'RIFF')
        payload.stems[stem] = wav
      }
    }
    for (const out of outputsOf(args)) fs.writeFileSync(out, 'x')
    proc.stdout.emit('data', Buffer.from(JSON.stringify(payload)))
    proc.close(0)
  }
  return proc
}

function loadMain() {
  const handlers = new Map()
  const appEvents = new Map()
  const spawned = []
  const kills = []
  const dialog = {
    savePath: null,
    showSaveDialog: async () => (
      dialog.savePath ? { canceled: false, filePath: dialog.savePath } : { canceled: true }
    ),
    showOpenDialog: async () => ({ canceled: true, filePaths: [] }),
  }
  const electron = {
    app: {
      whenReady: () => new Promise(() => {}),
      on: (name, fn) => { appEvents.set(name, fn) },
      quit: () => {},
    },
    BrowserWindow: class { static getAllWindows() { return [] } },
    ipcMain: { handle: (name, fn) => { handlers.set(name, fn) } },
    dialog,
    shell: { openPath: async () => '' },
  }

  const original = {
    spawn: childProcess.spawn,
    kill: process.kill,
    stat: fs.promises.stat,
    electron: require.cache[electronPath],
  }
  childProcess.spawn = (command, args, options) => {
    const proc = createFakeProc(FAKE_PID_BASE + spawned.length, command, args, options)
    spawned.push(proc)
    return proc
  }
  // 偽PIDへの kill だけを記録する。実プロセスへは決して転送しない。
  process.kill = (pid, signal) => {
    const proc = spawned.find((p) => p.pid === Math.abs(pid))
    if (!proc) throw new Error(`テスト外のPIDへのkillは禁止: ${pid}`)
    proc.killedBy = signal
    kills.push(proc)
    return true
  }
  require.cache[electronPath] = {
    id: electronPath, filename: electronPath, loaded: true, exports: electron,
  }
  delete require.cache[mainPath]
  require(mainPath)

  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'earpaper-test-'))
  const sender = { isDestroyed: () => false, send: () => {} }

  return {
    spawned,
    kills,
    dialog,
    workDir,
    invoke: (name, ...args) => handlers.get(name)({ sender }, ...args),
    emitApp: (name) => appEvents.get(name)(),
    makeInput(name = 'song.wav') {
      const file = path.join(workDir, name)
      fs.writeFileSync(file, 'RIFF')
      return file
    },
    // matcher に合うパスの fs.promises.stat を、release() が呼ばれるまで保留する。
    gateStat(matcher) {
      const reached = deferred()
      const gate = deferred()
      fs.promises.stat = async (p, ...rest) => {
        if (matcher(String(p))) {
          reached.resolve()
          await gate.promise
        }
        return original.stat(p, ...rest)
      }
      return { reached: reached.promise, release: () => gate.resolve() }
    },
    dispose() {
      try { appEvents.get('before-quit')() } catch { /* best effort */ }
      childProcess.spawn = original.spawn
      process.kill = original.kill
      fs.promises.stat = original.stat
      if (original.electron) require.cache[electronPath] = original.electron
      else delete require.cache[electronPath]
      delete require.cache[mainPath]
      fs.rmSync(workDir, { recursive: true, force: true })
    },
  }
}

module.exports = { loadMain }
