# TAB運指の慣用ヴォイシング — #142実装前調査（2026-07-25）

**目的:** #142（TAB運指に慣用ヴォイシング優先を導入）の実装前に、英語・中国語圏の学術・実務知見と失敗例を収集する（DS-04東スポ氏指摘「ロックに5/3/3は存在しない」への対応設計の根拠）。
**調査手段:** Web検索（英・中）＋主要論文精読＋grok CLI網羅調査2系統（学術系・コミュニティ系）。

## 1. 学術アプローチの系譜

| 年 | 貢献 | 要点 |
|---|---|---|
| 1989 | Sayegh — Optimum Path Paradigm | 弦・フレット候補をグラフ化し手移動コスト最小経路。**現行tab.pyのDPと同系** |
| 2004 | Miura（指位置）/ Radisavljevic | 移動最小化。後年「上級者に窮屈」と批判 |
| 2005 | Tuohy & Potter — 遺伝的アルゴリズム | fitness に**バレーコード報酬**を明示的に組込み（慣用形ボーナスの先行例） |
| 2013 | Hori & Sagayama — IO-HMM / Burlet — A*-Guitar | 運指遷移を確率化。2016年に minimax Viterbi（最悪遷移の最大化） |
| 2019 | TabCNN（音声→TAB・ISMIR） | 「妥当だが演奏者の真の運指ではない」問題を明示 |
| 2021 | **DadaGP**（コミュニティTAB 25,000曲・ロック/メタル中心） | 学習・統計の標準コーパスに |
| 2024 | Edwards MIDI-to-Tab（BART系）/ **Sakai — typical forms辞書** / Bontempi rich TAB / **D'Hooge コード押さえ形提案** | 明示的な**慣用形辞書制約**と**文脈依存の形選択**が登場 |
| 2025 | Fretting-Transformer（T5系 MIDI→TAB）/ Open-Fret | 慣用形はデータから暗黙学習（保証なし） |

## 2. 慣用形（イディオム）の扱い — #142に直結する知見

- **Sakai (2024) typical forms**: コード＋メロディのソロギター編曲で「典型形辞書」を制約に使う。**現状もっとも明示的な慣用形の扱い**（grok学術調査の総合示唆）
- **D'Hooge et al. (2024)** [arXiv:2407.14260]: DadaGP/mySongBook統計で（a）**パワーコードはロック/メタルで極めて優勢**（b）同一コードラベルに**11.5〜24通り（最大108通り）の押さえ形**が実在（c）**直前の形を文脈に入れると提案F1が最大+32%**。抽出済み形データを algomus.fr/data で公開 → **形テンプレの統計的裏付けとして利用可能**
- Tuohy & Potter (2005): fitness関数のバレー報酬 — コスト関数への形ボーナスは20年前からの定石
- Fretting-Transformer等のNN系: 慣用形は暗黙学習に依存し**保証がない** → 明示的テンプレの価値は残る

## 3. 失敗例・教訓（実装で避けるべきこと）

- **playability単独最適化は人間の選好と乖離**: Edwardsの主観評価（ギタリスト15名×30抜粋）で人手GT 7.45 / 提案6.04 / **Guitar Pro自動 ≈4.7 / TuxGuitar ≈3.3** — 市販の自動運指も低評価
- **一致率だけの評価は危険**: 同一フレーズに複数の等価に妥当な運指（スタイルで正解が分岐: ジャズ=開放活用/メタル=形固定/クラシック=ポジション奏法）。Bontempi et al. [arXiv:2407.09052] も同旨
- **クラウドTAB学習は誤運指を再生産**（DadaGPにも誤ラベル: G MajorがG/BやG5と混在）
- **移動最小化の過制約**は上級者に不評（Miura系への批判）
- 自動TABがパワーコードを壊す典型（grokコミュニティ調査）: root/5thを離れた弦・フレットに分置 / 3度の混入（倍音誤検出）/ オクターブの遠隔配置 / 複数ギター混合の不可能ヴォイシング / Drop D同フレットの1指形無視

