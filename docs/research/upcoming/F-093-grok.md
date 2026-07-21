# X調査レポート：人手仕上げ作業パッケージ出力  
（区間音源・下書きMusicXML・信頼度ハイライト／外部採譜者向け一式）

**調査日**: 2026-07-21  
**媒体**: X（旧Twitter）実投稿  
**言語優先**: 英語中心 ＋ 中国語試行（後述の通り中国語はスパムノイズが大きく、実務密度は英語・日本語投稿が厚い）  
**対象機能の対応関係**:

| パッケージ要素 | X上でよく語られる隣接トピック |
|---|---|
| 区間音源 | stem分離、区間切り出し、BPM/グリッド合わせ、マルチ頭合わせ |
| 下書きMusicXML | audio→MIDI→記譜、MusicXML import/export 互換破綻 |
| 信頼度ハイライト | 音声ASRの confidence 運用、alignment の unsupervised confidence、採譜品質の「どこを直すか」 |

---

## 1. 結論（先に）

1. **完全自動採譜は実務ではまだ「下書き」止まり**。バイラルな full-mix→MIDI でも、実測体感は「人力でもいける曲で約50%、無理な曲で約10%」級の辛口評価が出ている。  
2. **下書きMusicXMLの最大の失敗コストは「記譜としては開けるが、移調・スラー・テンポ・全音符結合などが壊れる」互換地獄**。採譜者への納品物として MusicXML 単体は危険。  
3. **信頼度ハイライトは音楽採譜より音声ASR／alignment研究側が進んでおり**、「低confidenceは見せない／要約に載せない」が現場の共通言語。  
4. **成功パターンは「フルミックス直叩き」ではなく「分離（stem/区間）→単一音色寄りでMIDI化→人が直す」**。  
5. **外部採譜者向け一式**は、技術精度以前に **メタデータ・頭合わせ・テンポマップ・著作権/ライセンス境界** の欠落で失敗する（制作納品の失敗談と構造が同型）。

---

## 2. 失敗例（多め・実投稿）

### 2.1 自動採譜そのものが「使えない下書き」になる

**A. ポピュラー音楽の自動採譜／コミュニティ譜面の品質崩壊**  
@T_R_E_X_12（2025-10-18）  
> The absolute state of music transcription for popular music is shocking. Open source resources like Musescore uploads are almost never right, usually incomplete, often in the wrong key, or losing the entire essence of the original writing... and AI still suck.  
→ **誤り／不完全／キー違い／本質喪失**が同時多発。外部採譜者に「下書き譜」を渡す前提でも、**キー誤りの下書きは修正コストが上がる**。

**B. 最新バイラル full-mix Audio-to-MIDI でも体感精度が低い（重要）**  
@CabbageLettuce1（2026-07-18）が Mirelo の Audio-to-MIDI を実試行:  
- 自分でも人力でいける曲: **約50%**  
- 自分だけでは絶望的な曲: **約10%**（認識結果 vs 原曲比較動画付き）  
- さらに「専用モデルより torch+Demucs+librosa をエージェントに持たせた方がいいのでは」→ 試したら **リード／コード／ベース／上物の区別が付かず悲惨**  
→ **「フルミックス一発」の失敗**と **「分離してもパート分離が崩れる」失敗**が同一スレで観測される。

**C. コード推定（採譜前段）への不信**  
同ユーザーは事前に  
> chord.tube も deCoda のコード推定でさえ悲惨なので、今のところ全く信用していない  
と明言。**コード下書きも信頼度なしでは毒**。

**D. 既存 audio-to-MIDI は「生の周波数ダンプ」で楽器演奏に使えない**  
@LatentDhruva（2026-04-18）  
> every existing tool gives you a raw frequency dump. totally useless for real instruments.  
→ 下書きが「音符の海」になり、**人手仕上げの出発点として悪化**する失敗モード。

