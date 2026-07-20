# 歌声合成向け単旋律 MIDI/UST/USTx エクスポート 調査レポート（codex=論文・WEB担当、失敗例重視）

調査日: 2026-07-21
対象: monophonic MIDI / UST / USTx export for singing voice synthesis（SynthV / UTAU / VOCALOID）— ノート分割・ブレス・連続ピッチカーブ
分担: codex担当（論文＋WEB、失敗例を最大限）
方針: 実在ソースのみ・URL併記・憶測なし。英語・中国語中心。SOME/GAME/ROSVOT等のリポジトリと arXiv、フォーマット公式仕様を優先。

> 注1: 本文中の openvpi/SOME・openvpi/GAME・ROSVOT(arXiv:2405.09940)・DiffSinger(arXiv:2105.02446)は別途 WebSearch で実在確認済み。
> 注2: 一部の非公式ミラー（github-wiki-see.page 経由の OpenUtau Wiki など）は原本が GitHub Wiki 側にあり、URL 表記はミラー経由になっている箇所がある。一次情報は openutau/OpenUtau Wiki 本体を参照のこと。

---

## 要約

歌唱音声を「歌声合成エディタで再利用できるノート列」に変換する最大のリスクは、F0抽出そのものよりも、**連続的な歌唱表現を離散ノートへ切る段階**にある。特に、ビブラート、しゃくり、ポルタメント、メリスマ、無声子音、ブレスは、単純な「MIDIノート化」と相性が悪い。

結論として、実装は次の方針が堅い。

| 領域 | 推奨 |
|---|---|
| ノート列 | 量子化済みノートと未量子化タイミングを両方保持 |
| ピッチ | ノート本体と連続ピッチカーブを分離して保持 |
| ブレス | 音高付きノートにしない。`AP` / `SP` / 休符 / aspiration系として扱う |
| UST/USTx | UTAU固有の音源タイミングを勝手に推定しない |
| SynthV | MIDIだけでなく、将来的にはSVP相当の内部表現も検討 |
| 検証 | 自動変換後に「過分割」「しゃくり誤分割」「ブレス誤ノート化」を可視化してユーザー確認させる |

---

## 1. 形式仕様と保持できる情報

