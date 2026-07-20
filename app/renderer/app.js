/* EarOnPaper Renderer */

let selectedEngine = 'mono'

document.querySelectorAll('.engine-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.engine-btn').forEach(b => b.classList.remove('active'))
    btn.classList.add('active')
    selectedEngine = btn.dataset.engine
  })
})

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
    const name = filePath.split('/').pop()
    startTranscribe(filePath, name)
  }
}

// ===== PROCESSING =====

const processingFile = document.getElementById('processing-file')
const progressLog = document.getElementById('progress-log')

async function startTranscribe(filePath, fileName) {
  processingFile.textContent = fileName
  progressLog.textContent = ''
  showState('processing')

  // 進捗ログ受信
  if (removeProgressListener) removeProgressListener()
  removeProgressListener = window.earpipe.onProgress((line) => {
    progressLog.textContent += line + '\n'
    progressLog.scrollTop = progressLog.scrollHeight
  })

  try {
    const result = await window.earpipe.transcribe(filePath, selectedEngine)
    if (removeProgressListener) {
      removeProgressListener()
      removeProgressListener = null
    }
    currentResult = result
    showResult(result)
  } catch (err) {
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
    embed.src = `file://${result.paths.pdf}`
    embed.type = 'application/pdf'
    scorePanel.innerHTML = ''
    scorePanel.appendChild(embed)
  }

  showState('done')
}

// エクスポートボタン
document.getElementById('btn-export-pdf').addEventListener('click', async () => {
  if (!currentResult?.paths?.pdf) return
  const name = currentResult.paths.pdf.split('/').pop()
  await window.earpipe.saveFile(currentResult.paths.pdf, 'pdf', name)
})

document.getElementById('btn-export-musicxml').addEventListener('click', async () => {
  if (!currentResult?.paths?.musicxml) return
  const name = currentResult.paths.musicxml.split('/').pop()
  await window.earpipe.saveFile(currentResult.paths.musicxml, 'musicxml', name)
})

document.getElementById('btn-export-midi').addEventListener('click', async () => {
  if (!currentResult?.paths?.midi) return
  const name = currentResult.paths.midi.split('/').pop()
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
