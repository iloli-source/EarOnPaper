# 実装状況トレーサビリティ（要件 → コード）

**最終更新:** 2026-07-21
**目的:** 要件定義（機能117件・非機能50件）のどれが実装され、どれが未着手かを常時可視化する。「フル構想版」の要件と、実際に作ったスパイク（Pitchsieve）の距離を隠さないための台帳。
**判定方法:** `spike/ear-pipeline/earpipe`・`app/`・`tools/ai-ears/` のコードを実読して判定（2026-07-21 実装インベントリ）。推測での「実装済」判定は禁止。

## 凡例

| 記号 | 意味 |
|---|---|
| ✅ 実装済 | エンジン/出力として動作するコードがあり、実採譜フローから**到達可能** |
| 🟡 部分 | 一部だけ実装、または限定条件でのみ動く |
| ⬜ 未着手 | 該当コードなし |
| 🚫 対象外 | Won't（作らない決定）／廃止／非コード業務項目 |

> **✅ の読み方(重要・外部レビュー反映):** ✅ は「コードがあり CLI から到達可能」を意味し、
> **「素の `transcribe` 既定出力(五線譜/MIDI/PDF/TAB)や GUI に組込み済み」とは限らない**。
> 多くの機能は `--emit`/`--analysis`/`--format` の**オプトイン副次出力**でのみ到達でき、既定譜面には
> 反映されない(例: F-023 声部分離・F-016 強弱・F-102 ペダル・F-078 奏法は `--emit` の別ファイル出力
> であって既定の五線譜には注記されない)。「既定/GUI 経由か」は各行の根拠欄で判別すること。

> **重要な前提:** 機能要件は「フル構想版」で、事業判断（結論v5=No-Go）とは独立した構想ドキュメント。Phase1は「候補プール25件から6-8件を選抜実装する」設計であり、未着手＝漏れとは限らない。ただし**選抜/見送りの記録が無かった**ため本台帳を新設した（きっかけ: F-003ステム分離がMust/Phase1なのに未実装だと発覚。混合音源が採れない実害に直結）。

## 機能要件 Must（34件）

