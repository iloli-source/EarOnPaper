# 譜面差分ハイライト調査報告  
## 2つのMusicXML/MIDIのピッチ・リズム差分可視化（X投稿ベース）

**調査日**: 2026-07-21  
**調査対象**: X（旧Twitter）実務者・研究者・開発者投稿（英語・中国語中心、日本語は需要補完）  
**調査範囲**: MusicXML/MIDI比較、git差分、採譜評価、Audio→MIDI失敗、ソフト間移行、MIR alignment  
**重要前提**: 「譜面差分ハイライト」という**完成プロダクト名での議論はX上ほぼ不在**。需要・失敗・限界は隣接領域（version control / OMR / AMT / MusicXML import）に散在。

---

## 0. エグゼクティブサマリー

| 観点 | 結論 |
|------|------|
| 製品成熟度 | **未成熟**。Git用の生XML diff需要はあるが、**意味論的な音高/リズム差分UI**はほぼ話題に上がらない |
| 失敗の主因 | (1) MusicXMLの冗長性 (2) レイアウト差分ノイズ (3) テンポ正規化失敗 (4) 多声音符/ペダル (5) 12平均律前提のMIDI |
| 成功の芽 | MuseScore→`.musicxml`でgit追従、MIDIを「比較可能な中間表現」にする、MIRのOnset F1/DTW alignment |
| 最新トレンド | 評価インフラ整備（aligned multitrack MIDI）、DTW並列化、Audio-to-Score alignmentの弱教師、OMR→MusicXMLパイプライン商品化 |
| 市場シグナル | 「欲しいが心折れる」投稿が成功事例より多い＝**pain is real, product is missing** |

---

## 1. 失敗例（特に多い／実装者が避けるべき罠）

### 1.1 生MusicXMLのtext diffは実務で死ぬ

**失敗パターン**: 楽譜のバージョン差分を取りたい → プロプライエタリ形式は解析不能 → MusicXMLならdiffできるはず → 仕様を読んだら心折れる / 可読性がなく死ぬ

- プログラマ/演奏者 **@t_motooka**  
  > 楽譜の前バージョンと新バージョンのdiffを取りたい…FinaleやSibeliusのファイルフォーマット解析はしんどすぎる。MusicXMLのdiffなら取れるかなと仕様を流し読みしたが…途中で心が折れた。  
  出典: https://x.com/t_motooka/status/1751802440582942999

- 実務者リプライ文脈 **@akito_kk**  
  > もしかしてmusicXMLで比較なら！？と思ったのですが普通に可読性なくてしにました  
  出典: https://x.com/akito_kk/status/1928808848632008838

- 英語研究者 **@Lari_island**  
  > MusicXML export… looks exceptionally ugly and verbose…  
  > MusicXML looks terribly verbose, there should be better formats  
  出典: https://x.com/Lari_island/status/2031988637546708994 / https://x.com/Lari_island/status/2032085927213089034

**示唆**: ハイライト機能を「XML行差分の色付け」で実装すると**即失敗**。人間が欲しいのは *musical semantic diff*（pitch/onset/duration/voice）であり、属性順序・レイアウト・エンコーディング差分ではない。

---

### 1.2 Git管理需要はあるがツールがない

- **@L17za**（英語投稿）  
  > I want to open musicXML file at vscode, and check diff. Because I want to manage my sheetmusic at git. What plugin should I use???? #musescore  
  出典: https://x.com/L17za/status/1882449648021020821

- 作編曲 **@m_yatani**  
  > Doricoのプロジェクトファイルのバージョン間の差分を取りたいけど無理…MusicXMLを介するdiffツールはあるらしい（readme読んだだけで触ってません）  
  出典: https://x.com/m_yatani/status/1790390673662972334（言及: musichub）

**示唆**: 「存在するかもしれないツール」への弱い期待はあるが、**使って満足した成功談はほぼゼロ**。探索段階で止まる。

---

### 1.3 Audio→MIDI / 自動採譜：テンポ・余分音・多声で破綻

