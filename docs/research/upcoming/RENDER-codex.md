# テキスト記譜（简谱/数字譜・リードシート・度数表記）の PDF/SVG 描画・レイアウト整形 — 調査

- 調査日: 2026-07-21
- 調査手段: mcp\_\_codex\_\_codex（成功）＋ WebFetch による主要 URL 検証
- 対象機能: 简谱(jianpu / numbered notation)、リードシート(chord symbols 付きメロディ)、度数表記(Nashville number / scale-degree)の PDF/SVG 描画・レイアウト整形
- 方針: URL は実在確認できたもののみ掲載。捏造禁止。不確実なものは明記。

---

## 結論（要点）

- **リードシート中心**なら canonical data は MusicXML、出力は `LilyPond / OSMD / Verovio` の比較テストが現実的。chord 表現は成熟している。
- **简谱 / jianpu 中心**なら標準 renderer の対応が薄い。実用候補は `jianpu-ly -> LilyPond`、OSMD の **Jianpu mode（sponsor early access）**、または hand-rolled SVG。
- MusicXML には `clef sign=jianpu` があるが、**それだけでは octave dots / duration underlines / dashes / 漢字レイアウトを表現しきれない**。renderer 依存で五線譜に落とされるリスクがある。

---

## フォーマット別対応表

| 対象 | 標準表現 | 実用 renderer | 注意点 |
|---|---|---|---|
| 简谱 / jianpu | MusicXML 4.0 に `clef sign=jianpu` あり | jianpu-ly, OSMD Jianpu mode, 一部 MuseScore plugin / web tools | `clef=jianpu` だけでは octave dots / duration underlines / dashes / 中国語レイアウトを十分表現できない |
| Lead sheet | MusicXML `<harmony>`, melody, lyrics | LilyPond, OSMD, Verovio | chord symbol の横位置、long chord、slash chord、line break で崩れやすい |
| Nashville number / scale-degree | MusicXML `<harmony>` の `<numeral>` 系 | renderer 依存 | 多くの表示系は pop chord root (`C`, `G7`) が強く、degree chord は要検証 |

---

## MusicXML

MusicXML は jianpu を独自記譜言語として持つのではなく、`clef-sign` に `jianpu` を追加して「以後を numbered notation として表示する」合図を持つ形。公式 reference に `jianpu` clef があり、`TAB` と異なり visual clef symbol ではないと説明される。

- https://www.w3.org/2021/06/musicxml40/musicxml-reference/data-types/clef-sign/

Lead sheet / chord symbols は強い。`<harmony>` が chord symbols / functional harmony analysis を表し、root, bass, kind, degree, numeral を持てる。

- https://w3c.github.io/musicxml/musicxml-reference/elements/harmony/
- https://w3c.github.io/musicxml/tutorial/chord-symbols-and-diagrams/

**壊れどころ**: `jianpu clef` を renderer が無視して五線譜化する / Nashville `<numeral>` を解析情報として扱い印字しない / long chord names が短い音符の上で衝突する / enharmonic spelling が transpose 後にズレる / `C/E`, `G7/B` の bass alignment が崩れる。

---

## Verovio

native input は MEI。MusicXML, Humdrum, Plaine & Easie (PAE), ABC も入力可能。PAE は incipit 向けで jianpu 用ではない。

- https://book.verovio.org/toolkit-reference/input-formats.html

MEI では `<harm>` が supported elements に入り、ABC 入力例でも chord symbols がメロディ上に出る。**Lead sheet 的な chord 表示は可能**。

- https://book.verovio.org/toolkit-reference/mei-support.html

ただし公式 docs 上で **jianpu renderer 対応は確認できない**。MEI の `data.NOTATIONTYPE` allowed values にも `jianpu` は無く、`cmn`, `mensural`, `neume`, `tab` 系が中心。

- https://music-encoding.org/guidelines/dev/mei-all/data-types/data.NOTATIONTYPE.html

