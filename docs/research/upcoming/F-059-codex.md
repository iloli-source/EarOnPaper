# 機能「テンポ変更再生（ピッチ維持での減速再生・タイムストレッチ・区間ループ）」論文＋WEB調査報告（codex担当）

**調査日:** 2026-07-21
**対象:** 採譜/記譜ソフト機能「テンポ変更再生」＝ (a) ピッチ維持での減速再生（pitch-preserving slow-down）／(b) タイムストレッチ（time-scale modification, TSM）／(c) A-B区間ループ（section loop）
**担当:** codex（OpenAI Codex 読取りセッション ＋ WebFetch による一次URL検証）
**方針:** 実在情報のみ・URL併記・捏造禁止。**特に失敗例を最大化**。未確認は「未確認」と明記。英語中心（中国語圏は「变速不变调」の語は豊富だが実務トラブルログは薄く、信号処理は英語論文・公式Doc・GitHub Issueに偏在）。

---

## 0. 調査範囲と限界（重要）

| 項目 | 内容 |
|------|------|
| 学術論文 | TSM（phase vocoder / WSOLA / トランジェント処理 / formant保存）は査読論文が豊富。**Driedger & Müller (2016) のレビューが本テーマの決定版。** A-Bループのclick問題は論文より公式マニュアル（Audacity/WaveLab）が主軸。 |
| 実機再現なし | librosa/Rubber Band/SoundTouch を実機再現していない。GitHub Issue・フォーラムは「報告事例」扱い。 |
| URL検証 | 主要URLは WebFetch で本文確認済み（下記★印）。SoundTouch READMEはbot 403だったが別経路で本文確認済み（★）。MDPIレビューはfetch 403だがDOI実在・著名論文（未再取得URL）。 |
| 二層モデル | 「アルゴリズム品質の失敗（transient破壊・phasiness）」と「境界処理の失敗（loop click・latency）」は別レイヤ。混同が事故源。 |

---

## 1. Phase Vocoder（位相ボコーダ）の失敗

Phase Vocoder系TSMの典型失敗は **transient smearing（過渡音のにじみ）**・**phasiness（位相の濁り・こもり）**・**reverberant/echo-like artifacts（残響状の尾引き）**・**loss of presence（音の輪郭消失）**。

- Driedger & Müller のレビュー論文は、PV-TSMが**水平位相（horizontal phase）**の連続性を保てる一方、フレーム内の**垂直位相コヒーレンス（vertical phase coherence）**を壊しやすく、その結果トランジェントが時間方向ににじみ phasiness が出ると整理。本テーマの最重要文献。
  - Jonathan Driedger, Meinard Müller, "A Review of Time-Scale Modification of Music Signals", *Applied Sciences* 6(2):57, 2016.
  - https://www.mdpi.com/2076-3417/6/2/57 ／ DOI: https://doi.org/10.3390/app6020057

- Laroche & Dolson はこの問題を "phasiness" と命名し、identity phase locking 等の改善を提案。
  - Jean Laroche, Mark Dolson, "Improved phase vocoder time-scale modification of audio", *IEEE TASLP* 7(3), 1999. DOI: https://doi.org/10.1109/89.759041
  - 関連: "Phase-vocoder: about this phasiness business", WASPAA 1997. DOI: https://doi.org/10.1109/ASPAA.1997.625603

- 中国語圏の特許文献でも同じ失敗を記述: 相位声码器による時間伸縮では垂直相干性が破壊され、瞬变が "模糊(smear)" し、歪んだ・回响的（残響状）・不自然な音になる。
  - CN102789785B, Google Patents. https://patents.google.com/patent/CN102789785B/zh

**採譜用途での危険箇所（失敗が可視化される場面）:**
- ピッキング音がぼやけ、**発音タイミングが読みにくくなる**（採譜の根幹に直撃）
- ドラム／カッティングが二重化 or 前後に尾を引く
- コード楽器は音程を保っても定位・質感が濁る
- 強いスロー（`0.5x` 以下）で破綻が顕著化

---

## 2. WSOLA / OLA 系の失敗

WSOLAは時間領域で波形類似箇所を探して重ねる方式。声・単音には強いが、複雑なポリフォニックでは失敗しやすい。

- Driedger & Müller は WSOLA系の代表アーティファクトとして **transient doubling / stuttering（過渡音の複製・どもり）** と **transient skipping（過渡音の脱落）** を明示。伸長時は単一トランジェントが二度聞こえ、圧縮時は消える。
  - https://www.mdpi.com/2076-3417/6/2/57

