/* EarOnPaper Renderer — 分離→楽器選択→選択楽器のみ採譜 */

// ステージ定義（採譜フェーズの進捗表示に使う）
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
// 中央への収束速度の倍率(ステージ毎に段階的に速く。小さいほど速い)
const STAGE_SPEED = [1.0, 0.8, 0.62, 0.48, 0.36]

function clearStageTimers() {
  stageTimers.forEach(clearTimeout)
  stageTimers = []
}

function startStageTimers() {
  clearStageTimers()
  STAGE_DELAYS.forEach((delay, i) => {
    if (i === 0) return
    stageTimers.push(setTimeout(() => setStage(i), delay))
  })
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

  // 収束アニメの速度をステージ毎に上げる(段階的に速くなる)
  const notesBg = document.getElementById('notes-bg')
  if (notesBg) notesBg.style.setProperty('--speed', String(STAGE_SPEED[index] ?? STAGE_SPEED[STAGE_SPEED.length - 1]))
}

// 分離フェーズなど、ステージに乗らない任意ラベルを出す
function setPhaseLabel(text) {
  const label = document.getElementById('stage-label')
  if (label) label.textContent = text
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
  container.style.setProperty('--speed', String(STAGE_SPEED[0]))  // 収束速度を初期化
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

// 星空を生成(処理画面の宇宙背景)。notes-bgとは別レイヤーなので音符の再生成で消えない。
function spawnStars(container) {
  container.innerHTML = ''
  const N = 90
  for (let i = 0; i < N; i++) {
    const s = document.createElement('div')
    s.className = 'star'
    const size = 0.7 + Math.random() * 1.9
    s.style.width = `${size}px`
    s.style.height = `${size}px`
    s.style.left = `${Math.random() * 100}%`
    s.style.top = `${Math.random() * 100}%`
    if (i % 7 === 0) s.style.background = 'oklch(85% 0.09 250)'  // まれに青白い星
    if (size > 2) s.style.boxShadow = `0 0 ${size * 2}px oklch(90% 0.05 250 / 0.7)`  // 大きい星は淡いグロー
    s.style.setProperty('--tw', `${2 + Math.random() * 4}s`)
    s.style.setProperty('--twd', `${Math.random() * 4}s`)
    container.appendChild(s)
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

let currentInput = null           // 現在の入力ファイルパス
let currentTitle = ''             // 楽譜タイトル
let currentInstrument = null      // 現在選択中のステムID
let instrumentMeta = {}           // stemId -> {id,label,hasTab}
const stemResults = new Map()     // stemId -> 採譜結果(このファイル内でキャッシュ)
let currentView = 'staff'         // 'staff' | 'tab'
let currentOverrides = {}         // 任意上書き {bpmRange, beat, keyTonic, keyMode}(曲全体に適用)
let removeProgressListener = null
let flowGeneration = 0            // 古い非同期結果が新しい入力を上書きしないための世代番号
let urlGeneration = 0
let activeTranscription = null    // 重い採譜は1件ずつ。連打時は直列化する
let transcriptionGeneration = 0   // 設定変更前の採譜結果も破棄する
let progressGeneration = 0        // 別処理のstderr進捗が現在画面へ混入しないためのトークン
let activeUrlOperationToken = null // 新しい入力開始時に古いURL取得を停止する

function showState(name) {
  Object.values(states).forEach(el => el.classList.remove('active'))
  states[name].classList.add('active')
}

function nextProgressToken(kind) {
  progressGeneration += 1
  return `${kind}-${progressGeneration}`
}

function attachProgress(expectedToken) {
  if (removeProgressListener) removeProgressListener()
  removeProgressListener = window.earpipe.onProgress((payload) => {
    if (!payload || payload.token !== expectedToken || typeof payload.line !== 'string') return
    const stage = detectStageFromLog(payload.line)
    if (stage >= 0) setStage(stage)
  })
}
function detachProgress() {
  if (removeProgressListener) { removeProgressListener(); removeProgressListener = null }
}

async function cancelActiveUrlOperation() {
  const token = activeUrlOperationToken
  activeUrlOperationToken = null
  if (!token) return
  try { await window.earpipe.cancelOperation(token) } catch { /* best effort */ }
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
    startFlow(filePath, file.name)
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
    startFlow(filePath, name)
  }
}

// ===== URL取り込み(#128) =====

const btnUrl = document.getElementById('btn-url')
const urlInput = document.getElementById('url-input')

async function triggerUrlImport() {
  const url = (urlInput.value || '').trim()
  if (!url) return
  const requestId = ++urlGeneration
  await cancelActiveUrlOperation()
  // ダウンロード中も既存のPROCESSING画面で進捗を見せ、完了後にファイルフローへ合流する
  let displayHost = '指定URL'
  try { displayHost = new URL(url).hostname || displayHost } catch { /* main側でも拒否 */ }
  document.getElementById('processing-file').textContent = displayHost
  currentStage = -1
  setStage(0)
  setPhaseLabel('動画から音声を取り込み中…')
  showState('processing')
  const starfield = document.getElementById('starfield')
  if (starfield) spawnStars(starfield)
  const progressToken = nextProgressToken('url')
  activeUrlOperationToken = progressToken
  attachProgress(progressToken)
  try {
    const imported = await window.earpipe.importUrl(url, progressToken)
    if (activeUrlOperationToken === progressToken) activeUrlOperationToken = null
    if (requestId !== urlGeneration) {
      try { await window.earpipe.releaseInput(imported.path) } catch { /* best effort */ }
      return
    }
    detachProgress()
    urlInput.value = ''
    await startFlow(imported.path, imported.title)
  } catch (err) {
    if (activeUrlOperationToken === progressToken) activeUrlOperationToken = null
    if (requestId === urlGeneration) {
      detachProgress()
      showError(err.message)
    }
  }
}

btnUrl.addEventListener('click', triggerUrlImport)
urlInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') triggerUrlImport()
})

