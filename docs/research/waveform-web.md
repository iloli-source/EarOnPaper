# 波形表示のWeb実装・プロダクト調査（Web情報源）

**調査日:** 2026-07-19
**担当:** 波形実装・プロダクト調査（Web担当。論文=codex / X=grok と分担）
**位置づけ:** AI採譜アプリ（絶対音感エミュレータ）の波形・同期・音質診断・シェアUIに関するWeb一般情報源（技術ブログ・競合ドキュメント・レビュー）の網羅調査。姉妹編に `waveform-codex-papers.md`（論文）・`waveform-grok-x.md`（X）あり。
**関連要件:** F-039〜043（編集UI）・F-001/002/004/005/108（入力系）・NF-006（長尺）・NF-046（UI応答予算）

> **出典方針:** 各節に出典URLを明記。数値・仕様は出典に基づき、推測は「※判断」と注記する。

---

## 1. 波形描画ライブラリ比較

JS波形ライブラリは大きく「再生プレーヤー型（wavesurfer.js）」「アノテーション/検証型（peaks.js）」「データ層のみ（waveform-data.js）」に分かれる。本プロダクトは"譜面と同期した検証ビュー"が主用途のため、peaks.js系の設計思想（precomputed peak + 検証マーカー）が近い。

| ライブラリ | 役割 | 描画基盤 | ライセンス | 長尺対応 | 本件適性 |
|---|---|---|---|---|---|
| **wavesurfer.js** v7 | 再生プレーヤー中心。リージョン/スペクトログラム/タイムライン等プラグイン豊富 | HTML canvas（v7でWeb Audio依存を分離、MediaElement再生可） | BSD-3-Clause（寛容） | precomputed peaks 受け渡し可。ただし高px/秒で描画が重い（既知issue #2336） | ◯ プレーヤー実装が速い。プラグインでスペクトログラム(F-041)も賄える |
| **peaks.js** (BBC) | 波形の"検証・アノテーション"UI。ズーム波形＋概観波形の2段＋point/segmentマーカー | HTML canvas（Konva.js） | **LGPL-3.0**（動的リンク前提。改変配布に注意） | **precomputed .dat/.json 前提設計**。8bit(`-b 8`)推奨で長尺に強い | ◎ 「要確認区間マーカー」「原音源同期」の思想がF-042/043と直結 |
| **waveform-data.js** (BBC) | データ層のみ（描画なし）。audiowaveform出力の読み込み・リサンプル・スケール | 非描画（自前canvas/WebGL可） | LGPL-3.0 | ◎ mipmap的なscale/resample APIを提供 | ◎ 描画を自前実装するなら基盤に最適 |
| **audiowaveform** (BBC, C++ CLI) | 音源→peak .dat/.json 事前計算ツール。上記2つの入力を生成 | — | GPL（サーバ側CLI利用は自製品に伝播しにくいが要確認） | ◎ サーバ/ローカルで事前計算し、長尺でも軽量データ配信 | ◎ NF-006(最大24h)前提なら事前計算パイプラインは事実上必須 |

**ライセンス上の含意:** wavesurfer.jsのBSD-3-Clauseが最も寛容。peaks.js/waveform-data.jsはLGPL-3.0で、ライブラリを改変せず動的リンクで使う限りアプリ本体のライセンス伝播は避けやすいが、Electron等で同梱する場合は配布形態を法務確認すべき（※判断）。完全ローカル処理（F-066）と両立する。

**採用の見立て（※判断）:** 「BBCのaudiowaveform（事前計算）＋ waveform-data.js（データ層）＋ 自前canvas/WebGL描画」が、長尺(NF-006)・検証マーカー(F-043)・譜面同期(F-042)の要件と最も整合。ズーム波形＋概観波形の二段構成はpeaks.jsの設計をそのまま参考にできる。