**E. DAW内蔵 audio-to-MIDI が「少し間違った音を足す」**  
@dj_irl（2026-01-29）  
> Ableton often gets it slightly wrong, adding bad notes. instead of manually fixing it, just forcing it into scale tends to be a quick way to get close.  
→ **誤検知ノートの追加**が典型失敗。スケール強制は応急処置であり、**信頼度ハイライトがあれば誤ノート優先修正**が設計できる。

**F. Basic Pitch 系の「精度 vs 待ち時間」トレードオフ失敗**  
@kykukaz32768（2026-07-14）  
- Basic Pitch: 便利だが **MIDI変換が遅すぎ／エンドレス待ち**  
- 曲によっては **全く変換できない** → 精度は低いが速い Open Music AI に乗り換え  
→ 外部採譜パッケージでは **区間分割して並列処理しないと待ち時間で運用が死ぬ**。

**G. MIDI stem 生成のタイムアウト**  
@entrepeneur4lyf（2026-07-11）  
> I tried to get it to generate midi stems from a simple rock song yesterday and it timed out 3 times  
→ 単純なロックでも **3回タイムアウト**。パッケージ生成自体が失敗する運用リスク。

**H. OpenUTau 等の注意書き：伴奏付きだと品質が落ちる**  
@urchin_p（2026-05-17）  
> audio should be clean with no backing tracks, and results vary in quality  
→ **区間音源（クリーンな単独音源）を渡さない失敗**の直接証拠。

---

### 2.2 下書きMusicXML／記譜インターチェンジの失敗

**I. Finale→他ソフト: 全音符が全部「タイで繋がった二分音符」に崩壊**  
@yodaclaus（2009）  
> the guy exported to MusicXML from Finale, but it was a mess on the import. ALL the whole notes were tied half notes. ALL!  
→ 下書きMusicXMLが **リズム表記を破壊**する古典的大失敗。外部採譜者が「まずリズムを直す」地獄。

**J. 移調楽器＋調号なしの import でキーと音高が不正**  
@robertpuff（2020-03-01）  
Sibelius 原譜のホルン（調号なし Fmi）→ Finale import で **調号が出て音が不正**。  
→ 下書きMusicXMLの **移調・コンサートピッチ不一致**は人手仕上げの地雷。

**K. stem 要素が無視される**  
@Alan_R_White（Drum Score Editor 作者, 2021）  
MusicXML import が `<stem>` を選択的に無視。  
→ 符幹方向など **記譜意図が消える**。

**L. テンポが playback-only 要素で export され、import側が落とす**  
MusicXML 発明者 @MichaelDGood（2020）  
Finale から出た開始テンポが playback-only → **他ソフトの import 問題**と診断。  
→ 外部採譜パッケージに **テンポマップを MusicXML だけに頼るのは失敗**。

**M. 複数スラーの export バグ（後に Finale 修正）**  
@MusicXML 公式アカウント（2020）  
Finale の multiple slurs export 問題が 26.2.2 で修正、と説明。  
→ **スラー系アーティキュレーションは互換の歴史的弱点**。

**N. 現代実務：Dorico → Logic で MusicXML と MIDI の役割が分裂**  
@takuyah（2026-07-19）  
- MusicXML: 音楽記号は移行するが、音符・スラーは Logic デフォルト表示、**繰り返し未展開**、テンポざっくり  
- スタッフMIDI: 繰り返し展開・テンポ・音価・強弱が比較的残る  
→ **「MusicXML＝完全な譜面下書き」という期待が現場で崩れる**。パッケージは **MusicXML + MIDI + PDF + 音源** の多層が必須。

**O. MusicXML が「唯一の橋」だが品質競争が必要**  
@MichaelDGood（2024-08-30）  
Finale 終了後、Dorico / MuseScore / Sibelius の **MusicXML import 品質の大幅向上**を期待。  
→ 下書きMusicXML品質は **アプリ依存の未解決問題**として業界認知。

**P. オープンソースでも MusicXML 非 export がある**  
@MichaelDGood（2024-08-26）  
> open source does not mean open data（MusicXML export しない記譜ソフトがある）  
→ 外部採譜ワークフローの **出口ロックイン失敗**。