// ===== フロー: 分離 → 楽器選択 → 選択楽器のみ採譜 =====

async function startFlow(filePath, fileName) {
  const flowId = ++flowGeneration
  ++urlGeneration
  ++transcriptionGeneration
  await cancelActiveUrlOperation()
  const previousInput = currentInput
  if (previousInput && previousInput !== filePath) {
    try { await window.earpipe.releaseInput(previousInput) } catch { /* best effort */ }
  }
  if (flowId !== flowGeneration) return
  currentInput = filePath
  currentTitle = cleanTitle(fileName)
  stemResults.clear()
  currentInstrument = null

  document.getElementById('processing-file').textContent = currentTitle
  currentStage = -1
  setStage(0)
  setPhaseLabel('楽器を分離中…（少し時間がかかります）')
  showState('processing')
  const starfield = document.getElementById('starfield')
  if (starfield) spawnStars(starfield)
  const notesBg = document.getElementById('notes-bg')
  if (notesBg) spawnFlyingNotes(notesBg)
  const progressToken = nextProgressToken('separate')
  attachProgress(progressToken)

  try {
    const { instruments } = await window.earpipe.separateAudio(filePath, progressToken)
    if (flowId !== flowGeneration || currentInput !== filePath) return
    detachProgress()
    buildInstrumentButtons(instruments)
    // デフォルト=ギター。無ければ先頭。
    const def = instruments.find(i => i.id === 'guitar') || instruments[0]
    await selectInstrument(def.id, flowId)
  } catch (err) {
    if (flowId === flowGeneration) {
      detachProgress()
      showError(err.message)
    }
  }
}

function buildInstrumentButtons(instruments) {
  instrumentMeta = {}
  const box = document.getElementById('instrument-switch')
  box.innerHTML = ''
  for (const it of instruments) {
    instrumentMeta[it.id] = it
    const btn = document.createElement('button')
    btn.className = 'instr-btn'
    btn.dataset.stem = it.id
    btn.textContent = it.label
    btn.addEventListener('click', () => selectInstrument(it.id))
    box.appendChild(btn)
  }
}

function highlightInstrument(stemId) {
  document.querySelectorAll('#instrument-switch .instr-btn').forEach((b) => {
    b.classList.toggle('active', b.dataset.stem === stemId)
  })
}