出典: [npm trends 比較](https://npmtrends.com/peaks.js-vs-react-waveform-vs-react-wavesurfer-vs-waveform-data-vs-waveform-playlist-vs-waveform-react-vs-wavesurfer) / [wavesurfer.js FAQ](https://wavesurfer.xyz/faq/) / [wavesurfer #2336 高px描画の遅さ](https://github.com/katspaugh/wavesurfer.js/issues/2336) / [bbc/peaks.js](https://github.com/bbc/peaks.js/)

---

## 2. DAW/大容量ファイルの波形描画戦略

DAWフロントエンド開発者の技術ブログ・フォーラムから、長尺・ズーム対応の描画戦略が抽出できた。**NF-006（最大24時間）はブラウザのCanvas2Dナイーブ実装では確実に破綻する領域**であり、以下が要点。

- **ピークファイル（peak cache）:** 512サンプル等のブロック単位でmin/max値を事前計算して保存。生波形を毎回走査しない。audiowaveformもこの方式。（[KVR: peak-files](https://www.kvraudio.com/forum/viewtopic.php?t=193993)）
- **ズームレベル別ミップマップ:** 32/64/128/256/512/1024サンプル等、段階的に粗いピークデータを持ち、ズーム率に応じて最適な粒度を選ぶ（1pxが1ブロック未満になったら生サンプル、超えたらピークデータ）。（同上）
- **可視範囲のみ描画:** クリップがpx上で非常に長くなるため「見えている部分だけ処理・描画する」ことが必須。ズーム変更時は可視クリップを全再描画する負荷が発生。（[billydm: DAW frontend struggles](https://billydm.github.io/blog/daw-frontend-development-struggles/)）
- **ストリーミング:** 超長尺はディスクから逐次ストリーム。非同期処理になりタイムライン描画が複雑化。（同上）
- **GPU描画（WebGL/WebGPU）:** Canvas2DはCPUバウンドで、高px/秒では10分MP3で34秒・1.5時間動画で3分という実測遅延の報告あり（wavesurfer）。カスタムシェーダでGPUに描画コマンドを送る方式が推奨されるが、CPU側でコマンドバッファを組む負荷は残る。WebGPUで「100万点を60fpsで滑らかにズーム/パン」の事例、5GB動画をブラウザ内で波形化した事例が登場している。（[HN: WebGPU waveform](https://news.ycombinator.com/item?id=40046774) / [mrkev/webgpu-waveform](https://github.com/mrkev/webgpu-waveform) / [Medium: 5GB動画をブラウザで](https://medium.com/@gjovanov/audio-waveform-how-i-made-my-browser-process-5gb-videos-without-catching-fire-589e3c5f5e57)）

**本件への含意（※判断）:** 「audiowaveformで事前計算 → ミップマップ化したピークデータ → 可視範囲のみ描画、必要ならWebGPU」の3段構えが、NF-006とNF-046（UI応答予算）を同時に満たす現実解。F-105（部分結果の先出し）とも接続し、"解析中でも確定区間の波形を逐次描画"できる。

---

## 3. 競合・先行プロダクトの波形/スペクトル表示の分解

| プロダクト | 波形/スペクトル表示 | 見せ方の特徴 | 本件への示唆 |
|---|---|---|---|
| **Melodyne**（Celemony） | ピアノロール上に音を「ブロブ（blob）」として描画。縦=ピッチ、横=タイミング/長さ、形/太さ=立ち上がり・減衰・音量。背後にスペクトログラムを薄いグレーで重ね、Show Pitch Curveで各音の実ピッチ曲線を細線で重畳。**未確定音は輪郭のみの"シルエットblob"** として代替候補を提示 | 「波形の中に音符が見える」理想形の実体。音の高さ・長さ・強さを**色と形で直感的に**表現。日本語レビューでも"他ツールとの決定的な差別化"と評価 | **本プロダクトの理想形に極めて近い。**シルエットblob = F-043「要確認/低信頼」の二重符号化(色+形)の完成例。スペクトログラム重畳(F-041)＋ピッチ曲線＝解析根拠の可視化。ただしMelodyneは単声中心の編集ツールで、採譜下書きUXとは目的が異なる |
| **AnthemScore** | スペクトログラム＋スライダー式補正。全工程を1アプリ内に統合、オフライン | スペクトログラム上で誤検出を目視確認する定番設計（F-041の直系） | オフライン・スペクトログラム目視はF-066/F-041の参照実装 |
| **Songscription** | Web版。新モデル＋フル記譜ワークフロー、内蔵エディタ | ピッチ良好だが拍子/小節が弱点との既知評価。波形より譜面編集中心 | 譜面編集(F-039)側の参照。波形UIは主役でない |
| **Moises** | ステム分離が主役。波形は分離済みステムごとの再生ビュー | 波形自体は控えめ。分離→練習/リミックスの導線 | F-003(ステム分離)＋F-063(パート別ソロ/ミュート)の導線設計に参照 |
| **Sonic Visualiser** | 波形＋スペクトログラムの複数レイヤ、編集可能な解析レイヤ、タイムライン注釈 | 解析レイヤを重ね合わせる研究者向け設計 | 「波形＋スペクトログラム＋注釈レイヤ」の多層重畳はF-041/F-042の上位参照 |

**Melodyne検証の結論:** 理想形として妥当。特に(1)ブロブによる音符と波形の融合表現、(2)シルエットblobによる低信頼度の形状符号化、(3)スペクトログラム薄重ね＋ピッチ曲線による根拠可視化 の3点は、F-041/042/043の受入条件を「実在する到達点」として具体化できる。相違点は、Melodyneが編集ツール／本件が採譜"下書き"UXである点で、下書きバッジ(F-038)や要確認警告はMelodyneにない独自要素。

出典: [Celemony M5 表示オプション](https://helpcenter.celemony.com/M5/doc/melodyneStudio5/en/M5tour_ViewOptions-ARA) / [Sound on Sound: Melodyne DNA](https://www.soundonsound.com/reviews/celemony-melodyne-dna-editor) / [サンレコ Melodyne 5](https://www.snrec.jp/entry/product/celemony_melodyne5_pt1) / [ほんみく: Melodyne使い方](https://piko-mix.com/blog/how-to-melodyne/) / [Songscription vs AnthemScore](https://www.songscription.ai/blog/songscription-vs-anthemscore) / [Gitnux: ATMソフト比較2026](https://gitnux.org/best/automatic-music-transcription-software/)

---

## 4. 波形と譜面の同期UI（カラオケ字幕式追従）先行例

| プロダクト | 同期の仕組み | 追従表現 |
|---|---|---|
| **Soundslice** | 楽譜をYouTube/音源に同期、カーソルが音に追従 | カーソル形状を Line/細矩形/太矩形/非表示 から選択、色（橙/青/黄/控えめ）も選択。再生中の音符ハイライトのON/OFF可 |
| **Flat.io** | MP3をアップロードし手動同期ポイントを打つ。小節頭のズレはクリックで同期点追加・小節番号調整 | 同期点間の時間からスライダー移動を再生アルゴリズムで自動補間 |

**本件への含意:** F-042の受入条件「低信頼箇所へ1操作ジャンプ＋自動ループ＋波形/譜面の同期ハイライト」に直結する先行例。特に**Soundsliceのカーソル形状/色の選択肢と音符ハイライト**は、NF-033（モーション低減）やNF-047（カラー3系統）との整合設計の参考になる。Flat.ioの「手動同期点＋自動補間」は、AI推定テンポマップ(F-017)がズレたときのユーザー補正導線として応用可能。カラオケ字幕式の追従は、この"カーソル追従＋現在音符ハイライト"の組み合わせで実現される。

出典: [Flat: 録音との同期](https://help.flat.io/en/music-notation-software/synchronize-external-recording/) / [Flat: 再生](https://help.flat.io/en/music-notation-software/playback/) / [Tunescribers: Noteflight/Flat/Soundslice比較](https://www.tunescribers.com/blog/comparing-online-music-notation-tools-noteflight-flat-io-and-soundslice)

---

## 5. 音質診断UI（入力レベル/クリッピング警告）の先行例

録音/DAW界の確立したUXパターンが、F-002（音質診断・警告）の色設計・閾値表現に直接使える。

- **色分けの慣行:** 緑（〜-12dB、安全）→ 黄/橙（-6dB付近、注意）→ 赤（0dB接近＝過大/クリッピング危険）。（[Audacityメーター](https://manual.audacityteam.org/man/meter_toolbar.html)）
- **クリッピング指示器の"粘り":** 同一チャンネルで4サンプル以上連続が上限超過で赤バーが点灯し、**そのセッション中は消えず残る**。＝「今クリップ中」ではなく「この録音のどこかでクリップが起きた」ことの絶対的表示。（[Logic Pro: ピークレベル/クリッピング](https://support.apple.com/guide/logicpro/peak-level-display-and-signal-clipping-lgcp8ec1ad64/mac) / [Source Nexus: Peak Hold](https://support.source-elements.com/source-nexus-review-user-guide/peak-hold-and-clipping-indicator)）
- **出力/入力での色差:** クリップ時、出力ストリップは赤・その他ストリップは橙で点灯するなど、文脈で色を分ける実装がある。（Logic Pro同上）

**本件への含意:** F-002は「クリッピング率>0.1%またはSNR<20dBで警告」（判定保留閾値）を持つが、UXとしては(1)緑→黄→赤の段階色、(2)クリップが一度でも起きたら"粘る"永続バッジ、(3)録音後に「この音源はどこでクリップしたか」を波形上に赤マーカーで残す、が既存ベストプラクティス。**F-108フィールド録音モード（雑音混じり日常録音）では特に、"どこが拾えてどこが拾えなかったか"を波形上に正直表示する**用途と親和的で、絶対音感エミュレータの「拾えたものだけ信頼度つき」思想（F-043連動）とUX的に一致する。NF-047のカラー3系統・衝突ルールと調整が必要。

---

## 6. シェア用波形ビジュアル（SNS映え）の事例

「街の音が楽譜になる」（product-vision）のSNS共有フックに応用できる、音声→波形動画の生成ツール群。

- **Headliner:** 音声を波形アニメーション＋字幕＋ブランディングの短尺動画（オーディオグラム）化。正方形/縦/横フォーマット、自動字幕、Pro版は新エピソード自動生成。無料5本/月。ポッドキャスト販促のSNSクリップ標準ツール。（[Headliner](https://www.headliner.app/) / [Headliner: 波形生成](https://www.headliner.app/blog/2020/09/01/how-to-quickly-generate-a-waveform-from-your-audio/)）
- **Riverside / Transistor.fm:** 同種のオーディオグラム/波形動画をSNS向けに生成するガイドを提供。（[Riverside: 波形動画ガイド](https://riverside.com/blog/audio-waveform) / [Transistor: audiogram](https://transistor.fm/podcast-audio-video-clip/)）

**本件への含意（※判断）:** これらは"音声＋波形"の映えだが、本プロダクトの独自性は**"波形＋そこから起こした音符（譜面/TAB）"を重ねてシェアできる**点。日常音採譜（F-108）の成果を、波形＋抽出音符＋信頼度ハイライトを載せた短尺動画/静止画として書き出せば、Melodyneのブロブ表現をシェア用に転用でき、耳コピ学習層の「世界が音名で聴こえる体験」への憧れに刺さる。要件化されていない領域で、将来のバイラル導線候補（現状は観測レベル）。

---

## 7. 既存要件IDへのマッピング表

| 要件ID | 名称 | 本調査が強化する受入条件 | 主な出典節 |
|---|---|---|---|
| **F-001** | 音声ファイル入力 | D&D・対応形式表示は各ライブラリ標準。実装難度低 | §1 |
| **F-002** | 音質診断・警告 | 緑→黄→赤の段階色・クリップ永続バッジ・波形上の赤マーカー（DAW慣行） | §5 |
| **F-004** | 長尺音源の自動分割 | ピークキャッシュ＋ミップマップで分割せず全体描画も可能に | §2 |
| **F-005/F-108** | 録音入力/フィールド録音 | 入力レベルメーター・"拾えた/拾えなかった"の波形正直表示 | §5,§6 |
| **F-039** | 楽譜エディタ | 波形と別レイヤの譜面編集。Songscription/Soundsliceが参照 | §3,§4 |
| **F-040** | ピアノロール編集 | Melodyneブロブ＝FL級手触りの上位到達点 | §3 |
| **F-041** | スペクトログラム表示 | AnthemScore/Sonic Visualiser＝スペクトログラム目視の定番。Melodyneの薄重ね | §3 |
| **F-042** | 原音源同期再生 | Soundsliceのカーソル追従＋音符ハイライト、Flatの手動同期点＋自動補間 | §4 |
| **F-043** | 信頼度ハイライト | Melodyneのシルエットblob＝色+形の二重符号化の実在例 | §3 |
| **F-105** | 部分結果の先出し | 可視範囲のみ描画＋逐次描画で"確定区間から波形/譜面を先出し" | §2 |
| **NF-006** | 長尺（最大24h） | 事前計算peak＋ミップマップ＋可視範囲描画＋WebGPUの3段構え | §1,§2 |
| **NF-046** | UI応答予算/大量表示 | Canvas2Dの限界（10分34秒等）を避けGPU/事前計算で予算内に | §2 |
| **NF-047** | カラー3系統/衝突ルール | クリップ警告色・カーソル色・信頼度色の3系統衝突を設計時に調停 | §4,§5 |

---

## 8. 調査カバレッジと未取得領域（正直な報告）

**取得できた:** ライブラリ比較（DL数/ライセンス/長尺適性）、DAW描画戦略（peak cache/ミップマップ/GPU/ストリーミング）、Melodyneのブロブ/シルエット/スペクトログラム重畳の具体、Soundslice/Flatの同期UI仕様、録音アプリのクリッピング警告UX、Headliner系シェア動画ツール。

**取得しきれなかった/要追加調査:**
- **定量ベンチマーク:** 3ライブラリの直接的な描画fps/メモリ比較の公開データは乏しい。wavesurferの遅延実測（10分34秒等）は断片的で、条件統一されたベンチは未発見。実装前に自前計測が必要（※判断）。
- **WebGPU大容量事例の実測値:** HNスレッド本文はレート制限で全文未取得。「100万点60fps」「5GB動画」は見出し/要約レベルで、24時間音源での具体数値は未確認。
- **Melodyneの内部描画方式:** ブロブ描画のGPU利用有無など内部実装は非公開。UI観察レベルの情報のみ。
- **競合のスクリーンショット精査:** Moises/Klangioの波形UIの最新スクショはテキスト情報が中心で、視覚的分解は限定的。実機/スクショの直接確認が望ましい。
- **シェア波形＋音符の合成事例:** "波形＋抽出音符"を重ねてシェアする既存プロダクトは未発見（＝空白＝独自性の裏付けだが、需要実証は別途必要）。
