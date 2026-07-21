# F-019: 多声部一括採譜（バンド／アンサンブルのフルスコア生成・小編成2-3パート）— 論文＋WEB調査

> 調査手段: `mcp__codex__codex`（cwd: 採譜）による Web リサーチ。主要URLは WebFetch/WebSearch で実在検証済み。
> 方針: 失敗例の最大化。英語・中国語ソース中心。実在URLのみ併記。捏造禁止。
> 調査日: 2026-07-21

---

## エグゼクティブサマリー（結論）

「混合音源（band/ensemble のミックス）から、楽器ごとに分離された、記譜可能なフルスコアを確実に生成する」機能は、**現時点の学術・商用いずれにも成功例がほぼ存在しない**。使える成果はソロピアノ、単一楽器のポリフォニー、合成マルチトラック（MIDI風出力）に限定される。

失敗は累積構造になっている:

1. **マルチピッチ検出（multi-F0）そのものが不完全**（楽器割り当て以前の段階）。
2. **ノートトラッキング（onset+offset）はピッチ検出よりさらに悪化**。休符・音価・声部連続性が絡むと崩壊。
3. **音源分離（source separation）は採譜ではない**。同音・同系音色・倍音重畳・内声・弱音で最も破綻。
4. **MIDI風イベント出力 ≠ フルスコア**。五線・声部割当・拍子・小節線・調号・異名同音の綴り・音価・タイ・休符・音部記号・レイアウトが別途必要。
5. **混合音源から正しいフルバンドスコアを確実に出す独立検証済みシステムは事実上ゼロ**。公開されている最良の証拠も、ピアノ限定／合成データ／短いクリップ／粗いステム分離／ノートイベント(MIDI)止まりのいずれか。

---

## 1. 「混合アンサンブル音源→フルスコア」が要求するもの

2-3パートのアンサンブルでも、フルスコア生成器は以下を同時に解く必要がある:

- 全同時ピッチの検出
- ピッチを onset/offset を伴うノートに分割
- 各ノートを正しい楽器／声部に割当
- 時間方向の声部連続性の保持
- 拍子・ビートグリッド・音価・休符・タイ・小節線・調・音部記号・綴りの推定
- ピアノロール/MIDIではなく妥当な**記号スコア**の出力

MIREX 2026 の Audio-to-Score(A2S) タスクは、まさにこのギャップを課題定義している（従来のMIREX AMTはMIDI/ノートイベント止まり、A2Sは五線・拍子・音部・調号・小節構造を含む可読スコアを要求）。声部/楽器識別にはメタデータ補助が要る前提で blind/staves-informed の2トラックを用意している。
→ **F-019への含意: MIDI採譜機能はフルスコア機能ではない。**

- MIREX A2S 参考論文（Zeng et al. 2024, 実世界ポリフォニックピアノ A2S / 階層デコード）: https://arxiv.org/abs/2405.13527 （PDF: https://arxiv.org/pdf/2405.13527 ）

---

## 2. MIREX の証拠: Multi-F0 とノートトラッキングは混合楽器で依然弱い

### 2.1 Multiple Fundamental Frequency Estimation and Tracking

MIREX 2018 の Multi-F0 タスク（木管・IAL四重奏・合成RWC、ポリフォニー2-5）では、**MF0 estimation で accuracy が約 0.42〜0.50 台**という水準。記譜以前に、フレームレベル内容の約半分が正しく表現できていないという警告。

- MIREX 2018 Multiple F0 Estimation & Tracking Results:
  https://www.music-ir.org/mirex/wiki/2018:Multiple_Fundamental_Frequency_Estimation_%26_Tracking_Results

### 2.2 ノートトラッキングはピッチ検出よりさらに悪い

同ページの Note Tracking（mixed set）で、**onset+offset を要求すると平均 F値が 0.30 / 0.21 程度**まで低下。onset-only の緩和スコアでも 0.50 / 0.37 止まり（offsetの正しさは含まない）。
→ スコアは音価・休符・タイ・声部連続性を必要とするため、offset を外す系は信頼できる記譜を生成できない。

