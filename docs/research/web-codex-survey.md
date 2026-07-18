> 【歴史的記録】本書は作成時点の前提・知見に基づくスナップショットです。その後の決定により一部前提は更新されています。現在の前提は `README.md`・`docs/requirements/product-vision.md`・`docs/research/gate-execution-spec.md`(最新改訂) を参照してください。

# AI採譜（Automatic Music Transcription）市場・技術調査

## 0. 要約

- 現在のAI採譜市場は、**完全自動の最終譜面生成**よりも、**人間が直す前提の初稿生成**として実用化が進んでいる。
- 実用度が高い順に見ると、現状は **単一楽器・単旋律 > ソロピアノ > ギター/ベースTab > ドラム/コード検出 > フルミックス多楽器の完全採譜**。
- 商用では **Klangio / Songscription / AnthemScore / ScoreCloud / Songsterr AI / audio2guitar** が「譜面・Tab・MusicXML」寄り、**Moises / AudioJam / Chordify / Fadr / LALAL.AI** は「練習・耳コピ補助・ステム分離・コード検出」寄り。
- OSS・研究系では **Basic Pitch / MT3 / Transkun / ByteDance PianoTrans / MuScriptor / YourMT3** が重要。特に2024-2026は、Transformer系、多楽器モデル、歌詞アラインメント、音源分離との統合、マルチモーダル化が進んでいる。
- ユーザー報告では、成功例は「きれいな単一楽器」「短いフレーズ」「練習用の下書き」に集中し、失敗例は「複雑なミックス」「速いピアノ和音」「歪みギター」「ノイズ/リバーブ」「リズム・拍子・運指・表情記号」に集中している。

---

## 1. 既存AI採譜ツール・サービス一覧

