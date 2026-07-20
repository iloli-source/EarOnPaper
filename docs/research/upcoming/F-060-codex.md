# 機能「移調・キー変更（移調再生と移調譜の生成）」論文＋WEB調査報告（codex担当）

**調査日:** 2026-07-21
**対象:** 採譜/記譜ソフト機能「移調・キー変更」＝ (a) 移調再生（pitch-shift playback）／(b) 移調譜・移調パートの生成
**担当:** codex（OpenAI Codex 読取りセッション ＋ WebFetch による一次情報検証）
**方針:** 実在情報のみ・URL併記・捏造禁止。**特に失敗例を最大限**。未確認は「未確認」と明記。英語中心（中国語圏は移調概念の語は多いが「機能トラブルの実務ログ」は薄く、FOSS/公式Help側に情報が偏在）。

---

## 0. 調査範囲と限界（重要）

| 項目 | 内容 |
|------|------|
| 学術論文 | 「記譜ソフトの移調UI/異名同音」を直接扱う査読論文はほぼ皆無。**移調譜まわりは公式Help・GitHub Issue・フォーラムが主軸。** 一方 **pitch-shift の音質劣化は信号処理論文が豊富**（phase vocoder / STN分解 / formant保存）。 |
| 実機再現なし | MuseScore/Dorico/music21 を実機再現していない。フォーラム個別事例は「報告事例」として扱う。 |
| 検証状況 | 主要URLは WebFetch で本文確認済み（下記★印）。**中国語版 MuseScore フォーラム(`musescore.org/zh-hans/...`) は bot 403 で本文未確認 → 「未確認」扱い。** |
| 二層モデル | 「音は正しいが表記が読めない（譜面移調の失敗）」と「表記は原形だが音が劣化（再生移調の失敗）」は別レイヤ。混同が事故源。 |

---

## 1. 異名同音・調号選択の失敗（enharmonic / key-signature）

最頻の失敗は **「音高は合っているが譜面として読めない」**。半音数ベース移調・MIDI由来データ・移調楽器・カポ系で顕在化する。

### 1.1 music21: 整数移調は異名同音を保持しない ★検証済み
`.transpose(i)`（整数）は内部で `ChromaticInterval` になり、**設計上 enharmonics を「気にしない」**。music21 が文脈上よいと思う綴りに自由に変え、正しいことも誤ることもある。異名同音を守るなら `"P8"` / `"m-3"` のような **diatonic interval 文字列**を使えという公式案内。

> "Transposing by a number is equivalent to creating a `ChromaticInterval` object. ChromaticIntervals are designed *not* to care about enharmonics."
> — music21 公式FAQ（WebFetchで本文確認）
> https://music21.org/music21docs/about/faq.html

### 1.2 music21: “absurd” な調号は重臨時記号を生み MusicXML で表示不能に
User Guide は `KeySignature(12)` の例で `F` が double-sharp になること、こうした調号は LilyPond では出せても **多くの MusicXML リーダで表示されない**と説明。移調で極端な調号に飛ばすと往復で壊れる典型。
> https://music21.org/music21docs/usersGuide/usersGuide_15_key.html

### 1.3 music21: 自動 respell は万能でなく重みが固定
`EnharmonicSimplifier` は「最良の綴り」を返すが、**基準と重みが現状固定**（将来ユーザー選択可能にしたい旨）。ジャンル・調性感に応じた正解を保証しない。
> https://music21.org/music21docs/moduleReference/moduleAnalysisEnharmonics.html

### 1.4 MuseScore: concert pitch と written pitch の混同で移調楽器の調号がズレる
Handbook は「**調号は concert pitch に対して定義される**」と明記。移調楽器譜へ調号を入れる際は concert pitch 側の調号を入れねばならず、ここを誤ると B♭/E♭ 楽器のパート調号が期待と逆になる。
> https://musescore.org/en/handbook/3/key-signatures

### 1.5 MuseScore: 移調楽器の enharmonic key が期待通りにならない実ユーザー報告
E major の B♭クラリネットを `Gb Major` 表記にしたいが MuseScore 3.5 では F# に戻る、という 2020 年の報告。回答は Staff/Part Properties の "Prefer sharps or flats for transposed key signatures" 案内。**設定はあるが自動では意図通りにならない**ことを示す事例。
> https://musescore.org/en/comment/1026667

### 1.6 Dorico: 少ない臨時記号の enharmonic key を「勝手に」選ぶ（仕様）
Help は C#major と Dbmajor のような enharmonic key で、**臨時記号が少ないキーを選ぶ場合がある**と明記。通常は可読性向上だが、C# を意図した場面では「勝手に Db になった」と見える。
> https://www.steinberg.help/r/dorico-se/6.1/en/dorico/topics/notation_reference/notation_reference_key_signatures/notation_reference_key_signatures_enharmonic_c.html

