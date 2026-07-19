> 【歴史的記録】本書は作成時点の前提・知見に基づくスナップショットです。その後の決定により一部前提は更新されています。現在の前提は `README.md`・`docs/requirements/product-vision.md`・`docs/research/gate-execution-spec.md`(最新改訂) を参照してください。

Slackログは未投稿です。この環境では `send_message` 系のSlack送信ツールが公開されておらず、`tool_search` でも直接送信用アクションを取得できませんでした。

**対象要件**
[functional-requirements.md](<repo>/docs/requirements/functional-requirements.md:10) は `F-001`〜`F-075` の75件、[non-functional-requirements.md](<repo>/docs/requirements/non-functional-requirements.md:12) は `NF-001`〜`NF-031` の31件として確認しました。

**1. 欠落要件リスト**
| 提案ID | 欠落要件 | 既存対応 | 提案カテゴリ | MoSCoW | 根拠 |
|---|---|---:|---|---|---|
| GAP-01 | `**kern`/Humdrum 形式の内部評価入出力と `CER/WER/LER/MV2H` ベンチ対応 | `NF-019`はMV2Hあり、形式要件なし | 評価/出力 | Should | MIREX 2026 A2S は `**kern` 出力、WER/MV2Hを主順位基準としている  |
| GAP-02 | TAB受入条件: `TAB` clef、`staff-lines`、`staff-tuning`、`capo`、`show-frets`、弦/フレット整合 | `F-032/F-048/F-052/NF-011`が粗い | 規格準拠 | Must | MusicXML 4.0 はTAB clef、staff-details/tuning/string/fretを定義      |
| GAP-03 | ギター奏法の自動検出: bend/slide/hammer-on/pull-off/tap/harmonic/open-string の候補出力と信頼度 | `F-045`は編集のみ | 解析/TAB | Should | MusicXML technical は奏法要素群を持ち、TENTや技法データセットは奏法が採譜を難化させると扱う    |
| GAP-04 | ギターTAB品質評価: string/fret accuracy、playability、人間評価、標準/変則チューニング別ベンチ | `F-028/F-029`のみ | 採譜品質 | Must | MIDI-to-Tabは弦割当の組合せ問題とplayability user studyを採用、GAPS/GuitarSetはギター専用データ    |
| GAP-05 | ステム分離の品質ゲート: stem別SDRだけでなく、採譜への悪影響を測る note-wise MSS 評価 | `F-003`のみ | 前処理/評価 | Should | Demucsは4 stem中心、6-sourceはguitar/pianoにbleeding/artifactsあり。ISMIR 2024は分離を音符単位で評価   |
| GAP-06 | ドラム採譜の受入条件: キットクラス、tom/cymbal、同時打音、伴奏干渉、GM Drum Map/MusicXML percussion mapping | `F-018/F-036`が抽象的 | ドラム/TAB以外記譜 | Should | 2025研究はtom/cymbal、同時オンセット、 melodic interference を制約として報告。MusicXMLもpercussion pictogramを定義   |
| GAP-07 | SMuFL準拠フォント・記号セット検証 | `F-030`のみ | エングレービング | Should | SMuFLは記譜記号の標準 glyph mapping。ギター、ドラム、コード図、TAB系 glyph 群も含む  |
| GAP-08 | MIDI 2.0/UMP対応方針: MIDI 1.0互換、per-note control、Property Exchangeを採譜結果へどう落とすか | `F-049`のみ | 出力/互換性 | Could | MIDI 2.0はMIDI 1.0を置換せず拡張し、UMP/Property Exchange/per-note controlを持つ  |
| GAP-09 | MNXは監視対象に留める要件: stable標準でないためMust出力にしない | なし | 標準動向 | Could | MNXはMusicXML後継を志向するが、まだwork in progressでstable implementation標準ではない  |
| GAP-10 | 評価指標の限界明記: mir_evalはピアノロール的note単位、MUSTERはMusicXML score差分、MV2Hは複合だが全要素を常に測れない | `NF-019`に列挙のみ | 採譜品質 | Must | mir_evalは単一ピッチnote集合でinstrument-agnostic、MUSTERはMusicXML同士の編集距離、MV2Hはvoice/metric/harmonic等の複合評価    |

