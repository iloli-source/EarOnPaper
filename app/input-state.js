'use strict'

// 入力ごとの世代と、世代に紐づくキャッシュ(分離済みステム / 採譜済みMusicXML)。
// IPCハンドラは開始時に capture() したチケットを await の後で照合し、その間に
// release-input やウィンドウ終了の後始末が走っていたら結果を公開しない(refs #152)。
// Electron にも fs にも依存しない純粋な状態管理(モデル: formal/InputLifecycle.tla)。

class StaleInputError extends Error {
  constructor() {
    super('入力が切り替えられたため、この処理結果は破棄されました')
    this.name = 'StaleInputError'
    this.code = 'EARPAPER_STALE_INPUT'
  }
}

function createInputState() {
  let epoch = 0                    // 全体の後始末(cleanupAllResources)で進む
  const generations = new Map()    // inputPath -> 入力単位の解放で進む世代
  const separations = new Map()    // inputPath -> { ticket, entry: { dir, stems } }
  const musicxmlByInput = new Map() // inputPath -> Map(stemKey -> MusicXML パス)

  function capture(inputPath) {
    return Object.freeze({ inputPath, epoch, generation: generations.get(inputPath) || 0 })
  }

  function isCurrent(ticket) {
    return ticket.epoch === epoch
      && ticket.generation === (generations.get(ticket.inputPath) || 0)
  }

  function assertCurrent(ticket) {
    if (!isCurrent(ticket)) throw new StaleInputError()
  }

  function invalidateInput(inputPath) {
    generations.set(inputPath, (generations.get(inputPath) || 0) + 1)
    separations.delete(inputPath)
    musicxmlByInput.delete(inputPath)
  }

  function invalidateAll() {
    epoch += 1
    generations.clear()
    separations.clear()
    musicxmlByInput.clear()
  }

  function publishSeparation(ticket, entry) {
    assertCurrent(ticket)
    separations.set(ticket.inputPath, { ticket, entry })
  }

  function getSeparation(inputPath) {
    const held = separations.get(inputPath)
    return held ? held.entry : null
  }

  // 失敗した呼び出しが、後続の呼び出しの登録を巻き添えで消さないよう所有者を確認する
  function discardSeparation(ticket) {
    const held = separations.get(ticket.inputPath)
    if (held && held.ticket === ticket) separations.delete(ticket.inputPath)
  }

  function publishMusicxml(ticket, stemKey, musicxmlPath) {
    assertCurrent(ticket)
    if (!musicxmlByInput.has(ticket.inputPath)) musicxmlByInput.set(ticket.inputPath, new Map())
    musicxmlByInput.get(ticket.inputPath).set(stemKey, musicxmlPath)
  }

  function getMusicxml(inputPath, stemKey) {
    const byStem = musicxmlByInput.get(inputPath)
    return (byStem && byStem.get(stemKey)) || null
  }

  return {
    capture, isCurrent, assertCurrent, invalidateInput, invalidateAll,
    publishSeparation, getSeparation, discardSeparation, publishMusicxml, getMusicxml,
  }
}

module.exports = { createInputState, StaleInputError }
