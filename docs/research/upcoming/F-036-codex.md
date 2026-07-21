# ドラム譜の記譜（percussion clef / unpitched note / キット音色マップ / MusicXML percussion）調査レポート（codex=論文・WEB担当、失敗例重視）

調査日: 2026-07-21
対象機能: F-036（ドラム譜の記譜）
分担: codex担当（論文＋WEB、失敗例を最大限）
方針: 実在ソースのみ・URL併記・憶測なし。英語圏/中国語圏の一次情報（W3C MusicXML仕様・MuseScore/Dorico/Finale/Sibeliusドキュメント・GitHub issue・GM仕様・学術）を優先。実在確認できないURLは「未確認」と注記。

> 検証済み（WebFetchで一次確認）:
> - `<midi-unpitched>` は **1〜128 の 1-based**。仕様原文「specifies a MIDI 1.0 note number ranging from 1 to 128」「Note that MIDI 1.0 note numbers are generally specified from 0 to 127 rather than the 1 to 128 numbering used in this element」を確認。([W3C midi-unpitched](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/midi-unpitched/))
> - W3C percussion tutorial の実例が Kick=`37`, Closed HH=`43`, Crash=`50`, Cowbell=`57`（＝GM 36/42/49/56 に +1）を使用。clef=`<sign>percussion</sign>`、`<unpitched><display-step>B</display-step><display-octave>3</display-octave>`、同一線上で cymbal=`<notehead filled="no">diamond</notehead>` / hi-hat=`<notehead>x</notehead>` で楽器を区別、cowbellは `<staff-lines>1</staff-lines>` の1線譜を確認。([W3C percussion tutorial](https://www.w3.org/2021/06/musicxml40/tutorial/percussion/))

---

## 結論（最重要の罠）

1. **off-by-one が最大の地雷**: GM の note 番号（0〜127）をそのまま `<midi-unpitched>` に入れると、全打楽器が半音1つ下の別楽器になる。MusicXMLは 1-based（1〜128）なので `midiUnpitched = gmNote + 1`。W3C自身の例が GM 36/42/49/56 に対し 37/43/50/57 を出している。
2. **staff position（display-step）を音色キーにしてはいけない**: percussion clef は音高を持たず、同じ線・同じ display-step に複数楽器が乗る。区別は notehead + instrument + voice/stem の組み合わせで、ソフトごとに優先順位が違う。
3. **「標準ドラム譜」は事実上存在しない**: PAS のガイドラインはあるが絶対標準ではなく、Kick/Snare/HH の線位置・notehead 割当・stem/voice 規約はソフト・出版・テンプレートで揺れる。単一エクスポータで全ソフト互換は取れない。

---

## (1) ドラム記譜規約の失敗例・落とし穴

| 落とし穴 | 具体例 / バグ化する点 |
|---|---|
| 「標準ドラム譜」は絶対標準ではない | PAS のドラムセット記譜も “guideline” であり絶対標準なし。Kick / Snare / HH / Ride の線位置は出版・ソフト・テンプレートで揺れる。**staff position だけを楽器IDにしてはいけない**。 |
| percussion clef は音高ではない | `<clef><sign>percussion</sign></clef>`。ただし `display-step/display-octave` の座標計算では percussion clef は **treble clef 扱い**。bass clef 前提で座標変換すると全ノートがずれる。 |
| `display-step` は音色ではなく表示位置 | 同じ見た目の上部スペースが bass clef なら B3、percussion clef なら別位置。MIDI音色と混同すると hi-hat が別音になる。 |
| notehead が「装飾」でなく音色選択に使われる | Sibelius / MuseScore / Finale では同じ線上でも normal / x / diamond / slash / circle-x で別楽器・別奏法（cross-stick, ride bell, HH open等）。notehead を正規化して潰すと音色が混線する。 |
| normal / x / diamond の割当がソフトごとに異なる | W3C tutorial は cymbal に hollow diamond、hi-hat に x を例示。MuseScore `.drm` は `normal`, `cross`, `x`, `diamond`, `circled`, `triangle` 等をローカル名で持つ。Sibelius は notehead + articulation + sound の組で drum map を作るため、同じ x でも別音になり得る。 |
| stem/voice 変更で importer が誤判定 | MuseScore handbook は voice 1/up-stem=hands、voice 2/down-stem=feet を推奨。小節ごとに voicing が変わると import 時に一部音符が誤認識・未importになり得る。([MuseScore Percussion input](https://handbook.musescore.org/idiomatic-notation/percussion/inputting-percussion-notation)) |
| 「上向き=手、下向き=足」を硬く実装しすぎる | 実譜では snare を down-stem、HH pedal を up-stem に混ぜる例、教育譜の単声化がある。voice/stem は**強いヒントであって唯一の楽器根拠にしない**。 |
| 線位置番号の座標系がソフトで逆 | MuseScore `.drm` の `<line>` は 0=top line 基準で下方向が正。Finale の Percussion Layout の Staff Position は別基準（下方ledger基準で上へ正のことがある）。数値を直接流用すると上下反転する。([Drumset .drm doc](https://musescore.org/en/handbook/developers-handbook/references/drumset-drm-file-documentation)) |
| 同じ staff position に複数楽器 | Finale/Sibelius は同一 staff position に複数 notehead/Note Type を置ける。`display-step` だけでは一意にならない。([Finale percussion tutorial](https://usermanuals.finalemusic.com/FinaleWin/Content/Finale/Tut9Percussion.htm)) |
| 入力経路で譜面構造が変わる | MuseScore の percussion panel default voice はクリック/キーボード入力に効くが、MIDI keyboard 入力では任意 voice を使える。入力経路で voice 構造が変わる。 |
| 採譜AIのクラス粒度と記譜粒度が不一致 | ADT論文は 3-class（kick/snare/HH）や 8-class（+tom/ride/crash/other）へ集約されがち。譜面出力では ride bell / pedal HH / side stick / rimshot 等が必要で、ADT出力をそのまま kit にできない。([Vogl et al. DAFx2018](https://ifs.tuwien.ac.at/~vogl/dafx2018/)) |

---

## (2) MusicXML percussion 表現の落とし穴

| 項目 | 罠 |
|---|---|
| `<pitch>` vs `<unpitched>` | percussion clef のノートは `<pitch>` でなく `<unpitched>` を使う。`<pitch>` で出すと解析側が実音高扱いし heuristics 依存になる。([W3C unpitched](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/unpitched/)) |
| `display-step/display-octave` 省略 | 省略すると中央線配置になる。1線譜では通っても5線 kit に戻すと情報不足。 |
| `display-step` に臨時記号がない | display-step は A–G＋octave の表示座標であり黒鍵情報を持たない。MIDI音色は `<midi-unpitched>`/`<instrument>` 側で持つ。 |
| **`<midi-unpitched>` は 1-based（最大の off-by-one 罠）** | 仕様原文で 1〜128。GM 36 Bass Drum 1 → MusicXML `37`、GM 38 Snare → `39`、GM 42 Closed HH → `43`、GM 49 Crash 1 → `50`。GM値をそのまま入れると半音1つ下の別打楽器になる。([W3C midi-unpitched](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/midi-unpitched/)) |
| W3C tutorial が +1 を実例化 | kick=`37`, hi-hat=`43`, crash=`50`, cowbell=`57`。GM表の 36/42/49/56 を直入れするとバグ。([W3C percussion tutorial](https://www.w3.org/2021/06/musicxml40/tutorial/percussion/)) |
| `<instrument>` 省略 | 1パートに複数 `<score-instrument>` を持つなら各 `<note>` に `<instrument id="..."/>` が必要。省略すると再生楽器が別物に化ける（下記 MuseScore issue 参照）。([W3C instrument](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/instrument/)) |
| `score-instrument id` のスコープ | id は文書全体で unique 必須。パートごとに `I1` を使い回すと IDREF 解決が壊れる。([W3C score-instrument](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/score-instrument/)) |
| notehead と instrument の不整合 | 見た目 x／`<instrument>`=snare／`midi-unpitched`=ride のような不整合時、どれを優先するかがソフトで割れる（表示優先／再生優先／kit map優先）。 |
| `<percussion>` 要素の誤解 | MusicXML の `<percussion>` は `<direction-type>` 配下の pictogram 用（MusicXML 3.0で導入・3.1で追加値）。note の音色マップではない。kit note の代替に使うと importer は無視しがち。 |
| `<instrument-sound>` は完全な drum map ではない | `drum.snare-drum`, `metal.cymbal.ride` 等の標準 sound id はあるが、staff位置・notehead・MIDI note・奏法を一括定義しない。補助情報であり唯一キーにしない。 |
| 1パート複数楽器 vs 複数パート | drum kit は1 `<score-part>` に複数 `<score-instrument>` が自然。Doricoは、Finale由来の5線打楽器は mapping 情報を含むことが多いが Sibelius由来は含まない場合があると説明。([Dorico: MusicXML unpitched percussion](https://www.steinberg.help/r/dorico-pro/6.1/en/dorico/topics/project_file_handling/project_file_handling_musicxml_unpitched_percussion_r.html)) |
| round-trip で map が消える | Dorico forum で Dorico 3.1 の unpitched percussion MusicXML export が未成熟と開発者が回答。MuseScore forum でも midi-unpitched off-by-one 誤解や display-step 混同が繰り返し報告。([Dorico forum: Exporting Drum Set XML](https://forums.steinberg.net/t/exporting-drum-set-xml-issue/147740)) |
| 実装分岐の具体例 | MuseScore issue で、追加 `<instrument>` 要素の有無だけで再生楽器が snare / piano に分岐する報告あり（MuseScore 4系）。([MuseScore issues](https://github.com/musescore/MuseScore/issues)) ※個別issue番号は本文で言及したが番号自体は**未確認**（要確認）。 |

**GM ↔ MusicXML `<midi-unpitched>` 数値ズレ早見表（+1オフセット）**

| 楽器 | GM MIDI note (0..127) | MusicXML `<midi-unpitched>` (1..128) |
|---|---:|---:|
| Acoustic Bass Drum | 35 | 36 |
| Bass Drum 1 / Kick | 36 | 37 |
| Side Stick | 37 | 38 |
| Acoustic Snare | 38 | 39 |
| Closed Hi-Hat | 42 | 43 |
| Pedal Hi-Hat | 44 | 45 |
| Open Hi-Hat | 46 | 47 |
| Crash Cymbal 1 | 49 | 50 |
| Ride Cymbal 1 | 51 | 52 |
| Cowbell | 56 | 57 |

出典: GM percussion map ([CMU GM Perc Map](https://www.cs.cmu.edu/~music/cmp/archives/cmsip/readings/GMSpecs_PercMap.htm))、+1オフセットは W3C midi-unpitched 仕様およびtutorialで確認。

---

## (3) キット音色マップの互換失敗例

| 項目 | 失敗例 |
|---|---|
| GM channel 10 への過信 | GMは channel 10 + note 35..81 が基本。ただし MusicXML `<midi-channel>` は 1..16、`<midi-unpitched>` は 1..128。MIDI wire の channel 9/10 表記混乱と note off-by-one が同時発生する。 |
| GM 35 vs 36 の Kick二重定義 | GMには `35 Acoustic Bass Drum` と `36 Bass Drum 1` が両方存在。「Kick=36固定」にすると concert/acoustic bass drum と kit kick が混ざる。([CMU GM Perc Map](https://www.cs.cmu.edu/~music/cmp/archives/cmsip/readings/GMSpecs_PercMap.htm)) |
| Roland拡張は rim/edge が GM外 | Roland TD-17 default map は KICK=36, SNARE HEAD=38 だが HH CLOSED EDGE=22, HH OPEN EDGE=26, AUX 等が GM基本範囲外。GMに丸めると edge/bow, rim/head を失う。([Roland TD-17 default MIDI note map](https://support.roland.com/hc/en-us/articles/360005173411-TD-17-Default-MIDI-Note-Map)) |
| GM2 / GS / XG の範囲拡張 | XG/GS前提のSMFをGM音源で鳴らすと別音・無音・簡略化が起きる。※GM2/GS/XGの正式マッピング表URLは**未確認**（メーカー一次資料で要確認）。 |
| Cubase Drum Map | Cubase の drum map は 128 MIDI note 各設定。GM Map以外を選ぶと note name と音源 trigger が不一致になる。([Cubase Drum Map Settings](https://www.steinberg.help/r/cubase-pro/15.0/en/cubase_nuendo/topics/midi_editors/midi_editors_drum_editor_drum_map_settings_c.html)) |
| Logic Drum Machine Designer | input note → pad output note へ変換して subtrack へ送る。export 時に input/output どちらを採用するか誤ると DAW内では鳴るが外部で鳴らない。([Logic DMD](https://support.apple.com/en-ae/guide/logicpro/lgsi7e4c8c73/10.7/mac/11.0)) |
| MuseScore `.drm` 非互換 | `.drm` は MuseScore独自XML。`Drum pitch`=MIDI note、`line`=top line基準、`voice`=0..3、`stem`=0/1/2。別ソフトへは移せない。([Drumset .drm doc](https://musescore.org/en/handbook/developers-handbook/references/drumset-drm-file-documentation)) |
| Sibelius は未マップ音を鳴らさない | unpitched staff は notehead/position が sound に map されていなければ playback / MIDI export されない。Edit Staff Type で sound allocation が必要。([Avid Drum Mapping KB](https://kb.avid.com/pkb/articles/en_US/How_To/Drum-Mapping), [Sibelius hi-hat notehead](https://www.sibelius.com/helpcenter/article.php?id=332)) |
| Finale の三層マップ | Percussion Input Map / Percussion Layout / MIDI(Output) Map が分離。表示だけ直しても playback が直らず、逆も同様。([Finale Percussion Layout Designer](https://usermanuals.finalemusic.com/Finale2012Mac/Content/Finale/DRUMDLG.htm)) |
| Web譜面サービスの表示優先 | Soundslice等は percussion playback が staff position + notehead の percussion map に依存。`<midi-unpitched>` を完全優先するとは限らない。※Soundslice公式一次URLは**未確認**。 |
| MusicXML→DAWで記譜情報が落ちる | SMF は notehead/stem/voice/staff position を持たない。MusicXML→MIDI→DAW経路で人間向け記譜情報が消える。DAW連携には drum map sidecar が必要。 |

---

## 採譜プロジェクトが取るべき安全な実装方針

- **内部モデルは `kitPieceId` を主キーにする**。`display-step` / MIDI note / notehead / voice のいずれも主キーにしない。
- 各 hit に最低限これを持たせる: `label`, `canonicalInstrument`, `gmNote0`（0-based）, `musicXmlMidiUnpitched = gmNote0 + 1`, `scoreInstrumentId`, `displayStep/displayOctave`, `staffPosition`, `notehead`, `filled`, `smufl`, `voice`, `stem`, `articulation`, `sourceConfidence`。
- **off-by-one を単一関数に閉じ込める**: `gmNote0` と `musicXmlMidiUnpitched` を混同しないよう、変換は 1 箇所（`gm0ToMusicXmlUnpitched(n) => n + 1`）のみ。テストで Kick 36→37 を固定。
- MusicXML export は冗長に出す: `<clef><sign>percussion</sign>`, `<staff-details><staff-lines>5</staff-lines>`, `<unpitched>`, `<instrument>`, `<notehead>`, `<voice>`, `<stem>`, `<score-instrument>`, `<midi-instrument><midi-channel>10</midi-channel><midi-unpitched>...</midi-unpitched>`。
- Import優先順位を固定する: `instrument id` → `<midi-unpitched>` → `<instrument-sound>` → `notehead + display-step + voice/stem`。最後の組は推定扱いで warning を残す。
- **全譜面に drum legend（凡例）を出力**。カスタムkit・GM外note・XG/GS/Roland系 edge/rim を含む場合は必須。
- **target profile を分ける**: `generic MusicXML` / `MuseScore` / `Dorico` / `Finale` / `Sibelius` / `DAW-GM` / `Roland TD` / `Yamaha XG`。単一エクスポータで吸収しない。
- **round-trip テスト fixture** を用意: Kick 35/36, Snare 38, Side Stick 37, Rim 40, Closed/Pedal/Open HH 42/44/46, HH edge 22/26, Crash 49, Ride 51, Ride Bell 53, Cowbell 56。書き出し→再読み込み後の staff位置・notehead・voice/stem・instrument id・再生MIDI note を全て検査（XML文字列一致だけでは不十分）。
- **DAW export では SMF に加え drum map sidecar** を出す（Cubase map / REAPER note names / Logic DMD 用CSV相当）。
- **ADT出力粒度を最初から kit map に合わせる**。3-class出力しかない場合、closed/open HH や ride/crash や rim/side stick を勝手に細分化しない（誤情報を生む）。

---

## 一次ソース一覧（実在確認レベル付き）

**WebFetch検証済み（原文引用確認）**
- [W3C MusicXML 4.0 `<midi-unpitched>`](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/midi-unpitched/) — 1..128 の1-based を原文確認
- [W3C MusicXML 4.0 Percussion tutorial](https://www.w3.org/2021/06/musicxml40/tutorial/percussion/) — 37/43/50/57 と clef/unpitched/notehead 実例を確認

**既知の一次ソース（URL構造は妥当、個別ページ内容は要現地確認）**
- [W3C `<unpitched>`](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/unpitched/) / [`<score-instrument>`](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/score-instrument/) / [`<instrument>`](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/instrument/) / [`<clef>`](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/clef/) / [notehead-value](https://w3c.github.io/musicxml/musicxml-reference/data-types/notehead-value/)
- [MuseScore Percussion input](https://handbook.musescore.org/idiomatic-notation/percussion/inputting-percussion-notation) / [Percussion kit customization](https://handbook.musescore.org/idiomatic-notation/percussion/percussion-kit-customization) / [Drumset .drm file doc](https://musescore.org/en/handbook/developers-handbook/references/drumset-drm-file-documentation)
- [Dorico: MusicXML unpitched percussion import](https://www.steinberg.help/r/dorico-pro/6.1/en/dorico/topics/project_file_handling/project_file_handling_musicxml_unpitched_percussion_r.html) / [Dorico forum: Exporting Drum Set XML](https://forums.steinberg.net/t/exporting-drum-set-xml-issue/147740)
- [Finale percussion tutorial](https://usermanuals.finalemusic.com/FinaleWin/Content/Finale/Tut9Percussion.htm) / [Percussion Layout Designer](https://usermanuals.finalemusic.com/Finale2012Mac/Content/Finale/DRUMDLG.htm)
- [Avid Drum Mapping KB](https://kb.avid.com/pkb/articles/en_US/How_To/Drum-Mapping) / [Sibelius hi-hat notehead](https://www.sibelius.com/helpcenter/article.php?id=332)
- [CMU GM Percussion Map](https://www.cs.cmu.edu/~music/cmp/archives/cmsip/readings/GMSpecs_PercMap.htm) / [Cubase Drum Map Settings](https://www.steinberg.help/r/cubase-pro/15.0/en/cubase_nuendo/topics/midi_editors/midi_editors_drum_editor_drum_map_settings_c.html) / [Logic Drum Machine Designer](https://support.apple.com/en-ae/guide/logicpro/lgsi7e4c8c73/10.7/mac/11.0) / [Roland TD-17 default MIDI note map](https://support.roland.com/hc/en-us/articles/360005173411-TD-17-Default-MIDI-Note-Map)
- 論文: [Vogl et al. "Towards Multi-Instrument Drum Transcription" DAFx2018](https://ifs.tuwien.ac.at/~vogl/dafx2018/)

**未確認（本文で言及したが個別に検証できていない — 実装前に要確認）**
- GM2 / Roland GS / Yamaha XG の正式拡張マッピング表の公式URL
- MuseScore の該当 issue 番号（追加 `<instrument>` 要素で再生楽器が分岐する報告）
- Soundslice の percussion playback 仕様の公式ページURL
- Vogl et al. の DOI（DAFx2018 は査読会議、DOI付与状況は要確認）
