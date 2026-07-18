> 【歴史的記録】本書は作成時点の前提・知見に基づくスナップショットです。その後の決定により一部前提は更新されています。現在の前提は `README.md`・`docs/requirements/product-vision.md`・`docs/research/gate-execution-spec.md`(最新改訂) を参照してください。

Slack作業ログは未投稿です。`tool_search` で確認しましたが、この環境には `slack_send_message` / `send_message` 相当のチャンネル直接投稿ツールが公開されていませんでした。

**1. v2でもなお欠落**
| ID | 新規欠落 | 根拠文献 / 一次資料 | 提案カテゴリ・MoSCoW | 既存IDでカバーできない理由 |
|---|---|---|---|---|
| NEW-GAP-01 | ボーカル譜の歌詞・音符アライメント受入条件。音符、歌詞、同期を別々でなく同時に評価する | AMNLT 2026は「notation, lyrics, synchronization」を同時対象化し、専用データセット/指標を提示  | 解析/評価・Should | `F-020`は「歌声採譜・歌詞同期」だけで、音節、melisma、同期誤差、評価指標が未定義 |
| NEW-GAP-02 | ボーカルのビブラート/ピッチ遷移の扱い。記譜する、無視する、装飾扱いにする境界を定義 | 歌声採譜は声質・ビブラート・オンオフセット曖昧性が課題 。MusicXMLの`<bend>`は連続bend/slide表現を持つ  | 解析/記譜・Could | `F-078`はギター奏法限定、`F-020`はボーカル装飾の記譜方針を含まない |
| NEW-GAP-03 | ベース専用TABプロファイル。slap-thumb/slap-pluck/dead-note/harmonics/vibrato/slide等を別KPI化 | IDMT-SMT-Bassはonset/offset/pitchに加えstring/fret、5種plucking、6種expressionを注釈化  | TAB/採譜品質・Should | `F-032/F-079/NF-032`はベースを含むが、ベース固有奏法と評価クラスがない |
| NEW-GAP-04 | 鍵盤運指推定。右手/左手、複数正解、個人差、教育用途の表示/編集を定義 | PIG/ThumbSet系研究はピアノ運指を独立タスクとして扱い、複数奏者差や部分注釈のノイズを明示   | 整譜/教育・Could | `F-028`はギターTAB運指で、鍵盤の指番号・手割当・複数正解を扱えない |
| NEW-GAP-05 | サステインペダル検出・記譜。CC64、pedal-extended note、MusicXML pedal出力を定義 | MIREX 2024 Polyphonicはsustain pedal CC64を評価対象にし、pedal extension手順を定義 。MusicXMLにも`<pedal>`がある  | ピアノ解析/出力・Should | `F-016`強弱や`F-045`記号編集では、ペダル自動検出と音価評価への影響を扱えない |
| NEW-GAP-06 | リアルタイム/ストリーミング採譜。因果モデル、lookahead、暫定出力の後修正、レイテンシKPI | リアルタイムAMTでは高レイテンシが対話用途を阻害し、window/hop/kernel/label shift等で削減する研究がある  | 性能/UX・Could | `NF-004`はバッチ処理時間、`F-067`は進捗表示で、逐次推論の遅延/安定性がない |
| NEW-GAP-07 | 弱教師・自己教師・合成データの学習戦略。未整列スコア、pseudo-label、評価データ漏洩防止を台帳化 | NoteEMは未整列 supervision、pseudo-label、pitch shiftでin-the-wild学習を扱う 。GTTでも合成音色/エフェクト追加で頑健性改善  | モデル運用・Should | `NF-025`はライセンス、`NF-031`は再現性だけで、弱教師データ品質とtrain/eval汚染防止がない |
| NEW-GAP-08 | ユーザー修正フィードバックからの継続学習。オンデバイス個別化、連合評価、削除/撤回、DP要否 | Googleは連合学習を「ユーザーデータをサーバーへ出さずに」個別化評価へ使うと説明 。Appleもon-device personalization向け連合評価/調整を大規模運用として説明  | プライバシー/モデル運用・Could | `F-074`は収集オプトインだけで、修正履歴の学習経路、個別化、撤回、集約方式が未定義 |
| NEW-GAP-09 | オンデバイス推論ランタイム・量子化受入ゲート。ONNX/CoreML/TFLite別に演算子対応、fallback、精度劣化、電力を測る | ONNX RuntimeはEPの性能が端末/モデル依存で、非対応op分割で劣化し得ると明記 。ONNX量子化は古い端末で遅くなる場合がある 。TFLite full integerは代表データセットで校正が必要  | 非機能/配布・Must | `NF-004/NF-017/NF-038`は環境・時間の大枠で、ランタイム別の通過条件になっていない |
| NEW-GAP-10 | MusicXMLリードシート/歌詞/.mxlプロファイル。`<lyric>`、`<harmony>`、chord diagram、compressed `.mxl`を受入条件化 | MusicXML 4.0は`<lyric>`のsyllabic/elision/extendを定義 、`<harmony>`/`<frame>`でコード記号・コード図を表現 、`.mxl` zip構造と`META-INF/container.xml`を定義 ([w3.org](https://www.w3.org/2021/06/musicxml40/tutorial/compressed-mxl-files/)) | 出力/規格・Should | `F-048`はTAB中心、`F-014/F-034/F-020`は解析/表示中心で、XML出力プロファイルがない |
| NEW-GAP-11 | 人間評価・知覚評価プロトコル。2AFC、短尺刺激、評価者属性、聴取回数、難しさ評価を標準化 | AMT評価指標は人間判断と常に一致せず、2択聴取テストと4000件超の知覚評価データで検証した研究がある  | 採譜品質・Should | `NF-019`は「人間評価」とだけ書き、プロトコルがない |

**2. v2受入条件の検証**
- TAB受入条件は、前回GAP-02/03/04の反映として妥当です。`string/fret`、チューニング、カポ、奏法、TAB KPIまで入っており、ギターTABの大枠は最新研究・MusicXML細目と整合しています。
- ただし、`ベースTAB`はまだ粗いです。IDMT-SMT-Bassの注釈粒度を見る限り、ベースは単なる4/5弦プロファイルではなく、plucking/expression style単位で評価すべきです。
- `NF-032 TAB品質KPI`は方向性は正しいですが、音色/エフェクト/録音条件への頑健性が抜けています。GTT研究では合成音色・実エフェクトの多様化が性能改善に効いています。
- `NF-019`の研究水準但し書きは概ね妥当です。ただしMIREX 2024 Polyphonicのpedal/velocity/データ分割/アライメント補正は未反映で、ピアノ評価としては古いというより未拡張です。
- `NF-004/NF-017`は「仮」と明記されているため誤りではありません。ただし量子化やEP利用で必ず高速化する前提に進むと危険です。ランタイム別ベンチを受入条件に分離すべきです。

**3. 結論**
v2は、前回GAP-01〜10を処理した要件定義としてはかなり強いです。特にTAB、MusicXML TAB、評価指標限界、成果物非関与、ローカル処理は研究・規格面から大枠十分です。

残る懸念は「フル構想の広さ」に対して、ボーカル、ベース、鍵盤、リアルタイム、継続学習、オンデバイス実行の受入条件がまだ抽象的なことです。MVPの前に全部をMust化する必要はありませんが、Phase3/Couldでも評価不可能なまま置くと、後で“できたことに見えるが使えない”要件になります。

**4. 調査カバレッジ**
確認済みローカル文書: `functional-requirements.md` v2、`non-functional-requirements.md` v2、前回 `codex-papers-gap-scan.md` GAP-01〜10。

Web確認範囲: ボーカル採譜/歌詞同期、ベース採譜、鍵盤運指、リアルタイムAMT、弱教師/合成データ、連合学習/オンデバイス個別化、ONNX Runtime/TFLite/CoreML系制約、Electron/Tauri配布、macOS公証/Windows署名、MIREX 2024/2026、MUSTER、知覚評価、MusicXML 4.0、MEI。

証拠が見つからなかったもの: 2026年7月時点で、混合音源からボーカル歌詞・ギター/ベースTAB・鍵盤運指・ペダルまで一括で商用品質に達した一次資料は確認できませんでした。