| 失敗モード | 実投稿 | 意味 |
|-----------|--------|------|
| BPM固定で使い物にならない | **@that_kinda_song**: Piano Transcriptionはリアルだが「どんな曲もBPM120で吐き出される…使いもんにならなかった」 https://x.com/that_kinda_song/status/2068677013758791913 | ピッチが当たっても**リズム正規化失敗＝差分比較の前処理で死亡** |
| 書き出しBPMタイミングが合わない | **@DJ_OMKT**: audio to midiの書き出しBPMタイミングが全然合ってない → AbletonでMIDIタイムストレッチ補正 https://x.com/DJ_OMKT/status/2079374724967407621 | 差分ハイライト前に**時間軸アライメントが必須** |
| 余分な悪音を足す | **@dj_irl**: Ableton Audio-to-MIDI often gets it slightly wrong, **adding bad notes** → scaleに押し込んで近似 https://x.com/dj_irl/status/2016891106236256452 | FP（false positive pitch）が差分を赤だらけにする |
| 多声・ペダルがモデルを壊す | **@irshit0**（英語）: audio to midi for piano is genuinely hard — **polyphony pedal and overlapping notes wreck most models** https://x.com/irshit0/status/2071641834087215303 | 重なりノートの対応付けなしでは可視化が無意味 |
| 人間採譜でも精度50% | **@Animenzzz**: transcription technique… accuracy of hitting the right notes is like **50%** https://x.com/Animenzzz/status/1133199608983695360 | 「正解譜」自体が不安定だと差分の信頼性が崩壊 |
| マルチトラックにならない | **@old_pgmrs_will**: Audio-to-MIDIはシングルトラック変換になりがち https://x.com/old_pgmrs_will/status/2004843413775241353 | パート別差分が取れない |

**中国語側の失敗**:

- **@cups_table**（楽器音認識アプリ開発）  
  演奏音声からリズム・テクニック・**錯音・漏音**を判定し楽譜にマークする需要。しかし雑音・伴奏・メトロノームで結果がぶれ、訓練データもなく「2週間でできる」と言われて苦しんだ、という**実務失敗ログ**。  
  出典: https://x.com/cups_table/status/2032651377412067539

- **@Ishisashi_Ryuh**（中国語・微分音）  
  > MIDI 本身设计得太十二平均律中心了。十九平均律的偏差容易超过 64 音分…Pitch Bend 则需手动倍乘…不然音程不对  
  出典: https://x.com/Ishisashi_Ryuh/status/1915408600144675069  

  → ピッチ差分を半音グリッド前提でハイライトすると、**意図的な非12平均律が全部「エラー」になる**。

---

### 1.4 MusicXML相互運用：音符は近いが「差分ノイズ」だらけ

- 作曲家 **@missi0429**（Finale→Dorico via MusicXML、無修正比較）  
  > Textとレイアウト以外はほぼ変わらないが、五線や休符やフラットのラインはDoricoが太くダサい  
  出典: https://x.com/missi0429/status/1829141674674782293  

  → **音楽内容は同値でも視覚差分が出る**。レイアウト層を差分対象に含めると偽陽性。

- Sibelius公式が繰り返し「MusicXML import improvements」を告知（margins, multirests, Bass instruments, brackets…）  
  例: https://x.com/Avid/status/1864067124211146900  
  → 逆説的に、**長年importが壊れていた**ことの公式自白。ソフト間比較の前提が不安定。

- MuseScoreバージョン問題 **@kz_holiutschi**  
  旧データが新版で壊れ/開けない → レイアウト崩れを許容してでもMusicXML exportしておくべきだった  
  出典: https://x.com/kz_holiutschi/status/1970148603131048040

- 作曲家 **@keiryan0307**  
  > MusicXMLでの読み込みがどこまで再現できるか…比較できないのが痛い  
  出典: https://x.com/keiryan0307/status/1828215949176221903

---

### 1.5 比較UIの失敗（近傍領域）

- リズムゲーム譜面 **@hifish__**  
  > notes look way too similar to the normal notes because they keep a similar color scheme… frustrating  
  出典: https://x.com/hifish__/status/2078576570172690635  

  → **差分色が通常ノートと同系色だと視認性失敗**。形状差別化の提案（square dish）まで出る＝UI設計への実フィードバック。

- 手動ノート比較の例 **@snail_inactive**  
  > here's the actual note comparison, notice how the notes have the same placement and timing  
  出典: https://x.com/snail_inactive/status/2038720948451287359  

  → ユーザーは「ツール」ではなく**スクリーンショット手作業**でピッチ/タイミング比較している＝市場未充足の証拠。

---

### 1.6 失敗パターン早見表（実装チェックリスト）

