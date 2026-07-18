# 実演奏音源 × 正解楽譜 マッチング（real-audio ベンチ資産）

正解つきベンチマーク用に、ユーザー提供の楽譜（正解 MIDI）に対応する **実演奏の YouTube 音源**を収集・照合し、
楽譜と最も一致する 1 本ずつを確定した記録。合成レンダリングと違い、ルバート・残響・実楽器音色を含む
「現実条件での正解つき評価」が可能になる。

- 照合ツール: `tools/ai-ears/ears.py compare`（chroma-DTW による音高一致度、onset F値、テンポ整合、譜面健全性）
- 調推定: Krumhansl-Schmuckler プロファイルによる audio 側キー推定 vs 正解 MIDI の調
- 音源は git 外（`tools/ai-ears/testdata/pd-corpus/real-audio/`）。DL はスクリーニング用低ビットレート、
  照合前に無音トリム＋ラウドネス正規化した 22.05kHz mono wav に変換
- **私的検証利用**: 本照合は採譜評価ツールの精度検証という私的・研究目的の内部利用に限る。音源の再配布・公開は行わない

`ears.py compare` の総合スコア重み: chroma 0.4 / onset 0.3 / tempo 0.1 / health 0.2。
chroma は移調に敏感なため、**移調演奏は自動的に低スコア＝不一致として検出される**（本件では全候補が正しい調だった）。

---

## 曲1: モーツァルト トルコ行進曲（Rondo alla Turca, K.331 第3楽章）

### 正解 MIDI 分析 — `Turkish_March_K331_C-Am.mid`

| 項目 | 値 |
|---|---|
| 調 | A minor → A major（MIDIのkey_sig表記は "C Major" だが、実音の音高クラス集中は A・E・C#・B＝Aメジャー基調。K.331終楽章の標準どおり Am→A） |
| 拍子 | 2/4 |
| テンポ | 120（MIDI設定。二分音符グリッド換算。実演奏の♩換算では約120〜136相当） |
| 長さ | 223 秒（記譜上のリピートを全展開してレンダリングしたもの） |
| 楽器 | Acoustic Grand Piano ×3トラック（右手旋律／装飾／左手伴奏）計 2,572音 |
| 音域 | MIDI 45–88（A2–E6） |

### 候補一覧と照合スコア

| 順位 | 候補 | チャンネル | 長さ | 調推定 | overall | chroma | onset | tempo(audio/midi) | health |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **turk_brooklyn** | **Brooklyn Duo (Marnie Laird, piano)** | 247s | A maj (0.856) | **0.831** | 0.910 | 0.581 | 129.2 / 120 | 1.00 |
| 2 | turk_yundi | Warner Classics (YUNDI) | 204s | A maj (0.857) | 0.828 | 0.923 | 0.570 | 136.0 / 120 | 1.00 |
| 3 | turk_tzvierez | Tzvi Erez | 214s | A maj (0.823) | 0.823 | 0.911 | 0.569 | 136.0 / 120 | 1.00 |
| 4 | turk_kassia | Kassia | 141s | A maj (0.820) | 0.757 | 0.875 | 0.380 | 112.3 / 120 | 1.00 |

- 4本すべて調は正しく **A major**（K.331終楽章の主要部の基調）。移調版・別調版は無し
- 上位3本は overall 0.82〜0.83 で拮抗。chroma 単独では yundi (0.923) が最高
- kassia は onset F値が低く（0.380）テンポも速め、リピート省略で長さも短い（141s）ため 4位

### 採用音源

- **turk_brooklyn** — Brooklyn Duo（ピアノ独奏 Marnie Laird）
  - URL: https://www.youtube.com/watch?v=A_THdzBnHy0
  - チャンネル: Brooklyn Duo（@BrooklynDuo, 再生 673万回）
  - **採用理由**: 総合スコア最高（0.831）。クリーンなスタジオ独奏ピアノ録音でchroma 0.910、テンポも標準的。
    プロ演奏・クリーン録音・リピート込みのフル演奏で、正解 MIDI の A-B-A 構造と対応が良い
  - 次点 yundi (Warner Classics) は chroma 最高で権威も高く、代替として同等に有力

### 楽譜との既知の乖離（注意点）

- **テンポ**: 実演奏は 129〜136bpm と MIDI 設定(120)よりやや速い。compareは倍/半テンポ許容のため
  スコアには軽微な影響のみ。正解グリッドは二分音符=120 だが♩換算では演奏と近い
- **リピート/構造**: MIDI は記譜リピートを機械展開。演奏者ごとにリピートの取り方・繰り返し回数が異なり、
  総尺（141〜247s）が変動する。chroma-DTW が時間整列するため尺差は罰せられない
- **ルバート・装飾**: 実演奏は主部/中間部の緩急やペダル残響を含む。onset F値が 0.57 前後に留まるのは主にこの残響と
  和音アルペジオのタイミング揺れによるもので、音高一致（chroma 0.91）は高い

---

## 曲2: 愛のロマンス（禁じられた遊び / Romance）

### 曲名特定

正解 PDF のタイトルは **「愛のロマンス（禁じられた遊び）／ Romanze Castellana ／ スペイン民謡」**。
これは世界的に知られるクラシックギター独奏曲 **"Romance"（別名 Romance Anónimo / Spanish Romance /
Romance de Amor / Jeux Interdits＝映画『禁じられた遊び』主題曲）** である。作曲者不詳のスペイン民謡系。

