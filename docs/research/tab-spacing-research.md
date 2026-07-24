# TAB/楽譜の横スペーシング — #139実装前調査（2026-07-25）

**目的:** #139（16分連続でTAB数字が癒着・最大77重なり/曲）の実装前調査。英中網羅（WebSearch＋LilyPond文書＋grok CLI調査）。
**症状の根本:** 現行tab.pyは「固定4小節/段＋拍位置比例配置」— 音符密度に関係なく小節幅一定のため、2桁フレットの16分連打で数字間隔<数字幅となり癒着する。

## 1. 世界標準のアルゴリズム（正典）

- **spring-rodモデル**（Gourlay → Haken-Blostein改良 → LilyPond実装）: 音価に比例した自然長を持つバネ(spring)＝伸縮する理想間隔、最小距離制約(rod)＝衝突禁止の床。制約付き二次計画として解く（LilyPond Simple_spacer: rods=制約・springs=最小化目的）
- **音価比例は「圧縮済み比例」**: Gould/Ross流は生の音価比ではなく音価比を圧縮した配分表（例: 音価2倍→間隔√2倍相当のlog圧縮）。純粋比例は短音符が詰まりすぎる
- **LilyPond文書が明記する失敗例**: 基準音価が粗いproportional spacingは「音符が詰まりすぎ衝突を起こす」— **うちの現象そのもの**
- 行分割(system break)はKnuth-Plass型の詰め込み問題。Guitar Proは「auto=密度でpack / fixed-N=強制後にstretch」の二択UI

## 2. grok調査の推奨アーキテクチャ（合流点）

```
1) 各onsetのink幅を計測（TABはフレット桁数・和音幅）
2) ideal_gap = 音価の圧縮比例配分
3) min_gap = max(最小音符間隔, 数字幅+padding)   ← rod
4) spring自然長 = max(ideal_gap, min_gap)
5) 小節natural幅 = Σspring
6) 段組: natural幅でgreedy pack（or 固定Nならstretch＋overflow警告）
```
- **「固定小節幅は高密度でminを破るか可読性を捨てる。密度可変packingか局所stretchが必須」**（調査総括）
- TAB特有: min_gapは2桁フレットで広げる（うちのcount_overlapsは既にこの幅モデルを持つ）

## 3. 失敗例・教訓

- 純粋な拍比例（現行実装）: LilyPond文書が衝突を明記。MuseScoreにも「inconsistent spacing」系Issue、Verovio #3990等レイアウト衝突Issueが現存 — 一流実装でも衝突対策は継続課題
- 固定小節数レイアウト（GP fixed-N）はオーバーフロー検出と警告が必須とされる
- 多声の同時刻揃え: 同一x上の縦integrityを崩すと読めない（リズム帯・休符・楕円と数字のx共有は維持必須 — 現行の `_note_x` 共有は正しい設計）

## 4. 中国語圏

- 理論は英語文献（Gourlay/Renz/Gould）依存。実務はMuseScoreの「最小间距＋拉伸」操作とGuitar Pro固定小節数運用が中心。TABのスペーシングアルゴリズム議論は稀（＝ここを自動で正しくやる価値）

## 5. #139への設計示唆

1. **段あたり小節数の密度適応（GP auto方式）**: 小節ごとに必要幅（Σ max(拍比例, 数字幅+padding)）を算出し、ページ幅に収まる数だけ greedy pack（1〜4小節/段・上限4維持）。これが本命
2. **小節内は簡易spring-rod**: 拍比例位置を初期値に、隣接onset間に min_gap（数字幅+padding・count_overlapsと同じ幅モデル）を左→右の1パスで強制し、小節幅に再正規化。厳密QPは不要（1小節内は1次元・単調）
3. `_note_x` の共有構造は維持（数字・リズム帯・休符・楕円が同じxを使う現行設計は正しい）— `_note_x` を「小節ごとのonset→xマップ」に置き換える
4. 検証は count_overlaps=0 化を主指標に（clean_arpeggio 77→0等）、10本コーパスで前後比較＋目視
5. 音楽的情報は不変（描画レイアウトのみ）— クロマ等の音高指標は非対象

## 主要出典

- LilyPond spacing overview / essay: https://lilypond.org/doc/v2.26/Documentation/notation/horizontal-spacing-overview
- LilyPond Contributor spacing-algorithms（Simple_spacer=制約付きQP）: https://lilypond.org/doc/v2.25/Documentation/contributor/spacing-algorithms
- Haken & Blostein改良スペーシング（ICMC2002）: https://quod.lib.umich.edu/i/icmc/bbp2372.2002.097
- Renz spacing: https://guido.grame.fr/papers/renz-spacing.pdf
- Gould, Behind Bars（配分表の受容はDorico開発日誌等経由）: https://blog.dorico.com/2015/03/development-diary-part-10/
- Guitar Pro layout tips（固定/auto段組）: https://www.guitar-pro.com/blog/p/17044-tuto-10-tips-to-give-a-professional-look-to-your-scores-in-guitar-pro
- MuseScore spacing手引き・中文版式: https://musescore.org/en/handbook/4/score-size-and-spacing
- 知乎 Behind Bars笔记: https://zhuanlan.zhihu.com/p/493149160
