# basic-pitch後継の検出モデル調査 — #114/#144（2026-07-25）

**目的:** 正解付きベンチ（夢見る・#144）でF1≈0.74-0.76に収束した現行検出器（basic-pitch）を超えるための、ローカル実行可能な後継モデルの網羅調査（英中・grok併用・失敗例/ライセンス重視）。

## 結論（一文サマリ）

> 論文のGuitarSetではMT3/YourMT3/Lu系がbasic-pitch(~79%)を明確に上回る(~90%)が、実世界ソロではRiley型（High-Resolution Guitar Transcription）が強く、**歪みパワーコードではどの公開モデルも決定打がない** — EGDB/Guitar-TECHSによる再学習かMuScriptorの自前評価が次の一手。ローカル導入の最短経路は `basic-pitch + mt3-infer`（MR-MT3/YourMT3の並列比較）。

## 導入判断マトリクス

| 用途 | 第一候補 | 注意 |
|---|---|---|
| 精度アップ最小コスト | `pip install mt3-infer` → MR-MT3(MIT)とYourMT3を同一音源で比較 | YourMT3は**GPL**（製品組込に注意）|
| クリーン/ソロギター | Riley HRGT（GS zero-shot 87%・商用85%級） | 重み入手可否の確認が先 |
| TAB(弦・フレット)直接出力 | FretNet / TabCNN+Guitar-TECHS | 研究実装・要検証 |
| 歪み・パワーコード | EGDB系 or Guitar-TECHSで**自前fine-tune** | 既製ckptに過大期待しない（調査結論）|
| 多楽器2026 SOTA | MuScriptor | **重みBY-NC**（商用不可）|
| 避ける | 公式JAX MT3フルスタック（Apple Silicon非現実的）・Omnizart単独 | |

## 当プロジェクトへの適用計画（#144完全一致への道）

1. **第1手（次セッション）**: `mt3-infer` を別venvに導入し、MR-MT3/YourMT3を夢見るベンチ（決定化済み・F1で判定）で basic-pitch と三つ巴比較。60秒で並べるだけ — 導入コスト最小・判断材料最大
2. 第2手: クリーン系に強いRiley重みの入手可否確認（GS zero-shot 87%は現状比+10pt級の期待値）
3. 第3手（R&D本丸）: 歪みギターは公開モデル決定打なし → **Guitar-TECHS + EGDBでの自前fine-tune** をG3以降の投資判断として提示
4. ライセンス整理: 製品同梱可=MIT系（basic-pitch/MR-MT3）。GPL(YourMT3)・BY-NC(MuScriptor)は評価専用に隔離

## 主要出典

- MT3: https://arxiv.org/abs/2111.03017 / MR-MT3(MIT): https://github.com/gudgud96/MR-MT3 / mt3-infer: https://pypi.org/project/mt3-infer/
- YourMT3+: https://arxiv.org/abs/2407.04822 (GPL)
- Riley HRGT: https://arxiv.org/abs/2402.15258 / https://xavriley.github.io/HighResolutionGuitarTranscription/
- FretNet: https://arxiv.org/abs/2212.03023 / EGDB: https://arxiv.org/abs/2202.09907 / Guitar-TECHS: https://arxiv.org/abs/2501.03720
- MuScriptor(2026・重みNC): https://kyutai.org/blog/2026-07-10-muscriptor/
- 中文HRGT評述: https://www.themoonlight.io/zh/review/high-resolution-guitar-transcription-via-domain-adaptation