| # | ツール | 種別 | 主な機能 | 価格/提供形態 | 対応楽器・素材 | 出力 | 強み | 弱み |
|---:|---|---|---|---|---|---|---|---|
| 1 | AnthemScore / AnthemScore Web | 商用 | 音声/MIDIから譜面化、Tab、複数楽器指定、編集 | Web: Free、Plus `$9.99/月`、Pro `$29.99/月`。Desktopは買い切り系 | MP3/WAV/M4A/FLAC/OGG/MP4/MID、録音 | PDF, MusicXML, MIDI | ローカル版あり、編集UI、譜面寄り | 完成譜ではなく修正前提。複雑音源は誤検出しやすい。Webは曲数/長さ制限あり ([lunaverus.com](https://lunaverus.com/transcribe?utm_source=openai)) ([lunaverus.com](https://lunaverus.com/transcribe/pricing?utm_source=openai)) |
| 2 | Basic Pitch | OSS/無料 | 音声→MIDI、ピッチベンド検出 | 無料、GitHub/PyPI/npm、Web demo | ほぼ任意の単一楽器、声、ポリフォニック単一楽器 | MIDI | 軽量、速い、OSS、DAW連携しやすい | 譜面/PDF/MusicXMLなし。基本は「1楽器ずつ」が得意 ([engineering.atspotify.com](https://engineering.atspotify.com/2022/6/meet-basic-pitch?utm_source=openai)) ([github.com](https://github.com/spotify/basic-pitch?utm_source=openai)) |
| 3 | MuScriptor | OSS/研究 | 多楽器AMT、音源→ノート列 | Open-weight。small/medium/largeあり | 任意ジャンル、多楽器録音 | 主にMIDI/ノートイベント系 | 2026時点で重要なオープン多楽器モデル候補 | 実運用UI/商用ワークフローは未成熟。大規模モデルは計算資源が重い ([huggingface.co](https://huggingface.co/MuScriptor/muscriptor-large?utm_source=openai)) |
| 4 | Songscription AI | 商用 | 音声/URL→譜面・MIDI・Tab・MusicXML、内蔵エディタ | 無料30秒系、長尺/出力は有料 | Piano, guitar, bass, violin, flute, trumpet, sax, drums, vocals | PDF, MIDI, MusicXML, Guitar Pro | 対応楽器と出力形式が広い。YouTube/Instagram/TikTok対応 | 価格・品質は継続確認必要。フルミックス完全採譜はまだ課題 ([songscription.ai](https://www.songscription.ai/?utm_source=openai)) |
| 5 | Klangio Transcription Studio | 商用 | 多楽器譜面化、各種Klangioアプリ統合 | 20秒無料デモ、有料サブスク | ピアノ、ギター、歌、ドラム、複数楽器 | PDF, MIDI, MusicXML, GuitarPro | 楽器別モデルとWeb入力が強い | 複雑ミックス・変拍子・歪みギターは弱い可能性 ([klang.io](https://klang.io/transcription-studio/?utm_source=openai)) |
| 6 | Melody Scanner | 商用 | YouTube/録音/アップロード→譜面、ピアノアレンジ、編集 | Free、月額 `$4.99`、年額 `$39.99` など表示あり | ピアノ、ギター、フルート、バイオリン、サックス、ベース、歌、コード。旧ページでは「ソロ楽器のみ」明記 | PDF, MIDI, MusicXML | ブラウザ/モバイル、YouTube入力、譜面編集 | レビューでは複雑曲・多楽器・ハミング精度に不満が多い ([klang.io](https://klang.io/melodyscanner/?utm_source=openai)) ([melodyscanner.com](https://melodyscanner.com/?sid=0aKI57&utm_source=openai)) |
| 7 | Piano2Notes | 商用/Klangio | ピアノ録音→譜面 | Klangioサブスク | ピアノ | PDF, MIDI, MusicXML | ピアノ特化 | バンド音源や非ピアノは別アプリ前提 ([klang.io](https://klang.io/melodyscanner/?utm_source=openai)) |
| 8 | Guitar2Tabs | 商用/Klangio | ギター/ベース→Tab・コード・譜面 | 20秒無料デモ、有料プラン | アコギ、エレキ、ベース、リード/リズム | PDF, MIDI, MusicXML, GuitarPro | Tab特化、YouTube/録音/アップロード、編集モード | 運指・弦選択は誤りやすい。複雑歪み/ミックスは要修正 ([klang.io](https://klang.io/ja/guitar2tabs/?utm_source=openai)) |
| 9 | Sing2Notes | 商用/Klangio | 歌声→譜面 | Klangio系 | ボーカル/ハミング | PDF, MIDI, MusicXML | メロディ採譜に向く | 歌詞・ブレス・ビブラート処理は完全譜面化が難しい ([klang.io](https://klang.io/melodyscanner/?utm_source=openai)) |
| 10 | Drum2Notes | 商用/Klangio | ドラム→譜面 | Klangio系 | ドラム | PDF, MIDI, MusicXML | ドラム特化 | シンバル/ゴーストノート/マイク被りは難所 ([klang.io](https://klang.io/melodyscanner/?utm_source=openai)) |
| 11 | Songsterr AI | 商用 | YouTube/音声→ギター・ベース・ドラムTab生成、Songsterr編集/再生 | Songsterr PlusでAI full tabs、50 complete tabs/月 | ギター、ベース、ドラム、ボーカル指定あり | Songsterr Tab, Guitar Pro, MIDI, MP3, WAV | 既存Tabライブラリ、合法ライセンス、Tabプレイヤー統合 | 標準譜・MusicXMLよりTab中心。Plus依存 ([songsterr.com](https://www.songsterr.com/new?utm_source=openai)) ([songsterr.com](https://www.songsterr.com/terms?utm_source=openai)) |
| 12 | MT3 | OSS/研究 | Multi-Task Multitrack Music Transcription | GitHub/Colab、Apache-2.0 | ピアノ/多楽器 | MIDI/トークン列 | Transformer系多楽器AMTの基礎モデル | Google公式製品ではなく研究実装。学習/運用は重い ([github.com](https://github.com/magenta/mt3?utm_source=openai)) |
| 13 | YourMT3 / YourMT3+ | OSS/研究 | MT3系を一般向けに扱いやすくした派生 | GPL-3.0、HuggingFace demo | 多楽器/マルチトラック | MIDI | 2024のYourMT3+、デモあり | YouTube連携はブロックされるなど運用面が不安定 ([github.com](https://github.com/mimbres/YourMT3?utm_source=openai)) |
| 14 | Transkun | OSS/研究 | ピアノ音源→MIDI、Neural Semi-CRF/Transformer | MIT、pip install | 表現豊かなピアノ | MIDI | ISMIR 2024系、ピアノ精度が高い | ピアノ特化。マルチトラック非対応 ([github.com](https://github.com/yujia-yan/transkun?utm_source=openai)) |
| 15 | ByteDance PianoTrans | OSS/研究 | 高解像度ピアノ採譜、ペダル推定 | Apache-2.0。リポジトリは2025年にarchive | ピアノ | MIDI | MAESTRO系ピアノAMTの代表実装 | 古い依存関係、研究者向け、保守停止 ([github.com](https://github.com/bytedance/piano_transcription?utm_source=openai)) |
| 16 | ScoreCloud | 商用 | 録音/歌/演奏→譜面、MIDI/MusicXML入出力、SongwriterでLead Sheet | Free、Plus `$5.99/月`、Songwriter `$11.99/月`、Pro `$20.99/月` | 歌、楽器、オーディオファイル、MIDI | PDF/印刷, MIDI, MusicXML | 譜面編集とアカウント同期が強い | 高度な多楽器フル採譜より作曲メモ/リードシート向き ([my.scorecloud.com](https://my.scorecloud.com/plans?utm_source=openai)) |
| 17 | Chordify | 商用 | YouTube/SoundCloud等からコード検出、同期コード表示 | 無料2曲/日、アカウントで4曲/日、Premium | ギター、ピアノ、ウクレレ、マンドリン向けコード | コード表示、PDFはPremium | コード練習に強い、曲数が多い | メロディ/完全譜面/MusicXMLではない ([chordify.net](https://chordify.net/pages/is-chordify-free/?utm_source=openai)) ([chordify.net](https://chordify.net/pages/chordify-app/?utm_source=openai)) |
| 18 | Moises | 商用 | ステム分離、コード、キー、BPM、スマートメトロノーム、歌詞 | Free/Premium/Pro、アプリ内課金 | ボーカル、ドラム、ベース、ギター等 | 譜面より練習/ステム/コード中心 | 練習・耳コピ前処理に強い | 採譜ツールではなく譜面出力は限定的 ([moises.ai](https://moises.ai/products/moises-app/?utm_source=openai)) ([help.moises.ai](https://help.moises.ai/hc/en-us/articles/9410960985628-Reasons-to-subscribe-to-the-Moises-Premium-Plan?utm_source=openai)) |
| 19 | AudioJam | 商用 | ステム分離、コード、AB loop、速度/ピッチ、Tab preview | Base Free、Pro、Enterprise | ボーカル、ドラム、ギター、ベース、鍵盤等 | MusicXML/GTP/PDF等の表示、譜面生成より練習補助 | リード/リズムギター分離、練習UI | 本格譜面エクスポートより耳コピ補助寄り ([audiojam.app](https://audiojam.app/features/?utm_source=openai)) ([audiojam.app](https://audiojam.app/purchase/?utm_source=openai)) |
| 20 | Samplab | 商用 | ポリフォニック音声のノート編集、Audio-to-MIDI、コード、ステム | 2026年9月17日でサービス終了予定 | サンプル、ポリフォニック音声 | MIDI, WAV, stems | DAW内ノート編集、コード/テンポ/キー連携 | クラウド依存だったが終了予定。長期採用リスク大 ([samplab.com](https://samplab.com/?__sl_c=metapromo7)) ([help.soundcloud.com](https://help.soundcloud.com/hc/en-us/articles/31509632447899-Samplab?utm_source=openai)) |
| 21 | AudioScore Ultimate | 商用 | MP3/CD/マイク/MIDI→譜面、最大16同時音、Sibelius連携 | 日本代理店表示で `¥43,780` | 非打楽器中心、歌/演奏/MP3/CD | PDF, MusicXML, NIFF, MIDI | Sibelius連携、古参の譜面変換 | UI/技術が古め。打楽器や現代的ミックスに弱い ([sibelius.com](https://www.sibelius.com/products/audioscore/ultimate.html?utm_source=openai)) ([h-resolution.com](https://h-resolution.com/product/audioscore-ultimate/?utm_source=openai)) |
| 22 | Melodyne | 商用 | ノート単位音声編集、Audio-to-MIDI、DNAポリフォニック編集 | 有料版 | ボーカル、単音楽器、Editor/Studioでピアノ/ギター等ポリフォニック | MIDI | 音程補正・音声編集の業界標準級 | 譜面作成ではなくMIDI/編集中心。価格高め ([helpcenter.celemony.com](https://helpcenter.celemony.com/M5/doc/melodyneStudio5/en/M5tour_ExportMIDI_standalone?env=standAlone&utm_source=openai)) ([helpcenter.celemony.com](https://helpcenter.celemony.com/M5/doc/melodyneStudio5/en/M5tour_AudioAlgorithms?env=standAlone&utm_source=openai)) |
| 23 | RipX DAW | 商用 | AI DAW、ステム分離、ノート単位編集、Audio-to-MIDI | RipX DAW `$99`、PRO `$198` | フルミックス、ボーカル、楽器、効果音 | MIDI, WAV, stems | 混合音源を分解してノート編集 | 採譜清書ではなく音声編集/制作寄り ([hitnmix.com](https://hitnmix.com/?utm_source=openai)) ([hitnmix.com](https://hitnmix.com/buy-ripx-wp/?utm_source=openai)) |
| 24 | Ableton Live Audio-to-MIDI | 商用DAW機能 | Harmony/Melody/Drums to MIDI、Slice to MIDI | Live Standard/Suite等 | メロディ、和音、ドラム | MIDI clip | DAW内完結、制作ワークフローが速い | isolated音源推奨。複雑曲はタイミング/音/velocityが崩れる ([ableton.com](https://www.ableton.com/en/live-manual/11/converting-audio-to-midi/?utm_source=openai)) |
| 25 | Logic Pro Flex Pitch to MIDI | 商用DAW機能 | Flex Pitch解析→MIDI track作成 | Logic Proライセンス | 主に単旋律 | MIDI/Score Editor | Mac標準DAW内で完結 | Apple公式も単旋律が最適、和音/ポリフォニーは誤解釈しやすい ([support.apple.com](https://support.apple.com/en-ie/guide/logicpro/lgcpe2fd1b83/mac?utm_source=openai)) |
| 26 | Cubase VariAudio Extract MIDI | 商用DAW機能 | VariAudio解析→MIDI抽出 | Cubase Artist/Pro等 | 主に音程付きオーディオ | MIDI | Cubase内で音程/タイミング修正後にMIDI化 | 事前セグメント修正が必要。譜面清書ではない ([steinberg.help](https://www.steinberg.help/r/cubase-artist/15.0/en/cubase_nuendo/topics/sample_editor_variaudio/sample_editor_variaudio_midi_extract_from_audio_t.html?utm_source=openai)) |
| 27 | Fadr | 商用 | ステム分離、MIDI detection、リミックス、API | Basic無料、Plus `$10/月` または `$100/年` | ボーカル、メロディ、ピアノ、ギター、ドラム、ベース等 | MIDI検出、stems, remix | 無料でもステム/リミックス/MIDI検出 | 採譜PDF/MusicXMLではなく制作補助 ([fadr.com](https://fadr.com/?via=aigregator&utm_source=openai)) |
| 28 | LALAL.AI | 商用/API | ステム分離、ノイズ除去、BPM/Key、音声/歌詞系、API | Starter無料、Lite `$7.5/月`、Pro `$15/月` | vocals, drums, bass, guitar, synth, strings, wind等 | stems中心 | 前処理・分離・APIに強い | 採譜本体ではなく補助。MIDI/MusicXML中心ではない ([lalal.ai](https://www.lalal.ai/pricing/?utm_source=openai)) |
| 29 | Music-To-Sheet | 商用 | 音声→譜面、Demucs分離、polyphonic note detection | Free 60秒、Pro/VirtuososでMIDI/MusicXML | vocals, drums, bass, piano, guitar等 | PDF, MIDI, MusicXML | 入力から譜面まで単純 | 新興。実精度・価格詳細は要検証 ([musictosheet.com](https://musictosheet.com/?utm_source=openai)) |
| 30 | Musirion | 商用/alpha | ソロピアノ→譜面/MIDI/MusicXML | alpha無料、30秒デモ | ソロピアノ、MP3/WAV/M4A/FLAC/動画等 | MIDI, MusicXML | ピアノ特化でシンプル | alpha段階、ソロピアノ限定 ([musirion.ai](https://musirion.ai/?utm_source=openai)) |
| 31 | audio2guitar | 商用 | 音声→ギターTab、コード、歌詞、ステム、MIDI/PDF | Free 3曲、10曲 `$9.99`、月額 `$8.99`、年額 `$59.99` | ギター中心 | Tabs, MIDI, PDF, stems | ギターTab用途が明確、安価 | ギター以外や標準譜フルスコアには狭い ([audio2guitar.com](https://audio2guitar.com/pricing?utm_source=openai)) |
| 32 | AI-MIDI | 商用/無料Web | 音声/動画/録音→MIDI | 無料preview、DLはサインイン | Piano、Guitar beta、Drum予定 | MIDI | シンプルなMIDI化 | 譜面/PDF/MusicXMLなし。品質検証が必要 ([ai-midi.com](https://ai-midi.com/?utm_source=openai)) |
| 33 | Demucs系ツール | OSS/補助 | ステム分離 | 無料/OSS派生多数 | drums, bass, vocals, other等 | stems | 採譜前処理として重要 | 採譜自体はしない ([demucs.app](https://demucs.app/about?utm_source=openai)) |
| 34 | AmazingMIDI | レガシー無料 | WAV→MIDI | 無料、古いWindows系 | 単純音源向け | MIDI | 軽量・無料 | 古く、AI以前、複雑音源には不向き ([chip.de](https://www.chip.de/downloads/AmazingMIDI_12997973.html?utm_source=openai)) |

---

## 2. ユーザー報告の成功例・失敗例

### 成功例

- **Basic Pitch / Spotify公式例**  
  アーティストBad Snacksは、バイオリンソロをBasic PitchでMIDI化し、複数のシンセ音色へ差し替えて楽曲制作に使った。Spotify側も「完全譜面」ではなく、DAWで調整する「出発点」として位置づけている ([basicpitch.spotify.com](https://basicpitch.spotify.com/about?wptouch_preview_theme=enabled&utm_source=openai))。

- **Basic Pitch / ギター録音の応用例**  
  Spotify研究者の例では、ギターのアルペジオ録音をBasic Pitchに通し、デフォルトMIDI、低音だけを抽出したベース、上声部のtoy piano、オンセットを使ったパーカッションなどへ再構成している。つまり「採譜」よりも「制作素材化」に強い ([basicpitch.spotify.com](https://basicpitch.spotify.com/about?wptouch_preview_theme=enabled&utm_source=openai))。

- **Klangio / Sing2Notesの個人成功例**  
  Saxophonforumの投稿では、サックス初心者がPlayalongに合わせて歌ったフレーズをSing2Notesのデモで採譜し、「音程・音価の修正不要」な結果を得た。その後PDFからMusicXML化し、MuseScoreでアルトサックスに移調して使っている ([saxophonforum.de](https://www.saxophonforum.de/threads/erfahrung-mit-klangio-bzw-melody-scanner.69309/?utm_source=openai))。

- **Melody Scanner / 簡単なピアノ曲・学習用途**  
  App Storeレビューには、完全ではないが「ピアノ学習に役立った」「比較的難しいピアノ曲でも思ったより悪くなかった」「簡単なピアノ曲なら試す価値がある」という報告がある ([apps.apple.com](https://apps.apple.com/us/app/melody-scanner/id6472921068?platform=iphone&see-all=reviews&utm_source=openai))。

- **AudioJam / 練習補助としての成功例**  
  Google Playレビューでは、リード/リズムギター分離を評価し、「他のstem appにない」とする報告がある。これは採譜そのものより、耳コピ・練習前処理として価値がある例 ([play.google.com](https://play.google.com/store/apps/details?id=com.kirakuapp.aum&utm_source=openai))。

- **Chordify / コード学習用途**  
  Chordify公式のユーザー引用では、動画を入れるとコードを推定して練習に使える点が評価されている。完全採譜ではなく、コード伴奏・練習用途の成功例 ([chordify.net](https://chordify.net/pages/chordify-app/?utm_source=openai))。

### 失敗例・不満

- **Melody Scanner / 多音・オクターブ誤り**  
  App Storeレビューでは、片手で弾けないほど同時音が増える、2オクターブ離れた不自然な音が出る、アプリ版にも単一楽器モードが欲しい、という具体的な不満がある ([apps.apple.com](https://apps.apple.com/us/app/melody-scanner/id6472921068?platform=iphone&see-all=reviews&utm_source=openai))。

- **Melody Scanner / ハミング失敗**  
  ハミング入力で「長さは合っているが音が大きく外れた」という報告があり、録音環境・マイク・ノイズの影響が大きいことが示唆される ([apps.apple.com](https://apps.apple.com/us/app/melody-scanner/id6472921068?platform=iphone&see-all=reviews&utm_source=openai))。

- **Melody Scanner / 有料後の品質不満**  
  「課金してから低品質な採譜だと分かった」「買った楽譜を使う方が早い」というレビューがあり、無料プレビューと課金導線の設計が重要 ([apps.apple.com](https://apps.apple.com/us/app/melody-scanner/id6472921068?platform=iphone&see-all=reviews&utm_source=openai))。

- **Melody Scanner / 集計レビュー**  
  Chrome Statsのレビュー要約では、長所はYouTube取り込み・手修正・遅く単純な曲での精度、短所は複雑曲/多楽器/音価/編集UI/バグ/録音時間制限と整理されている ([chrome-stats.com](https://chrome-stats.com/d/com.melodyscanner.app/reviews?utm_source=openai))。

- **Basic Pitch / HNでの実務懸念**  
  HNでは「Webサービスが突然有料化/終了するリスク」への懸念が出ており、GitHub版・npm版があることが緩和策として指摘されている ([news.ycombinator.com](https://news.ycombinator.com/item?id=35955934&utm_source=openai))。

- **Ableton Audio-to-MIDI / 速いピアノ和音の失敗**  
  HNコメントでは、AbletonのAudio-to-MIDIが「速いピアノ曲・多音和音」でタイミング、ノート、velocityを誤るという報告がある ([news.ycombinator.com](https://news.ycombinator.com/item?id=35955934&utm_source=openai))。

- **Basic Pitch / Webアップロードの権利・プライバシー懸念**  
  HNでは、Web版に入力した音源やMIDIの権利・保存扱いを気にするコメントがある。OSS版をローカル実行できることは重要な差別化要素 ([news.ycombinator.com](https://news.ycombinator.com/item?id=31595188&utm_source=openai))。

- **Spotify自身の限界認識**  
  SpotifyはBasic Pitchについて、出力品質はまだ人間レベルから遠いと明記している。研究側も「初稿生成」前提で見ている ([newsroom.spotify.com](https://newsroom.spotify.com/2022-09-01/rachel-bittner-on-basic-pitch-an-open-source-tool-for-musicians/?utm_source=openai))。

---

## 3. 採譜ツール/サービスに必要な機能カタログ

### 入力

- ファイル: MP3, WAV, FLAC, M4A, AAC, OGG, MP4, MOV, WEBM
- URL: YouTube、TikTok、Instagram、SoundCloud、直接音源URL
- 録音: ブラウザ/スマホ/マイク入力、リアルタイム録音
- MIDI入力: 既存MIDIの譜面化、MIDI-to-score
- 複数ファイル: パート別stem、リファレンス音源、クリック、歌詞テキスト
- 権利確認: アップロード前の著作権確認、私的利用/教育利用/商用利用の区分

### 前処理

- 音源分離: vocals, drums, bass, guitar, piano, strings, winds, other
- 高度分離: lead/rhythm guitar、lead/backing vocals、kick/snare/toms/hi-hat/cymbals
- ノイズ除去: hiss、hum、クリック、環境音、マイクノイズ
- リバーブ/エコー除去
- 音量正規化、EQ、帯域制限
- テンポ推定、拍位置推定、クリック生成
- キー推定、ピッチ基準A4補正、チューニング推定
- 歪みギター/ライブ音源/低ビットレート圧縮への補正
- 長尺曲の分割、セクション検出、繰り返し検出

### 解析

- ピッチ検出: 単旋律F0、多重F0、ピッチベンド、ビブラート
- オンセット/オフセット検出
- 音価推定、量子化、スイング/シャッフル対応
- 拍子推定: 4/4, 3/4, 6/8, 5/4, 7/8、途中拍子変更
- テンポ変化、ルバート、フェルマータ
- 調号、転調、臨時記号
- コード推定: triad, 7th, tension, slash chord, modal interchange
- メロディ/ベース/内声分離
- 楽器認識、パート割当、音域制約
- ピアノ: 左右手分離、ペダル、voice separation、運指候補
- ギター: Tab、弦/フレット/ポジション、チューニング、カポ、ベンド、スライド、ハンマリング、プリング、ミュート
- ベース: Tab、スラップ、ゴーストノート、ポジション
- ドラム: キック/スネア/タム/ハイハット/シンバル、ゴースト、オープン/クローズHH
- ボーカル: 歌詞認識、音節アラインメント、ブレス/子音、ビブラート処理
- 管弦: アーティキュレーション、奏法、トリル、装飾音
- アンサンブル: パート分離、重複音、ユニゾン、音色が近い楽器の分離

### 出力

- MIDI: quantized/unquantized、velocity、pitch bend、tempo map
- MusicXML/MXL: MuseScore, Sibelius, Finale, Dorico互換
- PDF: 印刷譜、リードシート、パート譜
- Guitar Pro: .gp, .gp5, Tab譜
- DAW: Ableton/Logic/Cubase/FL Studio/Reaper向けMIDI drag/drop
- Stem: WAV/MP3分離音源
- 表示形式: 五線譜、Tab、ピアノロール、コード譜、歌詞付きリードシート
- 移調: 楽器移調、キー変更、カポ反映
- パート別出力: full score、part score、lead sheet、fake book
- バージョン管理: AI初稿、人間修正版、差分、再解析履歴

### 編集UI

- 音源波形・スペクトログラム・ピアノロール・五線譜の同期表示
- 誤検出ノートの追加/削除/分割/結合/移動
- 音価再量子化、拍子/小節線修正
- コード名修正、調号/拍子/テンポ修正
- パート分割/統合、左右手分離修正
- Tab運指修正、チューニング/カポ変更
- オーディオ再生と譜面カーソル同期
- ループ、スロー再生、ピッチ維持タイムストレッチ
- MuseScore/Sibelius/Dorico連携、MusicXML round-trip
- DAW plugin、VST/AU/ARA連携
- Confidence表示、疑わしい小節のハイライト
- 人間校正者向けレビューキュー

### 事業・運用

- 無料プレビュー: 20秒/30秒/60秒など、課金前に精度確認
- 従量課金: 曲数、分数、出力形式、API minute
- サブスク: 個人、教育、プロ、チーム、API
- API: upload、job status、stem separation、AMT、export、webhook
- 著作権: アップロード権利確認、DMCA、出版社ライセンス、私的利用制限
- データ保持: 即時削除、短期保存、学習利用のopt-in/opt-out
- プライバシー: ローカル処理/クラウド処理の明示
- 教育市場: 先生向け課題作成、パート譜配布、LMS連携
- B2B: 楽譜出版社、音楽教室、カラオケ、UGC監視、音楽アーカイブ
- 品質保証: 楽器別ベンチマーク、ジャンル別評価、編集時間削減率

---

## 4. 技術的な現状の限界

### 根本的な難しさ

- **混合音源からの完全採譜は未解決**  
  同時に鳴る複数楽器、同音ユニゾン、倍音の重なり、ドラム/歪み/リバーブがあると、音源分離とピッチ推定の誤差が連鎖する。

- **MIDI化と譜面化は別問題**  
  MIDIは「いつ、どの高さの音が鳴ったか」だが、譜面は「拍子、調、声部、運指、記譜規則、読みやすさ」を含む。AIがMIDIを当てても、読みやすいMusicXML/PDFになるとは限らない。

- **リズム・小節線・拍子が難しい**  
  ルバート、ライブ演奏、テンポ揺れ、シャッフル、変拍子、ポリリズムでは量子化が崩れやすい。Abletonも高品質/孤立音源を推奨している ([ableton.com](https://www.ableton.com/en/live-manual/11/converting-audio-to-midi/?utm_source=openai))。

- **単旋律と多声音楽の差が大きい**  
  Logic ProはFlex PitchからMIDI化できるが、公式に単旋律が最適で、和音/ポリフォニーは誤解釈しやすいとしている ([support.apple.com](https://support.apple.com/en-ie/guide/logicpro/lgcpe2fd1b83/mac?utm_source=openai))。

- **ギターTabは音高だけでは決まらない**  
  同じ音を複数の弦/ポジションで弾けるため、運指、チューニング、カポ、奏法、手癖を推定する必要がある。

- **ドラムは音高より音色分類が難しい**  
  キック/スネアは比較的強いが、ゴーストノート、ハイハット開閉、シンバルの重なり、ルーム音が問題になる。

- **歌詞と音符の統合はまだ難しい**  
  歌詞認識、音節分割、母音/子音/ブレス、メリスマ、複数ボーカルをMusicXMLに整合させる必要がある。

---

## 5. 最新研究動向（2024-2026）

### 2024

- **調査研究の整理**  
  2024年の包括レビューは、機械学習系AMT論文65本を対象に、手法・性能・データセットを整理している。AMTが単一技術ではなく、ピッチ、オンセット、楽器分離、記譜変換、データセット設計の複合問題であることが明確になっている ([publisher.resbee.org](https://publisher.resbee.org/mr/archive/v7i1/a1.html?utm_source=openai))。

- **Transkun V2 / Transformer + Semi-CRF**  
  Transkunは、フレーム単位予測からイベント区間スコアリングへ寄せる設計で、2024年にはTransformer化したV2を提示。ピアノAMTでは、オンセット/オフセット/velocity/ペダルに近い表現を高精度に扱う方向が進む ([github.com](https://github.com/yujia-yan/transkun?utm_source=openai))。

- **YourMT3+**  
  MT3系を一般利用・HuggingFace demoへ寄せる試み。多楽器/マルチトラックAMTを研究室外で動かしやすくする流れがある一方、YouTube入力など外部依存はブロックや認証で不安定 ([github.com](https://github.com/mimbres/YourMT3?utm_source=openai))。

### 2025

- **音源分離との結合が実用側で標準化**  
  Music-To-Sheetのように、Demucs系ステム分離を前処理に置き、その後ポリフォニック検出で譜面化する設計が増えている ([musictosheet.com](https://musictosheet.com/?utm_source=openai))。Moises、AudioJam、Fadr、LALAL.AIも、採譜前の分離・コード・BPM・キー推定を商品化している ([moises.ai](https://moises.ai/products/moises-app/?utm_source=openai)) ([audiojam.app](https://audiojam.app/features/?utm_source=openai)) ([fadr.com](https://fadr.com/?via=aigregator&utm_source=openai)) ([lalal.ai](https://www.lalal.ai/pricing/?utm_source=openai))。

- **譜面だけでなく、練習・制作ワークフローへ拡張**  
  単なるPDF生成ではなく、ABループ、ピッチ/テンポ変更、ステムミキサー、DAW drag/drop、Tab player、コード同期などが差別化要素になっている。

### 2026

- **MuScriptor: open-weight multi-instrument AMT**  
  2026年のMuScriptorは、一般目的・多楽器・オープンウェイトAMTモデルとして提示され、small/medium/largeの複数サイズを持つ。商用SaaSに閉じない多楽器AMT基盤として注目度が高い ([huggingface.co](https://huggingface.co/MuScriptor/muscriptor-large?utm_source=openai))。

- **Cross-modal Transformer / 長期依存の扱い**  
  AMT-CMTは、従来の単一音声入力モデルが複雑なリズム構造や長期依存に弱いことを課題とし、クロスモーダルTransformerで改善を狙う研究として発表されている ([sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S0957417426023444?utm_source=openai))。

- **画像+音声のマルチモーダル採譜**  
  2026年のマルチモーダルTransformer研究では、楽譜画像と音声を組み合わせることで特定のポリフォニック採譜ケースが改善する一方、画像単独が強いベースラインであり、融合方法によって差が出ると報告されている ([sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S1568494626000918?utm_source=openai))。

- **歌詞付き採譜の形式化**  
  Aligned Music Notation and Lyrics Transcriptionでは、音符と歌詞のアラインメント課題を formalize し、データセットと評価指標を提案している。ボーカル採譜は「音高だけ」から「歌詞・音節・譜面同期」へ広がっている ([sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S003132032500754X?utm_source=openai))。

- **サービス継続性がリスクとして顕在化**  
  Samplabは2026年9月17日でサービス停止予定を公表している。クラウド解析型の採譜/音声編集サービスでは、モデル精度だけでなく、終了時のデータ移行、オフライン版、返金、API継続が重要な評価軸になる ([samplab.com](https://samplab.com/?__sl_c=metapromo7))。

---

## 6. 参入機会

- **最も現実的なMVP**  
  「フルミックス完全採譜」ではなく、`アップロード/YouTube → stem分離 → 楽器選択 → MIDI/MusicXML/PDF/Tab初稿 → 疑わしい小節ハイライト → MuseScore連携` が現実的。

- **差別化しやすい領域**  
  ギターTabの運指最適化、ピアノ左右手分離、歌詞アラインメント、ドラム詳細記譜、教育向け難易度調整、出版社/教室向け権利処理、API提供。

- **避けるべき訴求**  
  「どんな曲も完璧に採譜」はレビュー炎上しやすい。成功している表現は「下書き」「数分で始める」「編集して仕上げる」「練習用」「DAW素材化」。

- **プロダクト要件の優先順位**  
  1. 精度確認用の無料短尺プレビュー  
  2. MusicXML/MIDI/PDF/Tabの堅実な出力  
  3. 人間が直しやすい編集UI  
  4. stem分離と楽器別モデル  
  5. 著作権・データ保持・ローカル/クラウド方針の明示  
  6. DAW/MuseScore/Songsterr/Guitar Pro連携  

- **結論**  
  2026年時点の勝ち筋は、万能AI採譜ではなく、**対象楽器・入力条件・出力ワークフローを絞った「修正しやすい採譜初稿エンジン」**。単一楽器やTab/コード/練習補助から入り、音源分離・歌詞・マルチモーダル研究を段階的に統合するのが最も実装リスクが低い。
