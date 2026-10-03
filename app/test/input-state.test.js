'use strict'

const test = require('node:test')
const assert = require('node:assert/strict')
const { createInputState, StaleInputError } = require('../input-state')

test('解放された入力のチケットでは MusicXML を公開できない', () => {
  // Arrange
  const state = createInputState()
  const ticket = state.capture('/a.wav')

  // Act
  state.invalidateInput('/a.wav')

  // Assert
  assert.equal(state.isCurrent(ticket), false)
  assert.throws(() => state.publishMusicxml(ticket, 'guitar', '/r/g.musicxml'), StaleInputError)
  assert.equal(state.getMusicxml('/a.wav', 'guitar'), null)
})

test('全体の後始末は全入力のチケットを失効させ、キャッシュを空にする', () => {
  // Arrange
  const state = createInputState()
  const ticket = state.capture('/a.wav')
  state.publishMusicxml(ticket, 'guitar', '/r/g.musicxml')
  state.publishSeparation(ticket, { dir: '/s', stems: {} })

  // Act
  state.invalidateAll()

  // Assert
  assert.equal(state.isCurrent(ticket), false)
  assert.equal(state.getMusicxml('/a.wav', 'guitar'), null)
  assert.equal(state.getSeparation('/a.wav'), null)
  assert.equal(state.isCurrent(state.capture('/a.wav')), true)
})

test('MusicXML は (入力, 楽器) ごとに保持し、別の入力の解放では消えない', () => {
  // Arrange
  const state = createInputState()
  const a = state.capture('/a.wav')
  const b = state.capture('/b.wav')

  // Act
  state.publishMusicxml(a, 'guitar', '/r/g.musicxml')
  state.publishMusicxml(a, 'piano', '/r/p.musicxml')
  state.publishMusicxml(b, 'guitar', '/r/b.musicxml')
  state.invalidateInput('/b.wav')

  // Assert
  assert.equal(state.getMusicxml('/a.wav', 'guitar'), '/r/g.musicxml')
  assert.equal(state.getMusicxml('/a.wav', 'piano'), '/r/p.musicxml')
  assert.equal(state.getMusicxml('/a.wav', 'bass'), null)
  assert.equal(state.getMusicxml('/b.wav', 'guitar'), null)
})

test('分離キャッシュは登録した呼び出しのチケットでしか破棄できない', () => {
  // Arrange
  const state = createInputState()
  const stale = state.capture('/a.wav')
  state.invalidateAll()
  const owner = state.capture('/a.wav')
  state.publishSeparation(owner, { dir: '/s', stems: { guitar: '/s/guitar.wav' } })

  // Act
  state.discardSeparation(stale)

  // Assert
  assert.deepEqual(state.getSeparation('/a.wav'), { dir: '/s', stems: { guitar: '/s/guitar.wav' } })
  state.discardSeparation(owner)
  assert.equal(state.getSeparation('/a.wav'), null)
})