async function selectInstrument(
  stemId, expectedFlow = flowGeneration, expectedTranscription = transcriptionGeneration,
) {
  if (expectedFlow !== flowGeneration || expectedTranscription !== transcriptionGeneration || !currentInput) return
  currentInstrument = stemId
  highlightInstrument(stemId)

  // 採譜済みならキャッシュを即表示（楽器切り替えは高速）
  if (stemResults.has(stemId)) {
    showInstrumentResult(stemResults.get(stemId))
    return
  }

  // 別ステムを連打されてもCPU/GPU負荷の高い採譜を並列起動しない。
  // 先行処理後、最後に選ばれたステムだけを続けて処理する。
  if (activeTranscription) {
    try { await activeTranscription } catch { /* 先行エラーは先行側で表示 */ }
    if (expectedFlow !== flowGeneration || expectedTranscription !== transcriptionGeneration
        || currentInstrument !== stemId) return
    if (stemResults.has(stemId)) {
      showInstrumentResult(stemResults.get(stemId))
      return
    }
    return selectInstrument(stemId, expectedFlow, expectedTranscription)
  }

  // 未採譜: この楽器だけ採譜する
  const meta = instrumentMeta[stemId] || { label: '楽器' }
  currentStage = -1
  setStage(0)
  setPhaseLabel(`${meta.label}を採譜中…`)
  showState('processing')
  const notesBg = document.getElementById('notes-bg')
  if (notesBg) spawnFlyingNotes(notesBg)
  startStageTimers()
  const progressToken = nextProgressToken('transcribe')
  attachProgress(progressToken)

  const inputAtStart = currentInput
  const titleAtStart = currentTitle
  const overridesAtStart = { ...currentOverrides }
  const promise = window.earpipe.transcribeStem(
    inputAtStart, stemId, titleAtStart, overridesAtStart, progressToken,
  )
  activeTranscription = promise
  try {
    const result = await promise
    if (expectedFlow !== flowGeneration || expectedTranscription !== transcriptionGeneration
        || currentInput !== inputAtStart) return
    clearStageTimers()
    detachProgress()
    stemResults.set(stemId, result)
    if (window.__earpipeTest) window.__earpipeTest.lastResult = result
    const bar = document.getElementById('stage-progress-bar')
    if (bar) bar.style.width = '100%'
    document.querySelectorAll('.stage-step').forEach(el => el.classList.add('done'))
    document.querySelectorAll('.stage-connector').forEach(el => el.classList.add('done'))
    setTimeout(() => {
      if (expectedFlow === flowGeneration && expectedTranscription === transcriptionGeneration
          && currentInstrument === stemId) {
        playChime()
        showInstrumentResult(result)
      }
    }, 250)
  } catch (err) {
    if (expectedFlow === flowGeneration && expectedTranscription === transcriptionGeneration) {
      clearStageTimers()
      detachProgress()
      showError(err.message)
    }
  } finally {
    if (activeTranscription === promise) activeTranscription = null
  }
}

// ===== DONE =====

const scorePanel = document.getElementById('score-panel')

function renderScore(result) {
  let url = result.pdfUrl
  if (currentView === 'tab' && result.tabUrl) url = result.tabUrl
  else if (currentView === 'chord' && result.chordChartUrl) url = result.chordChartUrl
  else if (currentView === 'analysis' && result.confViewUrl) url = result.confViewUrl
  if (!url) return
  const embed = document.createElement('embed')
  embed.src = url
  embed.type = 'application/pdf'
  scorePanel.innerHTML = ''
  scorePanel.appendChild(embed)
}

function updateViewButtons() {
  document.querySelectorAll('#view-toggle .view-btn').forEach((b) => {
    b.classList.toggle('active', b.dataset.view === currentView)
  })
}

function showInstrumentResult(result) {
  document.getElementById('stat-notes').textContent = result.n_notes ?? '—'
  // #136: テンポの出所を正直表示(audio=音響フォールバック / default=推定不能で仮定値)
  const bpmNote = result.bpm_source === 'audio' ? ' (音響推定)'
    : result.bpm_source === 'default' ? ' (推定不能・仮定値)' : ''
  document.getElementById('stat-bpm').textContent =
    result.bpm ? `${Math.round(result.bpm)} BPM${bpmNote}` : '—'
  document.getElementById('stat-engine').textContent = result.engine ?? '—'

  // 表示切替: コード譜(一次導線・#116)は常時、TAB はギターだけ。
  // 既定はコード譜 → TAB → 五線譜 の優先順(コード譜を一次に昇格)。
  const hasTab = !!result.tabUrl
  const hasChord = !!result.chordChartUrl
  const hasAnalysis = !!result.confViewUrl
  document.getElementById('view-toggle-card').hidden = !(hasTab || hasChord || hasAnalysis)
  document.querySelector('#view-toggle .view-btn[data-view="tab"]').hidden = !hasTab
  document.querySelector('#view-toggle .view-btn[data-view="chord"]').hidden = !hasChord
  document.querySelector('#view-toggle .view-btn[data-view="analysis"]').hidden = !hasAnalysis
  currentView = hasChord ? 'chord' : (hasTab ? 'tab' : 'staff')
  updateViewButtons()
  renderScore(result)

  // エクスポート: TAB/コード譜/解析ビューは生成できたときだけ表示
  document.getElementById('btn-export-tab').hidden = !result.paths?.tab
  document.getElementById('btn-export-chord').hidden = !result.paths?.chordChart
  document.getElementById('btn-export-analysis').hidden = !result.paths?.confView

  showState('done')
}