---

### 2.3 人手採譜・コミュニティ譜でも起きる「意味の失敗」

**Q. 記譜は綺麗だがメロディが全然違う**  
@MusicOfLee（2022）  
> The notation is actually completely fine. It's just entirely the wrong melody for that text!  
→ **見た目の正しさ ≠ 内容の正しさ**。信頼度ハイライトが「見た目」だけだと失敗。

**R. 複雑なフレーズを誤って変拍子に書いてしまう（後で4/4と判明）**  
@jazzanalysis 経由の Connie Han 採譜紹介（@echtzeitklavier, 2023）  
最初の版は 5/8・7/8 等の変拍子だらけ → よく聴くと **実は4/4**。  
→ **リズム解釈の過分割**は高難度曲の典型失敗。区間音源＋グリッド提示が有効。

**S. 有名曲でもオンライン譜の拍子が誤っていた例（Pyramid Song）**  
@DjRecode（2022）  
難曲として変拍子扱いされがちだったが、調査で **多くのオンライン譜が誤りで実際は4/4**。  
→ 「みんなが載せてる下書き」を信じると連鎖失敗。

**T. 市販ギターTAB本が「completely wrong」だったという業界談**  
ニュース投稿（Opeth ギタリストが TAB 本の誤りを回想）や、  
@Keith02（2026）: アーティストがサイン時に TAB 本の音をわざと直して遊んだ、という話。  
→ **人手成果物でも誤りが流通**。パッケージに **正本音源区間**がないと検証不能。

**U. 自分の採譜がベースの解釈を誤っていた（後で自己訂正）**  
@0t0shir00t0tr0（2026-07-19）  
ベースが他声と衝突すると思い込んでいたが、**採譜が間違っていた**と再聴で訂正。  
→ 人手でも誤り。**音源との同時再生検証 UI**がパッケージ価値になる。

---

### 2.4 「パッケージ納品」そのものの失敗（メタデータ／アライン）

**V. 制作データ送信の定番ミス（区間・マルチ・テンポ）**  
作詞作曲家 @TomoyaKinoshita（2024）— 学生の企業案件で頻出:  
- 2mix 無音  
- サンプルレート／BPM 未記載  
- コード譜・歌詞不備  
- **マルチの頭が揃っていない**  
- **テンポチェンジ曲なのにテンポデータなし**  
- トラック名が自分言語 等  
→ 外部採譜パッケージでも同型失敗が起きる。**区間音源は「切る」だけでは不十分で、頭合わせ・BPM・テンポマップが必須**。

**W. ライセンス／権利の失敗（技術成功でも事業失敗）**  
@nikskld（2026-07-12）MuScriptor について  
コード MIT / 重み **CC-BY-NC** / **入力音源の権利保持が必要**  
→ 外部採譜者に音源を渡す機能は **権利境界をパッケージ仕様に書かないと事故る**。

---

### 2.5 信頼度まわりの失敗（主に隣接分野だが設計示唆が強い）

**X. 低confidenceなのに転写を出してしまうことへの苛立ち**  
@an_engineer_log（2026-07-19）  
> if you have low confidence score on a transcription just don't transcribe it  
→ **信頼度ハイライトより強い運用: 低信頼は出さない**。  
※文脈は音声寄りだが、採譜UIでも「赤塗りで出す」vs「空欄で渡す」の設計分岐。

**Y. confidence が要約層に露出しないとボイスノートが汚れる**  
@sebuzdugan（2026-06-29）  
> voice notes get messy fast when transcription confidence isn't exposed to the summary layer  
→ **信頼度を下流（人手仕上げUI）に渡さない設計失敗**。

**Z. confidence 自体が過信されやすい**  
@IshwarJha（2026-07-15）LLM の confidence 100%→レビュー後 40–60% に落ちる話。  
→ 採譜でも **モデル自己申告confidenceの校正なし提示は危険**（過信失敗）。

---

## 3. 成功例・部分成功

