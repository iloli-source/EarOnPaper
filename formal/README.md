# formal/ — メインプロセス競合の TLA+ モデル（#152）

`app/main.js` の IPC ハンドラ同士の競合を、小さな有界モデルで再現して直した記録。
確認したのは「有界な TLA+ モデルを TLC でモデル検査した」ことまでで、コードそのものの形式検証ではない。

## 実行

公式リリースの `tla2tools.jar`（TLA+ tools）と Java 11 以降を用意し、`tlc-checks.json` に並んだ
spec と config の組を 1 件ずつ TLC にかける。

```bash
cd formal
java -cp /path/to/tla2tools.jar tlc2.TLC -config InputLifecycleFixed.cfg InputLifecycle.tla
```

`tlc-checks.json` の `expect` が各組の期待結果。`*Bug*.cfg` は名前の付いた不変条件の違反を再現できれば成功、
`*Fixed.cfg` と `*NoCleanup.cfg` は違反なしで成功。

## 追跡の鎖

| 事象 | モデル / 性質 | 反例（最短の実行順） | 修正 | 回帰テスト |
|---|---|---|---|---|
| 採譜後の stat 待ちに `release-input` が割り込み、解放済みの MusicXML をキャッシュへ公開して成功応答する | `InputLifecycle` / `NoPublishAfterRelease`（`BugRelease.cfg`） | Start → EngineExit → ReleaseSync → Publish | 開始時のチケットを公開直前に照合（`app/input-state.js`、`main.js` の `publishMusicxml`） | `release-input が採譜後の stat 待ちに割り込んだら…` |
| 同じ割り込みがウィンドウ終了の後始末で起きる | 同上（`BugCleanup.cfg`） | Start → EngineExit → Cleanup → Publish | `cleanupAllResources` が全チケットを失効させる | `ウィンドウ終了の後始末が…` |
| `release-input` が kill 待ちの間に始まった子プロセスを止めず、出力先だけ消す | `InputLifecycle` / `NoOrphanEngine`（`BugOrphan.cfg`） | Start(h1) → ReleaseKill → Start(h2) → Close(h1) → ReleaseFinish | 残りが無くなるまで止め直す（`releaseInputResources`） | `release-input は kill 待ちの間に…` |
| 楽器を切り替えて戻すと、追加形式が別の楽器の MusicXML から作られる | `StemCache` / `CacheKeyMatchesInstrument` | Transcribe(guitar) → Transcribe(piano) → Switch(guitar) → Export | キャッシュのキーを (入力, 楽器) にし、`export-extra` に表示中の楽器を渡す | `楽器を切り替えて戻した後の追加形式は…` |
| 失敗した分離が、後続の分離の登録を消す | `SeparationOwner` / `OwnerOnlyDelete` | A_Start → Cleanup → B_Start → B_Done → A_LateClose | 登録した呼び出しだけが削除できる（`discardSeparation`） | `後始末で止められた分離の失敗処理は…` |

`SeparationOwnerNoCleanup.cfg` は、後始末（`cleanupAllResources`）が絡まない通常経路では修正前のコードでも違反しないことを示す。
後続の `separate-audio` が先行の子プロセスを kill して close を待つため、先行の失敗処理は必ず後続の登録より前に走る。
違反には「後始末で追跡表が空になった後、kill された先行の close が、後続の分離完了より遅れて届く」ことが要る。

## モデルの仮定

- Node のイベントループは単一スレッドで、割り込みは await 点でしか起きない。各アクションは await から次の await までの同期区間に対応する。
- 入力は1つ、ハンドラは2つ、無効化操作は2回まで。別の入力どうしは状態を共有しないので1入力で足りる。
- `ReleaseFinish` の「止め直し」は、kill と close 待ちを繰り返すループを1アクションにまとめている。
- `StemCache` は採譜をレンダラが直列化する前提（`activeTranscription`）で、採譜を原子的に扱う。
- `SeparationOwner` の反例は、SIGKILL された子の close が数分かかる分離の完了より後に届くことを要し、実運用ではほぼ起きない。修正は所有者確認の1箇所で、世代チケットの導入に含まれる。

## モデル化していない境界

- ファイルシステムの実挙動、プロセスグループへの SIGKILL、`waitForProcessClose` の5秒タイムアウト。
- 子プロセスの一時領域の残留（`TMPDIR` を追跡中ルート配下へ向ける修正）。OS とプロセスの性質なので、モデルではなく実行テストで固定している。
- 応答がレンダラへ届いた後の解放。レンダラ側の世代ガード（`flowGeneration` ほか）が受け持つ。
- `import-url`（yt-dlp）と `cancel-operation`。