- Grofit & Lavner: 標準WSOLAは知覚上重要なトランジェント区間も一様に伸縮し音質を大きく劣化させるとして transient management を提案。
  - Shahaf Grofit, Yizhar Lavner, "Time-Scale Modification of Audio Signals Using Enhanced WSOLA With Management of Transients", *IEEE TASLP* 16(1), 2008. DOI: https://doi.org/10.1109/TASL.2007.909444

- WSOLA原典:
  - Werner Verhelst, Marc Roelands, "An overlap-add technique based on waveform similarity (WSOLA) for high quality time-scale modification of speech", ICASSP 1993. DOI: https://doi.org/10.1109/ICASSP.1993.319366

- **SoundTouch は WSOLA-like な時間領域処理**（"SoundTouch uses WSOLA-like time-stretching routines that operate in the time domain"）。time-stretch時の典型I/O latencyは **約 `100 ms`**。ステレオを2つのモノとして別処理するのは**位相コヒーレンシ喪失でステレオ像が壊れる**ため非推奨と明記。★本文確認済み
  - https://www.surina.net/soundtouch/README.html

**採譜用途での危険箇所:**
- 速いピッキング・ハイハット・スネアが「タタッ」と二重化（stutter）
- 圧縮方向（速くする）で発音が抜ける（skipping）
- 歪みギター・ミックス音源で類似波形探索が誤りやすい
- ステレオ左右別処理で定位が動く

---

## 3. librosa.effects.time_stretch の限界

`librosa.effects.time_stretch` は内部で `phase_vocoder` を用いる。

- librosa公式Docは `phase_vocoder` を **"a simplified implementation, intended primarily for reference and pedagogical purposes. It makes no attempt to handle transients, and is likely to produce many audible artifacts."** と明記。高品質用途には Rubber Band / pyrubberband を推奨。★本文確認済み
  - https://librosa.org/doc/main/generated/librosa.phase_vocoder.html

- 現行 `librosa 0.11.0` の `time_stretch` は multi-channel supported と記載。
  - https://librosa.org/doc/latest/generated/librosa.effects.time_stretch.html

- ただし**歴史的に mono-only 制約**があり、Google Groupで Brian McFee が "time-stretcher only operates on one channel at a time" と回答（`Invalid shape for monophonic audio`）。古い実装・古い記事・既存コードを踏む場合は注意。
  - https://groups.google.com/g/librosa/c/ELUESZqgn6g

- `pitch_shift` には明示的な **formant preservation 制御がない**。docsも高品質ピッチシフトは `pyrubberband` を参照。
  - https://librosa.org/doc/latest/generated/librosa.effects.pitch_shift.html

**採譜ソフトでの扱い:** プロトタイプ・解析バッチには可。**UIのリアルタイム再生エンジンには不向き**。`metallic`／`phasiness`／transient smear をQA項目化。声・歌はformant保存が別エンジン必須。

---

## 4. Rubber Band / SoundTouch / élastique の既知リスク

- **Rubber Band**: ブロックベースPhase Vocoder＋percussive transientでのphase reset＋adaptive stretch ratio＋vertical phase coherence改善の "lamination"。裏を返せば transient検出・phase reset・lamination が音質の要点。"Time-stretching is not magic" と自認。★本文確認済み
  - https://www.breakfastquay.com/rubberband/technical.html
  - 実装リスク: real-time modeは `getPreferredStartPad()` / `getStartDelay()` 補償が必要／ratio変更は出力に遅れて反映（予定時刻より早くスケジュール要）／typical delay は設定により `512`,`1024`,`2048` samples、R3では `1280`,`2048` samples 等。
    - https://www.breakfastquay.com/rubberband/integration.html
  - **dynamic pitch change で大量の小クリック**が出るGitHub Issue（"Clicks while changing pitch shift factor #30"、RealTime modeでブロック間でpitch scaleを補間変更すると "lots and lots of small clicks" が累積）。★本文確認済み
    - https://github.com/breakfastquay/rubberband/issues/30

- **SoundTouch**: WSOLA-likeゆえ複雑音楽ではstutter/skippingに注意／time-stretchで約 `100 ms` レイテンシ／想定8kHz〜48kHz／ステレオ左右別処理は非推奨。
  - https://www.surina.net/soundtouch/README.html

- **élastique / Ableton Complex Pro 系**: Complex/Complex ProはCPU負荷高、必要時Freeze/Resample推奨／Complex Pro の Formants は**移調時のみ有効**／Complex系playbackは非中立処理で元テンポでも完全中立でない（Audio Fact Sheet）。
  - EN: https://www.ableton.com/en/live-manual/11/audio-clips-tempo-and-warping/
  - 中文: https://www.ableton.com/zh-cn/live-manual/11/audio-clips-tempo-and-warping/
  - Audio Fact Sheet: https://www.ableton.com/en/live-manual/11/audio-fact-sheet/