| 形式 | 実体 | 代表情報 | ピッチ表現 | 主な落とし穴 |
|---|---|---|---|---|
| MIDI / SMF | 標準MIDIファイル | Note On/Off、テンポ、拍子、Pitch Bend | 14-bit Pitch Bend。MIDI Association仕様ではPitch Bend Changeは14-bit値で中心は`0x2000` [MIDI 1.0 Summary](https://midi.org/summary-of-midi-1-0-messages) | 歌詞、音素、ブレス、歌唱パラメータは標準的に弱い。Pitch Bend Sensitivity不一致で音程が壊れる |
| UST | UTAU Sequence Text | `Length`, `Lyric`, `NoteNum`, `PreUtterance`, `VoiceOverlap`, `PBS/PBW/PBY/PBM`, `VBR`など [pyutau](https://pypi.org/project/pyutau/1.1.0/) | UTAU Mode1/Mode2のピッチベンド | 文字コード、音源別OTO、CV/VCV/CVVC/Arpasing差分を外部から判断しにくい |
| USTx | OpenUtau YAML | `notes`, `tone`, `duration`, `lyric`, `pitch`, `vibrato`, `curves`。480 ticks/quarter固定 [USTX file format (Wiki mirror)](https://github-wiki-see.page/m/openutau/OpenUtau/wiki/USTX-file-format) | ノート内pitch control points、curve expression | YAML 1.2、曲線座標、phonemizer依存。PyYAMLではなく`ruamel.yaml`推奨と明記 |
| SVP / SynthV | Synthesizer V project | `.svp`保存、ノート、トラック、テンポ等 [SynthV project manual](https://sv1.docs.dreamtonics.com/en/synthv/basic-usage/project) | Pitch Deviation、AI/Manual pitch、computed pitch API [SV scripting](https://resource.dreamtonics.com/scripting/SV.html) | Sing/Rap modeでは文脈変更でAIピッチが再生成され、手書きPitch Deviationと二重化しやすい [Pitch Curves Basics](https://sv1.docs.dreamtonics.com/en/synthv/advanced-usage/pitch-basic) |
| VSQX / VPR | VOCALOID系 | VSQXはVOCALOID3/4、VPRはVOCALOID5+。VOCALOID6互換表あり [VOCALOID compatibility](https://www.vocaloid.com/en/learn/ln6105/) | PIT/PBS/DYN等 | MIDI経由ではVOCALOID固有表現が落ちる。VOCALOID6でも互換データと非互換データが分かれる |

補足: UtaFormatix は VSQX/VPR/VSQ/MID/UST/USTX/SVP/S5P/DV 等を扱う変換ツールで、公式サイトにも対応形式が列挙されている [UtaFormatix](https://utaformatix.tk/)。ただし、変換で全パラメータが残るわけではない。LibreSVIP の形式一覧でも、`svp`はJSON、`ustx`はYAML、`vsqx`はXML、`vpr`はJSON+zip圧縮、`vsq`はMIDI+INI系と整理されている [LibreSVIP project formats](https://soulmelody.github.io/LibreSVIP/project_formats/)。

---

## 2. ノート化の失敗パターン

### 2.1 F0抽出からノート列への基本リスク

歌唱音声転写では、F0を取るだけでは不十分で、オンセット・オフセット・音高ラベルを決める必要がある。Tony/pYIN系も「モノフォニック音声からpitch trackとnoteを抽出し、ユーザーが修正する」前提のツールである [Tony wiki](https://code.soundsoftware.ac.uk/projects/tony/wiki/Wiki/46)。pYIN自体はYINを確率化したF0推定器 [pYIN paper DOI](https://doi.org/10.1109/ICASSP.2014.6853678)。

| 失敗 | 原因 | 出力上の症状 |
|---|---|---|
| オクターブ誤り | 倍音・声区・裏声・伴奏漏れ | UST/MIDIで突然1オクターブ跳ぶ |
| 無声区間のノート化 | 子音、ブレス、摩擦音をF0ありと誤判定 | `R`にすべき箇所が短い音符になる |
| 過分割 | ビブラートや細かい揺れを音高変化と解釈 | 同一ロングトーンが多数の短音符になる |
| 過結合 | レガート、弱いオンセット、滑らかな母音遷移 | メリスマや連続音が1音に潰れる |
| テンポずれ | BPM推定・拍位置推定・量子化の誤差 | SynthV/UTAU上で伴奏と合わない |
| ピッチ代表値の偏り | しゃくり、フォール、ポルタメントが平均値を引っ張る | NoteNumが半音ずれる |

古典的にも、歌唱のノート分割エラーは支配的な問題として報告されている。McNab & Smithのメロディ転写では、誤りのほぼ全てがノート分割由来とされる [Melody transcription for interactive applications](https://hdl.handle.net/10289/1194)。

---

## 3. メリスマ / ビブラート / しゃくりの失敗

ROSVOTは、歌唱AST（Automatic Singing voice Transcription）を「ノート境界予測 + ピッチ予測」として扱い、実用上は精度、単語・ノート同期、ノイズ耐性が課題だと述べている [ROSVOT arXiv](https://arxiv.org/abs/2405.09940), [ACL Anthology](https://aclanthology.org/2024.acl-long.526/), [GitHub](https://github.com/RickyL-2000/ROSVOT)。特にメリスマでは、**単語境界はノート境界を含意するが、ノート境界は必ずしも単語境界ではない**という非対称性が重要。ROSVOTはこの非対称性に対処するため word boundary を分割のガイドに使う。

| 表現 | ありがちな誤処理 | なぜ危険か | 推奨 |
|---|---|---|---|
| メリスマ | 1音節1ノートに強制 | 同じ母音で複数音高がある箇所が潰れる | slur/continuationを持つ。DiffSinger系の`note_slur`やOpenCPOPのslur指標に近い考え方 |
| ビブラート | 各周期を別ノート化 | ロングトーンが半音上下の連打になる | F0を低周波の骨格と高周波の揺れに分離 |
| しゃくり | 低い開始音を独立ノート化 | 実際は到達音への装飾なのに楽譜上の別音になる | 短すぎる前置音はpitch curve側へ回す |
| ポルタメント | クロマチック階段に分割 | MIDIとしては読めるがSynthV/UTAUで不自然 | ノートは目標音、滑りはPitch Bend/USTx pitch curveへ |
| アポジャトゥーラ | 装飾音を主音と同格にする | 歌詞割りが破綻 | 閾値以下の装飾候補にconfidenceを付け、UIで確認 |
| ソフトオンセット | 開始が遅れる | 子音開始と母音F0開始がずれる | 音素境界とF0オンセットを分ける |

Vibratoの検出・抽出は、Rossignolらが「F0軌跡からビブラートを抜いたflatな旋律がノート分割に有用」と述べている [DAFx vibrato paper](https://www.dafx.de/paper-archive/details/N2Kpz2NdMSLXkSnquj5qQw)。つまり、ビブラートをそのままノート境界検出へ入れるのは危険。

---

## 4. ピッチカーブとブレス表現の落とし穴

SynthVでは最終ピッチは「ノート本来のピッチカーブ + Pitch Deviation」と説明され、Sing/Rap modeではノートや歌詞編集でAIピッチが再生成される [Pitch Curves Basics](https://sv1.docs.dreamtonics.com/en/synthv/advanced-usage/pitch-basic)。またPitch Deviationは±1200 cents、Breathinessは-2〜+2等の範囲を持つ [Parameter Panel](https://sv1.docs.dreamtonics.com/en/synthv/advanced-usage/parameters)。

| 領域 | 失敗 | 実装上の対策 |
|---|---|---|
| MIDI Pitch Bend | bend rangeを明示せず、受け側のPBSに依存 | RPN 0でPitch Bend Sensitivityを設定し、書き出し時にメタ情報にも記録 |
| MPE | 単旋律なのにMPE前提にする | 基本は通常Pitch Bendで十分。重なりノートや独立表現が必要な場合のみMPE。MPEはノートごと表現を複数チャンネルで扱う仕様 [MPE announcement](https://midi.org/the-midi-association-announces-the-v1-1-update-to-the-midi-polyphonic-expression-mpe-specification) |
| Pitch curve二重適用 | SynthV AI pitch + 変換pitchが同時に効く | SynthVではManual Mode相当、またはPitch Deviationの意味を明示 |
| 過密カーブ | 10msごとの生F0をそのまま書く | カーブ点を間引き、知覚差分ベースで簡略化 |
| ビブラート消失 | 形式変換でvibratoが落ちる | USTx/SVPはvibratoを保持しやすいが、MIDI単体ではPitch Bendへ焼き込みが必要 |
| ブレス誤音高化 | breath/noiseに仮のNoteNumを付ける | `R`, `AP`, `SP`, aspiration/voicing系へ分離 |
| Breathiness乱用 | ブレス音の代わりに全区間Breathinessを上げる | ブレスイベントと声質パラメータを分ける |

SynthVのレンダリングでは、非周期成分、無声子音、ノイズ等を aspiration と呼び、Pro版ではaspiration componentを分離出力できる [Rendering and Export](https://sv1.docs.dreamtonics.com/en/synthv/basic-usage/render)。これは「ブレスは音高ノートではなく、周期成分と別の表現」という設計上の示唆になる。

---

## 5. DiffSinger / SOME / GAME / OpenCPOP / ROSVOT から得られる実務上の示唆

| ソース | 関係する知見 |
|---|---|
| DiffSinger | 楽譜条件付きSVSで、music score / MIDI的入力の重要性が高い [DiffSinger arXiv](https://arxiv.org/abs/2105.02446), [GitHub](https://github.com/MoonInTheRiver/DiffSinger) |
| SOME | Singing-Oriented MIDI Extractor。歌唱音声からMIDI列を抽出し、**非整数（浮動小数）MIDI値**を出せるためDiffSinger variance labeling向けと説明されている。beta版で後方互換は保証しないと明記 [SOME](https://github.com/openvpi/SOME) |
| GAME | Generative Adaptive MIDI Extractor（SOME後継）。境界しきい値、ノート存在しきい値、word boundary alignment、`note_seq`, `note_dur`, `note_slur`を扱う [GAME](https://github.com/openvpi/GAME) |
| OpenCPOP | 中国語SVSコーパス。note, duration, phoneme, slur, AP/SPなどを含む注釈体系 [OpenCPOP](https://xinshengwang.github.io/opencpop/), [arXiv](https://arxiv.org/abs/2201.07429) |
| ROSVOT | ASTをSVSデータ注釈へ使う際、精度不足、単語ノート非同期、ノイズ脆弱性を明示 [ROSVOT](https://arxiv.org/abs/2405.09940) |

重要なのは、SOME/GAME系は「MIDI抽出」ツールであっても、実務上は単なるSMF生成ではなく、**浮動小数ピッチ、境界、slur、word alignment、v/uv**を扱う方向に進んでいる点である。アプリ側も、MIDIだけを最終成果物にせず、中間表現を保持すべき。

---

## 6. ベストプラクティス

### 6.1 中間表現

内部では次を分ける。

| レイヤ | 内容 |
|---|---|
| frame-level | time, f0, confidence, voiced/unvoiced, energy |
| event-level | onset, offset, pitch_median, pitch_mode, lyric/syllable, breath/rest |
| expression-level | vibrato, scoop, fall, portamento, breath, dynamics |
| export-level | MIDI/UST/USTxごとの変換済み表現 |

### 6.2 ノート分割ルール

| ルール | 理由 |
|---|---|
| ビブラート帯域を境界検出から弱める | vibrato周期の過分割を防ぐ |
| しゃくりは短時間・目標音到達型ならpitch curveへ | 装飾をノート化しすぎない |
| メリスマは同一歌詞の複数ノートを許す | 歌唱合成では一般的 |
| ブレス・無声子音はF0ノートにしない | UTAU/SynthVで破綻しやすい |
| confidenceを出す | 自動変換の不確実性をUIで見せられる |
| 量子化前後を保持 | 楽譜用途と原演奏再現用途の両立 |

### 6.3 書き出し方針

| 出力 | 方針 |
|---|---|
| MIDI | 1トラック、tempo map、note events、必要ならPitch Bend。bend rangeを明示 |
| UST | `R`休符、`Lyric`, `NoteNum`, `Length`を基本。Mode2 pitchは簡略化後に出す |
| USTx | `notes.pitch`, `vibrato`, `curves`を優先。OpenUtauの480 TPQに合わせる |
| SynthV向け | MIDIだけだとPitch/lyrics/phonemeが落ちやすい。SVPまたはUtaFormatix経由も検討 |
| VOCALOID向け | MIDIは最低限。VSQX/VPR変換が必要ならUtaFormatix/LibreSVIP相当の中間表現が必要 |

---

## 7. 実装チェックリスト

| チェック | 合格条件 |
|---|---|
| ビブラート過分割 | ロングトーン1個が短音符列にならない |
| しゃくり | 目標音前の短い滑りが独立ノート化されすぎない |
| メリスマ | 1音節複数ノートを保持できる |
| ブレス | breathがNoteNum付きノートにならない |
| Pitch Bend | bend range不一致で半音/全音が崩れない |
| UST文字コード | Shift-JIS/UTF-8差分で壊れない。UTAU-SynthはUST 2.0 UTF-8/Shift-JIS等を扱う [UTAU-Synth help](https://utau-synth.com/ushelp/guide18.html) |
| OpenUtau | `.ustx`, `.ust`, `.vsqx`, `.mid`, `.ufdata`, `.musicxml`読み込みを想定 [OpenUtau Getting Started (Wiki mirror)](https://github-wiki-see.page/m/openutau/OpenUtau/wiki/Getting-Started) |
| 変換損失 | UtaFormatix等で保持されないパラメータをユーザーに表示 |

---

## 最終提言

この機能は「MIDIエクスポート」ではなく、**歌唱表現をノート列・連続ピッチ・無声/ブレス・歌詞同期へ分解する変換器**として設計すべき。最も危険な失敗は、ビブラートやしゃくりをノートに切り刻むこと、ブレスを音高ノートにすること、SynthV/VOCALOID/UTAU間でピッチカーブの意味が違うのに同じものとして扱うこと。
実装上は、まずUSTxを高忠実度ターゲット、MIDIを互換ターゲット、USTをUTAU互換ターゲットとして扱うのが現実的。

---

## 参照URL一覧（実在確認・主要ソース）

- MIDI 1.0 Summary: https://midi.org/summary-of-midi-1-0-messages
- MPE v1.1 announcement: https://midi.org/the-midi-association-announces-the-v1-1-update-to-the-midi-polyphonic-expression-mpe-specification
- pyutau (UST fields): https://pypi.org/project/pyutau/1.1.0/
- OpenUtau USTX file format (Wiki mirror): https://github-wiki-see.page/m/openutau/OpenUtau/wiki/USTX-file-format
- OpenUtau Getting Started (Wiki mirror): https://github-wiki-see.page/m/openutau/OpenUtau/wiki/Getting-Started
- SynthV project manual: https://sv1.docs.dreamtonics.com/en/synthv/basic-usage/project
- SynthV Pitch Curves Basics: https://sv1.docs.dreamtonics.com/en/synthv/advanced-usage/pitch-basic
- SynthV Parameter Panel: https://sv1.docs.dreamtonics.com/en/synthv/advanced-usage/parameters
- SynthV Rendering and Export: https://sv1.docs.dreamtonics.com/en/synthv/basic-usage/render
- SynthV scripting API: https://resource.dreamtonics.com/scripting/SV.html
- VOCALOID compatibility: https://www.vocaloid.com/en/learn/ln6105/
- UtaFormatix: https://utaformatix.tk/
- LibreSVIP project formats: https://soulmelody.github.io/LibreSVIP/project_formats/
- Tony wiki: https://code.soundsoftware.ac.uk/projects/tony/wiki/Wiki/46
- pYIN paper (DOI): https://doi.org/10.1109/ICASSP.2014.6853678
- McNab & Smith, Melody transcription: https://hdl.handle.net/10289/1194
- ROSVOT arXiv 2405.09940: https://arxiv.org/abs/2405.09940
- ROSVOT ACL Anthology: https://aclanthology.org/2024.acl-long.526/
- ROSVOT GitHub: https://github.com/RickyL-2000/ROSVOT
- DAFx vibrato paper: https://www.dafx.de/paper-archive/details/N2Kpz2NdMSLXkSnquj5qQw
- DiffSinger arXiv 2105.02446: https://arxiv.org/abs/2105.02446
- DiffSinger GitHub: https://github.com/MoonInTheRiver/DiffSinger
- SOME (Singing-Oriented MIDI Extractor): https://github.com/openvpi/SOME
- GAME (Generative Adaptive MIDI Extractor): https://github.com/openvpi/GAME
- OpenCPOP: https://xinshengwang.github.io/opencpop/  /  arXiv: https://arxiv.org/abs/2201.07429
- UTAU-Synth help: https://utau-synth.com/ushelp/guide18.html