function currentResult() {
  return currentInstrument ? stemResults.get(currentInstrument) : null
}

// 表示切替(五線譜/TAB)
document.querySelectorAll('#view-toggle .view-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    currentView = btn.dataset.view
    updateViewButtons()
    const r = currentResult()
    if (r) renderScore(r)
  })
})

// エクスポート（選択中の楽器の成果物を保存）
document.getElementById('btn-export-pdf').addEventListener('click', async () => {
  const r = currentResult()
  if (!r?.paths?.pdf) return
  const name = window.earpipe.exportFileName(currentTitle, currentInstrument, 'score', 'pdf')
  await window.earpipe.saveFile(r.paths.pdf, 'pdf', name)
})

document.getElementById('btn-export-tab').addEventListener('click', async () => {
  const r = currentResult()
  if (!r?.paths?.tab) return
  const name = window.earpipe.exportFileName(currentTitle, currentInstrument, 'tab', 'pdf')
  await window.earpipe.saveFile(r.paths.tab, 'pdf', name)
})

document.getElementById('btn-export-chord').addEventListener('click', async () => {
  const r = currentResult()
  if (!r?.paths?.chordChart) return
  const name = window.earpipe.exportFileName(currentTitle, currentInstrument, 'chord', 'pdf')
  await window.earpipe.saveFile(r.paths.chordChart, 'pdf', name)
})

document.getElementById('btn-export-analysis').addEventListener('click', async () => {
  const r = currentResult()
  if (!r?.paths?.confView) return
  const name = window.earpipe.exportFileName(currentTitle, currentInstrument, 'analysis', 'pdf')
  await window.earpipe.saveFile(r.paths.confView, 'pdf', name)
})

document.getElementById('btn-export-midi').addEventListener('click', async () => {
  const r = currentResult()
  if (!r?.paths?.midi) return
  const name = window.earpipe.exportFileName(currentTitle, currentInstrument, null, 'mid')
  await window.earpipe.saveFile(r.paths.midi, 'mid', name)
})

// 詳細設定(任意)を読む。未選択は null（自動）。
function readOverrides() {
  return {
    bpmRange: document.getElementById('opt-bpm').value || null,
    beat: document.getElementById('opt-beat').value || null,
    keyTonic: document.getElementById('opt-key').value || null,
    keyMode: document.getElementById('opt-mode').value || 'major',
  }
}

// 「この設定で採譜し直す」: 上書きは曲全体に効くので全楽器キャッシュを破棄し、
// 現在の楽器を新しい設定で採り直す。
document.getElementById('btn-reapply').addEventListener('click', async () => {
  if (!currentInput || !currentInstrument) return
  currentOverrides = readOverrides()
  ++transcriptionGeneration
  stemResults.clear()
  await selectInstrument(currentInstrument)
})

document.getElementById('btn-retry').addEventListener('click', () => {
  const oldInput = currentInput
  cancelActiveUrlOperation().catch(() => {})
  ++flowGeneration
  ++urlGeneration
  ++transcriptionGeneration
  clearStageTimers()
  detachProgress()
  currentInput = null
  currentInstrument = null
  currentOverrides = {}
  stemResults.clear()
  ;['opt-bpm', 'opt-beat', 'opt-key'].forEach((id) => {
    const el = document.getElementById(id)
    if (el) el.value = ''
  })
  const modeEl = document.getElementById('opt-mode')
  if (modeEl) modeEl.value = 'major'
  scorePanel.innerHTML = '<div class="score-placeholder" id="score-placeholder"><span>📄</span><span>楽譜を読み込み中...</span></div>'
  showState('idle')
  if (oldInput) window.earpipe.releaseInput(oldInput).catch(() => {})
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

// E2Eテスト専用フック(#61): ドロップと同一の入口をテストから起動できるよう公開する。
// **本番では絶対に露出しない**: main.js が E2E 起動時(env EARPAPER_E2E=1)にのみ
// URL へ ?e2e=1 を付与し、その時だけフックを生やす。
if (new URLSearchParams(window.location.search).get('e2e') === '1') {
  window.__earpipeTest = { startFlow, selectInstrument }
}
