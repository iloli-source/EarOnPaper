// platform-utils.js の純関数の単体テスト(node:test・依存なし)。
// 外部デバッグ EOP-DEBUG-20260721-001 の 3.2/3.3/3.4/3.6/3.14/3.15/3.16/3.19/3.20 に対応。
const { test } = require('node:test')
const assert = require('node:assert')
const path = require('path')
const pu = require('../platform-utils')

// 3.3 js_basename_cross_platform
test('basenameForDisplay: POSIXとWindows双方の区切りを処理', () => {
  assert.strictEqual(pu.basenameForDisplay('/a/b/song.wav'), 'song.wav')
  assert.strictEqual(pu.basenameForDisplay('C:\\a\\b\\song.wav'), 'song.wav')
  assert.strictEqual(pu.basenameForDisplay('a/b\\song.mp3'), 'song.mp3')
  assert.strictEqual(pu.basenameForDisplay('song.flac'), 'song.flac')
  assert.strictEqual(pu.basenameForDisplay(''), '')
  assert.strictEqual(pu.basenameForDisplay(null), '')
})

// 3.4 js_file_url_encoding
test('filePathToUrl: 空白/#/? を符号化した file URL', () => {
  const u = pu.filePathToUrl('/tmp/a b/c#d?e.pdf')
  assert.ok(u.startsWith('file://'))
  assert.ok(u.includes('%20'))  // 空白
  assert.ok(u.includes('%23'))  // #
  assert.ok(!u.includes('#d'))  // フラグメント誤解釈しない
})

// 3.14/3.15/3.20 js_path_containment
test('isManagedOutput: 区切り境界を理解した包含判定(prefix偽装を拒否)', () => {
  const root = path.join(path.sep, 'tmp', 'job')
  assert.strictEqual(pu.isManagedOutput(root, path.join(root, 'out.pdf')), true)
  assert.strictEqual(pu.isManagedOutput(root, path.join(root, 'sub', 'out.musicxml')), true)
  // 同名prefix偽装 /tmp/job-evil は拒否
  assert.strictEqual(pu.isManagedOutput(root, path.join(path.sep, 'tmp', 'job-evil', 'out.pdf')), false)
  // 許可外拡張子は拒否
  assert.strictEqual(pu.isManagedOutput(root, path.join(root, 'evil.exe')), false)
  // ルート自身(ファイルでない)は拒否
  assert.strictEqual(pu.isManagedOutput(root, root), false)
  // 親方向(..)は拒否
  assert.strictEqual(pu.isManagedOutput(root, path.join(root, '..', 'out.pdf')), false)
})

// 3.16 js_audio_extension_allowlist
test('isAllowedAudioInput: 音声拡張子のみ許可(大文字も)', () => {
  assert.strictEqual(pu.isAllowedAudioInput('/x/y.WAV'), true)
  assert.strictEqual(pu.isAllowedAudioInput('/x/y.mp3'), true)
  assert.strictEqual(pu.isAllowedAudioInput('/x/y.aif'), true)
  assert.strictEqual(pu.isAllowedAudioInput('/x/y.txt'), false)
  assert.strictEqual(pu.isAllowedAudioInput('/x/y'), false)
  assert.strictEqual(pu.isAllowedAudioInput(null), false)
})

// 3.2 js_python_runtime_candidates
test('pythonCandidates/resolveExecutable: OS別候補と実在優先', () => {
  const win = pu.pythonCandidates('/eng', {}, 'win32')
  assert.ok(win.some(c => c.includes('Scripts') && c.endsWith('python.exe')))
  const posix = pu.pythonCandidates('/eng', {}, 'linux')
  assert.ok(posix.some(c => c.includes('/.venv/bin/python')))
  // 環境変数指定が最優先
  const withEnv = pu.pythonCandidates('/eng', { EARPIPE_PYTHON: '/custom/py' }, 'linux')
  assert.strictEqual(withEnv[0], '/custom/py')
  // 実在する絶対パスを優先、無ければコマンド名へフォールバック
  const existsNone = () => false
  const resolved = pu.resolveExecutable(['/no/py', 'python3', 'python'], existsNone)
  assert.strictEqual(resolved, 'python3')
  const existsFirst = (p) => p === '/yes/py'
  assert.strictEqual(pu.resolveExecutable(['/yes/py', 'python3'], existsFirst), '/yes/py')
})

// 3.6 basic-pitch python: 実在時のみ返す
test('resolveExistingPath: 実在する最初のパス、無ければnull', () => {
  assert.strictEqual(pu.resolveExistingPath(['/a', '/b'], () => false), null)
  assert.strictEqual(pu.resolveExistingPath(['/a', '/b'], (p) => p === '/b'), '/b')
})

// 3.19 clampTitle
test('clampTitle: 200文字上限', () => {
  assert.strictEqual(pu.clampTitle('x'.repeat(300)).length, 200)
  assert.strictEqual(pu.clampTitle('short'), 'short')
  assert.strictEqual(pu.clampTitle(null), '')
})

// ==== #128 URL取り込み(yt-dlp) ====

test('isAllowedMediaUrl: https/httpのみ許可し危険スキームを拒否', () => {
  assert.strictEqual(pu.isAllowedMediaUrl('https://www.youtube.com/watch?v=abc'), true)
  assert.strictEqual(pu.isAllowedMediaUrl('http://example.com/v'), true)
  assert.strictEqual(pu.isAllowedMediaUrl('file:///etc/passwd'), false)
  assert.strictEqual(pu.isAllowedMediaUrl('javascript:alert(1)'), false)
  assert.strictEqual(pu.isAllowedMediaUrl('ftp://example.com/a'), false)
  assert.strictEqual(pu.isAllowedMediaUrl('https://'), false)
  assert.strictEqual(pu.isAllowedMediaUrl('not a url'), false)
  assert.strictEqual(pu.isAllowedMediaUrl(''), false)
  assert.strictEqual(pu.isAllowedMediaUrl(null), false)
})

test('buildYtDlpArgs: --no-playlist固定・音声抽出・URLは末尾', () => {
  const args = pu.buildYtDlpArgs('https://youtu.be/x', '/tmp/dl')
  assert.ok(args.includes('--no-playlist'), 'プレイリスト展開は常に禁止')
  assert.ok(args.includes('-x'), '音声抽出')
  assert.ok(args.includes('m4a'), 'm4aへ変換(エンジン対応形式)')
  assert.ok(args.some((a) => a.startsWith('/tmp/dl/')), '出力先が指定dir配下')
  assert.strictEqual(args[args.length - 1], 'https://youtu.be/x', 'URLが最終引数')
})

test('ytDlpCandidates: 環境変数が最優先・Homebrewパス・PATHフォールバック', () => {
  const withEnv = pu.ytDlpCandidates({ EARPIPE_YTDLP: '/custom/yt-dlp' })
  assert.strictEqual(withEnv[0], '/custom/yt-dlp')
  const noEnv = pu.ytDlpCandidates({})
  assert.ok(noEnv.includes('/opt/homebrew/bin/yt-dlp'), 'Homebrew(Apple Silicon)候補')
  assert.strictEqual(noEnv[noEnv.length - 1], 'yt-dlp', 'PATH解決のコマンド名で終わる')
})