## 4. ギタリスト側の暗黙ルール（コミュニティ実測・grok調査2）

- **パワーコードは root–5th(–oct) の視覚的・身体的ユニット** — 「形がジャンル言語」。形で書かないと「それはパワーコードじゃない」と言われる（東スポ氏指摘と完全一致）
- 指使いの標準: 人差し指=ルート・薬指=5度・小指=オクターブ（1-3-4）。中指はミュート
- Drop D系: 同フレット3弦は**1指バレーがデフォルト**
- フレーズ単位で**ポジション窓を固定**（小節ごとに再最適化しない）
- パワーコードに開放弦を混ぜない（ミュート・音色の理由）
- TABへの信頼階層: 耳 > ライブ映像 > 公式 > Songsterr/UG人気票 > **GP自動** > 無名TAB

## 5. 中国語圏

- 台湾: 陳見齊（NTU碩士2024）楽譜→ギター譜の系列モデル変換 / Chen et al. ISMIR2020 Transformer-XLフィンガースタイルTAB生成
- 知乎・CSDN: アルゴリズムより**教育・実務**（「規範はなく合理・経済」「コードシェイプに沿って指法を変える」= 形優先文化）。CSDNにNN＋データ拡張の指法生成実践記事
- CNKI本体は認証壁で未踏査（推奨検索式: 吉他指法 自动生成 / 六线谱 指法 规划 / 隐马尔可夫 吉他）
- 総括: 基礎アルゴリズムは英語文献の輸入が主・中国語圏は応用/教育が厚い。**「固定指型を先に教える」文化はテンプレ方式の妥当性を支持**

## 6. #142への設計示唆（調査からの逆算）

1. **同時発音が root+5th(+oct) ならパワーコード形テンプレへボーナス**（Sakai型辞書の最小版・Tuohy以来の定石。優先度最高＝東スポ氏指摘の直接対応）
2. バレー形（同一フレット横並び）・オクターブ形（2弦スキップ+2フレット）を同様にテンプレ化
3. ポジション窓の慣性は既存DP（_MOVE_COST）が既に持つ — 壊さない
4. 開放弦ペナルティ・look-aheadは第2段（過剰適合に注意: ジャズ等では開放活用が正解）
5. **評価は二段**: 機械指標（10本コーパス・クロマ不変＋形一致率）＋**ギタリスト主観**（Edwardsの教訓。Discordの東スポ氏に結果を見てもらえる体制がある=DS-04）
6. 形テンプレの統計的正当化が必要になったら DadaGP抽出データ（algomus.fr/data）を参照

## 主要出典

- Fretting-Transformer: https://arxiv.org/pdf/2506.14223
- D'Hooge et al., Guitar Chord Diagram Suggestion: https://arxiv.org/pdf/2407.14260
- Bontempi et al., From MIDI to Rich Tablatures (SMC2024): https://hal.science/hal-04575313
- Edwards, MIDI-to-Tab: https://arxiv.org/html/2408.05024v1
- Hori & Sagayama, Minimax Viterbi (ISMIR2016): https://www.semanticscholar.org/paper/0a67d89bf25567495955b4785ae6379bda7b88d9
- TabCNN (ISMIR2019): https://archives.ismir.net/ismir2019/paper/000033.pdf
- Chen et al. (ISMIR2020): https://archives.ismir.net/ismir2020/paper/000349.pdf
- 陳見齊 NTU碩士論文(2024): https://tdr.lib.ntu.edu.tw/retrieve/e124f04c-afab-4373-9ab4-82c4eaa0f791/ntu-112-2.pdf
- A*-Guitar実装: https://github.com/gburlet/astar-guitar
- コミュニティ一次証言: r/Guitar「ears right, tab wrong」/ r/guitarlessons Drop D barre / 知乎 指法Q&A（詳細URLはgrok調査ログ）
