/* EarOnPaper Renderer */

// ステージ定義
const STAGES = [
  { index: 0, label: '音声読み込み中...', keywords: ['librosa', 'loading', 'reading', 'audio'] },
  { index: 1, label: '音高検出中...',     keywords: ['detect', 'pyin', 'adaptive', 'pitch', 'onset'] },
  { index: 2, label: 'リズム量子化中...', keywords: ['quantize', 'rhythm', 'tempo', 'meter', 'beat'] },
  { index: 3, label: '楽譜生成中...',     keywords: ['score', 'notate', 'spell', 'key', 'measure'] },
  { index: 4, label: 'PDF書き出し中...', keywords: ['engrave', 'pdf', 'verovio', 'svg'] },
]

let currentStage = 0
let stageTimers = []
const STAGE_DELAYS = [0, 4000, 14000, 24000, 34000] // ms

function clearStageTimers() {
  stageTimers.forEach(clearTimeout)
  stageTimers = []
}

// 譜面タイトル: 拡張子と末尾のフォーマット表記(mp3等)を除いた曲名にする
function cleanTitle(fileName) {
  const base = fileName.replace(/\.[^.]+$/, '')
  const cleaned = base.replace(/[\s_-]*(mp3|wav|m4a|flac|aiff|ogg)$/i, '').trim()
  return cleaned || base
}

function setStage(index) {
  if (index <= currentStage && currentStage > 0) return
  currentStage = index

  const label = document.getElementById('stage-label')
  if (label) label.textContent = STAGES[index]?.label ?? '処理中...'

  const bar = document.getElementById('stage-progress-bar')
  if (bar) bar.style.width = `${(index / (STAGES.length - 1)) * 85}%`

  document.querySelectorAll('.stage-step').forEach((el, i) => {
    el.classList.remove('active', 'done')
    if (i < index) el.classList.add('done')
    else if (i === index) el.classList.add('active')
  })

  document.querySelectorAll('.stage-connector').forEach((el, i) => {
    el.classList.toggle('done', i < index)
  })
}

function detectStageFromLog(line) {
  const lower = line.toLowerCase()
  for (let i = STAGES.length - 1; i >= 0; i--) {
    if (STAGES[i].keywords.some(k => lower.includes(k))) {
      return i
    }
  }
  return -1
}

const NOTE_CHARS = ['♩','♪','♫','♬','𝄞','♩','♪']
const NOTE_COLORS = [
  'oklch(78% 0.22 55)', 'oklch(74% 0.22 140)', 'oklch(70% 0.21 250)',
  'oklch(74% 0.22 320)', 'oklch(76% 0.22 20)', 'oklch(76% 0.19 180)',
]

function spawnFlyingNotes(container) {
  container.innerHTML = ''
  const W = container.offsetWidth / 2 || 400
  const H = container.offsetHeight / 2 || 300
  for (let i = 0; i < 22; i++) {
    const el = document.createElement('div')
    el.className = 'fly-note'
    el.textContent = NOTE_CHARS[i % NOTE_CHARS.length]
    el.style.color = NOTE_COLORS[i % NOTE_COLORS.length]
    el.style.filter = `drop-shadow(0 0 8px ${NOTE_COLORS[i % NOTE_COLORS.length]})`

    const side = i % 4
    let sx, sy
    if (side === 0) { sx = (Math.random() * 2 - 1) * W; sy = -(H + 40) }
    else if (side === 1) { sx = (Math.random() * 2 - 1) * W; sy = H + 40 }
    else if (side === 2) { sx = -(W + 40); sy = (Math.random() * 2 - 1) * H }
    else { sx = W + 40; sy = (Math.random() * 2 - 1) * H }

    el.style.setProperty('--sx', `${sx}px`)
    el.style.setProperty('--sy', `${sy}px`)
    el.style.setProperty('--sr', `${(Math.random() - 0.5) * 60}deg`)
    el.style.setProperty('--er', `${(Math.random() - 0.5) * 90}deg`)
    el.style.setProperty('--dur', `${1.8 + Math.random() * 2.2}s`)
    el.style.setProperty('--del', `${Math.random() * 3}s`)
    container.appendChild(el)
  }
}

function playChime() {
  try {
    const ctx = new AudioContext()
    const freqs = [523.25, 659.25, 783.99] // C5, E5, G5
    freqs.forEach((freq, i) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.frequency.value = freq
      osc.type = 'sine'
      const t = ctx.currentTime + i * 0.06
      gain.gain.setValueAtTime(0, t)
      gain.gain.linearRampToValueAtTime(0.18, t + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.8)
      osc.start(t)
      osc.stop(t + 0.8)
    })
  } catch {}
}


const states = {
  idle: document.getElementById('state-idle'),
  processing: document.getElementById('state-processing'),
  done: document.getElementById('state-done'),
  error: document.getElementById('state-error'),
}

let currentResult = null
let removeProgressListener = null

function showState(name) {
  Object.values(states).forEach(el => el.classList.remove('active'))
  states[name].classList.add('active')
}

// ===== IDLE =====

const dropzone = document.getElementById('dropzone')
const btnOpen = document.getElementById('btn-open')

dropzone.addEventListener('dragover', (e) => {
  e.preventDefault()
  dropzone.classList.add('over')
})

dropzone.addEventListener('dragleave', () => {
  dropzone.classList.remove('over')
})

dropzone.addEventListener('drop', (e) => {
  e.preventDefault()
  dropzone.classList.remove('over')
  const file = e.dataTransfer.files[0]
  if (file) {
    const filePath = window.earpipe.getPathForFile(file)
    startTranscribe(filePath, file.name)
  }
})

