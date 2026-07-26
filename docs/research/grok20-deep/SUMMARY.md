# grok X調査20周(深掘り) 統合レポート + 論文追跡読解

日付: 2026-07-26 / 前提: 10周調査(grok10-tab-chord/)と5度補完実装(909227d)を踏まえた深掘り
生ログ: round_1.md〜round_20.md / 論文読解は paper-review-chord-recall.md と本書に分載

## 最重要の新知見(実装に直結する順)

### 1. ギター分離モデルの世代交代 (R11) — 最大の即効レバー
- 現行Demucs 6-stemのguitar SDR≈5.22dBに対し、**BS-RoFormer/Mel-Band RoFormer系は
  +3.8dB(≈9dB)**。2025-26はRoFormer族が圧勝、UVR5/MVSEPの実用層も移行済み。
- 分離が良くなれば検出も裁定も全て楽になる(bleed減=幽霊減・証拠明瞭化)。
- 論文: BS-RoFormer arXiv:2309.02612(ByteDance) / Mel-Band arXiv:2310.01809。
  実装: lucidrains/BS-RoFormer、python audio-separatorコミュニティcheckpoint。
- → Issue化: 分離バックエンド刷新の3ベンチA/B。

### 2. ストローク(一打)単位の和音判定 (R7) — ユーザー発案と合流
- 近藤ら(秋田大2023): spectral flux→τ=20-50msクラスタ→クラスタ内多基頻→和音投票。
- arXiv:2508.07973 (ISMIR2025): CRNNでストラム検出+コード分類のジョイント学習。
  マイク音声のみ・合成4h+実90分のハイブリッドで最高精度。
- 「1打=1ジェスチャー=N弦」の単位化は縦積み復元の自然な足場
  (我々のイベント単位補完をストローク単位に統合する方向)。

### 3. コード条件付き後処理 (R3) — 曲内コード語彙の事前分布の具体形
- レシピ: ACE(コード推定: madmom/ChordMini等)→コードトーンにλ_chord≈3の
  マスク優遇/非コード音は確信度<0.85でカット/スケール音は0.7許容(経過音)。
- 我々の兄弟テンプレ補完の一般化として実装可能(検出語彙でなくACE由来語彙)。

### 4. 位相・うなりによる同一周波数パーシャルの分離 (R10)
- Maher(JAES1990)のビート分離、Woodruff&Li(ISMIR2008)のCAM+位相LS、
  Stöter(DAFx2014)のAM/FM分離。重なった3f0を「1本分か2本分か」に分ける
  唯一の直接手段(振幅だけでは不可能な領域)。R&D中期候補。

### 5. 低音弦オクターブ誤りの定石 (R19)
- 弱基音×第2倍音ロックが常套原因。対策: f0範囲prior・HPS/SHS(missing
  fundamental対応・R18)・時間平滑。我々のサブオクターブ裁定と同型で、
  HPS的な「倍音積」証拠の追加はdown-completion系の強化に使える。

### 6. 再合成検証(AbS)のギャップ (R20)
- 研究はNMF/DDSP-Piano/Inverse Drum Machine(arXiv:2505.03337)路線があるが
  **「MIDI再合成→STFT残差マップでmiss/ghostを可視化」のワンクリック製品は不在**。
  STFT残差はlibrosaで実装容易・JPの職人は手作業で同じことをしている。
  → 我々の「作成した譜面から音楽を作成し突合」(既存方針)の裏付け+改善型。

## エンジン・製品の相場観 (R1-2, R14-17)

- MuScriptor: MulTTiPopでMulti-F1 48.2 (YourMT3+ 21.9)。ただしBasic Pitchとの
  三つ巴比較は不在。日本語圏最前線は「MuScriptor+Basic Pitch+コードモデルの融合」
  (@2zn01v)=アンサンブルが実務の答え。中国語圏は「98%」等の誇大広告のみ。
- 許容精度の相場: 「80%で形が合っていれば下書きとして使う」(JP実務)。
  クリーン音源のパワーコードは「ほぼ100%を期待される」→ 縦積み再現率の
  目標水準はやはり100%近傍が要件。
- 商用勢(Songsterr AI/Klangio/Chordify)は和音精度の数値公表なし。
  正解付きベンチを公開できること自体が差別化になる。

## 新出論文リスト(読解済み)

- arXiv:2508.07973 ストラム+コードCRNN (ISMIR2025) — 読解済み・上記2
- arXiv:2309.09085 SynthTab — DadaGP+商用プラグインで合成した大規模TAB音源。
  GTT事前学習で過学習緩和。fine-tune封印中のため将来素材としてマーク
- arXiv:2309.02612 / 2310.01809 分離RoFormer族 — 上記1
- arXiv:2505.03337 Inverse Drum Machine — AbS検証の研究例
- arXiv:2509.12712 note-level contrastive clustering (TISMIR2026) — 多楽器の
  音符レベル対比クラスタ。研究段階
- arXiv:2607.08756 MulTTiPop評価セット — エンジン比較の共通ものさし候補

## 反映(起票・実装への接続)

1. Issue: ギター分離バックエンド刷新(Mel-RoFormer系)の3ベンチA/B → #148
2. #144コメント: ストローク単位和音判定+コード条件付き後処理を次の実装2手として記録
3. AbS(STFT残差マップ)は既存の音楽突合方針の実装形として#144系に統合
4. SynthTab/位相うなり/slot-attentionはR&D在庫(コスト対効果で保留)
