# メインプロセスの非同期ハンドラ競合と一時領域の後始末 — #152 実装前調査（2026-10-03）

**目的:** #152（`app/main.js` の IPC ハンドラ同士の競合を TLA+/TLC で洗い出して直す）の実装前調査。WebSearch による確認と、手元環境での実測。
**対象の症状:** 採譜ハンドラが await している間に `release-input` やウィンドウ終了の後始末が走り、解放済みの出力を指すキャッシュが残る。子プロセスを SIGKILL するため Python 側の後始末が走らず、OS の一時領域に `earpipe_*` が残る。

## 1. 分かったこと

- **`ipcMain.handle` は並行に走る。** リスナーが Promise を返すと、その解決値が `ipcRenderer.invoke` の応答になる（Electron 公式）。ハンドラ間の排他や取消の仕組みは Electron には無く、await をまたいだ共有状態の整合はアプリ側の責任になる。
- **古い非同期結果の公開を防ぐ定石は2つ。** 先行処理を止める方法（AbortController）と、結果を公開する直前に「まだ自分が最新か」を照合する方法（リクエストID・世代番号、takeLatest 型の所有権）。前者だけでは、止める前に完了していた処理の結果が後から届く経路を塞げないため、公開側の照合が要る（FrontendAtlas / SitePoint）。
- **`detached: true` の子はプロセスグループのリーダーになり、負のPIDでグループごと止められる**（Node.js child_process 文書）。本アプリの `killProcessTree` はこの方式。
- **SIGKILL は後始末の機会を与えない。** 一般には SIGTERM を送り、猶予後に SIGKILL へ切り替える（"Die, Child Process, Die!" ほか）。猶予を入れると入力切替の待ち時間が延び、Demucs/basic-pitch の孫プロセスが SIGTERM を無視した場合の扱いも増える。
- **Python の `tempfile` は環境変数 `TMPDIR` → `TEMP` → `TMP` の順で一時領域を決める**（Python 公式）。手元の `.venv` で `TMPDIR=<dir> python -c "import tempfile; print(tempfile.gettempdir())"` が `<dir>` を返すことを確認した。

## 2. 採用する方針

| 論点 | 採用 | 見送り |
|---|---|---|
| 古い結果の公開 | 入力ごとの世代を開始時に捕まえ、await の後・公開の直前に照合する | AbortController（子プロセスは既に入力単位で kill しており、完了後の stat 待ちには効かない） |
| 楽器違いのキャッシュ | キーを (入力, 楽器) にし、追加形式の要求に表示中の楽器を載せる | レンダラ側で楽器切替のたびにメインへ通知する（状態が二重になる） |
| キャッシュの削除 | 登録した呼び出しだけが削除できる（所有者確認） | — |
| 一時領域の残留 | 子プロセスの `TMPDIR`/`TEMP`/`TMP` をアプリが追跡する一時ルート配下へ向ける | SIGTERM＋猶予への変更（待ち時間と停止性の検証範囲が広がる）、エンジン側の変更（今回の範囲外） |

## 3. 残る注意点

- `TMPDIR` を深くすると、一時領域に UNIX ドメインソケットを作るライブラリでパス長上限（macOS は 104 バイト）に近づく。ディレクトリ名は短く（`tmp`）し、実エンジンを通す E2E で確認する。
- 世代照合は「公開しない」ことを保証するだけで、応答がレンダラへ届いた後の解放は防げない。そこはレンダラ側の世代ガード（`flowGeneration` ほか）が受け持つ。

## 出典

- [ipcMain | Electron](https://www.electronjs.org/docs/api/ipc-main)
- [JavaScript Async Race Conditions: Fix Stale UI — FrontendAtlas](https://frontendatlas.com/javascript/trivia/js-async-race-conditions)
- [How to Prevent Stale API Responses with AbortController — SitePoint](https://www.sitepoint.com/how-to-prevent-stale-api-responses-with-abortcontroller/)
- [What's wrong with Electron IPC and how it can be fixed — TeamDev](https://teamdev.com/mobrowser/blog/what-is-wrong-with-electron-ipc-and-how-to-fix-it/)
- [Killing process families with node](https://medium.com/@almenon214/killing-processes-with-node-772ffdd19aad)
- [Die, Child Process, Die!](https://www.exratione.com/2013/05/die-child-process-die/)
- [Child process | Node.js 文書](https://nodejs.org/api/child_process.html)
- [tempfile | Python 文書](https://docs.python.org/3/library/tempfile.html)