### 2.3 現行 MIREX「Polyphonic Transcription」も大半はピアノMIDI

MIREX 2024 のポリフォニック採譜は**ソロピアノ audio-to-MIDI**が対象（onset/offset/pitch/velocity/sustain を MIDI で要求）。混合アンサンブルのフルスコアではない。

- MIREX 2024 Polyphonic Transcription Results:
  https://music-ir.org/mirex/wiki/2024:Polyphonic_Transcription_Results

  **注意（数値の扱い）**: このページの見出し指標「average note onset F1」は強豊なピアノ系で高い（例: Transkun V2 Aug ≈ 0.9648, teamWLY ≈ 0.9592, Transkun V2 ≈ 0.9490, hFT-Transformer ≈ 0.9416, wlazbzfll ≈ 0.7066）。ただしこれは**ソロピアノ・onsetのみ**の値であり、より厳しい onset+offset+velocity やデータセット横断（MAPS等）では大きく低下する。**「ピアノMIDIのonset検出が高い」ことは「混合バンドのフルスコアが解けている」ことの証拠にはならない。**

### 2.4 MIREX 2025 小編成タスクも MIDI であり、類似音色を除外

MIREX 2025 の Polyphonic Transcription Challenge は「最大3楽器の小編成」を対象とし F-019 に近いが、要求は**楽器ラベル任意付きの MIDI イベント**で、フル記譜ではない。さらに**音色が近い組合せ（violin/viola, oboe/bassoon 等）は出題から除外**すると明記。
→ 失敗例として重要: 小編成向けに設計された課題ですら、同系統の組合せは音源帰属が難しく回避されている。

- MIREX 2025 Polyphonic Transcription Challenge:
  https://www.music-ir.org/mirex/wiki/2025:Polyphonic_Transcription_Challenge

---

## 3. Audio-to-Score の証拠: スコアレベル出力は依然「新規・制約付き」

### 3.1 A2S は MIREX 2026 で「タスク定義」段階（解決済みではない）

MIREX 2026 A2S は CER/WER/LER/MV2H といったスコア品質指標を定義し、WERとMV2Hを主ランキング基準とする。妥当な `**kern` 出力（メタデータ・ピッチ・音価・小節線・声部/楽器構成）を要求。**公開リーダーボード（結果）は確認できなかった** → A2Sは「フルスコア出力がベンチマーク上の欠落ステップと認識されている」証拠であって、「解決済み」の証拠ではない。

### 3.2 既存 A2S 論文も統制条件下で大きな誤り率

Liu, Morfi & Benetos (ICASSP 2021) のポリフォニックピアノ A2S は、統制ピアノデータで**WER が概ね 35〜37% 台**（右手 WER 37.6 / 左手 35.3 / 全体 36.5、MV2H 87.8）。これは**ピアノ**であり混合アンサンブルではない。36% の token 誤り率は「出版可能な楽譜」品質ではない。

- 論文: "Joint Multi-pitch Detection and Score Transcription for Polyphonic Piano Music"
  https://arxiv.org/abs/2007.09805
- 付随コード（MuseSyn / MV2H 評価）: https://github.com/cheriell/PianoTranscription （著者リポジトリ系。URLは実行時に要再確認）

### 3.3 近年のポリフォニック A2S も大半がクラシック/合成/kern中心

MIREX 2026 A2S の Quartets データセットは Humdrum `**kern` から合成、非公開評価セットを含む。blind と staves-informed の両トラックを用意 = audio単独からの blind フルスコア抽出は難しいという認識の裏返し。Zeng et al. 2024 は「実世界ポリフォニックピアノA2Sは重要だが未探索」「先行end-to-endピアノA2Sは調号・拍子等の小節レベル情報に苦戦、合成データ依存」と述べる（中国語要約が存在）。

---

## 4. なぜ音源／声部分離が破綻するか

### 4.1 ステム分離ベンチマークはフルスコアには粗すぎる