楽譜構造: 前半 Em（1〜14小節, Moderato ♩=96, 3/4, 三連符アルペジオ）→ FINE → 後半 E major（17〜32小節,
♯4つに転調）→ D.C. で反復。標準的な Em→E の Romance。

### 正解 MIDI 分析 — `Romanze_Castellana_G-Em.mid`

| 項目 | 値 |
|---|---|
| 調 | E minor → E major（key_sig "E minor"。実音の音高クラスは E・B・F#・G# 集中で PDF の Em/E major 構成と一致） |
| 拍子 | 3/4 |
| テンポ | 96（PDF の Moderato ♩=96 と一致） |
| 長さ | 120 秒（記譜リピート全展開） |
| 楽器 | Acoustic Guitar (nylon) 192音 ＋ Piano 2トラック 612音（伴奏/バス）計 804音 |
| 音域 | MIDI 40–76（E2–E5） |

### 候補一覧と照合スコア

| 順位 | 候補 | チャンネル | 長さ | 調推定 | overall | chroma | onset | tempo(audio/midi) | health |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **rom_lucarelli** | **Michael Lucarelli** | 166s | E min (0.713) | **0.854** | 0.855 | 0.756 | 112.3 / 96 | 1.00 |
| 2 | rom_ilona | Ilona Guitar | 182s | E min (0.790) | 0.835 | 0.859 | 0.652 | 92.3 / 96 | 1.00 |
| 3 | rom_whittingham | Alexandra Whittingham | 187s | E min (0.877) | 0.816 | 0.864 | 0.678 | 143.6 / 96 | 1.00 |
| 4 | rom_agic | Marija Agic | 196s | E maj (0.684) | 0.803 | 0.845 | 0.612 | 117.5 / 96 | 1.00 |

- 4本すべて主音は正しく **E**（Em/E major の推定差は曲が両調を含むため。移調版は無し）
- chroma は 4本とも 0.845〜0.864 で高く拮抗。lucarelli は onset F値が最高（0.756）で音の出だしが明瞭
- ilona はテンポが♩=96 の記譜指示に最も近い（92.3）が、総合では lucarelli が上位

### 採用音源

- **rom_lucarelli** — Michael Lucarelli（クラシックギター独奏）
  - URL: https://www.youtube.com/watch?v=fIp6gE8XHHY
  - チャンネル: Michael Lucarelli（@michaellucarelli, 再生 116万回）
  - **採用理由**: 総合スコア最高（0.854）。温かい音色のクリーンなソロギター・スタジオ録音で、
    chroma 0.855／onset 0.756（出だしの明瞭さが4本中最良）。標準的な Em→E の Romance をアレンジ改変なく演奏
  - 次点 ilona はテンポが記譜(♩=96)に最も忠実で、テンポ厳密性を重視する評価では有力な代替

### 楽譜との既知の乖離（注意点）

- **テンポ**: lucarelli は 112bpm と記譜(♩=96)よりやや速い Moderato。テンポ厳密性を最優先するなら
  ilona（92.3bpm）が最も近い。compareは倍/半許容のため総合影響は軽微
- **リピート/構造**: MIDI は D.C./FINE を全展開（120s）。演奏者ごとにリピート回数・中間部への進み方が異なり
  総尺（166〜196s）が変動。chroma-DTW が整列するため尺差は非ペナルティ
- **編成差**: 正解 MIDI はギター＋ピアノ伴奏の3トラック（アンサンブル的レンダリング）だが、採用音源はギター独奏。
  chroma（音高クラス分布）は主旋律・和声が支配的なため独奏でも高一致（0.855）。onset F値がやや低い（0.756）のは
  アルペジオの三連符タイミングの揺れとナイロン弦の残響による
- **調の major/minor 推定ゆれ**: 曲が Em と E major の両セクションを含むため、audio 側キー推定が候補により
  E min / E maj に分かれる。いずれも主音 E は一致しており移調ではない

---

## 生成物

- `tools/ai-ears/testdata/pd-corpus/real-audio/turkish_march.wav` — 採用（Brooklyn Duo, 22.05kHz mono, 無音トリム＋正規化済）
- `tools/ai-ears/testdata/pd-corpus/real-audio/romanze.wav` — 採用（Michael Lucarelli, 同上）
- `cand_*.wav` / `cand_*.mp3` — 全候補のスクリーニング音源（git外）
- `_search.py` / `_score.py` / `_runall.py` — 収集・照合の再現スクリプト（git外）

### 再現手順（要点）

1. `_search.py "ytsearch8:<query>"` で候補収集（yt-dlp `--extractor-args youtube:player_client=android_vr` が
   SABR規制回避に有効。要 yt-dlp 2026.07 以降＋Node.js）
2. 候補DL → ffmpeg で `silenceremove`＋`loudnorm`、22.05kHz mono wav へ変換（無音フレームによる chroma-DTW の
   NaN を回避するため無音トリムが必須）
3. `_runall.py` で全候補を `ears.py compare` にかけ、調推定と併せて overall スコアでランキング → ベスト1本を確定