| ID | 名称 | Phase | 状況 | 根拠 / 備考 |
|---|---|---|---|---|
| F-001 | 音声ファイル入力 | 1 | ✅ | `stem/preprocess.py:load_audio()` wav/mp3/flac/ogg/m4a |
| F-003 | **ステム分離** | 1 | ✅ | `stem/separate.py` Demucs 4-stem(別venv・#65)。`--stem`/`separate-transcribe`で楽器毎に譜面化 |
| F-010 | 多重音高検出 | 1 | ✅ | `ear/mono.py` pYIN / `ear/poly.py` basic-pitch / `adaptive.py` / `engine_select.py` mono/poly自動選択(#64) |
| F-011 | オンセット/オフセット | 1 | ✅ | PitchEvent契約でonset/offset秒 |
| F-012 | 拍・小節推定 | 1 | ✅ | `rhythm/meter.py:estimate_meter()` `estimate_grid()` |
| F-017 | テンポマップ生成 | 1 | 🟡 | `rhythm/tempo_map.py` 分析出力のみ。記譜は単一テンポ格子 |
| F-021 | リズム量子化 | 1 | ✅ | `rhythm/quantize.py:quantize_events()` 16分/3連格子 |
| F-022 | 拍子整合チェック | 1 | ✅ | `meter.py` + `score.py:_cap_overlaps()` |
| F-023 | **声部分離・譜表割当** | 1 | 🟡 | `score.py:split_hands()` 左右手のみ。多声声部分離は未。→ 強化対象 |
| F-024 | **連桁・符尾の自動整理** | 1 | 🟡 | **music21 `makeNotation` に委譲**(`score.py:250`)。自前の連桁エンジンは持たない。`test_beaming.py` は music21 が出す `<beam>`/`<stem>` の存在回帰であり、拍境界品質の自前保証ではない(依存ライブラリの既定挙動を通しているだけ) |
| F-025 | 演奏可能性制約 | 1 | 🟡 | `tab.py:fold_to_range()` TAB音域のみ。汎用制約は未 |
| F-028 | 運指・ポジション最適化 | 1 | ✅ | `tab.py` ハンドポジションDP |
| F-031 | 五線譜 | 1 | ✅ | `notate/engrave.py:write_pdf()` Verovio |
| F-032 | TAB譜 | 1 | ✅ | `notate/tab.py:write_tab_pdf()` |
| F-038 | 下書き提示UX | 1 | 🟡 | appにステージ表示のみ。未確認音符区別・確認マークは未 |
| F-039 | 楽譜エディタ | 2 | ⬜ | エディタUI層なし |
| F-042 | 原音源同期再生 | 2 | 🟡 | app/viewerに再生導線の一部。同期ハイライトは未 |
| F-043 | 信頼度ハイライト | 2 | ⬜ | confidence値は保持。UI表示なし |
| F-045 | 奏法記号・強弱の編集 | 2 | 🟡 | コード帯出力あり。奏法記号/強弱編集は未 |
| F-046 | アンドゥ・版管理 | 2 | ⬜ | UI層なし |
| F-048 | MusicXMLエクスポート | 1 | ✅ | `score.py:write_musicxml()` music21 |
| F-049 | MIDIエクスポート | 1 | ✅ | `score.py:write_midi()` grid/raw二重 |
| F-050 | PDF楽譜出力 | 2 | ✅ | `engrave.py:write_pdf()` |
| F-052 | **MusicXML妥当性検証** | 1 | 🟡 | 検証機能は `notate/musicxml_validate.py`(XSD/構造/ラウンドトリップ・#66)に実装済だが、**既定出力へは自動適用せず** `--emit validate` で任意実行(NF-011と同じ限界) |
| F-066 | 完全ローカル処理 | 1 | ✅ | 外部送信コードなし |
| F-068 | 日本語UI | 2 | ✅ | app全体が日本語 |
| F-071 | 無料試用 | 2 | 🚫 | **OSS化で対象外(Won't)**。全機能無料のため「試用」概念が成立しない(前提追随・2026-07-21) |
| F-076 | 弦・フレット割当エンジン | 1 | ✅ | `tab.py` |
| F-077 | チューニング・カポ指定 | 1 | 🟡 | 基準ピッチ補正`tuning.py`済。カポ/staff-tuning印字は限定 |
| F-078 | ギター/ベース奏法検出 | 2 | ✅ | `notate/technique.py` bend/slide/vibrato/hammer/pull(#73) |
| F-081 | 調整合ピッチスペリング | 1 | ✅ | `notate/spelling.py:spell_midi()` KS法 |
| F-108 | フィールド録音モード | 1 | ✅ | `transcribe --field-mode` が `analyze_field`/`select_events` を実行し `field_report` を出力(既定フローに結線済)。なお下位公開API `classify_segment`/`gate_by_class` は本番未到達で allowlist 凍結(モード本体とは別) |
| F-002 | 音質診断・警告 | 2(Should) | ✅ | `stem/diagnose.py` クリッピング/SNR/残響/帯域/3段階rating(#67) |

## 機能要件 Should/Could の主な未着手（抜粋）

| ID | 名称 | Phase | 状況 | 備考 |
|---|---|---|---|---|
| F-004 | 長尺音源の自動分割 | 2 | ✅ | `stem/chunk.py:split_into_chunks()` 無音境界優先(#68) |
| F-005 | マイク/ライン録音入力 | 2 | 🟡 | `pipeline.py` `record` サブコマンド(録音→wav保存→任意で採譜)。録音は任意依存 sounddevice。**テストは `_record_audio` を全モックしており、実マイク/PortAudio 経路は未検証**(`test_record.py`)。実装済みだが実機採取は手動確認が必要 |
| F-013 | キー/スケール推定 | 2 | ✅ | `spelling.py:estimate_key()` |
| F-014 | コード進行解析 | 2 | ✅ | `notate/chord.py:estimate_chords()` |
| F-015 | 楽器分類・パート識別 | 2 | ✅ | `ear/instrument_classify.py` 実データ較正・粗判定(#72) |
| F-033 | 简谱(数字譜) | 3 | ✅ | `notate/jianpu.py:to_jianpu()`(#70) |
| F-034 | コード譜・リードシート | 2 | ✅ | `notate/leadsheet.py:to_leadsheet()`(#71) |
| F-041 | スペクトログラム表示 | 2 | ⬜ | UI未 |
| F-054 | 音声プレビュー出力 | 2 | ✅ | `notate/preview.py:render_preview()` MIDI→WAV/MP3(#69) |
| F-091 | 度数/ローマ数字/Nashville | 3 | ✅ | `notate/roman_nashville.py`(#74)。**CLI結線済(#109 B-2a)**: `transcribe --analysis roman/nashville` |
| F-100 | 移動ド記譜 | 3 | ✅ | `notate/movable_do.py:to_movable_do()`(#75)。**CLI結線済(#109 B-2a)**: `transcribe --analysis movable_do` |
| F-059〜F-065 | 練習支援群 | 2-3 | ⬜ | テンポ変更/移調/ループ/学習モード等 |

## 非機能要件 Must（20件）

| ID | 名称 | 状況 | 根拠 / 備考 |
|---|---|---|---|
| NF-001 | オフライン完全動作 | ✅ | 全処理ローカル |
| NF-004 | 採譜処理時間 | ✅ | `services/quality/latency.py`(p50/p95/p99計測)＋`bench/bench_latency.py`。`test_latency.py` |
| NF-009 | ログのプライバシー | ✅ | 音源内容をログしない構造 |
| NF-011 | MusicXML標準準拠 | 🟡 | 出力は music21 準拠。XSD/ラウンドトリップ検証機能は F-052(`validate_musicxml`)に**あるが既定出力へ自動適用はしていない**(`--emit validate` で任意実行) |
| NF-013 | 外部送信なしの既定 | ✅ | 送信コードなし |
| NF-022 | 拍子妥当性ゲート | 🟡 | meter推定はあるが「ゲート」化は限定 |
| NF-023 | 成果物非関与構造 | ✅ | サーバ経由なし |
| NF-024 | 私的複製整合設計 | ✅ | ローカル処理で担保 |
| NF-025 | 学習データのライセンスクリーン | 🚫 | 学習未実施（該当なし・将来） |
| NF-026 | コピーレフト部品の分離 | ✅ | 依存は寛容ライセンス中心（要監査） |
| NF-029 | モデル・部品のライセンス台帳 | ✅ | [dependency-licenses.md](../dependency-licenses.md)（実測・LGPL部品の扱い明記） |
| NF-032 | TAB品質KPI | 🟡 | OCR重なり計測等あり。客観KPIフルは未 |
| NF-037 | 署名付き配布・更新検証 | 🚫 | 配布業務項目（コード外） |
| NF-038 | 対応環境の明記 | ✅ | [supported-environments.md](../supported-environments.md)（OS×Python×機能マトリクス・限界も明記） |
| NF-043 | 推論ランタイム別受入ゲート | ⬜ | 未 |
| NF-045 | 出力層のプラグイン型拡張 | ✅ | 自動発見エミッタレジストリ(`services/emitters/`)＋dispatch/analysis の3系統。[output-plugins.md](../architecture/output-plugins.md)で正式化。1ファイル追加で結線 |
| NF-046 | UI応答予算と大量表示性能 | ⬜ | UI未成熟 |
| NF-047 | カラーシステム3系統 | ⬜ | UI未成熟 |
| NF-050 | 二層アーキテクチャ原則 | ✅ | 耳(ear)と記譜(notate)が分離 |

## 実装ロードマップ（本台帳に基づく着手順）

- **B. エンジン欠落**: ✅ mono/poly自動選択(#64)・F-003ステム分離(#65)完了。F-023声部分離は部分。
- **C/D/G. 解析・整譜・記譜・記譜描画・出力・練習ロジック**: ✅ batch1〜5(#66-108)で**エンジン/記譜のロジック系はほぼ全実装**(多声分離・歌詞同期・譜面差分・資産再利用・出力プロファイル・形式レジストリ・MuseScore連携・人手仕上げパッケージ・サウンドフォント試聴・区間採譜・解析ヒント・テンポ変更再生・バッチ・ドラム譜・楽器プロファイル・装飾音・鍵盤運指・ビジュアルカード・简谱/リードシートPDF描画 等)。**全体テスト1041緑**。
- **外部デバッグ21項目(#94)**: ✅ エンジン側6(DoS/OverflowError/TIMEOUT/未使用)＋アプリ側15(偽成功防止・IPC信頼境界・クロスプラットフォーム・ライフサイクル)。docs/debug/参照。
- **#109 結線(偽成功の解消)**: 「実装済み・ユニット緑だが pipeline から未到達(孤立)」を機械ゲート(#111)で可視化。**重要な限界の明示(外部レビュー反映)**:
  - **結線先はほぼ全て `--emit`/`--analysis`/`--format` のオプトイン副次出力**であり、**素の `transcribe` 既定出力(五線譜/MIDI/PDF/TAB)には反映されない**(「到達可能」≠「既定挙動に組み込み済み」)。例: 声部分離(F-023)は `--emit voices` で別MusicXMLを出すのみで、既定 `score.py` は左右手分割どまり。強弱/ペダル/装飾も既定譜面には注記されない。
  - **GUI 露出(2026-07 追加)**: 理論系出力(簡譜/リードシート/度数/Nashville/移動ド/GP5/UST/ABC)は Electron アプリの「詳細エクスポート(音楽家向け)」から生成・保存できる(`app/main.js` `export-extra`・E2E固定)。ただし依然「既定の一次出力」ではなく明示選択のオプトイン。声部分離・強弱等の**記譜内注記**系はまだ GUI 未露出。
  - B-2a: 移動ド/度数/Nashville を `transcribe --analysis`(F-091/F-100)
  - B-2 汎用エミッタ(`--emit KEY`, 自動発見レジストリ): 29モジュールを CLI 到達可能化(上記のとおり副次出力)。
  - #113: gp5 の非表現音価クラッシュを修正し `--format gp5` に再結線。
  - 残subcommand型: `chunk`/`diff`/`compare` を CLI サブコマンド化。
  - **孤立ゲートの誠実化(外部レビュー反映)**: 「定義モジュールが到達可能なら配線済み」という緩い条件で数字を0に見せていたのを撤廃。関数は**名前 import か直接呼び出しでの到達を厳密要求**(型/定数はデータ契約として緩和)。その結果、実装済みだが本番未到達の関数が正直に9件残り、`scripts/orphan_allowlist.txt` に**1件ずつ理由付きで凍結**(デモ用PNG/honest未実装のdetect_sustain_audio/下位API等)。「孤立0」は誇張だったため撤回。
- **残: PDF/SVG視覚化の一部**（簡譜/リードPDFは `--emit textpdf` で結線済。度数/移動ドはテキスト。五線譜/TABは従来どおり視覚化済み）
- **E. 編集UI/アプリ**: ✅ **Electron MVP動作(#61・E2E検証済)** — ドラッグ&ドロップ→採譜→PDFアプリ内表示→PDF/MusicXML/MIDIエクスポート。Playwright GUI E2Eで4受入条件を固定。**GUI E2Eが実バグ(sandbox既定でpreload失敗→window.earpipe未公開)を検出・修正**(偽成功の実例)。残: F-039楽譜エディタ・F-043信頼度ハイライト・F-046アンドゥ・波形/スペクトログラム
- **F. 非機能**: NF-004計測・NF-011検証・NF-029/038台帳・アクセシビリティ

各項目は着手時にIssueを立て、実装・テスト後に本台帳の状況を更新する。

> **v3連鎖更新(2026-07-21):** OSS前提で課金F-070/071/072をWon't化、機能F-118/119・非機能NF-051/052を新設、F-005/078/079/100等を再分類。詳細は [requirements-cascade-review-2026-07-21.md](requirements-cascade-review-2026-07-21.md)。

## OSS前提の連鎖更新（課金系は対象外・2026-07-21）

要件本体（functional-requirements.md）は**OSS化前の商用前提「フル構想版」**で、課金系が古い前提のまま残っている（NF-027 法務確認は既にOSS免責で廃止済み）。本プロジェクトはOSS（公開・AS-IS免責・支援はGitHub Sponsorsの寄付）であり、**製品課金は行わない**。連鎖更新として以下を整理する（要件本体もv3で追随すべき候補）:

| ID | 名称 | 扱い | 理由 |
|---|---|---|---|
| F-070 | 透明な課金・解約UX | 🚫 Won't | OSS＝課金なし。解約導線も無い |
| F-071 | 無料試用 | 🚫 Won't | 全機能無料のため「試用」が成立しない |
| F-072 | 買い切り+サブスク | 🚫 Won't | 販売しない |
| F-073 | 権利ガイダンス表示 | ✅ 実装済 | `services/rights.py` + `rights` サブコマンド。採譜物の配布/販売時の著作権注意を教育的に表示、transcribe の JSON にも要約を添付。法的助言でない旨の免責つき。`test_rights.py` |
| NF-014/037 | コード署名・公証/署名配布 | 配布作業(非コード) | 無料OSSアプリでも警告なく起動させるための署名。課金ではなくビルド/リリース設定 |

※「業務/法務/配布＝ほぼ非コード」と一括りにしたのは誤り。F-073はコード、課金3件は対象外(Won't)、署名は配布設定、と分けるのが正しい。