**2. 技術的に楽観すぎる要件**
| 要件ID | 判定 | 根拠 |
|---|---|---|
| `F-019` 多声部一括採譜 | Phase3 Couldでも「フルスコア一括生成」は研究ベンチ段階。受入条件なしだと過大。 | MIREX 2026 A2S自体が、MIDI止まりでなく「well-formed score」へ進むための新チャレンジとして設計されている  |
| `F-003` ステム分離 | 「ギター/ピアノ含む標準工程」は楽観的。 | Demucs v4は主に vocals/drums/bass/other。6-sourceは実験的でguitarはokay、pianoはbleeding/artifactsが多いと明記  |
| `F-021` リズム量子化 | Phase1 Mustで独自実装は妥当だが、成功基準が軽い。 | A2S研究では monophonic でも metering/barline が主要誤り。2024のMIDI-to-score Transformerも入力はaudioでなくperformance-MIDI   |
| `F-028/F-029` TAB運指・変則チューニング | 音声から直接の実用TABまでを暗黙に期待すると過大。 | MIDI-to-Tabはsymbolic inputからstring assignmentを推定する研究。音声→TABの完全系ではない  |
| `F-018` ドラム採譜 | 「キット別自動採譜」は、クラス別・同時打音・伴奏干渉を分けないと過大。 | 2025 ISMIR論文は、DTMでは伴奏干渉、DTDでは同時オンセットが主要制約と報告  |
| `NF-017/NF-004` CPUのみ・3分曲5分以内 | 可能性はあるが、現行要件は全機能一括で保証しすぎ。 | 最新ピアノ転写は計算量削減研究が出ている一方、ONNX/Core ML量子化は精度劣化があり得るため、機能別ベンチが必要 ([arxiv.org](https://arxiv.org/abs/2503.01362))   |

**3. 規格準拠の欠落**
- MusicXML TAB: `clef/sign=TAB`、`staff-details/staff-lines/staff-tuning/capo/show-frets`、`technical/string/fret`、`hammer-on/pull-off/bend/tap/harmonic/open-string` を受入条件化すべきです。
- MusicXML Drum: `percussion` pictogram、percussion clef、unpitched note、キット音色マップの互換テストが未定義です。
- SMuFL: PDF/画面描画で使う glyph 名、フォントメタデータ、ギター/コード図/ドラム記号の表示検証が未定義です。
- MEI: Verovio利用や学術系互換を狙うなら、MEI tablature の `tab.course/tab.fret/tabGrp/tabDurSym` への対応方針が必要です 。
- MIDI 2.0: `F-049`はMIDI 1.0相当のままなので、UMPやper-note controllerを「非対応/対応」のどちらで切るか明記が必要です。
- MNX: 現時点では監視対象。正式出力要件にする根拠は見つけていません。

**4. 調査カバレッジ**
- 検索済み: ISMIR 2024/2025、arXiv 2024-2026、MIREX 2026 A2S、MusicXML 4.0、MEI、SMuFL、MIDI 2.0、MNX、MV2H、MUSTER、mir_eval、Demucs/Source Separation、GuitarSet/GAPS、drum transcription。
- 見つからなかった領域: 2026年7月時点で、商用品質の「混合音源→全パートMusicXML/TAB完全譜」一次資料、混合音源からbend/slide/hammer-on等まで含む汎用ギターTAB SOTA、安定版MNX実装要件。
- 結論: 既存106件は方向性を広く押さえていますが、プロダクト受入条件に落ちるべき「TAB規格細目」「評価形式」「分離/ドラム/奏法の失敗モード」「オンデバイス性能の機能別ゲート」が不足しています。
