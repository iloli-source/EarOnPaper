# F-097 SoundFont audition（採譜結果を任意SF2音色で試聴）— 論文＋WEB調査

> 手法: mcp__codex__codex（web検索, read-only, cwd=採譜）+ WebSearch/WebFetch 補完。
> 方針: 英語・中国語中心 / 実在URLのみ / 捏造禁止 / 失敗例最大化。
> 調査日: 2026-07-21

---

## 0. 要点（TL;DR）

FluidSynth + SF2 での試聴機能は技術的には成立するが、危険は「音が出ない」ではなく**「間違った音色で試聴される」正しさの問題**にある。任意SF2はGMバンクのように振る舞わない前提で扱い、bank/program の解決を明示化しないと、試聴音色がサイレントに入れ替わる。SF2は「信頼できるGM音源パック」ではなく**ユーザーデータ**として扱うべき。

---

## 1. 学術・研究ソース（AMT→FluidSynth/SF2レンダリング）

採譜（AMT）研究では transcription 出力を MIDI/piano-roll 化し FluidSynth + SF2 でレンダリング/試聴するのが定番。失敗と直結する記述に注目。

- **MT3 (Multi-Task Multitrack Music Transcription)** — 出力をMIDI化しFluidSynthでレンダリング。補足資料に「楽器ラベルを持たないベースラインはすべてピアノでレンダリングされる」との記述があり、**「試聴の音色が誤る（全部ピアノ化）」問題**に直結。
  https://storage.googleapis.com/mt3/index.html
- **Omnizart (JOSS 2021)** — AMTツールボックス。`omnizart synth example.mid` で採譜MIDIをデフォルトSoundFontでレンダリング。試聴ワークフローの実装参照。
  https://joss.theoj.org/papers/10.21105/joss.03391
  https://music-and-culture-technology-lab.github.io/omnizart-doc/quick-start.html
- **Neural Music Synthesis for Flexible Timbre Control (ICASSP/arXiv)** — 学習音声をFluidSynth + MuseScoreデフォルトSoundFontでMIDIから合成。楽器/音色embeddingとSoundFontサンプルを探索。
  https://neural-music-synthesis.github.io/
- **Arranger (ISMIR 2021)** — automatic instrumentation サンプルを FluidSynth + MuseScore General SoundFont で合成。
  https://hermandong.com/arranger/
- **Downbeat Tracking with Tempo-Invariant CNNs** — 合成データセットをFluidSynthでレンダリングし、**テスト時に別SoundFontを使用**。SoundFont/音色の汎化テストの根拠。
  https://axi.lims.ac.uk/paper/2102.02282
- **Transfer of Knowledge among Instruments in AMT** — MAPS/GuitarSet派生データを FluidSynth + FluidR3_GM で合成。合成音は「クリーン過ぎて実世界のノイズと乖離」と指摘。
  https://www.researchgate.net/publication/370442723_Transfer_of_knowledge_among_instruments_in_automatic_music_transcription

---

## 2. 失敗例（最重要・優先実装対象）

### 2-1. SF2ロード失敗 / 破損SF2の拒否
- FluidSynthは出力前にSoundFontロードが必須。構造的に不正なSF2は拒否される。
  https://www.fluidsynth.org/api/LoadingSoundfonts.html

### 2-2. SoundFontスタック衝突（サイレントな音色すり替え）★最重要
- 複数SF2が同一bank/programを含む場合、**最後にロードされたSoundFontが勝つ**。明示的な `program_select` / bank offset を使わないと、試聴音色が黙って入れ替わる。
  https://www.fluidsynth.org/api/LoadingSoundfonts.html
- スタック時の誤結果の実例:
  https://github.com/FluidSynth/fluidsynth/discussions/1492

### 2-3. bank > 0 のプリセット探索失敗（間違った楽器 / 無警告ドラム誤り）★
- MIDIプレイヤーがbank 1のプリセットを**存在するのに見つけられず**、bank 0にフォールバックして誤楽器を鳴らす。**同じMIDIでも再生ごとに欠落数が変わるレース/タイミング問題**。ch10パーカッションは**無警告でbank 0にフォールバック**。
  https://github.com/FluidSynth/fluidsynth/issues/1475

### 2-4. 任意SF2の複数バンク/bank offset欠如
- bank offset運用が苦痛だったためCLIフラグが追加された経緯（issue #1538）。offsetなしではカスタムfontとGMバンクが上書きし合う。
  https://github.com/FluidSynth/fluidsynth/issues/1538

### 2-5. XG/GS/GMモードでのパッチ誤選択
- XG bank MSB が無視され、期待パッチではなく "Concert Grand" 等が鳴る（issue #1378）。
  https://github.com/FluidSynth/fluidsynth/issues/1378
- GM/GS/XG reset後に bank select が inactive のままになり誤音（issue #1323）。
  https://github.com/FluidSynth/fluidsynth/issues/1323
