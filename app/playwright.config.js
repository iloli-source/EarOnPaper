'use strict'
// Electron E2E 設定(#61)。採譜は Python エンジンを subprocess 起動するため時間がかかる。
// 直列実行(workers:1)・長めのタイムアウトにする。ユニットテスト(test/*.test.js)とは分離。

/** @type {import('@playwright/test').PlaywrightTestConfig} */
module.exports = {
  testDir: './test/e2e',
  testMatch: '**/*.e2e.spec.js',
  timeout: 120000,
  expect: { timeout: 90000 },
  fullyParallel: false,
  workers: 1,
  reporter: 'line',
}