| # | 失敗 | 投稿由来の根拠 | 対策の方向 |
|---|------|----------------|------------|
| F1 | 生XML diff | @t_motooka, @akito_kk, @Lari_island | 意味グラフ正規化後にdiff |
| F2 | レイアウト偽陽性 | @missi0429, Sibelius import fixes | pitch/rhythm層とlayout層を分離 |
| F3 | テンポ未正規化 | @that_kinda_song, @DJ_OMKT | 比較前にBPM/オンセットアライメント |
| F4 | 余分音・欠落音 | @dj_irl, @Animenzzz | match + insert/delete の編集距離可視化 |
| F5 | 多声/ペダル | @irshit0 | voice/staff単位の対応、ペダル別トラック |
| F6 | 12-TET前提 | @Ishisashi_Ryuh | セント単位の連続ピッチオプション |
| F7 | 色が似すぎ | @hifish__ | 色+形状+凡例の三重符号化 |
| F8 | 比較元が揃わない | @akito_kk（パート構成バラバラ） | パートマッピングUI必須 |
| F9 | プロプライエタリ形式 | @t_motooka, @m_yatani | MusicXML/MIDIを唯一の比較入力に限定し明記 |

---

## 2. 成功例・部分成功

### 2.1 MuseScore + MusicXML で git が「一応」回る

- **@hsjoihs**（エンジニア/研究者寄り）  
  > MuseScore で .musicxml を出力すると **diff が追えて便利です**  
  出典: https://x.com/hsjoihs/status/1713480003340620007  

**ただし**: 「追える」＝テキスト差分が取れる程度。**ピッチ/リズムのハイライト可視化の成功談ではない**。部分成功。

### 2.2 中間表現としてのMIDI/MusicXML共有

- **@chaosinthescore**  
  midもmusicxmlも頒布 → **音源と楽譜を比較すると構造がよくわかる**  
  出典: https://x.com/chaosinthescore/status/1893817293873766744  

→ 「差分ハイライト」ではなく**並列視聴・構造理解**としての比較成功。

### 2.3 MIR評価用のaligned MIDIデータセット

- **@OrchestralPit**（MIR研究フィード）  
  - MulTTiPop: 572 pop songs with **aligned multitrack MIDI**… **SOTA at 38% Onset F1—room to improve**  
    https://x.com/OrchestralPit/status/2075543197284000100  
  - Largest aligned piano MIDI… **note-level alignments**  
    https://x.com/OrchestralPit/status/2053488082725335533  

→ 「可視化プロダクト」ではないが、**ピッチ・オンセット対応付けのインフラ**が研究側では整備中。38% F1は「自動差分の正解率」がまだ低いことの定量証拠。

### 2.4 ソフト間移植の実務成功（比較の前提づくり）

- **@hidetakumi**（浄書・作曲教育）  
  Dorico流用のため可能な範囲でMusicXMLを書き出しておくべき  
  出典: https://x.com/hidetakumi/status/1828258708880830475  

- Flat **@flat_io** Opuscan  
  スキャン→MusicXML/MIDI→Flat/MuseScore/Dorico/Sibelius/DAW  
  出典: https://x.com/flat_io/status/2077069446087077893  

→ 比較入力の標準化パスは産業側で強化されている。

### 2.5 教育的「比較」ユースケース

- **@ScoreTail**  
  MusicXML portability; restは明示要素；every beat is accounted for  
  出典: https://x.com/ScoreTail/status/2068891747502244088  

→ 差分エンジン設計では**休符をギャップではなくイベントとして扱う**必要がある（公式説明と一致）。

---

## 3. 限界（投稿から抽出）

### 3.1 意味論 vs シリアライゼーション

MusicXMLは「可搬フォーマット」であり「diffフレンドリーな正準形」ではない。同一音楽内容でも:

- 属性順・タイ/スラーの分割
- 臨時記号の記譜法
- レイアウト・フォント・五線の太さ

で巨大なtext diffが出る（@Lari_island, @missi0429）。

### 3.2 評価指標の低さ

研究側SOTA Onset F1 ≈ 38%（@OrchestralPit / MulTTiPop）。  
→ 自動採譜結果と正解MIDIの差分ハイライトは、**大半が「モデル誤差」で赤くなる**可能性。プロダクトとしては「信頼度付き差分」が必要。

### 3.3 時間軸アラインメント問題

DTW alignmentの信頼度・並列化が2026年現在も活発な研究テーマ（@OrchestralPit: ParDTW, Segmental DTW, confidence scores）。  
→ 2ファイルをただ重ねるだけでは**ズレた差分**になる。

### 3.4 ドメイン外ノイズ

中国語実務（@cups_table）: 環境音・伴奏・メトロノームが識別を壊す。  
→ 「譜面同士の比較」と「演奏対譜面の比較」は別プロダクト。混ぜると失敗。

