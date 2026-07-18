**総評: 成熟度 2/5 維持**

第3巡の結論は厳しめに言うと、ビジョン転換は上位文書には入ったが、評価・需要検証・Phase優先度・アーキ境界にまだ染み込んでいません。特に「絶対音感エミュレータ」「非音楽家」「日常録音」「耳=楽器非依存」の4語が、要件体系の判定軸まで降りていない。

**重大指摘**

1. **P0: 手直し比率KPIがまだ主KPIとして残っている**
   [NF-018](REPO_ROOT/docs/requirements/non-functional-requirements.md:85) は「手直し工数比率を主要品質KPI」と明記したまま。これは [product-vision](REPO_ROOT/docs/requirements/product-vision.md:49) の「音楽家の判定基準に依存しない」と正面衝突します。さらに [gate-execution-spec](REPO_ROOT/docs/research/gate-execution-spec.md:98) は読み替え注記で逃げていますが、判定表本体は [手直し比率のまま](REPO_ROOT/docs/research/gate-execution-spec.md:100)。これは実装者・評価者に二重基準を残す危険な状態です。

2. **P0: 需要ゲートの対象者が旧プロダクトのまま**
   ビジョンは「非音楽家が日常音から音程成分を拾う」体験です。一方 G2 は「採譜外注の発注経験者」が主対象で、質問も「採譜に金を払ったか」「手直しするか」に寄っています [§4.1-4.2](REPO_ROOT/docs/research/gate-execution-spec.md:112)。これは新ビジョンの需要検証ではなく、旧来の採譜代替市場検証です。ここを直さないと、ゲートを通っても別プロダクトを検証しただけになります。

3. **P0: F-108が中核なのに Should / Phase2**
   [product-vision](REPO_ROOT/docs/requirements/product-vision.md:14) は「クリーン音楽ファイル前提を捨てる」と言い、[F-108](REPO_ROOT/docs/requirements/functional-requirements.md:136) はその中核です。にもかかわらず Should / Phase2。Phase1 はまだ TAB・整譜・MusicXML寄りです。これは優先度体系が転換前のまま残っている証拠です。最低でも F-108 は Phase1検証対象、できれば Must 候補に上げるべきです。

4. **P1: F-108の受入条件はデモであって要件ではない**
   「雨+口ずさみで口ずさみだけ五線化」「エアコンhumを主旋律に混入しない」は方向性としては良いですが、合格基準がありません。必要なのは、`pitched_stable` 検出の precision/recall、`noisy/inharmonic` の誤音符化率、SNR別・残響別・混入音別の閾値です。現状は「説明可能ならOK」に読めます。

5. **P1: NF-050の二層原則が解析要件に貫徹されていない**
   [NF-050](REPO_ROOT/docs/requirements/non-functional-requirements.md:30) は「エンジン層に楽器固有分岐なし」。しかし [F-010](REPO_ROOT/docs/requirements/functional-requirements.md:145) は音色クラス別閾値、[F-015](REPO_ROOT/docs/requirements/functional-requirements.md:150) はギター/ベース識別をTAB前置工程、[F-078](REPO_ROOT/docs/requirements/functional-requirements.md:156) はギター/ベース奏法検出を解析エンジンに置いています。これは「耳が楽器を知らない」設計と混線しています。楽器分類・奏法・弦フレットは出力プロファイル層へ隔離し、耳層は `pitch_event / onset_event / confidence / timbre_embedding / event_class` 程度に留めるべきです。

6. **P1: AIの耳4指標とNF品質KPIの対応表がない**
   READMEは4指標を掲げています [README](REPO_ROOT/tools/ai-ears/README.md:42)。しかし [NF-019〜021](REPO_ROOT/docs/requirements/non-functional-requirements.md:86) 側は mir_eval/MUSTER/MV2H/独自指標/CI の羅列で、AIの耳スコアを正式な受入条件としてどこに接続するかが未定義です。[ears.py](REPO_ROOT/tools/ai-ears/ears.py:205) の重み `0.4/0.3/0.1/0.2` も要件上は封緘対象になっていません。

7. **P1: chroma DTWを過信する構造が残る**
   Web確認では、chromaはFFT成分を「ピッチクラス」に投影する特徴量です。CENS系は音色・強弱・アーティキュレーションに頑健とされますが、これは裏返すとそれらを評価しにくいということです。Essentiaのcover song手法でも、曲はキー・テンポ・楽器編成・構造順が変わり得る前提で、chromaと局所アラインメントを使います。したがってAIの耳のchroma DTWは「同じ曲っぽさ」の粗い照合であり、オクターブ誤り、声部、ベースライン、音色源分離、日常音からの選択的抽出、譜面可読性は測れません。

8. **P1: G1ベンチが日常録音へ更新されていない**
   G1選曲は U1ピアノ、U2弾き語り、U3ギターTAB、U4バンド、U5低品質録音です [§3.2](REPO_ROOT/docs/research/gate-execution-spec.md:55)。U5は「スマホ録音のU1相当」であり、日常音の選択的抽出ではありません。NF-021には鳥・駅ジングル・ノック・雨+口ずさみが入っていますが [NF-021](REPO_ROOT/docs/requirements/non-functional-requirements.md:88)、封緘ゲートに入っていないため、実装前の意思決定材料になりません。

9. **P2: AIの耳READMEが旧評価観を混ぜている**
   READMEは「人間の耳なし」と言いながら [README](REPO_ROOT/tools/ai-ears/README.md:3)、限界では「音楽家の代替ではない」と書いています [README](REPO_ROOT/tools/ai-ears/README.md:54)。さらに `gemini_ears.py` に「手直し量の見立て」をさせる運用が残っています [README](REPO_ROOT/tools/ai-ears/README.md:39)。非音楽家聴感を第二判定にしたなら、AIによる手直し見立ては参考ログに降格すべきです。

**実装開始前の必須修正**

- NF-018を「AIの耳複合スコア＋非音楽家聴感」に置換し、手直し比率は演奏者向け出力QA専用へ降格。
- gate §3.6 と封緘記録の「手直し比率」表現を全削除し、AIの耳スコア帯に書き換える。
- G2の主対象を「日常音を音名化したい非音楽家」に分け、旧採譜外注者ゲートとは別ゲートにする。
- F-108を Phase1 検証対象へ昇格し、選択的抽出の precision/recall/誤音符化率を定義。
- NF-050準拠の責務表を作り、F-010/F-015/F-078/F-079/F-076/F-028 を耳層・記譜層へ再配置。
- AIの耳4指標と NF-019/020/021/032 の対応表、重み、封緘閾値、適用不能範囲を1枚に固定。
- G1ベンチにフィールド録音セルを追加し、鳥・駅ジングル・雨+口ずさみ・hum混入を撤退判定に含める。

Slack投稿は未実行です。このセッションに `send_message` / Slack送信ツールが露出しておらず、`slack` CLI と `SLACK_*` 環境変数も見つかりませんでした。
