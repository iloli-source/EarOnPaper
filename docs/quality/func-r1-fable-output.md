# 機能別ダメ出し R1 — 出力側3機能(notate / engrave / quality)

監査人: Fable(実行ベース攻撃・視覚検査担当)。codex は静的レビュー担当。
証拠方針: 未テスト入力で新規攻撃し、実測値を記録。file:line 引用つき。コード修正なし。
実測環境: `spike/ear-pipeline/.venv`(py3.14) / `tools/ai-ears/.venv`(py3.14)。全102テスト緑(notate系53 + ai-ears49)を確認済み。

---

## 1. notate(音符列 → 五線譜)

対象: `earpipe/services/notate/score.py`, `spelling.py`。

### 攻撃結果表

| 攻撃 | 入力 | 実挙動 | 判定 |
|---|---|---|---|
| 左右交差メロディ | 低音C3↔高音C5を交互(beat毎) | `split_hands`が拍毎に純高さで振り分け→C3=ヘ音/C5=ト音に機械分割。声部としての連続性ゼロ。両手が1拍毎に跳躍する非現実的運指 | P1 |
| 全音域アルペジオ | A0(21)〜C8(105) 22音 | クラッシュなし。ト音12音/ヘ音10音に分割、綴りDb/F/A(調号Db)。3小節・音域外エラーなし | OK |
| 弱起(anacrusis) | 最初の音が beat3.5 開始 | ピックアップ小節認識なし。**先頭に3.5拍の巨大休符**を挿入し1小節目を埋める(score.py:221 `makeRests` + ref_end切り上げ) | P1 |
| 転調 C→G(F#実在) | 前半Cメジャー音階+後半Gメジャー(F#=66含む) | 全体1調=G majorに固定(spelling.py:18)。F#は正しく綴るが、**前半のFナチュラル(65)にはG調号下でナチュラル臨時記号が必要**。区間調は未対応(docstring明記済み spelling.py:8) | P1(既知) |
| 持続音の重なり | 全音符C3の下で4分音符が動く | 別staffなら持続保持(part1: C3が4拍保持)。**同一staff内の重なりは`_cap_overlaps`が次onsetで切断**(score.py:93-109)→持続喪失 | P1(既知・記録済) |

### turkish_real.musicxml 再解剖(休符・声部残存)

- **声部爆発は解消**: part0/part1とも `max_voices/measure=0`(暗黙1声部)。旧codex指摘の「全小節休符で埋めた5声部」は再現せず。休符連鎖 `max_rest_run=3`(受入「小節内4以下」を満たす)。→ `_cap_overlaps`(score.py:93)+`_consolidate_rests`(score.py:133)の修正が効いている。
- **ただし休符比率が高い**: 実測 part0=46.4% / part1=40.4% が休符拍。持続音を次onsetで切断→ギャップを休符で充填する設計の副作用で、譜面が「スカスカ」に見える(視覚的品質の未達)。これは声部分離未対応の帰結で、P1として台帳化すべき。

---

## 2. engrave(MusicXML → PDF/PNG)

対象: `earpipe/services/notate/engrave.py`。verovio → cairosvg → pypdf。

### 攻撃結果表(クラッシュ/レイアウト)

| 攻撃 | 実挙動 | 判定 |
|---|---|---|
| 空の曲(0音) | クラッシュなし。1ページ・全休符・17.5KB。`render_svg_pages`のpages<1ガード(engrave.py:33)は通過 | OK |
| 1音のみ | クラッシュなし。1ページ・`notes_engraved=2`(実際は1音) | P2(計数バグ) |
| 500小節(2000音) | クラッシュなし。7ページ・1.36秒・548KB。線形にスケール | OK |
| 極端音域(A0+C8+C4和音) | クラッシュなし。大量の加線で正しく描画(視覚確認済) | OK |
| ゼロ音価/負値 | クラッシュなし | OK |

### 視覚検査所見(生成PNG 1ページ目を目視)

- **テンポ記号が豆腐(□)化**: 全PDF/PNGで `♩ = 120` が `□ = 120` と表示される。SVG側にはSMuFLのテンポ音符グリフが存在するが(class="tempo"を確認)、**cairosvgがラスタライズ時に音楽フォント(Bravura等)を解決できず**tofuになる。デモの信頼性に直結。→ **P1**(engrave.py:44 write_pdf経路全体)。
- extreme.png: 加線が上下に正しく伸び、A0/C8が判読可能。詰まり・重なりなし。
- big500.png: 7ページ・小節番号付き・レイアウト崩れなし。ただし入力がクロマ的にEb調号→ほぼ全音符に臨時記号(入力起因)。

### 計数整合バグ(P2)

`svg_note_count`(engrave.py:37)は `svg.count('class="note')` で **`class="note"` と `class="notehead"` の両方にヒット**し、常に実音数の2倍を返す。実測: 1音→2、3音和音→6。`notes_engraved`メタとテストの健全性代理指標が黙って2倍にずれている。

---

## 3. quality(審判自身 — 4指標 + score_rhythm)

対象: `tools/ai-ears/ears.py`(chroma/onset/tempo/health, WEIGHTS ears.py:213), `score_metrics.py`(score_rhythm)。
ground-truth = きらきら星系30音メロディ(BPM100)を正弦合成。baseline(同一MIDI)= overall **0.9029**。

### 審判を騙す攻撃 実測表

| 攻撃 | overall | chroma | onset | tempo | health | 判定 |
|---|---|---|---|---|---|---|
| **baseline(同一)** | 0.9029 | 0.9908 | 0.6905 | 0.9938 | 1.0 | — |
| (a) 同一音高・**リズムでたらめ** | **0.6819**「部分一致」 | 0.7487 | 0.2767 | 0.9938 | 1.0 | **P1** |
| (b) 密アルペジオ(**chroma稼ぎ**384音) | 0.6517 | 0.6968 | 0.2454 | 0.9938 | **1.0** | **P0** |
| (c) 無音に近い(1音) | 0.4804「低一致」 | 0.4525 | 0.0 | **0.9938** | 1.0 | P1 |
| (d) **全音オクターブ上げ** | **0.9012「高一致」** | 0.9866 | 0.6905 | 0.9938 | 1.0 | **P0** |
| (e) 50%オクターブ誤り | 0.9027「高一致」 | 0.9903 | — | — | 1.0 | **P0** |

### 「審判が測れていないもの」— 実験で裏づけ

1. **オクターブ誤り耐性ゼロ(P0)**: 全音を1オクターブ上げた採譜(ピアニストには完全な誤り)が **0.90「高一致」**=baseline同等。chromaがオクターブ不変(ears.py:62 chroma_cqt)、onsetは高さ非依存、tempo/healthは無視。最頻の実務誤りを検出できない。`score_rhythm`は音高完全一致要求ゆえ0.05で検出するが、**overallに入っておらず、production に存在しない正解MIDIを要求**(score_metrics.py:66)。
2. **リズム崩壊が overall に十分反映されない(P1)**: 攻撃(a)は拍が全崩壊でも chroma0.75+tempo0.99 が下駄を履かせ 0.68「部分一致」。`score_rhythm`=0.196 が真値だが、これは overall の外(重み0)。審判の主指標はリズムに鈍感。
3. **health密度ペナルティが崖=回避可能(P0)**: `score_health`(ears.py:190)の密度閾値は 25音/秒の**ハードカット**。攻撃(b)は 20音/秒に整えるだけで384幽霊音符でも **health=1.0・issues空**。40音/秒に上げて初めて health=0。攻撃者は間隔を空けるだけで健全性検査を素通りできる。
4. **tempo指標が採譜品質を測っていない(P1)**: tempo(ears.py:125)は「MIDIの**宣言テンポメタ** vs 音源テンポ推定」の比較で、音符内容を見ない。無音1音でも scramble でも **0.88〜0.99**。固定重み0.1で常時高得点→全overallを底上げ。
5. **強弱・アーティキュレーション・声部**: velocity/slur/staccato/声部情報はどの指標にも入力されていない(chroma/onset/health いずれも pitch・timing・countのみ参照)。測定対象外であることを実験外で確認(コード上、velocityを読む指標なし)。

---

## P0/P1/P2 分類サマリー(再現手順つき)

- **P0(3件)**: [quality] オクターブ誤り無検出 / [quality] density崖の回避 / [quality] score_rhythmがoverall外
  - 再現: `tools/ai-ears/.venv/bin/python` で ground-truth合成→全音+12して `ears.overall`。density=20/sで `score_health`→1.0。
- **P1(6件)**: [notate] 弱起の巨大休符 / [notate] 交差メロディの機械分割 / [notate] 休符46%(声部未分離) / [engrave] テンポ豆腐グリフ / [quality] リズム崩壊がoverallに鈍感 / [quality] tempo指標が内容非依存
- **P2(1件)**: [engrave] `svg_note_count`が2倍計数
- **既知・記録済(修正不要だが台帳化)**: 転調の区間調未対応(spelling.py:8) / 同staff持続切断(score.py:96)

---

## 品質ダッシュボード行案

| 機能 | 現在スコア/状態 | 既知の限界(正直リスト) | 次の改善候補 |
|---|---|---|---|
| notate | 大譜表分割・休符統合・stem付与は動作。turkish再解剖で声部爆発解消・休符run≤3 | 弱起未対応(先頭に巨大休符)/交差メロディを純高さで機械分割/休符比率40-46%(声部未分離)/区間調未対応 | ①ピックアップ小節検出 ②同時発音の声部連続性(高さヒステリシス)③持続音の声部化で休符削減 |
| engrave | 空/1音/500小節/極端音域すべてクラッシュ無・レイアウト健全 | テンポ音符グリフがPDF/PNGで豆腐化(音楽フォント未埋込)/`svg_note_count`が2倍計数 | ①cairosvgにBravura等を埋込 or 事前フォント解決 ②note計数を`class="notehead"`限定に |
| quality | 音高・出だし・健全性の勾配は出る(baseline0.90) | **オクターブ誤りを検出不能(0.90維持)**/リズム崩壊にoverallが鈍感/density崖で幽霊音符回避可/tempoが内容非依存/強弱・アーティキュレーション・声部は測定対象外 | ①オクターブ考慮の音高指標を導入 or score_rhythmをoverallへ統合 ②density閾値を連続ペナルティ化 ③tempoを内容依存化 or 重み再考 |