### 3.1 「MIDI＝演奏／MusicXML＝記譜」の役割分担

@dspreadbury（Dorico / Steinberg, 2022）  
> If you need to preserve the played performance, use MIDI. If you want the notation, open the Score Editor... display quantise to clean up the notation, then use MusicXML.  
→ 成功パターン: **生演奏MIDIを直にMusicXML化しない。display quantize（記譜用量子化）後に出す**。  
下書きMusicXMLは **「演奏転写」ではなく「記譜仮説」** と明示すべき。

### 3.2 stem → Melodyne/Basic Pitch → 人手調整（実務フロー）

- @NoR3_Music（2026）: ボーカル録音→Melodyne or Basic Pitch で MIDI。**精度は高くないが0からより楽**。BPM合わせ必須。  
- @you12gui（2026）: 鼻歌録音→Melodyne MIDI化→調整→SynthV へ。  
- @sorane_aimusic（2026）: **ステム分解してから** Melodyne でベース／ドラム MIDI 化（時間はかかるが本格）。  
→ **区間／stem 音源パッケージの成功根拠**。

### 3.3 フルミックス一発の「デモとしての成功」と研究トレンド

- Mirelo × Kyutai の MuScriptor / Audio-to-MIDI: フルミックスから楽器別 MIDI、コード・キー・テンポも（製品投稿・解説多数）。  
- @OrchestralPit（2026-07-11）: **Transcription at Scale and Depth** が週次トレンド、MuScriptor + MulTTiPop データセットで実世界多楽器へ。  
→ **「自動下書き生成」レイヤの成功は進むが、人手仕上げ前提が残る**。

### 3.4 調整可能UI（quantize / scale / pitch bend）

NeuralNote（Basic Pitch ベース）紹介 @DanKornas（2026-07-21）  
ポリフォニー、ピッチベンド、**聴きながら調整→スケール／時間量子化**、D&D export。  
→ 成功する下書きは **固定MusicXML一発より、調整パラメータ付き中間表現**。

### 3.5 人手ジャズ採譜の「聞き直しで拍子を収束」

Connie Han 採譜（前述）: 複雑に見えても最終的に4/4へ収束。  
→ 成功する人手仕上げは **最初の記譜仮説を区間単位で棄却できる**こと。信頼度ハイライトは「最初の仮説の疑義」を示すのに向く。

### 3.6 MusicXML が Finale 脱出の実務ブリッジ

@MichaelDGood が Jason Loffredo の Finale→Dorico 移行動画を推奨（2024）。  
→ 下書きMusicXMLは **「完成譜」ではなく「移行・再編集の出発点」** として成功。

---

## 4. 限界（Xから抽出できる合意）

| 限界 | 根拠の要約 |
|---|---|
| フルミックス多楽器の音高・パート分離 | Mirelo 実測 10–50%、パート混線 |
| ポピュラー／複雑リズムの記譜解釈 | MuseScore 公開譜のキー・不完全、変拍子誤記 |
| MIDI→五線の意味論ギャップ | frequency dump、display quantize 必須 |
| MusicXML 互換の穴 | 移調、stem、スラー、テンポ、全音符、繰り返し |
| レイテンシ／タイムアウト | Basic Pitch 待ち、MIDI stem 3回TO |
| 権利・ライセンス | NC 重み、入力音源権利 |
| confidence の校正 | 自己申告100%問題、音楽特化UIはX上で薄い |

**中国語投稿について**  
`扒谱 / 自动扒谱 / MusicXML / 转MIDI` 系キーワードは X 上で **スパム・無関係投稿に埋もれやすく、英語圏ほどの実務者スレ密度は取れなかった**。中国語圏の「扒谱」議論は、Bilibili・小红书・微信群・专业论坛側に厚く、**X単体では英語・日本語の方が信号対雑音比が高い**、というのが今回の観測限界。

---

## 5. ベストプラクティス（投稿から帰納）

### 5.1 区間音源パッケージ