音源分離の定番 MUSDB18 のターゲットは drums / bass / vocals / **other** の4つのみ。"other" は残り伴奏の一括で、guitar/piano/strings/synth 等の個別分離ではない。データセットには bleed（漏れ）や誤ステム混入といった実データエラーも記載。
→ フルスコアには "other accompaniment" は役に立たない。スコアは個別楽器パートを必要とする。

- MUSDB18: https://sigsep.github.io/datasets/musdb.html
- Demucs（drums/bass/vocals をその他伴奏から分離）: https://github.com/facebookresearch/demucs

### 4.2 粗いステムでも分離品質は完璧ではない

Hybrid Transformer Demucs は MUSDB で SOTA でも SDR ≈ 9.2 dB（追加学習データ使用時）程度。SDX'23 も広義デミックスで進展（平均SDR ≈ 9.97 dB, MDX'21 の 8.33 dB から改善）。**SDR は記号的正しさではない**。分離ステムは聴感上妥当でも、弱い内声の欠落・アタック不鮮明・アーティファクト・他楽器漏れを含み、それがそのまま採譜を汚染する。

- Hybrid Transformer Demucs 論文: https://arxiv.org/abs/2211.08553

### 4.3 同音衝突は構造的に曖昧

Melodyne 公式ドキュメントが明快な商用失敗例を提示: ポリフォニックDNAは**単独録音のポリフォニック楽器**向け。同一トラックで2楽器が同じ音を弾くと、個別blobではなく**合成音の単一blob**になる。
→ アンサンブル記譜の根本的曖昧性: violin と flute が同時に A4 を出すと、音声中に2音へ分けるだけの分離可能な証拠が存在しない場合がある。

### 4.4 類似音色はベンチマークで明示的に回避される

MIREX 2025 小編成タスクは violin/viola・oboe/bassoon 等を音色類似のため除外（§2.4 再掲）。2-3パート製品の具体的失敗モード: レジスタ・スペクトル包絡が近い楽器で小編成でも問題化する。

---

## 5. 現行研究システム: 有用だがフルスコア信頼性はない

### 5.1 MT3 は強力なMIDI風マルチトラックベースラインであってフルスコアではない

Google MT3 は AMT の難しさ（複数楽器・精密なピッチ/タイミング・低リソース）を明示し、任意の楽器組合せを横断的に採譜できたモデルは存在しなかった、先行系は固定楽器ヘッド／楽器ラベル無視／全ノートを単一ピアノロールに統合、と述べる。**出力はMIDI風イベントであり記譜ではない**。GitHub は非公式・学習は容易でないと明記。

- MT3 論文: https://arxiv.org/abs/2111.03017
- MT3 GitHub: https://github.com/magenta/mt3

### 5.2 実世界ポップ・マルチトラックAMTは依然低性能（最重要の失敗証拠）

MulTTiPop（2026, 実世界ポップ・マルチトラック採譜データセット, 572セグメント/約3.5時間）は、**SOTA AMTでも最良で Onset F1 が約 38%** と報告。合成ベンチマークに比べ実世界マルチトラックの困難さが顕著。バンド的素材における「成功例ゼロ」信号として最も直接的。

- MulTTiPop 論文: https://arxiv.org/abs/2607.08756 （HTML: https://arxiv.org/html/2607.08756v1 ）
- 中国語含む解説（英中対訳ブログ）: https://alanhou.org/blog/arxiv-multtipop-a-multitrack-transcription-dataset-for/

---

## 6. 商用システム: フルバンドスコアの信頼できる証拠なし

### 6.1 Basic Pitch（Spotify）

audio-to-MIDI ドラフトとして有用・ポリフォニック対応・楽器非依存。ただし公式README が **"works best on one instrument at a time"（一度に1楽器が最良）** と明記。Spotify のエンジニアリング記事もポリフォニーの難しさ（時間/周波数の重畳、ノートグルーピングの曖昧性、楽器横断の汎化困難）を説明。
→ Basic Pitch系はドラフトのノート抽出用であり、信頼できるフルバンドスコアではない。