### 1.7 Dorico: double accidental 入力を無効化できないケース
Steinberg forum で「Dbmajor で A natural を入れると B double-flat になり読みにくい」との報告。開発者 Daniel Spreadbury が「デフォルトでは double accidental 入力を無効化できない。入力後に perfect unison transpose ＋ 'Respell to avoid double and triple sharps and flats' を使え」と回答。
> https://forums.steinberg.net/t/avoid-double-accidentals/160762

### 1.8 Dorico/一般: MIDI import は綴り情報を失う（採譜で致命的）
Forum では MIDI import 後に double sharps / B# / D# が大量発生した報告。回答は「**MIDI は note number であって flats/sharps ではない**。XML export を試すべき」。**自動採譜・MIDI変換の出力を移調すると accidental 事故が増幅される**という、本プロジェクトに直結する論点。
> https://forums.steinberg.net/t/problem-with-dorico-displaying-different-accidentals-between-parts-and-full-score/702366

---

## 2. 臨時記号の散乱（accidental spam）と TAB 音域外の失敗

### 2.1 accidental spam が増える条件
Dorico Help によれば horn/trumpet/percussion 等で **no key signature** を使うと調号を出さず必要な臨時記号で表示する（慣習上は正しい）。だが移調後は**臨時記号が散在**しやすい。MIDI由来・無調号パート・移調楽器で顕著。
> https://www.steinberg.help/r/dorico-se/6.1/en/dorico/topics/notation_reference/notation_reference_key_signatures/notation_reference_key_signatures_enharmonic_c.html

### 2.2 MuseScore: Diatonic Transpose は調号を変えず「旋法内移動」になる
Handbook は Diatonic Transpose が **existing key signatures を変えず音程関係が変化**すると注意。「移調」のつもりが「旋法内移動」になり、臨時記号・音程が期待と違う失敗。
> https://musescore.org/en/handbook/4/transposition （Handbook Transposition 章）

### 2.3 MuseScore: respell は手動/一括はあるが完全自動でない
`J` で異名同音を循環、Tools → Respell Pitches で一括 respell 可能。裏返せば **移調後に E#/Fb/B#/double accidental を人間が検査する工程が必須**。
> https://musescore.org/en/handbook/4/transposition

### 2.4 TAB: 移調で弦・ポジションが保持されない（Dorico, works as designed）★検証済み
ギター練習フレーズを半音移調すると **TAB の弦指定が保持されず別弦に割り当てられる**。モデレータが "works as designed"、"Dorico is not yet smart enough to work with fixed positions on the neck" と回答。Guitar Pro はショートカット一発で解決できる旨の対比あり。
> https://forums.steinberg.net/t/tablature-transposition-issue/776147

### 2.5 TAB: フレット上限・弦設定で移調後に playable でなくなる
MuseScore Handbook は TAB の "Number of frets" が入力可能な最大フレットを定義すると説明。**上方移調で高フレットに押し出され、下方移調で開放弦未満になる** → 再配置・チューニング変更・capo 指定が必要。
> https://musescore.org/en/handbook/2/tablature

### 2.6 MuseScore: 楽器レンジ外は「色付け」だけで export に反映されない
Handbook は usable pitch range 外の音を**画面上で色付けするだけ**で、印刷/export には影響しないと明記。**移調で range 外になっても生成パイプラインでは見逃されうる**。→ 自動チェックの必要性。
> https://handbook.musescore.org/notation/instruments-staves-and-systems/staff-part-properties

### 2.7 カポ/リンクTAB: 再生だけ移調し譜面は変えない → 二重移調のリスク
MuseScore の capo 機能は capo marking により **playback だけ希望ピッチへ移調し、notes/fretmarks は変えない**（意図的仕様）。譜面移調と混ぜると二重移調事故。
> https://handbook.musescore.org/idiomatic-notation/guitar/applying-capos

---

## 3. 移調再生（pitch-shift）の音質劣化の失敗

譜面移調と違い、**再生移調は音質劣化が原理的に避けられない**。

### 3.1 Audacity: pitch 変更は time-stretch であり極端設定で歪む
Change Pitch は tempo を変えず pitch を変えるが、**time-stretching effect ゆえ極端な設定ほど audible distortions が予想される**と明記。高品質モード（SBSMS, "Use high quality stretching"）でも percussive で有利な場合があるだけで万能でない。
> https://manual.audacityteam.org/man/change_pitch.html

### 3.2 librosa: phase vocoder は transient を扱わず可聴 artifact を出す ★検証済み
公式 docs が明言。

> "This is a simplified implementation, intended primarily for reference and pedagogical purposes. It makes no attempt to handle transients, and is likely to produce many audible artifacts."
> — librosa `phase_vocoder`（WebFetchで本文確認。高品質には RubberBand 推奨とも）
> https://librosa.org/doc/main/generated/librosa.phase_vocoder.html

### 3.3 代表 artifact: transient smearing / phasiness（STN分解研究）
Polak & Erkut 2025 は pitch-shifting で入力を harmonic / transient / noise に分解し成分別処理する手法を提案。背景の common artifacts として **transient smearing と phasiness** を挙げる。評価では blind listening test ＋ interview で **state-of-the-art 商用ソリューションとの音質差が残る**と要約。
> https://vbn.aau.dk/en/publications/low-latency-pitch-shifting-with-stn-decomposition/