**失敗例**: unsupported MEI elements は読み込み時に無視され再出力でも保存されない / SVG 出力では Firefox・Linux の default `DejaVu Serif` による text layout 問題が明記 / MusicXML import は converter 経路差があり、JS toolkit では Humdrum 経由 import が default でない点が罠。

- https://book.verovio.org/toolkit-reference/output-formats.html

---

## LilyPond

**Lead sheet に強い**。`ChordNames`, `\chords`, melody, lyrics で simple lead sheet を作れ、chord name の表示体系も Scheme で拡張可能。公式 docs は inversion / altered bass を simultaneous pitches で入れると chord names が正しくならない既知問題も明記。

- https://lilypond.org/doc/v2.27/Documentation/notation/displaying-chords

**CJK** は UTF-8 入力と font 指定が重要。Pango / FontConfig 経由で text fonts を使い、`set-global-fonts` や `font-name` 指定ができる。glyph が無い場合は fallback または missing glyph。

- https://lilypond.org/doc/v2.24/Documentation/notation/fonts

**jianpu** は core LilyPond 単体ではなく、通常は `jianpu-ly` のような preprocessor を使う。`jianpu-ly`（Silas S. Brown「Jianpu in Lilypond」）は lyrics, 漢字 lyrics, guitar chords, fret diagrams, multiple parts, tuplets, grace notes, repeats, WithStaff, MusicXML conversion などを扱う。（GitLab ページ・PyPI で実在確認済み）

- https://gitlab.com/ssb22/jianpu-ly
- https://pypi.org/project/jianpu-ly/1.800/
- http://ssb22.gitlab.io/mwrhome/jianpu-ly.html （プロジェクト解説ページ）

**失敗例**: bar length 不整合で `barcheck fail` / MusicXML 変換で multi-voice・chord・pickup の同期ズレ / LilyPond version 差で grace notes や octave dots が壊れる / 漢字 lyrics の自動空白と syllable alignment のズレ / `1 - -` 系の長音 dash と tie・lyric attachment の衝突。

`lilyjazz` は handwritten jazz font/style であって jianpu engine ではない。Lead sheet の見た目改善に有用だが、install 漏れで chord/text font だけ default になる事例。

- https://github.com/OpenLilyPondFonts/lilyjazz

`tunefl` は LilyPond をオンラインで試す web interface として docs に記載。jianpu 専用機能は未確認。

- https://lilypond.org/doc/v2.23/Documentation/web/easier-editing

---

## music21

engraving engine ではなく Python の解析・変換 toolkit。`.show()` / `.write()` は MusicXML, LilyPond, MIDI 等へ出力し、**表示は MuseScore / LilyPond など外部アプリに委ねる**。

- https://music21.org/music21docs/usersGuide/usersGuide_08_installingMusicXML.html
- https://music21.org/music21docs/moduleReference/moduleConverterSubConverters.html

`JianpuClef` はある。docs には MusicXML が specialized `jianpu` sign で印を付ける、とある。ただし music21 自体が jianpu layout を描くわけではない。

- https://music21.org/music21docs/moduleReference/moduleClef.html

Lead sheet chord は `harmony.ChordSymbol` として扱えるが、supported chord syntax は限定的で duration realization は別処理が必要。

- https://music21.org/music21docs/moduleReference/moduleHarmony.html

---

## OSMD / abc2svg / その他

**OSMD** は MusicXML を browser / Node で SVG/PNG rendering する実用的 renderer。Chord symbols 対応があり、1.8.0 で short chords 上の chord centering bug 修正が記録。**Jianpu mode は sponsor early access（feat/jianpu ブランチ）**として公開情報あり（`JianpuAlwaysUsed = true` で有効化、audio playback + cursor sync 付き。WebFetch で内容確認済み）。

- https://github.com/opensheetmusicdisplay/opensheetmusicdisplay
- https://opensheetmusicdisplay.org/blog/release-1-8-0/
- https://opensheetmusicdisplay.org/blog/jianpu-mode/

