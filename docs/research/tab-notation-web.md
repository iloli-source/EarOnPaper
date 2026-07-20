# ギターTAB譜 Web調査レポート（Claude=Web担当）

調査日: 2026-07-20 / 英語・中国語重点

## 1. TAB譜の標準記法・必須要素

- 6本の横線＝6弦（下が6弦=太い低E、上が1弦=細い高E）。左→右に読み、線上の数字が押さえるフレット。出典: [Guitar Lesson World](https://www.guitarlessonworld.com/lessons/reading-notation-tablature/) / [MusicRadar](https://www.musicradar.com/tutorials/guitar-lessons-techniques/confused-by-guitar-tabs-and-notation-use-this-complete-guide-to-reading-music-for-guitar)
- **チューニング表記は必須**: 「チューニングベクトルのないTABは、音部記号・調号のない五線譜と同じくらい無意味」。出典: [Guitar Lesson World]
- **TAB単体は音価（リズム）を表現できない**のが根本的弱点。標準記法（五線譜）を併記して初めてリズム・音名・運指が揃う。出典: [Acoustic Guitar Notation Guide](https://acousticguitar.com/acoustic-guitar-notation-guide/) / [Guitar Lesson World]
- 技法記号: ハンマリング(h)、プリング(p)、スライド(s/ /)、ベンド(b)、ビブラート(~)、ミュート(x) 等が標準

## 2. 可読性の具体的課題（今回の実装に直結）

- **「数字が弦の線で打ち消される(struck through)と可読性を損なう」**。特に 0/8/3/6/9 はフォントと線の太さ次第で一目では紛らわしい。出典: [Donald Sauter: Proposal for a standardized tablature](http://www.donaldsauter.com/tablature.htm)
  - → 本実装が数字の背後に白背景を敷いて線をマスクしているのは、この課題への正しい対処。数字混同はフォント選択の残課題
- 1行あたりの小節数・数字の間隔が詰まりすぎると判読不能になる（音数過多の問題は今回のSong 1実測=540箇所重なりで顕在化）

## 3. 中国語圏（六线谱）の慣習

- 六线谱は「**指法を記録し音高は記録しない**譜。简谱/五线谱と併用対照で音高＋指法が揃う」。分解和弦の右手順序・時値、和弦図の1/2/3（食指/中指/无名指）、↑↓（扫弦方向）を注記。出典: [知乎: 吉他干货](https://zhuanlan.zhihu.com/p/187122846) / [知乎: 六线谱入门](https://zhuanlan.zhihu.com/p/348523245)
- **AI扒谱ツール「爱扒谱」**: 主流音楽を自動認識し規範的な五線譜を生成、**ギター/ベースには五線譜に加えて適配の六線譜を追加生成**（平均認識率96.3%と自称）。出典: [爱扒谱 aibapu.cn](https://aibapu.cn/) / [CNBlogs: 2026 AI扒谱工具比較](https://www.cnblogs.com/1698-20260688/p/20606871)
  - → 中国語圏の実運用でも「五線譜＋六線譜の併記」が標準形。TAB単体は補助的
- 制譜はGuitar Pro（滑音・倚音・推弦・揉弦・泛音・闷音・琶音・分解和弦・BASS打弦等の技法表現に強み）が定番。出典: [Sibelius中文站](https://sibelius.mairuan.com/banben/sibe-dpcum.html)

## 4. 規格（TAB表現）

- MusicXMLでは `technical/fret` と `string`、`staff-details`（staff-lines/staff-tuning/capo）でTAB表現。DadaGP（Guitar Proトークン化データセット）が研究の標準。出典: [DadaGP arXiv](https://arxiv.org/pdf/2107.14653)
- 弦楽器のチューニング・運指のトポロジー的考察（開放弦・ポジションの数学的扱い）: [arXiv 1105.1383](https://arxiv.org/pdf/1105.1383)

## 5. 見つからなかったこと（正直な報告）

- 「1行あたり最適小節数」「数字フォントサイズの数値基準」といった定量的レイアウト規範は、権威ある一次資料としては確認できず（教則サイトの経験則レベルに留まる）
- AI生成TABの音数削減（メロディ/伴奏分離してギター向けに減らす）の体系的手法は、Web一般記事では確認できず（論文側=codexレポートのarrangement研究に該当）

## Sources

- https://www.guitarlessonworld.com/lessons/reading-notation-tablature/
- https://acousticguitar.com/acoustic-guitar-notation-guide/
- https://www.musicradar.com/tutorials/guitar-lessons-techniques/confused-by-guitar-tabs-and-notation-use-this-complete-guide-to-reading-music-for-guitar
- http://www.donaldsauter.com/tablature.htm
- https://zhuanlan.zhihu.com/p/187122846
- https://zhuanlan.zhihu.com/p/348523245
- https://aibapu.cn/
- https://www.cnblogs.com/1698-20260688/p/20606871
- https://arxiv.org/pdf/2107.14653
- https://arxiv.org/pdf/1105.1383