1. **クリーンな単一パート優先**（伴奏なし）— OpenUTau 利用者の明示条件。  
2. **頭合わせ・BPM・テンポチェンジマップを同梱** — 制作納品失敗リストと同型。  
3. **フルミックス直ではなく stem 分離後に MIDI 化** — Melodyne 実務、Mirelo 失敗後の代替案。  
4. **区間は「人が聴き比べできる長さ」**（フレーズ／8〜16小節）— 変拍子誤記の再聴修正パターンから。  
5. **生成タイムアウトを前提に区間分割・再試行** — timeout 実例。

### 5.2 下書きMusicXML

1. **「下書き／仮説」ラベルを必須化**（完成譜と混同させない）。  
2. **MusicXML 単体納品を避け、MIDI + PDF/画像 + 音源をセット** — Dorico→Logic 比較。  
3. **display quantize 後の記譜用データを出す** — Spreadbury の公式的実務指針。  
4. **移調楽器・調号・コンサートピッチをメタデータで固定** — Puff の bug 報告。  
5. **テンポは MusicXML に依存せず sidecar（JSON/CSV）でも渡す** — playback-only 問題。

### 5.3 信頼度ハイライト（外部採譜者向け）

X上の**音楽特化ハイライト製品談**は薄いが、隣接ベストプラクティスは明確:

1. **低confidenceは無理に音符化しない／空欄 or 要確認フラグ**（ASR運用）。  
2. **confidence を編集UIの下流に露出**（要約層に出さないと汚れる）。  
3. **alignment 系では unsupervised confidence 研究が進む**（DTW reliability, AUROC 0.97 報告投稿）→ 区間同期の信頼度に転用可。  
4. **「見た目の記譜美しさ」と「音高正しさ」を別スコアにする**（wrong melody 事例）。  
5. **自己申告スコアは校正前に信じない**（100%→40%問題）。

### 5.4 外部採譜者オペレーション

1. チェックリストで納品品質を段階ゲート（無音／BPM／頭合わせ）。  
2. 権利: 誰がどの音源を扱えるか、再配布可否をパッケージマニフェストに。  
3. 修正ログ（どの区間を人が直したか）— 研究寄りの “every correction logged” 型ワークも観測（実験プロトコル投稿）。

---

## 6. 最新トレンド（2025–2026 のX信号）

1. **Full-mix multi-instrument transcription**  
   MuScriptor / Mirelo Audio-to-MIDI が爆発的に拡散。ただし **デモ成功 ≠ 現場精度** のギャップが即日レビューで露呈。

2. **Stem → MIDI プロダクト化**  
   StemCraft、Sunofriend、Harmony Helper 等、「AI曲はMP3しかない→stem+MIDIで編集可能に」系。  
   採譜ソフトの「区間音源パッケージ」と同コンセプト。

3. **評価インフラ／データセット**  
   Orchestral Pit: transcription の評価・pop 向けデータセットがトレンド。  
   PitchBench で audio-language model の **基本的な pitch 聴き取り失敗**を計測、という厳しい側の研究信号も。

4. **Alignment の confidence と高速化**  
   unsupervised DTW confidence、並列 DTW 100× 等。  
   **「譜面と音源の同期信頼度」** は人手仕上げUIの次の本命。

5. **Finale 終了 → MusicXML import 品質競争**  
   記譜ソフト間移動需要が急増し、**下書きMusicXMLの品質が製品差別化点**に。

6. **オープンウェイトでも商用不可（NC）の罠**  
   技術トレンドと事業・外注フローの齟齬が明示的に語られ始めた。

---

## 7. 機能設計への示唆（本調査の実務翻訳）

「人手仕上げ作業パッケージ出力」を X 実務に合わせると、最低限こうなる:

```text
package/
  manifest.json          # BPM, key, 移調方針, 権利, 生成モデル, バージョン
  audio/
    full_mix.wav
    stems/...            # 可能なら
    segments/s01.wav     # 頭合わせ済み区間
  draft/
    draft.musicxml       # 明示的に draft
    draft.mid
    draft.pdf            # 見た目の参照
  confidence/
    notes.csv            # t, pitch, conf, source_stem
    regions.json         # 低信頼区間ハイライト
  tempo_map.json
  README_for_transcriber.md
```