### 3.4 formant 問題: 声・管・歌入り音源で不自然化
Lenarczyk 2017 は phase vocoder に spectral whitening ＋ envelope reconstruction を組合せ **formant structure preservation** を扱う。裏返せば通常の pitch shift では **formant がずれ声質が変わる**問題がある。
> https://www.isca-archive.org/interspeech_2017/lenarczyk17_interspeech.html

---

## 4. ベストプラクティス（本プロジェクトへの示唆）

- **半音数だけで移調しない。** music21 なら `transpose(2)` より `"M2"` 等の diatonic interval を優先。MIDI note number から譜面化する場合は調号・旋法・和声・声部情報を別途与える（§1.1, 1.8）。
- **移調後に必ず respell pass を入れる。** double-sharp/flat・E#/Fb/B#/Cb・コード記号・パート表示・concert/written pitch の両方を検査（§1.7, 2.3）。
- **調号選択は「少ない臨時記号」だけで決めない。** C# vs Db、F# vs Gb は楽器・奏者・既存譜面・コード表記との一貫性で選ぶ（§1.5, 1.6）。
- **移調楽器は concert pitch 基準を明文化する。** 入力/内部表現/表示/パート譜/再生音高のどれが基準かを固定（§1.4）。
- **TAB は音高移調後に string/fret/playable range を再最適化する。** 既存 fingering を保持したい場合、音高変換と運指変換を別工程に分ける（§2.4, 2.5）。
- **range 外は「自動失敗」として検出する。** 色付けだけでは export で見逃す。最高音・最低音・TAB フレット上限・開放弦未満をチェック項目化（§2.6）。
- **再生移調と譜面移調を状態として分離する。** capo playback / pitch-shift playback / score transpose のどれを使ったかを保持し二重移調を防ぐ（§2.7）。
- **音源 pitch shift は小幅に留める。** 採譜確認用途でも ±1〜2 semitone で artifact を検証。歌・打楽器・ピアノ・歪みギターは transient/formant 劣化を前提に（§3.2〜3.4）。

---

## 5. 出典一覧（★＝WebFetchで本文確認済み）

- ★ music21 FAQ（整数移調と異名同音）: https://music21.org/music21docs/about/faq.html
- music21 KeySignature guide: https://music21.org/music21docs/usersGuide/usersGuide_15_key.html
- music21 EnharmonicSimplifier: https://music21.org/music21docs/moduleReference/moduleAnalysisEnharmonics.html
- MuseScore key signatures (concert pitch): https://musescore.org/en/handbook/3/key-signatures
- MuseScore 移調楽器 enharmonic key 事例: https://musescore.org/en/comment/1026667
- MuseScore Handbook Transposition 章: https://musescore.org/en/handbook/4/transposition
- MuseScore 2 Tablature (frets 上限): https://musescore.org/en/handbook/2/tablature
- MuseScore Studio Staff/Part properties (range 色付け): https://handbook.musescore.org/notation/instruments-staves-and-systems/staff-part-properties
- MuseScore applying capos (再生のみ移調): https://handbook.musescore.org/idiomatic-notation/guitar/applying-capos
- Dorico enharmonic key signatures: https://www.steinberg.help/r/dorico-se/6.1/en/dorico/topics/notation_reference/notation_reference_key_signatures/notation_reference_key_signatures_enharmonic_c.html
- Dorico transposing instruments (concert pitch内部保存): https://www.steinberg.help/r/dorico-pro/6.1/en/dorico/topics/setup_mode/setup_mode_instruments_transposing_c.html
- ★ Dorico forum, tablature transposition (弦保持されず): https://forums.steinberg.net/t/tablature-transposition-issue/776147
- Steinberg forum, double accidentals: https://forums.steinberg.net/t/avoid-double-accidentals/160762
- Steinberg forum, MIDI import と accidental: https://forums.steinberg.net/t/problem-with-dorico-displaying-different-accidentals-between-parts-and-full-score/702366
- Audacity Change Pitch (歪み注意): https://manual.audacityteam.org/man/change_pitch.html
- ★ librosa phase_vocoder (transient未対応・artifact): https://librosa.org/doc/main/generated/librosa.phase_vocoder.html
- Polak & Erkut 2025, STN分解 pitch-shifting: https://vbn.aau.dk/en/publications/low-latency-pitch-shifting-with-stn-decomposition/
- Lenarczyk 2017, formant保存 phase vocoder: https://www.isca-archive.org/interspeech_2017/lenarczyk17_interspeech.html

### 未確認（要注意）
- 中国語版 MuseScore フォーラム（移調オプションの中国語解説）: bot 403 で本文未確認。中国語圏は「転調/移調」概念語は多いが**機能トラブルの実務ログは薄く FOSS/公式Help側に情報が偏在**する、という調査バイアスを付記する。
