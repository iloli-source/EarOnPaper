// 外部デバッグ EOP-DEBUG-20260721-001 のアプリ側修正で共通化した純関数群。
// クロスプラットフォーム・パス検証・実行ファイル解決・入力検証をここへ集約し、
// Node標準の node:test で単体検証できるよう副作用のない関数として実装する。
// 参照: docs/debug/EOP-DEBUG-20260721-001.md（3.2/3.3/3.4/3.6/3.14/3.15/3.16/3.19/3.20）

const path = require('path')
const fs = require('fs')
const net = require('net')
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
  // 既存ファイルは実体パスを使う。字面上はroot配下でも、symlink経由で
  // root外を指すファイルを「管理下」と誤認しないため。
  let canonicalRoot = path.resolve(rootDir)
  let canonicalFile = path.resolve(filePath)
  try { canonicalRoot = fs.realpathSync.native(rootDir) } catch { /* 未作成rootはresolveで判定 */ }
  try { canonicalFile = fs.realpathSync.native(filePath) } catch { /* 未作成fileはresolveで判定 */ }
  const rel = path.relative(canonicalRoot, canonicalFile)
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

// GUIから渡されるBPM範囲をCLIへ渡す前に正規化する。
// 20〜400BPMに制限し、非有限値・逆転範囲・巨大整数を拒否する。
function normalizeBpmRange(value, min = 20, max = 400) {
  if (typeof value !== 'string' || !/^\d{1,3}-\d{1,3}$/.test(value)) return null
  const [lo, hi] = value.split('-').map(Number)
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) return null
  if (lo < min || hi > max || hi <= lo) return null
  return `${lo}-${hi}`
}


// 環境変数由来の数値を安全な整数範囲へ閉じ込める。Infinity/NaN/負数や
// 桁違いの設定値は採用せず、既定値へ戻す。
function boundedPositiveInt(value, fallback, min = 1, max = Number.MAX_SAFE_INTEGER) {
  const parsed = Number(value)
  if (!Number.isSafeInteger(parsed) || parsed < min || parsed > max) return fallback
  return parsed
}


// 入力に紐づく一時ルートのうち、今回削除すべきものを選ぶ。
// URL取り込み元は再分離の直前だけ保持し、入力切替・終了では削除する。
function selectRootsForRelease(roots, sourceRoots, preserveSource = false) {
  const all = roots ? [...roots] : []
  if (!preserveSource) return all
  const sources = sourceRoots || new Set()
  return all.filter((root) => !sources.has(root))
}

function normalizeEngine(value) {
  return ['auto', 'mono', 'poly'].includes(value) ? value : 'auto'
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
  if ((parsed.protocol !== 'https:' && parsed.protocol !== 'http:') || parsed.hostname === '') return false
  if (parsed.username || parsed.password) return false
  // ローカル/プライベートネットワークへの到達は、動画取り込み機能の目的外。
  // 悪意あるリンクによるlocalhost・ルータ管理画面等へのアクセスを明示的に拒否する。
  const host = parsed.hostname.replace(/^\[|\]$/g, '').replace(/\.+$/, '').toLowerCase()
  if (host === 'localhost' || host.endsWith('.localhost')
      || host.endsWith('.local') || host === 'home.arpa' || host.endsWith('.home.arpa')) return false
  const family = net.isIP(host)
  if (family === 4) {
    const octets = host.split('.').map(Number)
    const [a, b] = octets
    if (a === 0 || a === 10 || a === 127 || a >= 224) return false
    if (a === 169 && b === 254) return false
    if (a === 172 && b >= 16 && b <= 31) return false
    if (a === 192 && b === 168) return false
    if (a === 100 && b >= 64 && b <= 127) return false
    // IANA special-purpose/documentation/benchmark ranges。外部メディア取得先として不要。
    if (a === 192 && b === 0) return false
    if (a === 198 && (b === 18 || b === 19 || b === 51)) return false
    if (a === 203 && b === 0) return false
  } else if (family === 6) {
    if (host === '::1' || host === '::') return false
    if (/^(fc|fd)/.test(host) || /^fe[89ab]/.test(host) || /^ff/.test(host)) return false
    // IPv4-mapped/compatible IPv6は表記揺れが多く、ローカルIPv4を隠せるため直指定を拒否。
    if (host.startsWith('::ffff:') || /^::[0-9a-f]/.test(host)) return false
    if (host.startsWith('2001:db8:')) return false
  }
  return true
}

// #128: yt-dlp引数の組み立て(純関数・シェル非経由のspawn配列用)。
// --no-playlist は常に固定(プレイリスト一括DLを構造的に不可能にする)。
// 音声はエンジン対応形式のm4aへ抽出し、確定した保存先パスをstdoutに印字させる。
function buildYtDlpArgs(url, outDir) {
  return [
    '--no-playlist',
    '--max-filesize', '4G',
    '-f', 'bestaudio/best',
    '-x', '--audio-format', 'm4a',
    '-o', path.join(outDir, '%(title)s.%(ext)s'),
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
  normalizeBpmRange,
  boundedPositiveInt,
  normalizeEngine,
  selectRootsForRelease,
  isAllowedMediaUrl,
  buildYtDlpArgs,
  ytDlpCandidates,
}