**やってはいけない（失敗投稿からの否定形）**  
- フルミックス一発MusicXMLだけ渡す  
- キー未確認の下書きを「ほぼ完成」と見せる  
- confidence なしで誤音符を埋め尽くす  
- テンポチェンジを省略  
- マルチ／区間の頭がずれている  
- ライセンス境界を書かない  

**やるべき（成功投稿からの肯定形）**  
- 区間＋stem で難所を切る  
- MIDI（演奏）と MusicXML（記譜仮説）を分ける  
- display quantize 後の記譜  
- 低信頼は空欄 or 赤帯で「要人手」  
- 原曲区間と並走チェック  

---

## 8. 主要出典（X投稿）

| 区分 | 投稿者 | 内容の要点 | 投稿ID（例） |
|---|---|---|---|
| 失敗 | @T_R_E_X_12 | ポピュラー採譜・MuseScore・AIが壊滅 | 1979380334673146295 |
| 失敗 | @CabbageLettuce1 | Mirelo 50%/10%、パート混線 | 2078348054697246827 |
| 失敗 | @LatentDhruva | audio-to-MIDI が frequency dump | 2045449645221171588 |
| 失敗 | @dj_irl | Ableton が悪い音を足す | 2016891106236256452 |
| 失敗 | @kykukaz32768 | Basic Pitch 遅延・変換不能 | 2077021737850704240 等 |
| 失敗 | @entrepeneur4lyf | MIDI stems 3回タイムアウト | 2076011531565682854 |
| 失敗 | @yodaclaus | 全音符→タイ二分音符 | 1641095493 |
| 失敗 | @robertpuff | 移調楽器 import で音高不正 | 1234251912402198530 |
| 失敗 | @Alan_R_White | stem 要素無視 | 1470112984538259456 |
| 失敗 | @takuyah | MusicXML vs MIDI の Logic 取り込み差 | 2078691801943445613 |
| 失敗 | @TomoyaKinoshita | マルチ頭・BPM・テンポデータ欠落 | 1839225406517555488 |
| 失敗 | @nikskld | NC ライセンスの罠 | 2076316488529564070 |
| 成功/指針 | @dspreadbury | MIDI=演奏, MusicXML=quantize後記譜 | 1577940910461308929 |
| 成功 | @NoR3_Music 他 | Melodyne/Basic Pitch 下書き運用 | 2077725459601928277 等 |
| トレンド | @MireloAI / @OrchestralPit | full-mix AMT・評価データセット | 2075536492177354771 等 |
| 互換 | @MichaelDGood | MusicXML import 品質競争 | 1829580539537572008 |
| 信頼度 | @an_engineer_log 他 | 低confidenceは出さない | 2078713248417817044 |

---

## 9. 調査メモ（方法・バイアス）

- 検索: `MusicXML import/export`、`audio to MIDI`、`automatic music transcription`、`confidence transcription`、`扒谱/转MIDI`（中国語）、製品名（Mirelo, Basic Pitch, Melodyne, MuScriptor）等。  
- **失敗例は英語・日本語に濃く、中国語はノイズ多**。  
- 音楽「信頼度ハイライト」専用のバズ語は少なく、**ASR confidence と MIR alignment confidence からの類推が必要**。  
- バイラル製品投稿は成功バイアスが強いため、**同週の辛口実測（50%/10%）を必ず対で読む**こと。

---

### 一言で製品要件に落とすと

> **外部採譜者向けパッケージの価値は「自動で正しい譜を出すこと」ではなく、  
> 「誤りの位置が分かり、音源と照合でき、MusicXML互換事故を減らした下書きを渡すこと」。**  
> X上の実務者言説は、ほぼ一貫してその方向を支持し、**フルオート完成を支持していない**。
