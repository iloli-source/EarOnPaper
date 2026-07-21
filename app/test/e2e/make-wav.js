'use strict'
// E2E用の最小WAV生成(#61)。python 依存を避け、Node だけで 16bit PCM mono の
// 単純な旋律(ドミソド)を書き出す。soundfile/librosa がデコードできる標準WAV。

/**
 * @param {{ sampleRate?: number, seconds?: number, freqs?: number[] }} [opts]
 * @returns {Buffer} WAV(RIFF/PCM16/mono)全体のバイト列
 */
function makeWavBuffer(opts = {}) {
  const sampleRate = opts.sampleRate ?? 22050
  const seconds = opts.seconds ?? 2
  const freqs = opts.freqs ?? [261.63, 329.63, 392.0, 523.25] // C E G C
  const n = Math.floor(sampleRate * seconds)
  const data = Buffer.alloc(n * 2)
  const segLen = Math.max(1, Math.floor(n / freqs.length))
  for (let i = 0; i < n; i++) {
    const f = freqs[Math.min(freqs.length - 1, Math.floor(i / segLen))]
    const s = Math.sin(2 * Math.PI * f * (i / sampleRate)) * 0.3
    const v = Math.max(-32768, Math.min(32767, Math.round(s * 32767)))
    data.writeInt16LE(v, i * 2)
  }
  const header = Buffer.alloc(44)
  header.write('RIFF', 0)
  header.writeUInt32LE(36 + data.length, 4)
  header.write('WAVE', 8)
  header.write('fmt ', 12)
  header.writeUInt32LE(16, 16) // PCM fmt chunk size
  header.writeUInt16LE(1, 20) // audio format = PCM
  header.writeUInt16LE(1, 22) // channels = mono
  header.writeUInt32LE(sampleRate, 24)
  header.writeUInt32LE(sampleRate * 2, 28) // byte rate
  header.writeUInt16LE(2, 32) // block align
  header.writeUInt16LE(16, 34) // bits per sample
  header.write('data', 36)
  header.writeUInt32LE(data.length, 40)
  return Buffer.concat([header, data])
}

module.exports = { makeWavBuffer }