### 3.5 需要の断片化

「バージョン管理したい作曲家」「採譜誤差を見たい教育者」「モデル評価したい研究者」「移植後の崩れを確認したい浄書者」が同じ「差分」と言っているが要件が違う。

---

## 4. ベストプラクティス（投稿ベース合成）

1. **比較入力は MusicXML/MIDI に限定し、ネイティブ形式は対象外と明言**（@t_motooka の失敗回避）
2. **正規化レイヤを必ず挟む**  
   - 時間: BPM/オンセット正規化（@that_kinda_song, @DJ_OMKT）  
   - ピッチ: 半音 or セント切替（@Ishisashi_Ryuh）  
   - 声部: voice/staff マッピング（@akito_kk のパート比較需要）
3. **差分は編集操作として表現**  
   - pitch change / onset shift / duration change / insert / delete  
   - レイアウト差分はデフォルトOFF（@missi0429）
4. **休符は明示イベント**（@ScoreTail）
5. **可視化は色+形状+ラベル**（@hifish__ の「色が似てつらい」）
6. **信頼度を並べる**  
   - 自動採譜由来なら Onset F1 級の不確実性をUIに出す（@OrchestralPit）
7. **git用途なら「正準MusicXML」出力オプション**  
   - ソート済み属性、安定ID、レイアウト省略（@hsjoihs 成功条件の強化版）
8. **比較前のヒューマン確認**  
   - 手作業note comparison文化（@snail_inactive）を、ツールが置き換える対象として設計

---

## 5. 最新トレンド（2025–2026、X上）

| トレンド | 投稿シグナル | プロダクト含意 |
|----------|--------------|----------------|
| **評価インフラ** | @OrchestralPit 週次: transcription/aesthetics benchmarks が集中 | 差分ハイライトは「研究評価ビューア」としても売れる |
| **Aligned multitrack MIDI** | MulTTiPop, large piano alignment datasets | 正解アラインメント前提の可視化デモが可能に |
| **DTW高速化・信頼度** | ParDTW 100×, alignment confidence AUROC 0.97 | 長尺スコア比較が実用域へ |
| **弱教師 audio–score alignment** | FuSiLi: frame-level without local labels | 演奏↔譜面ハイライトのコスト低下 |
| **OMR→MusicXML商品化** | Flat Opuscan, PhotoScore推奨投稿 | 「スキャン譜 vs 手入力譜」差分ニーズ増 |
| **MusicXML import品質競争** | Sibelius 2024.x が連続改善告知 | 移植前後diffの市場タイミング |
| **AI採譜の実用と限界の両立** | Piano Transcription精度高いがBPM問題; Ableton FP notes | 「修正支援UI」としての差分が刺さる |
| **リズムゲーム譜面の多次元評価** | chart evaluation beyond note matching | ノート一致以外（難易度・配置品質）への拡張 |

---

## 6. 言語圏別の観測

| 言語 | 傾向 | 代表 |
|------|------|------|
| **英語** | MIR論文要約、DAW Audio-to-MIDI苦情、MusicXML verbose、Sibelius/Flat製品、多声の難しさ | @OrchestralPit, @dj_irl, @irshit0, @Lari_island, @flat_io |
| **中国語** | 微分音とMIDI限界、演奏採点アプリの雑音地獄、音源差によるMIDI聴感差 | @Ishisashi_Ryuh, @cups_table, @infoflashzz |
| **日本語（補完）** | **譜面version diff需要が最も明示的**。心折れ・可読性なし・git欲しい | @t_motooka, @akito_kk, @L17za, @hsjoihs, @m_yatani |

> 英語・中国語中心で探しても「Score Diff Highlight」製品議論は薄い。**明示的painは日本語圏の制譜者・開発者に濃い**一方、**技術的失敗モードの定量・研究語彙は英語MIR圏**、**エッジケース（微分音・騒音下採点）は中国語実務**に出る、という分業構造。

---

## 7. プロダクト示唆（調査から導く設計要件）

**Must（失敗投稿が示す非交渉条件）**
- Semantic note matching（pitch + onset + duration + voice）
- テンポ/時間軸アライメント
- レイアウト差分のデフォルト除外
- パート対応UI

**Should**
- 挿入/削除/置換の編集距離表示
- 信頼度/不確実性表示
- 正準MusicXMLエクスポート（git用）
- 色+形状の二重符号化

**Could**
- 演奏音声 vs 譜面（教育採点）— ただし別モード
- セント精度ピッチ
- リズムゲーム譜面評価の多次元指標

