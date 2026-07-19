# EarOnPaper 出力側3機能 辛口レビュー

前提: `docs/quality/function-critique-protocol.md:5-15` の3錨と証拠義務に沿って、コード読解、既存XML再解剖、未テスト攻撃を実施。全pytestは読み取り専用環境のため未実行です。

## notate（綴り・譜面化）

### 基準3錨との照合
- 受入: C4は転調追従まで要求、C5は大譜表・小節数・拍子/調号・連桁検査、C6はMusicXML往復差分ゼロまで要求（`docs/requirements/core-requirements-v3.md:57-66`）。
- 実測: `turkish_pd.musicxml` は30小節、641 note要素、 pitched 410 / rest 231。`turkish_real.musicxml` は120小節、2514 note要素、 pitched 1926 / rest 588。
- 外部水準: 声部・譜表割当はGNN系でcross-staff voiceまで扱うのが比較対象（`docs/research/rounds/round1-codex-papers.md:41-43`）。現状はそこから遠い。

### P0/P1/P2
- **P0: 転調曲のC4受入を満たしていない。** `spelling.py` 自体が「全体1調のみ。転調・区間調は将来課題」と明記（`spike/ear-pipeline/earpipe/services/notate/spelling.py:6-8`）。未テスト攻撃でも E minor→E major は `global_key e minor` に潰れ、Db→D 素材は `global_key b minor` に誤推定。C4の「Romanze: Em→Eで調号切替に追従」と正面衝突。
- **P0: 声部を捨てている。** `_cap_overlaps` は重なりを次グループ開始で打ち切り、「失われる持続」を将来課題にしている（`score.py:93-100`）。これは譜面化ではなく、破綻を隠すための音価切断。C5の「五線譜生成」としては音楽内容を保存していない。
- **P1: 大譜表は実装済みだが、左右手ではなく中央C分割。** `split_hands` は MIDI 60 以上をtreble、未満をbassに分けるだけ（`score.py:65-90`）。再解剖でも PD/real とも staff1 は MIDI 60以上100%、staff2は59以下100%。これは「左右手割当」ではなく高さ分類。
- **P1: 休符連鎖は改善したが休符密度はまだ汚い。** 最大連続休符は PD=2、real=3まで改善。一方、PDは小節内rest数>4が17箇所、realは12箇所。例: PD measure 3 は16分音符と16分休符の交互羅列（`tools/ai-ears/testdata/demo/turkish_pd.musicxml:433` 以降）。
- **P1: 弱起を表現できない。** `TIME_SIGNATURE = "4/4"` 固定、開始0から休符充填（`score.py:19-20`, `score.py:221-224`）。攻撃 `pickup_at_beat_3` は1小節目の3拍目開始として出るだけで、anacrusis/implicit measureにならない。
- **P2: stem/beamは付いたが、品質検査が浅い。** testsは「stemが90%以上」「声部2以下」程度（`tests/test_notate_layout.py:117-156`）。連桁が拍境界を跨がない、声部が音楽的に正しい、手割りが弾ける、は未検査。

### 攻撃案
- 左右交差: 左手が高音に出る伴奏、右手が低音に潜る旋律。実測攻撃では `right_hand_low_melody` が treble `[62,64]` / bass `[57,59]` に分断。
- アルペジオ: 中央Cを跨ぐ1ジェスチャ。実測攻撃 `middle_c_arpeggio` は bass `[55,59]` / treble `[60,64,67]` に割れて、同一手の動きが分裂。
- 弱起曲: 実測攻撃 `pickup_at_beat_3` は2小節化し、弱起小節ではなく先頭休符入り通常小節になる。

### ダッシュボード行案
| 機能 | 現在スコア | 既知の限界 | 次候補 |
|---|---:|---|---|
| notate | 45/100 | 大譜表は出るが声部・手割り・転調・弱起は未達 | 区間キー推定、voice/staff推定、anacrusis、cross-staff攻撃テスト |

## engrave（PDF描画）

### 基準3錨との照合
- 受入: NF-011は主要ソフトで警告なく開ける互換性、XSD妥当性、対象アプリ別確認、ラウンドトリップ差分を要求（`docs/requirements/non-functional-requirements.md:47`）。
- 実測: `turkish_pd` はSVG 2ページ/PDF 2ページ/251,994 bytes、`turkish_real` はSVG 5ページ/PDF 5ページ/730,327 bytes。
- 外部水準: Verovio採択自体は妥当。ただしADRもLGPL配布時の告知・差し替え可能性をリリース前確認事項にしている（`docs/architecture/ADR-004-engraving-engine.md:17-24`）。