**abc2svg** は ABC -> SVG renderer。npm / unpkg 上に `jianpu-1.js` module が確認できる。jianpu 仕様の完全性は別途検証が必要。

- https://www.npmjs.com/package/abc2svg
- https://app.unpkg.com/abc2svg@1.22.1

**jianpu99 / FanQie** は MusicScoresLab が MusicXML <-> Jianpu converter として説明。URL は確認できたが仕様の出所・保守性は追加確認要。

- https://www.musicscoreslab.com/

中国語圏の実用ツールとして `jianpu.info`（簡譜/鼓譜 editor tutorial）、MuseScore plugin の Jianpu Numbered Notation。

- https://jianpu.info/tutorial/video
- https://musescore.org/en/project/jianpu-numbered-notation-ms-2-46

---

## Hand-Rolled SVG

**最も自由**。jianpu の octave dots、duration underlines、dashes、漢字 lyrics、degree chords、Nashville numbers をそのまま設計できる。反面、music engraving の難所を全部自前で持つ: measure width 計算 / line breaking / collision avoidance / font metrics / PDF embedding / lyrics・chords の timestamp alignment / mobile・print scaling / transpose 時の semantic consistency。

---

## 失敗ケース一覧（最大化）

- **line break**: 4 小節固定にすると long lyrics / long chord で overflow。auto break にすると phrase boundary が崩れる。
- **chord alignment**: 短い eighth note 上の `F#m7b5/C` が次音符に被る。行頭の継続 chord を出す/出さないで演奏者の読みが変わる。
- **jianpu rhythm**: underlines が beam group 単位で切れない / dash sustain が barline を跨ぐ / dotted duration と dash の意味が混ざる。
- **jianpu pitch**: `1=C` と `6=A minor` の扱い / key change / 臨時記号の有効範囲 / octave dot 上下位置が崩れる。
- **CJK**: fallback font で漢字幅が変わり lyric alignment がズレる。PDF では表示されるが SVG/browser で tofu（豆腐＝□）になる。
- **conversion loss**: MusicXML `jianpu clef` は残っても renderer が五線譜で描く / MEI unsupported element は Verovio で落ちる / music21 は解析情報を保持しても描画は外部依存。
- **typography**: SVG text を path 化しないと環境差、path 化すると検索/編集不可。font 埋め込み漏れで PDF が別環境で崩れる。

---

## Best Practices

1. Lead sheet 中心なら canonical data は MusicXML、出力は LilyPond/OSMD/Verovio で比較テスト。
2. Jianpu 中心なら canonical data に「degree, key, octave, duration, lyric, chord」を持ち、表示は jianpu 専用 renderer か `jianpu-ly` に寄せる。
3. `MusicXML jianpu clef` だけに依存しない。renderer ごとの golden SVG/PDF を持つ。
4. CJK font を明示し PDF に埋め込む。SVG は target browser で pixel regression を取る。
5. chord symbols は timestamp anchor + collision box で扱う。long chord / slash chord / no-chord / repeated chord / line-start chord を fixtures 化。
6. jianpu fixtures には最低限 pickup, tuplets, grace notes, repeats, multiple verses, 漢字 lyrics, key change, minor-key `6=`, multi-voice を含める。

---

## 検証メモ

- 主要 URL のうち `opensheetmusicdisplay.org/blog/jianpu-mode/`（Jianpu mode = sponsor early access, feat/jianpu ブランチ, `JianpuAlwaysUsed`）と `gitlab.com/ssb22/jianpu-ly`（Silas S. Brown 作, Apache-2.0, 161 tags）は WebFetch で実在・内容確認済み。
- `musicscoreslab.com`（jianpu99/FanQie）、`jianpu.info`、abc2svg の `jianpu-1.js` は URL 実在確認レベル。**仕様の完全性・保守状況は未検証**につき採用前に要精査。
