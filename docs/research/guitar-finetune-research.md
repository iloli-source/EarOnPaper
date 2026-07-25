# 歪みギター採譜のfine-tune計画調査 — #114/#144（2026-07-25）

**目的:** 完全一致ゴール（#144・全公開モデルがF1≈0.75で収束と実測済み）の残る本丸=自前fine-tuneの実行計画策定。英中網羅（grok併用・失敗例重視）。

## 1. データセット（入手性確認済み）

| データセット | 規模 | ライセンス | 入手 |
|---|---|---|---|
| **Guitar-TECHS** | 5.2時間・DI/アンプ/マイク多録音・弦別MIDI同期 | **CC BY 4.0** | **Zenodo即DL可・計4.13GB**（chords=P1 0.98+P2 1.15GB が最優先） |
| EGDB | 240 DIタブ＋複数アンプレンダ | 要確認 | プロジェクトページ(Drive) |
| **EGDB-PG** | EGDB×256アンプ/キャビ(BiasFX2) | 要確認 | **申請制**: f08946011@ntu.edu.tw へメール |
| GOAT | 実DI 5.9h＋アンプ拡張29.5h・GuitarProタブ付 | CC BY 4.0 | Zenodo申請制(15690894) |
| GuitarSet | 360クリップ(アコースティック) | 公開 | Zenodo(3371780)・比較評価用 |

## 2. 手法の本命（2025-26エビデンス）

- **TIT（Tone-informed Transformer・arXiv:2504.07406・NTU+Positive Grid）**: hFT-Transformerにtone embedding(cross-attn)を追加しEGDB-PGで学習 → **high-gainでOnset F1 78-86%帯**。我々の課題（歪みパワーコード）への直接解。モデル重みは未公開・データは申請制
- **Riley方式（arXiv:2402.15258）**: 高解像度ピアノモデル→ギターdomain adapt。クリーン系はSOTA級だがhigh-gain metalは別ドメイン（限界明記）
- 学習の定石: **DIのみで学習すると歪みへ汎化失敗**（EGDB/PGが繰り返し実証）→ 3+アンプの音色拡張が必須

## 3. 失敗例（回避リスト）

- basic-pitchの自前fine-tune: **学習コード未公開で再実装コスト大 → 非推奨**（公開成功談ほぼ無し）
- MT3フル再学習: 依存・計算コスト大でエレキ単体ROI低
- **Mac MPSでの本番学習: 非推奨**（推論・ラベル整備のみに使い、学習はクラウド）
- CE-only Transformerの小データ学習は失敗（multi-loss/OAF系が優位）
- delay/reverb/ライブ多マイクは全モデル大幅低下（アンプ以外の時空間効果は別問題）

## 4. 実行計画（最小実行プラン）

1. **データ準備（ローカル・無料）**: Guitar-TECHS chords/techniques をZenodoからDL → 夢見るベンチ形式の評価分割＋学習用整形。EGDB-PGを**メール申請**（ユーザーアクション）
2. **ベースモデル**: hFT-Transformer（MAESTRO事前学習・公開実装）→ ギターdomain adapt。TIT論文のレシピ（content aug＋tone aug＋正規化）を再現
3. **学習環境**: クラウドGPU（RunPod A100/4090）**予算目安 $50〜200 で1〜2実験**
4. **評価**: ①夢見る決定化ベンチ（完全一致ゴールの直接指標）②GuitarSet（一般性）③high-gain held-out（過適合検出）
5. **統合**: 成功時はbp_workerと同形のワーカー（別venv・subprocess JSON契約）として本体へ

## 5. 判断が必要な点（ユーザー向け）

- **クラウドGPU費用 $50〜200**（無料方針の例外・要承認）
- EGDB-PGの申請メール送信（info@iloli.tokyo から f08946011@ntu.edu.tw へ・研究利用目的）
- 期間目安: データ整形1セッション＋学習/評価1〜2セッション

## 主要出典

- TIT/EGDB-PG: https://arxiv.org/abs/2504.07406 / https://ss12f32v.github.io/Guitar-Transcription-with-Amplifier/
- Guitar-TECHS: https://arxiv.org/abs/2501.03720 / https://zenodo.org/records/14963133
- EGDB: https://arxiv.org/abs/2202.09907 / GOAT: https://arxiv.org/abs/2509.22655
- Riley: https://arxiv.org/abs/2402.15258 / SynthTab: https://synthtab.dev/
- RunPod料金: https://www.runpod.io/pricing
