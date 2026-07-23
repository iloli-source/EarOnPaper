// 外部デバッグ EOP-DEBUG-20260721-001 のアプリ側修正で共通化した純関数群。
// クロスプラットフォーム・パス検証・実行ファイル解決・入力検証をここへ集約し、
// Node標準の node:test で単体検証できるよう副作用のない関数として実装する。
// 参照: docs/debug/EOP-DEBUG-20260721-001.md（3.2/3.3/3.4/3.6/3.14/3.15/3.16/3.19/3.20）

const path = require('path')
const fs = require('fs')
const { pathToFileURL } = require('url')

// 採譜入力として許可する音声拡張子(小文字・ドット付き)。UIフィルタではなくIPC境界の検証に使う(3.16)
const AUDIO_EXTENSIONS = ['.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aiff', '.aif', '.aac', '.opus', '.mp4']
// アプリが生成し、保存/外部オープンを許可する成果物の拡張子(3.14/3.15)
const OUTPUT_EXTENSIONS = ['.pdf', '.musicxml', '.mid']
const MAX_TITLE_LEN = 200

// 3.3: Windows(\)/POSIX(/) 双方の区切りに対応した表示用basename
function basenameForDisplay(filePath) {
  if (typeof filePath !== 'string') return ''
  const parts = filePath.split(/[\\/]/)
  return parts[parts.length - 1] || ''
}

// 3.4: 空白/#/?/非ASCII/ドライブ表記を安全に符号化した file:// URL
function filePathToUrl(filePath) {
  return pathToFileURL(filePath).href
}

// 3.20/3.14/3.15: 区切り境界を理解した包含判定。rootDir 直下(サブ含む)かつ許可拡張子のみ真。
// 文字列prefix方式(/tmp/job で /tmp/job-evil を誤許可)を避けるため path.relative を使う。
function isManagedOutput(rootDir, filePath, allowedExts = OUTPUT_EXTENSIONS) {
  if (typeof rootDir !== 'string' || typeof filePath !== 'string' || rootDir === '') return false
  const ext = path.extname(filePath).toLowerCase()
  if (!allowedExts.includes(ext)) return false
  const rel = path.relative(rootDir, filePath)
  if (rel === '' || rel.startsWith('..') || path.isAbsolute(rel)) return false
  return true
}

// 3.16: 拡張子allowlistによる音声入力判定(実ファイル判定は呼び出し側で stat.isFile() を併用)
function isAllowedAudioInput(filePath) {
  if (typeof filePath !== 'string') return false
  return AUDIO_EXTENSIONS.includes(path.extname(filePath).toLowerCase())
}

// 3.2: OS別のPython実行ファイル候補。環境変数指定→仮想環境→PATHコマンドの順。
function pythonCandidates(engineDir, env = process.env, platform = process.platform) {
  const cands = []
  if (env && env.EARPIPE_PYTHON) cands.push(env.EARPIPE_PYTHON)
  if (platform === 'win32') {
    cands.push(path.win32.join(engineDir, '.venv', 'Scripts', 'python.exe'))
  } else {
    cands.push(path.posix.join(engineDir, '.venv', 'bin', 'python'))
  }
  cands.push(platform === 'win32' ? 'python.exe' : 'python3', 'python')
  return cands
}

// 3.2: 実在する絶対パスを優先し、無ければコマンド名(PATH解決)へフォールバック。
function resolveExecutable(candidates, existsFn = fs.existsSync) {
  let commandFallback = null
  for (const c of candidates) {
    if (path.isAbsolute(c)) {
      if (existsFn(c)) return c
    } else if (commandFallback === null) {
      commandFallback = c
    }
  }
  return commandFallback || candidates[candidates.length - 1]
}

// 3.6: basic-pitch(poly)用Pythonの候補。存在確認して見つかった時だけ設定する運用。
function basicPitchPythonCandidates(engineDir, env = process.env, platform = process.platform) {
  const cands = []
  if (env && env.EARPIPE_BP_PYTHON) cands.push(env.EARPIPE_BP_PYTHON)
  const aiEars = path.resolve(engineDir, '..', '..', 'tools', 'ai-ears')
  if (platform === 'win32') {
    cands.push(path.win32.join(engineDir, '.venv312', 'Scripts', 'python.exe'))
    cands.push(path.win32.join(aiEars, '.venv312', 'Scripts', 'python.exe'))
  } else {
    cands.push(path.posix.join(engineDir, '.venv312', 'bin', 'python3.12'))
    cands.push(path.posix.join(aiEars, '.venv312', 'bin', 'python'))
  }
  return cands
}

// 3.6: 実在する最初のパスを返す。無ければ null(＝環境変数を強制せずエンジンの自動探索に委ねる)。
function resolveExistingPath(candidates, existsFn = fs.existsSync) {
  for (const c of candidates) {
    if (typeof c === 'string' && existsFn(c)) return c
  }
  return null
}

// 3.19: CLIタイトルの上限クランプ(引数・ログ・PDFメタの肥大化防止)
function clampTitle(title, max = MAX_TITLE_LEN) {
  return String(title == null ? '' : title).slice(0, max)
}

// ==== #128 URL取り込み(yt-dlp・完全ローカル実行) ====

// #128: 取り込み対象URLの検証。http(s)かつホスト名ありのみ許可
// (file:/javascript:等の危険スキームとローカルパス偽装をIPC境界で拒否する)
function isAllowedMediaUrl(url) {
  if (typeof url !== 'string' || url === '') return false
  let parsed
  try {
    parsed = new URL(url)
  } catch {
    return false
  }
  return (parsed.protocol === 'https:' || parsed.protocol === 'http:') && parsed.hostname !== ''
}

// #128: yt-dlp引数の組み立て(純関数・シェル非経由のspawn配列用)。
// --no-playlist は常に固定(プレイリスト一括DLを構造的に不可能にする)。
// 音声はエンジン対応形式のm4aへ抽出し、確定した保存先パスをstdoutに印字させる。
function buildYtDlpArgs(url, outDir) {
  return [
    '--no-playlist',
    '-f', 'bestaudio/best',
    '-x', '--audio-format', 'm4a',
    '-o', `${outDir}/%(title)s.%(ext)s`,
    '--no-simulate',
    '--print', 'after_move:filepath',
    url,
  ]
}

// #128: yt-dlp実行ファイル候補。環境変数→Homebrew(AppleSilicon/Intel)→PATHの順
// (pythonCandidates/resolveExecutable と同パターン)。
function ytDlpCandidates(env = process.env) {
  const cands = []
  if (env && env.EARPIPE_YTDLP) cands.push(env.EARPIPE_YTDLP)
  cands.push('/opt/homebrew/bin/yt-dlp', '/usr/local/bin/yt-dlp', 'yt-dlp')
  return cands
}

module.exports = {
  AUDIO_EXTENSIONS,
  OUTPUT_EXTENSIONS,
  MAX_TITLE_LEN,
  basenameForDisplay,
  filePathToUrl,
  isManagedOutput,
  isAllowedAudioInput,
  pythonCandidates,
  resolveExecutable,
  basicPitchPythonCandidates,
  resolveExistingPath,
  clampTitle,
  isAllowedMediaUrl,
  buildYtDlpArgs,
  ytDlpCandidates,
}