- Basic Pitch GitHub: https://github.com/spotify/basic-pitch

### 6.2 Melodyne

単独録音の1楽器（ピアノ/ギター等）のポリフォニック編集は可能だが、DNAは**楽器ではなくピッチで分離**、同音の複数楽器混合は1blobに潰れる（§4.3）。混合アンサンブルのパート抽出に対する明示的な商用限界。

- Celemony Melodyne（DNA/ポリフォニック）: https://www.celemony.com/en/melodyne/what-is-melodyne

### 6.3 AudioScore

AudioScore Ultimate は「ポリフォニック認識」「自動楽器編成・スコア作成」を謳うが、**混合音源から正しいフルバンドスコアを確実に生成できるという独立ベンチマークは確認できなかった**。自社機能ページはマーケティング主張であり研究級の信頼性の証拠ではない。

- Sibelius AudioScore: https://www.avid.com/sibelius / https://www.neuratron.com/audioscore.htm

---

## 7. F-019 に記載すべき失敗例カタログ

### A. ピッチレベルの失敗
- 大きい音の下の弱い内声を取りこぼす
- 倍音（特にオクターブ/5度の部分音）による誤検出
- 基音が弱い/マスクされる時のオクターブ誤り
- アタックが非同期な和音構成音の統合/欠落
- 速い連打が1つの長い音に潰れる

### B. ノートトラッキングの失敗
- onset正しいが offset 誤り
- 分離アーティファクトでサステインが切れる
- レガートが連打に分断される
- 残響の尾を音の継続と誤認
- 装飾音の脱落/過剰記譜
（MIREX 2018 数値: mixed set の onset+offset F ≈ 0.30/0.21、緩和onset-only ≈ 0.50/0.37）

### C. 声部／楽器割当の失敗
- 2楽器の同音が1イベントになる
- violin/viola, oboe/bassoon, guitar/keyboard pad の混同
- ベースギターとピアノ左手低音の統合
- ダブリングが2五線に表現されない
- 音色変化が弱いとメロディが楽器間を飛ぶ
- 伴奏オスティナートが誤ったパートに割当

### D. スコア構造の失敗
- 拍子/小節線の位置誤り
- リズムの量子化ミス
- タイ/休符の欠落
- 異名同音の綴り誤り
- 音部/五線割当の誤り
- アウフタクト/連符の誤処理
- 妥当なMIDIだが無効/不可読な記譜
（MIREX 2026 A2S が WER/LER/MV2H を用いる = 行レベル・声部レベルの整合が別個の失敗面）

---

## 8. 中国語ソースの補足

中国語ソースも同じ核心を反映: AMTはMIRの中心課題だが、複雑な倍音構造と解釈的ニュアンスにより現行システムは専門家精度に達していない。BAAI(智源)の 2024 AMT サーベイ中国語要約は「進展にもかかわらず専門家精度未達」と述べる。単耳ポリフォニック自動採譜に関する中国の特許も「ポリフォニック音楽は複雑」「既存装置は不正確な楽譜情報/低いスコア精度を生じうる」と枠づける。MulTTiPop の英中対訳解説（§5.2, alanhou.org）も「自動採譜がまだどれだけ遠いかを明らかにする」と要約。

（注: BAAI要約・特許は具体URLの実行時再検証を推奨。捏造回避のため本文では確度の高い MulTTiPop 中文解説URLのみ確定掲載。）

---

## 9. F-019 への製品的含意

### 推奨ポジショニング
「混合音源から正しいフルバンドスコアを確実に一括生成」を**信頼できるバッチ機能として仕様化しない**。安全な仕様は:
> 混合音源から**編集可能なドラフト**採譜を生成。信頼度警告付き、ステム/事前分離入力の任意受入、重畳楽器・類似音色・密なポリフォニー・ドラム・ボーカル・フルミックスに対する明示的限界を提示。

