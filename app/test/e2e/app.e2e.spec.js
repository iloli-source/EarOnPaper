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

// ドロップと同じ入口 startFlow をテストフック経由で起動する。
// startFlow は 楽器分離→既定楽器の採譜→DONE まで一気に進める(現行の分離フロー)。
// (以前の startTranscribe はアプリが分離フローへ移行した際に廃止された)。
async function triggerTranscribe(win, filePath) {
  await win.evaluate((p) => window.__earpipeTest.startFlow(p, 'e2e'), filePath)
}

test('採譜→PDF表示→エクスポートUIが揃う(受入1・2・3)', async () => {
  const app = await electron.launch({ args: [APP_DIR], env: { ...process.env, EARPAPER_E2E: '1' } })
  try {
    const win = await app.firstWindow()

    // #61回帰: sandbox:true 下で preload が正しくロードされ earpipe API が公開されていること。
    // (以前 sandbox 既定で preload が require 失敗し window.earpipe が未公開=アプリ不動だった)
    const api = await win.evaluate(() => (window.earpipe ? Object.keys(window.earpipe) : null))
    expect(api).toEqual(
      expect.arrayContaining(['transcribe', 'saveFile', 'getPathForFile', 'basenameForDisplay', 'onProgress'])
    )

    // 起動直後は IDLE(ドロップ待ち)
    await expect(win.locator('#state-idle')).toHaveClass(/active/)

    // #128: URL取り込みUI(入力欄・ボタン・注意文言)が表示される
    // (実DLはネットワーク依存でflakyなため表示と importUrl API の公開のみ固定)
    await expect(win.locator('#url-input')).toBeVisible()
    await expect(win.locator('#btn-url')).toBeVisible()
    await expect(win.locator('.url-note')).toContainText('私的利用')
    expect(api).toEqual(expect.arrayContaining(['importUrl']))

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

    // 受入2+: 表面(type/src)だけでなく **生成物の中身** を検証する。
    // 生成パスをフック経由で取得し、Node 側で実ファイルを読んで妥当性を確認する。
    const paths = await win.evaluate(() => window.__earpipeTest?.lastResult?.paths)
    expect(paths, '採譜結果の paths が取得できない').toBeTruthy()
    // MusicXML: 実在・非空・音符と音高を含む(空の殻でない)
    const xml = fs.readFileSync(paths.musicxml, 'utf8')
    expect(xml).toMatch(/<score-partwise|<score-timewise/)
    expect(xml).toMatch(/<note/)
    expect(xml).toMatch(/<pitch>|<step>/)
    // PDF: 実在・自明でないサイズ(空PDFでない)・%PDF シグネチャ
    const pdfBuf = fs.readFileSync(paths.pdf)
    expect(pdfBuf.length).toBeGreaterThan(1000)
    expect(pdfBuf.subarray(0, 5).toString()).toBe('%PDF-')
    // MIDI: 実在・非空・MThd ヘッダ
    const midiBuf = fs.readFileSync(paths.midi)
    expect(midiBuf.length).toBeGreaterThan(0)
    expect(midiBuf.subarray(0, 4).toString()).toBe('MThd')

    // 受入3: エクスポートボタン(五線譜/MIDI)が有効(現UIの実ボタン)
    for (const id of ['#btn-export-pdf', '#btn-export-midi']) {
      await expect(win.locator(id)).toBeEnabled()
    }

    // #123/#116: コード譜が一次導線に昇格している。表示タブとエクスポートボタンが
    // 実UIに出て、生成物が妥当なPDFであることを実ボタン経路で固定する。
    await expect(win.locator('#view-toggle .view-btn[data-view="chord"]')).toBeVisible()
    await expect(win.locator('#btn-export-chord')).toBeVisible()
    const ccPath = await win.evaluate(() => window.__earpipeTest?.lastResult?.paths?.chordChart)
    expect(ccPath, 'コード譜(chordChart)の paths が取得できない').toBeTruthy()
    const ccBuf = fs.readFileSync(ccPath)
    expect(ccBuf.length).toBeGreaterThan(1000)
    expect(ccBuf.subarray(0, 5).toString()).toBe('%PDF-')
    // 既定表示がコード譜(一次導線)になっている
    await expect(win.locator('#view-toggle .view-btn[data-view="chord"]')).toHaveClass(/active/)

    // #121: 解析ビュー(信頼度ハイライト＋波形)がタブ/エクスポートに出て、妥当なPDF
    await expect(win.locator('#view-toggle .view-btn[data-view="analysis"]')).toBeVisible()
    await expect(win.locator('#btn-export-analysis')).toBeVisible()
    const cvPath = await win.evaluate(() => window.__earpipeTest?.lastResult?.paths?.confView)
    expect(cvPath, '解析ビュー(confView)の paths が取得できない').toBeTruthy()
    const cvBuf = fs.readFileSync(cvPath)
    expect(cvBuf.length).toBeGreaterThan(1000)
    expect(cvBuf.subarray(0, 5).toString()).toBe('%PDF-')
  } finally {
    await app.close()
  }
})

test('不正入力でエラーメッセージが表示される(受入4)', async () => {
  const app = await electron.launch({ args: [APP_DIR], env: { ...process.env, EARPAPER_E2E: '1' } })
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

test('詳細エクスポート(簡譜)が GUI 経路で実ファイルを生成する(音楽家向け導線)', async () => {
  // 音楽家向け理論系出力を GUI(IPC→エンジン→保存)から実生成できることを固定する。
  const app = await electron.launch({ args: [APP_DIR], env: { ...process.env, EARPAPER_E2E: '1' } })
  try {
    const win = await app.firstWindow()
    // 詳細エクスポートボタンが DONE 画面に存在する(音楽家向け導線が UI に露出している)
    await expect(win.locator('#extra-export-buttons [data-extra="jianpu"]')).toHaveCount(1)

    // E2E は保存ダイアログを操作できないため、EARPAPER_E2E 時のみ許される savePath 引数で保存先を渡す。
    const outPath = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'earpaper-x-e2e-')), 'jianpu.txt')
    const saved = await win.evaluate(
      (arg) => window.earpipe.exportExtra(arg.p, 'jianpu', arg.sp),
      { p: wavPath, sp: outPath }
    )

    // 実ファイルが生成され、簡譜(数字譜)らしい内容を含む
    expect(saved).toBe(outPath)
    const content = fs.readFileSync(outPath, 'utf8')
    expect(content.trim().length).toBeGreaterThan(0)
    expect(content).toMatch(/[1-7]/)
  } finally {
    await app.close()
  }
})
