# 同音連打の併合問題 — #138実装前調査＋実データ診断（2026-07-25）

**目的:** #138（同音連打が1音に併合・かえるのうた23/29音）の実装前調査と根本原因診断。
**手段:** WebSearch＋grok CLI網羅調査（学術・製品実装・中国語圏）＋かえるのうた実データのフレームレベル診断。

## 1. 文献・実装の結論（grok調査）

- **F0単独デコーダ（pYIN notes / CREPE輪郭）は同音連打に構造的に弱い** — 文献・製品とも「onsetの特別扱い」を必須とする（CREPE Notes / Onsets&Frames / basic-pitchのonset head / Kwon multi-state re-onset）
- 成功系は必ず「活動(frame)」と「開始(onset/re-onset)」を分離
- **後処理のmin-duration/pitch-mergeはFP対策だが連打recallを削る**二律背反
- 失敗パターン診断表: 「同音連打が1本の長ノート」→ F0平坦＋onset欠落 → onset分割（副作用=過剰分割）／「減衰中の2打目欠け」→ energy谷が浅い → 適応閾値
- 中国語圏でも歌声ASTの「同母音上の複数音符」として同型問題が認識
- 主要文献: CREPE Notes (arXiv:2311.08884) / Basic Pitch (arXiv:2203.09893) / Onsets and Frames (arXiv:1710.11153) / ISMIR2020 re-onset multi-state / ISMIR2017 pitch-wise HMM

## 2. 実データ診断（かえるのうた・欠落6音の根本原因）

現行mono.pyには既にRMSフラックスによる連打分割（2026-07-23根治）と、ピッチ段差の事後分割（#46）がある。それでも23/29に留まる原因をフレームレベルで特定:

**根本原因A: フレーム数定数のサンプルレート非依存バグ（主犯）**
- `_SPLIT_WINDOW_FRAMES=7` は「≈81ms」を意図（コメントに明記）だが **22050Hz前提**。実音源は `load_audio` がネイティブsr（=48000Hz）を返すため **実窓は37ms** に縮む
- pYINの音替わり滑走（50〜100ms）が窓全体を覆い、F→E（ちょうど1半音）の局所中央値ギャップが **0.6 < SPLIT_GAP 0.8** となり分割失敗（実測: best_gap=0.600 @t=3.47s）
- `_SPLIT_MIN_FRAMES`・peak_pickの `pre/post/wait` も同様に時間が半減している

**根本原因B: onset閾値がグローバル最大比で、柔らかい再アタックを取りこぼす**
- `thr = 0.2 × max(flux)`: 曲頭の強アタックが基準になり、減衰後の再打撃（フレーズ4のCC等）は flux比0.6〜0.8×で閾値未満
- さらに閾値超（1.1〜4.5×）でも peak_pick の局所平均条件で拾われないケースが多数（実測表あり: F区間3.02×・E区間4.10×等が未分割）

## 3. #138への設計示唆

1. **時間ベース定数化（最優先・バグ修正）**: 窓・最小断片長・peak_pickパラメータを秒で定義し `sr/HOP` からフレーム数を導出（意図済みの81ms等を全srで保証）
2. **onset閾値の適応化**: グローバル最大比をやめ、fluxの頑健統計（中央値+k×MAD等）ベースへ。RMSベース自体は維持（スペクトルフラックスはビブラートを誤検出するため — 既存設計の正しい判断）
3. 過剰分割の副作用（診断表）に注意: ビブラート保存の既存テストを回帰ガードに、閾値はかえるのうた＋コーパスで実測調整
4. 評価: かえるのうた 23→29音（正解配列既知・誤音0維持）を主指標に、10本コーパス＋PD15ベンチ非劣化

## 主要出典

- CREPE Notes: https://arxiv.org/abs/2311.08884
- Basic Pitch: https://arxiv.org/abs/2203.09893 / note_creation.py: https://github.com/spotify/basic-pitch/blob/main/basic_pitch/note_creation.py
- Onsets and Frames: https://arxiv.org/abs/1710.11153
- ISMIR2020 re-onset multi-state: https://archives.ismir.net/ismir2020/paper/000341.pdf
- ISMIR2017 pitch-wise HMM segmentation: https://archives.ismir.net/ismir2017/paper/000100.pdf
- librosa onset_detect: https://librosa.org/doc/main/generated/librosa.onset.onset_detect.html