dropzone.addEventListener('click', (e) => {
  if (e.target === btnOpen || btnOpen.contains(e.target)) return
  triggerFileOpen()
})

btnOpen.addEventListener('click', (e) => {
  e.stopPropagation()
  triggerFileOpen()
})

async function triggerFileOpen() {
  const filePath = await window.earpipe.openFileDialog()
  if (filePath) {
    const name = window.earpipe.basenameForDisplay(filePath)
    startTranscribe(filePath, name)
  }
}

// ===== PROCESSING =====


async function startTranscribe(filePath, fileName) {
  const title = cleanTitle(fileName)
  document.getElementById('processing-file').textContent = title
  currentStage = -1
  setStage(0)
  showState('processing')
  const notesBg = document.getElementById('notes-bg')
  if (notesBg) spawnFlyingNotes(notesBg)

  // 時間ベースでステージを自動進行。完了/失敗時に必ず全部止める
  // (単一ハンドル保持だと残ったタイマーが完了後に発火しステージ表示が巻き戻る)
  clearStageTimers()
  STAGE_DELAYS.forEach((delay, i) => {
    if (i === 0) return
    stageTimers.push(setTimeout(() => setStage(i), delay))
  })

  if (removeProgressListener) removeProgressListener()
  // 3.5: 実処理ログからステージを検出してUIへ反映(タイマー任せの見かけ進捗を是正)
  removeProgressListener = window.earpipe.onProgress((msg) => {
    const stage = detectStageFromLog(msg)
    if (stage >= 0) setStage(stage)
  })

  try {
    const result = await window.earpipe.transcribe(filePath, 'auto', title)
    clearStageTimers()
    if (removeProgressListener) {
      removeProgressListener()
      removeProgressListener = null
    }
    currentResult = result
    // 完了: バー100%→チャイム→結果表示
    const bar = document.getElementById('stage-progress-bar')
    if (bar) bar.style.width = '100%'
    document.querySelectorAll('.stage-step').forEach(el => el.classList.add('done'))
    document.querySelectorAll('.stage-connector').forEach(el => el.classList.add('done'))
    setTimeout(() => {
      playChime()
      showResult(result)
    }, 300)
  } catch (err) {
    clearStageTimers()
    if (removeProgressListener) {
      removeProgressListener()
      removeProgressListener = null
    }
    showError(err.message)
  }
}

// ===== DONE =====

const scorePanel = document.getElementById('score-panel')
const scorePlaceholder = document.getElementById('score-placeholder')

function showResult(result) {
  // 統計表示
  document.getElementById('stat-notes').textContent = result.n_notes ?? '—'
  document.getElementById('stat-bpm').textContent =
    result.bpm ? `${Math.round(result.bpm)} BPM` : '—'
  document.getElementById('stat-engine').textContent = result.engine ?? '—'
  const cents = result.tuning_offset_cents
  document.getElementById('stat-tuning').textContent =
    cents != null ? `${cents > 0 ? '+' : ''}${cents.toFixed(1)} cents` : '—'

  // PDF表示
  if (result.paths?.pdf) {
    const embed = document.createElement('embed')
    embed.src = window.earpipe.filePathToUrl(result.paths.pdf)
    embed.type = 'application/pdf'
    scorePanel.innerHTML = ''
    scorePanel.appendChild(embed)
  }

  showState('done')
}

// エクスポートボタン
document.getElementById('btn-export-pdf').addEventListener('click', async () => {
  if (!currentResult?.paths?.pdf) return
  const name = window.earpipe.basenameForDisplay(currentResult.paths.pdf)
  await window.earpipe.saveFile(currentResult.paths.pdf, 'pdf', name)
})

document.getElementById('btn-export-musicxml').addEventListener('click', async () => {
  if (!currentResult?.paths?.musicxml) return
  const name = window.earpipe.basenameForDisplay(currentResult.paths.musicxml)
  await window.earpipe.saveFile(currentResult.paths.musicxml, 'musicxml', name)
})

document.getElementById('btn-export-midi').addEventListener('click', async () => {
  if (!currentResult?.paths?.midi) return
  const name = window.earpipe.basenameForDisplay(currentResult.paths.midi)
  await window.earpipe.saveFile(currentResult.paths.midi, 'mid', name)
})

document.getElementById('btn-retry').addEventListener('click', () => {
  currentResult = null
  scorePanel.innerHTML = '<div class="score-placeholder" id="score-placeholder"><span>📄</span><span>楽譜を読み込み中...</span></div>'
  showState('idle')
})

// ===== ERROR =====

function showError(message) {
  document.getElementById('error-message').textContent = message
  showState('error')
}

document.getElementById('btn-copy-error').addEventListener('click', () => {
  const text = document.getElementById('error-message').textContent
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById('btn-copy-error')
    btn.textContent = 'コピーしました'
    setTimeout(() => { btn.textContent = 'エラーをコピー' }, 2000)
  })
})

document.getElementById('btn-error-back').addEventListener('click', () => {
  showState('idle')
})

// E2Eテスト専用フック(#61): 実UIのドラッグ&ドロップは Electron の webUtils 経由でしか
// 実パスを得られず Playwright から合成できないため、ドロップと同一の入口 startTranscribe を
// テストから起動できるよう公開する。本番動作には影響しない(呼ばれなければ不活性)。
window.__earpipeTest = { startTranscribe }
