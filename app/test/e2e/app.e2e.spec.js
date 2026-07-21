'use strict'
// #61 受入条件の GUI E2E(実 Electron を Playwright で起動)。
// 「ユニット緑≠製品反映」を防ぐため、実 UI を通して 4 条件を機械固定する:
//   1. 音声を渡すと採譜が完了する
//   2. PDF がアプリ内に表示される
//   3. PDF/MusicXML/MIDI をエクスポートできる(ボタンが有効)
//   4. エラー時にわかりやすいメッセージが出る
//
// ドラッグ&ドロップは Electron webUtils 経由でしか実パスを得られず Playwright から
// 合成できないため、ドロップと同一の入口 window.__earpipeTest.startTranscribe を使う。

const { test, expect, _electron: electron } = require('@playwright/test')
const path = require('path')
const os = require('os')
const fs = require('fs')
const { makeWavBuffer } = require('./make-wav')

const APP_DIR = path.resolve(__dirname, '../..')
let wavPath = ''

test.beforeAll(() => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'earpaper-e2e-'))
  wavPath = path.join(dir, 'melody.wav')
  fs.writeFileSync(wavPath, makeWavBuffer({}))
})

// ドロップと同じ入口 startTranscribe をテストフック経由で起動する
// (preload が正常ロードされていれば evaluate はメインワールドで走り earpipe を参照できる)。
async function triggerTranscribe(win, filePath) {
  await win.evaluate((p) => window.__earpipeTest.startTranscribe(p, 'e2e'), filePath)
}

test('採譜→PDF表示→エクスポートUIが揃う(受入1・2・3)', async () => {
  const app = await electron.launch({ args: [APP_DIR] })
  try {
    const win = await app.firstWindow()
    // 起動直後は IDLE(ドロップ待ち)
    await expect(win.locator('#state-idle')).toHaveClass(/active/)

    // ドロップと同じ入口で採譜を起動
    await triggerTranscribe(win, wavPath)

    // 受入1: 採譜完了 → DONE 状態
    await expect(win.locator('#state-done')).toHaveClass(/active/)

    // 受入2: PDF がアプリ内に file URL で埋め込まれる
    const embed = win.locator('#score-panel embed')
    await expect(embed).toHaveAttribute('type', 'application/pdf')
    const src = await embed.getAttribute('src')
    expect(src || '').toMatch(/^file:/)

    // 統計が実値で埋まる(空プレースホルダ — のまま残っていない)
    await expect(win.locator('#stat-notes')).not.toHaveText('—')

    // 受入3: 3 形式のエクスポートボタンが有効
    for (const id of ['#btn-export-pdf', '#btn-export-musicxml', '#btn-export-midi']) {
      await expect(win.locator(id)).toBeEnabled()
    }
  } finally {
    await app.close()
  }
})

test('不正入力でエラーメッセージが表示される(受入4)', async () => {
  const app = await electron.launch({ args: [APP_DIR] })
  try {
    const win = await app.firstWindow()
    // 存在しないファイルを渡す → エンジン起動前の検証で失敗する想定
    await triggerTranscribe(win, '/no/such/earpaper-missing.wav')
    // 受入4: ERROR 状態にわかりやすいメッセージ
    await expect(win.locator('#state-error')).toHaveClass(/active/)
    const msg = (await win.locator('#error-message').textContent()) || ''
    expect(msg.trim().length).toBeGreaterThan(0)
  } finally {
    await app.close()
  }
})