---

## 5. Formant distortion（フォルマント歪み）

ピッチシフトを time-stretch + resample で実装すると**声道由来のformant envelopeまで移動**し、chipmunk/munchkin化・声質変化が発生。

- Quatieri & McAulay: 声の時間・ピッチ変換で vocal tract と vocal cord excitation の位相寄与を独立に扱い、shape invariance を保つ必要を論じる。
  - "Shape invariant time-scale and pitch modification of speech", *IEEE TSP* 40(3), 1992. DOI: https://doi.org/10.1109/78.120793
- Rubber Bandは vocals のピッチシフトで `OptionFormantPreserved` を追加する指針。
  - https://www.breakfastquay.com/rubberband/integration.html
- Ableton Complex Pro の Formants control は**移調しない場合は効果なし**と明記。
  - https://www.ableton.com/en/live-manual/11/audio-clips-tempo-and-warping/

**採譜での失敗:** 歌・管楽器・歪みギターで「音程は合っているが音色が別物」。

---

## 6. A-Bループの click / pop（境界不連続）

A-Bループは time-stretch品質とは独立に、**境界の波形不連続**でクリックが出る。ゼロクロスだけでは傾き・左右チャンネル差を保証しない。

- Audacity manual: 選択境界をゼロクロスへ移動すると編集点クリックのリスクは減るが、**ステレオでは左右のゼロクロス位置が異なり片側にクリックが残り得る**。★本文確認済み
  - https://manual.audacityteam.org/man/select_menu_at_zero_crossings.html
- Steinberg WaveLab manual: ゼロクロスで編集しないと波形不連続が生じ clicks/pops として知覚される。
  - https://www.steinberg.help/r/wavelab-pro/13.0/en/wavelab/topics/audio_files_editing/zero_crossing_c.html
- Web Audio API の `AudioBufferSourceNode.loop`/`loopStart`/`loopEnd` はループ点指定のみで**自動クロスフェード品質は保証しない**。
  - https://developer.mozilla.org/en-US/docs/Web/API/AudioBufferSourceNode/loop

**実装推奨:** 境界に `3-10 ms` の等パワークロスフェード／ゼロクロス探索は左右同時評価／波形値だけでなく傾き差も評価／time-stretch後のバッファでA/B点を再計算／ループ先頭の再生位置ジャンプをサンプル精度で処理。

---

## 7. リアルタイム制約とレイテンシ

採譜UIではスライダー操作・A-B範囲変更・波形カーソル・音声出力がずれると体験が壊れる。

- Rubber Band: real-time modeで start pad/start delay 補償が必要、ratio変更は出力に遅れて反映と明記。
  - https://www.breakfastquay.com/rubberband/integration.html
- DAFx-08のリアルタイムtime/pitch scale frameworkは、連続変化するパラメータに対し artifact防止・latency最小化・同期が課題と指摘。
  - Ivan Damnjanovic et al., "A Real-time Framework for Video Time and Pitch Scale Modification", DAFx-08. https://arrow.tudublin.ie/argcon/47/
- 一般DAWでも buffer size・plugin latency・spectral processing が遅延源。
  - https://help.ableton.com/hc/en-us/articles/360010545559-How-Latency-Works

---

## 8. 採譜（Pitchsieve）向け実装判断

- **MVP**: Rubber Band を第一候補、SoundTouch を低CPU代替として比較。
- **librosa**: 解析・オフライン変換・検証用に限定（リアルタイム再生には使わない）。
- **A-Bループ**: エンジン任せにせず**独自に境界クロスフェード**を実装。
- **QA音源**: ピアノ／歪みギター／アコギ単音／ドラム／女性ボーカル／ベース／フルミックスを必ず含める。
- **QA観点**: transient smear・stutter・metallic/phasiness・formant drift・stereo image drift・loop click・slider操作時click・UI波形と音の遅延。

---

## 付記: URL検証状況

- ★本文確認済み（WebFetch）: librosa phase_vocoder Doc／Rubber Band technical.html／GitHub Issue #30／SoundTouch README（別経路確認）／Audacity zero-crossings manual。
- MDPIレビュー（app6020057）はfetch時403だが**DOI実在・著名論文**。DOI併記。
- CN102789785B・IEEE各DOI・DAFx-08 arrow.tudublin.ie・Ableton各Docは codex 提示URL。DOI/公式ドメインで実在性は高いが、個別本文の逐語検証は上記★以外は未実施（「報告URL」扱い）。