### 能力ティア
- **Tier 1: ソロ／単一楽器ポリフォニー**（ピアノ・ギター・独奏弦・分離済みステム）— 有用出力の可能性最高
- **Tier 2: 楽器編成既知の小編成**（2-3楽器・クリーン音源・重畳少・音色差あり・ユーザ提供の五線/楽器メタデータ任意）
- **Tier 3: 混合バンド音源** — 実験的扱い。出力は「score」でなく「draft / unreliable」とラベル

### 必須UXセーフガード
- ノート/領域ごとの信頼度表示
- 採譜前に楽器編成/五線をロック可能に
- ノートのパート間手動再割当を許可
- ステムアップロード/DAW書出しの分離トラック対応
- 「complete score」でなく「draft MusicXML/MIDI」表記を優先
- 同レジスタ/同音色の重畳を高リスクとしてフラグ
- 人間レビュー無しに出版可能精度を示唆しない

---

## 10. ボトムライン

SOTA が支えるのは **assisted transcription（支援採譜）** であって、混合バンド音源からの信頼できるフルスコア生成ではない。MIREX と近年研究は、アンサンブルのスコアレベル採譜の**評価基盤自体がまだ構築途上**であることを示す。音源分離は有用な前処理だが、粗いステム出力と漏れ/アーティファクトの失敗モードによりパート精度の記譜には不十分。商用系も1楽器ずつ対象か、信頼できるフルバンドスコア生成の独立証拠を欠く。F-019で技術的に擁護可能なのは、**分離済みステムor既知小編成に制約した、信頼度考慮の編集可能ドラフトスコア・ワークフロー**。危険な機能主張は「混合音源から自動で正しいフルスコア」。

---

## 参照URL一覧（実在検証済み中心）

- MIREX 2018 Multiple F0 Estimation & Tracking Results: https://www.music-ir.org/mirex/wiki/2018:Multiple_Fundamental_Frequency_Estimation_%26_Tracking_Results
- MIREX 2024 Polyphonic Transcription Results（検証済み実在）: https://music-ir.org/mirex/wiki/2024:Polyphonic_Transcription_Results
- MIREX 2025 Polyphonic Transcription Challenge: https://www.music-ir.org/mirex/wiki/2025:Polyphonic_Transcription_Challenge
- Zeng et al. 2024 End-to-End Real-World Polyphonic Piano A2S（検証済み実在）: https://arxiv.org/abs/2405.13527
- Liu, Morfi & Benetos 2021 Joint Multi-pitch Detection and Score Transcription: https://arxiv.org/abs/2007.09805
- MulTTiPop 2026（検証済み実在, 最良 Onset F1≈38%）: https://arxiv.org/abs/2607.08756
- MulTTiPop 英中対訳解説: https://alanhou.org/blog/arxiv-multtipop-a-multitrack-transcription-dataset-for/
- MT3 論文: https://arxiv.org/abs/2111.03017 / GitHub: https://github.com/magenta/mt3
- Basic Pitch（"works best on one instrument at a time" 検証済み）: https://github.com/spotify/basic-pitch
- Hybrid Transformer Demucs: https://arxiv.org/abs/2211.08553 / Demucs: https://github.com/facebookresearch/demucs
- MUSDB18: https://sigsep.github.io/datasets/musdb.html
- Melodyne: https://www.celemony.com/en/melodyne/what-is-melodyne
- AudioScore(Neuratron/Avid): https://www.neuratron.com/audioscore.htm

> 検証メモ: 上記のうち MIREX 2024 結果ページ・arXiv 2405.13527・arXiv 2607.08756(MulTTiPop)・spotify/basic-pitch の文言は WebFetch/WebSearch で実在確認済み。arXiv 2007.09805 / 2111.03017 / 2211.08553 は標準的な既知論文だが、引用前に最終確認を推奨。著者コードリポジトリ・BAAI要約・中国特許のURLは実行時に個別再検証を推奨（捏造回避のため確度の高いもののみ本文確定掲載）。