**Won’t（投稿が戒めること）**
- 生XMLの行diffをメインUIにする
- 12-TET固定のみ
- 色だけ・同系色ハイライト
- ネイティブ.dorico/.sib 直接解析をv1スコープに入れる

---

## 8. 出典一覧（主要ポスト）

| ID | 著者 | 種別 | URL |
|----|------|------|-----|
| 1751802440582942999 | @t_motooka | 失敗・仕様心折れ | https://x.com/t_motooka/status/1751802440582942999 |
| 1928808848632008838 | @akito_kk | 失敗・可読性なし | https://x.com/akito_kk/status/1928808848632008838 |
| 1882449648021020821 | @L17za | 需要・git+MusicXML | https://x.com/L17za/status/1882449648021020821 |
| 1713480003340620007 | @hsjoihs | 部分成功・diff追従 | https://x.com/hsjoihs/status/1713480003340620007 |
| 1790390673662972334 | @m_yatani | 需要・未検証ツール | https://x.com/m_yatani/status/1790390673662972334 |
| 2031988637546708994 | @Lari_island | 失敗・verbose XML | https://x.com/Lari_island/status/2031988637546708994 |
| 2068677013758791913 | @that_kinda_song | 失敗・BPM120固定 | https://x.com/that_kinda_song/status/2068677013758791913 |
| 2079374724967407621 | @DJ_OMKT | 失敗・BPM timing | https://x.com/DJ_OMKT/status/2079374724967407621 |
| 2016891106236256452 | @dj_irl | 失敗・bad notes | https://x.com/dj_irl/status/2016891106236256452 |
| 2071641834087215303 | @irshit0 | 限界・polyphony/pedal | https://x.com/irshit0/status/2071641834087215303 |
| 1133199608983695360 | @Animenzzz | 失敗・50% accuracy | https://x.com/Animenzzz/status/1133199608983695360 |
| 1829141674674782293 | @missi0429 | レイアウト偽差分 | https://x.com/missi0429/status/1829141674674782293 |
| 1864067124211146900 | @Avid | import改善＝過去の欠陥 | https://x.com/Avid/status/1864067124211146900 |
| 2075543197284000100 | @OrchestralPit | SOTA 38% Onset F1 | https://x.com/OrchestralPit/status/2075543197284000100 |
| 1915408600144675069 | @Ishisashi_Ryuh | 中国語・MIDI 12-TET限界 | https://x.com/Ishisashi_Ryuh/status/1915408600144675069 |
| 2032651377412067539 | @cups_table | 中国語・採点アプリ苦闘 | https://x.com/cups_table/status/2032651377412067539 |
| 2078576570172690635 | @hifish__ | UI色失敗 | https://x.com/hifish__/status/2078576570172690635 |
| 2038720948451287359 | @snail_inactive | 手動ノート比較 | https://x.com/snail_inactive/status/2038720948451287359 |
| 2077069446087077893 | @flat_io | OMR→MusicXMLトレンド | https://x.com/flat_io/status/2077069446087077893 |
| 2068891747502244088 | @ScoreTail | rests as events | https://x.com/ScoreTail/status/2068891747502244088 |

---

## 9. 調査限界・バイアス

1. **X上に「Score Diff Highlight」専用ハッシュタグ/製品議論はほぼない**。隣接語検索で再構成した二次構造化である。  
2. 英語・中国語指定でも、**最も直接的な「楽譜diff欲しい」は日本語投稿が濃い**（需要の地理的偏り）。  
3. MIR系（@OrchestralPit）は論文自動投稿でエンゲージメントは低いが、**トレンドの一次ソース**として有用。  
4. 成功例は「プロダクト成功」より「ワークアラウンド成功」が大半。  
5. GitHub/論文本体までは本調査の主対象外（X実投稿優先）。

---

## 10. 一文結論

X上の実務・研究・開発投稿を横断すると、**譜面差分ハイライトは「痛いほど需要があるが、生MusicXML diff・テンポ未正規化・多声対応失敗・レイアウト偽陽性でほぼ全員つまずく未開領域」**であり、成功談は MuseScore+MusicXML の粗いversion追従と、MIRのaligned MIDI評価インフラに限られる。製品化するなら **semantic note edit-distance + time alignment + layout-off by default** が投稿群から逆算される最低条件である。

---

**補足**: 作業ログのSlack投稿（#倉田_ログ）は、本環境にSlack MCPが接続されておらず送信できませんでした。接続後に転記が必要なら指示ください。