### P0/P1/P2
- **P0: Verovio警告を握りつぶしている。** 再レンダリングで `ties left open` が2件、`Insufficient space to draw mixed beam` が1869件。`render_svg_pages` は `loadData` とページ数しか見ず（`engrave.py:22-34`）、警告をメタ情報にも失敗条件にもしていない。
- **P1: レイアウト品質は「PDFがある」だけ。** `write_pdf` の返却はページ数、1ページ目note概数、bytesのみ（`engrave.py:42-65`）。詰まり、衝突、改頁、警告数、ページあたり密度は見ていない。`tests/test_engrave.py:40-59` もPDFヘッダとページ数中心。
- **P1: 巨大曲・特殊記号の堅牢性テストがない。** Verovio optionsは固定A4/scale 40（`engrave.py:11-19`）。長大曲、空に近い曲、タイ未閉じ、装飾、歌詞、コード、ペダル、クロススタッフの負荷試験なし。
- **P1: LGPL配布リスクが未完了。** ADRは「告知・差し替え可能性の担保が必要」と書くが、実装/requirementsには台帳・NOTICE・差し替え検証がない（`requirements.txt:1-11`）。Python wheel同梱/Electron同梱時の配布形態レビューが未固定。
- **P2: `notes_engraved` が1ページ目だけ。** 複数ページPDFでも `svg_note_count(svgs[0])` だけ（`engrave.py:60-64`）。real 5ページの後続ページ欠落を検知できない。

### 攻撃案
- 巨大曲: 10,000音符、16分密集、5分以上、ページ数/警告数/処理時間/メモリを記録。
- 空曲: 休符だけ、メタだけ、壊れたタイだけ。現在のテストは例外でも成功扱い（`tests/test_engrave.py:50-59`）で甘い。
- 特殊記号: lyric/harmony/frame/pedal/ornament/cross-staff/tremolo/tuplets を混ぜ、Verovio警告ゼロをゲート化。

### ダッシュボード行案
| 機能 | 現在スコア | 既知の限界 | 次候補 |
|---|---:|---|---|
| engrave | 40/100 | PDFは出るがVerovio警告1869件を無視、配布LGPL未固定 | 警告捕捉、ページ密度KPI、巨大/特殊記号ベンチ、NOTICE/SBOM |

## quality（AIの耳＝審判自身）

### 基準3錨との照合
- 受入: NF-019はNote F1/MUSTER/MV2H/MusicXML validity/人間評価、NF-020は小節拍数・休符過剰・譜表跨ぎ等の自動計測を要求（`non-functional-requirements.md:86-87`）。
- 実測: PDベンチはF1@100msで BP 0.709 / spike 0.676、score_rhythmは rescue 0.402 vs BP 0.387（`bench/results-pd.md:24`, `bench/results-pd.md:60-66`）。
- 外部水準: 評価はMUSTER/MV2H/MusicXML validity/小節整合/人間評価を併用すべきと既存調査にもある（`docs/research/rounds/round1-codex-papers.md:169-170`）。

### P0/P1/P2
- **P0: 審判が測っていないものが多すぎる。** 4指標はchroma/onset/tempo/health固定（`tools/ai-ears/ears.py:213-228`）。強弱、アーティキュレーション、声部正しさ、左右手、譜表、調号、臨時記号、PDF可読性は総合点に入らない。
- **P0: 自作エンジンに甘くなる構造バイアスが実測済み。** `bench/results-pd.md:28-29` が、ears出だし指標は格子吸着を報酬し、正解忠実度を測れていないと明記。つまり審判が後処理の癖を褒める。
- **P1: `score_rhythm` は声部・強弱・アーティキュレーションを無視。** `_notes_sec` は全instrumentのnoteを平坦化（`score_metrics.py:37-44`）、greedy matchはpitch/startだけ（`score_metrics.py:66-85`）。攻撃実測: velocityを80→1にしても `score_rhythm total=1.0`、2楽器へ声部分割しても `total=1.0`。
- **P1: healthは譜面健全性という名前に負けている。** 見ているのは短すぎる音、音域外、秒あたり密度だけ（`ears.py:164-208`）。攻撃実測: octave up は health 1.0、split instrumentsも health 1.0。
- **P2: 自己検証が合成29音符級で狭い。** validationは同一/音高改変/リズム崩し/無関係の序列確認（`validation-report.md:8-13`）。譜刻や声部の敵対例はない。
- **P2: chromaはオクターブ情報を原理的に落とす。** `chroma_cqt` 12音クラス比較（`ears.py:54-80`）。オクターブ違いに甘くなりやすい設計。

### 攻撃案
- 審判を騙す出力: 同じpitch/start/durationでvelocityだけ破壊、声部を全入替、左右手を全交換。現score_rhythmは満点を返せる。
- 譜面を騙す出力: 同じMIDI内容を単一声部・休符だらけ・高密度beam警告だらけMusicXMLにする。音の指標は高く、PDF可読性は低い。
- chroma攻撃: 全音を1オクターブ上下、または低音を高音に畳む。音名だけ合えばchromaが高止まりする危険。

### ダッシュボード行案
| 機能 | 現在スコア | 既知の限界 | 次候補 |
|---|---:|---|---|
| quality | 50/100 | 音高/出だし/テンポ/密度寄り。声部・強弱・譜刻可読性は盲点 | MUSTER/MV2H、MusicXML構造KPI、Verovio警告KPI、人間レビュー列 |

## 総評

出力側は「ファイルが出る」段階から「譜面として正しい」段階へまだ上がっていません。最優先P0は notate の転調・声部保持、engrave のVerovio警告捕捉、quality の自己採点バイアス除去です。

Slack作業ログは未投稿です。このセッションで利用可能なツール検索を2回行いましたが、指定の `send_message` で #代表_ログチャンネル（SLACK_CHANNEL_ID）へ直接投稿するSlackツールが提供されていませんでした。