- MIDI冒頭の GM SYSTEM ON (SysEx) が bank-select モードをGMへ上書きし、以降のCC0/CC32(bank select)が無視される。

### 2-6. ドラムチャンネル不整合
- GMではch10がパーカッション。そこでのprogram changeは通常無視されるため、任意SF2試聴を「ピッチ楽器」と同様に扱うと**無音や誤ドラム**になる。SF2 2.01/2.04では欠落ノートは無音になる（旧仕様のbank0代替が効かない）。
  https://jfearn.fedorapeople.org/fdocs/en-US/Fedora_Draft_Documentation/0.1/html/Musicians_Guide/chap-Musicians_Guide-FluidSynth.html

### 2-7. アーティキュレーション/表現の非保存
- FluidSynthはMIDIアーティキュレーションが underspecified と警告。ADSR/filter/vibratoはSoundFontのmodulator依存で、「同じ音符＋別SF2」で表現が保存されない。
  https://www.fluidsynth.org/wiki/FluidFeatures/
- SoundFont仕様のグレーゾーン（linked modulator / sample-loop の未規定）。任意SF2がこれを露出させる。
  https://www.fluidsynth.org/wiki/SoundFont/

### 2-8. レイテンシ / チューニング失敗
- レイテンシは sample rate・buffer数・period sizeに依存。**ドライバのサンプルレート不一致で音程がずれる（out of tune）**。
  https://www.fluidsynth.org/wiki/LowLatency/
- ALSA `dmix` は高レイテンシ。Windows低レイテンシは PortAudio/WDM-KS が必要。ハードにより plughw / 別サンプルレートが必要。
  https://www.fluidsynth.org/wiki/LowLatency/

### 2-9. パッケージング / デフォルトSF2欠如
- コンパイル時のデフォルトSF2パスが存在せず「デフォルトで音が出ない」（Debian bug）。
  https://bugs-devel.debian.org/cgi-bin/bugreport.cgi?bug=929182
- インストール時に default.sf2 を配置する要望（issue #1005）。
  https://github.com/FluidSynth/fluidsynth/issues/1005

### 2-10. PipeWire/PulseAudio 由来の歪み・遅延
- FluidSynth/PipeWire で激しいcrackling・再生が時間より遅れる（Debian bug #1105956）。
  https://bugs-devel.debian.org/cgi-bin/bugreport.cgi?bug=1105956

---

## 3. 中国語ソース（運用・失敗・最適化）

- **ArchWiki CN（FluidSynth）** — PulseAudio競合、最初のMIDIデバイス誤指定でMIDI無音、stuck notes、PipeWire broken pipe、歪み/crackleはバッファ拡大で緩和、等の運用失敗集。
  https://wiki.archlinux.org.cn/title/FluidSynth
- **火山引擎: ブラウザで自作Soundfont(.sf2)をロードし楽器発声** — Web(WebAudio/WASM)での.sf2ロードと発声呼び出し。
  https://www.volcengine.com/article/1196540
- **火山引擎: AudioKitベースアプリが一部主流SoundFontを処理できない原因** — 実装依存でSF2解釈が割れる典型失敗。
  https://www.volcengine.com/article/364192
- **CSDN: FluidSynth SoundFont音源資料収集（規範/ダウンロード/エディタ）** — 三角钢琴プリセット番号0だがbank番号が128(GM)で0でない等、**シンセごとのSF2番号解釈差**を指摘。
  https://blog.csdn.net/shulianghan/article/details/120863626
- **CSDN: 8つの無料SoundFontサイト** — Timbres of Heaven 等、GM 128音色の品質差の実務メモ。
  https://blog.csdn.net/weixin_30898555/article/details/161760752
- **w3cschool: FluidSynth 2.2.X 命令行/API/範例（中文）** — 実装参照。
  https://m.w3cschool.cn/fluidsynth/fluidsynth-rw6y3lzj.html

---

## 4. 実装ガイダンス（採譜プロジェクト向け）

1. **SF2はユーザーデータとして扱う**（信頼GM音源前提を捨てる）。ロード後にプリセットを列挙し、`(soundfont_id, bank, program, channel, drum_flag, bank-select mode)` を**明示保存**。
2. 欠落プリセットは**警告**し、手動リマップUIを提供（サイレント・フォールバック禁止）。
3. **再現性のある試聴はオフラインレンダリング推奨**。ライブFluidSynthは低レイテンシ対話が必要な時のみ、buffer/sample-rate設定を露出し、レイテンシ推定を可視化。
4. ドラム(ch10)は別経路で扱う。program changeが無視される前提でUI設計。
5. 複数SF2ロード時は bank offset / 明示 program_select を必須化（スタック衝突の暗黙上書き防止）。
6. XG/GS/GMモードと GM SYSTEM ON の副作用を把握し、bank-selectモードを固定化してテスト。
