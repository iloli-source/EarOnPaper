# F-109 share-visual-card 調査メモ

対象: 採譜 / Pitchsieve の「share-visual-card」機能。音声波形に抽出ノート、ピッチラベル、簡易ピアノロールを重ね、SNSで共有しやすい静止画または短尺動画を生成する。

調査日: 2026-07-21  
検索方針: 英語・中国語ソースを優先。実装できる技術よりも、失敗ケース、見落としやすい仕様差、SNSで壊れる条件を多めに列挙する。

## 要点

- 波形カードは「ブラウザ Canvas/Web Audio」「サーバー/端末内 ffmpeg」「事前ピーク生成 + SVG/Canvas」「Remotion 等のコード生成動画」の4系統が現実的。Pitchsieve では再現性とSNS書き出しを優先し、最終レンダリングは ffmpeg/Remotion 系に寄せるのが安全。
- 波形と音符を同じ面に重ねると、音量ピーク、ノート密度、ピッチラベル、字幕、SNS UI が互いに隠し合う。色だけで意味を分ける設計、低コントラスト、細い線、1px のタイミング差は小画面と再圧縮で破綻しやすい。
- SNS共有では、同じ素材を 1:1、9:16、16:9 に機械クロップするとほぼ必ずどこかで重要情報が切れる。OGP/Twitter Card は画像キャッシュも失敗源になるため、画像URLのバージョニングと事前検証が必要。

## 1. Audiogram / waveform card の生成方式

### 1.1 ブラウザ / オンデバイス Canvas + Web Audio

利用候補:

- Web Audio API `AnalyserNode`: 音声ストリームから時間領域/周波数領域データを取得して Canvas に描画できる。
- wavesurfer.js: Web Audio / HTML5 Audio を使う対話型波形ライブラリ。v7系は Canvas を Shadow DOM 内に描画し、Regions、Timeline、Spectrogram などのプラグインを持つ。
- Peaks.js: BBC R&D 系。Canvas でズーム可能な波形を表示し、ポイント/セグメントマーカーを扱える。
- waveform-data.js: BBC 系。事前生成済み波形データ、または Web Audio API からの波形データを扱う JS ライブラリ。

失敗ケース:

- **長い音声をブラウザで丸ごとデコードして固まる**  
  wavesurfer.js のトラブルシューティングでは、Web Audio API は完全な音声ファイルが揃わないとデコードとピーク生成ができず、ストリーミング的な逐次描画はできないとされている。3分以上の演奏やスマホ低メモリ端末では、ローディング待ち、メモリ不足、タブ強制終了が起きる。
  - 回避: 共有カード生成ではブラウザ即時計算に頼らず、Pitchsieve の解析結果と同時にピークデータを事前生成する。プレビューだけ wavesurfer.js、最終書き出しはサーバー/ネイティブ/worker 側に分離する。

- **codec / container 非対応で波形だけ出ない**  
  Safari の Ogg / FLAC / WAV シーク問題、ブラウザ内蔵デコーダ差、CORS で `decodeAudioData` が失敗する。再生できても Canvas 解析できない場合がある。
  - 回避: 入力は MP3/AAC/WAV に正規化し、最終生成では ffmpeg に寄せる。リモート音声を解析する場合は CORS と `Access-Control-Allow-Origin` を明示する。

- **隠れた要素内で初期化して Canvas サイズが0になる**  
  wavesurfer.js は親要素の高さがない、`display: none` 内で初期化、DOM準備前に作成、などで波形が表示されない。
  - 回避: プレビューコンテナに固定高さを与え、可視化後に初期化する。タブ/モーダル内では表示後に再レンダリングする。

- **React Strict Mode で波形が二重生成される**  
  wavesurfer.js は React 18 開発モードで `useEffect` が二重実行され、cleanup 不備だとインスタンスが残って二重描画やプラグイン不具合が起きる。
  - 回避: `destroy()` を必ず cleanup に入れる。プレビュー/書き出し用レンダラーを分け、共有画像生成は React ライフサイクルに依存させない。

- **`timeupdate` イベントで音符カーソルを動かすと時間が粗い**  
  MDN では `timeupdate` は負荷に応じて約4Hzから66Hz。30fps/60fps動画に重ねるノート表示には粗く、演奏音とノートバーがカクつく。
  - 回避: プレビューは `requestAnimationFrame` と `audio.currentTime` を併用。書き出しはフレーム番号から時刻を決定し、`frame / fps` を唯一の時間軸にする。

- **オンデバイス生成は録音/解析/描画/エンコードが端末性能に引きずられる**  
  Canvas録画、WebCodecs、MediaRecorder はブラウザ差がある。色空間、フォント、アンチエイリアス、フレーム落ちでユーザーごとに出力が変わる。
  - 回避: SNSに出す本番カードは deterministic renderer で生成し、端末内処理を使う場合もフォント埋め込み、固定fps、固定サイズ、同一コーデックにする。

### 1.2 ffmpeg ベース

利用候補:

- `showwaves` / `showwavespic`: 音声から波形動画/静止画を生成。
- `showspectrum`: 周波数スペクトラム動画を生成。
- `filter_complex`: 背景、波形、ピアノロールPNG/SVG、字幕、ロゴ、進捗バーを合成。
- `drawtext`, `overlay`, `scale`, `pad`, `fps`, `format`, `setsar`, `aresample`: SNS向けの固定解像度/固定fps/同期調整に使う。

失敗ケース:

- **showwaves は「音量の形」は出るが、音高情報は出ない**  
  Pitchsieve の価値である絶対音感エミュレーション/抽出音符は別レイヤーで描く必要がある。波形だけを派手にすると、ノート情報が添え物になる。
  - 回避: 波形は低彩度・低優先度の背景情報にし、ノートバー/ピッチ名/現在音を主役にする。

- **ピーク波形の正規化で曲ごとの見た目が揃わない**  
  小さい音の素材はベタっと平坦、大音量素材はノートを覆う。正規化を強くすると静かな音まで太く見えて、音量感が嘘になる。
  - 回避: `peak` の最大値だけでなく、RMS/percentile で表示ゲインを決める。波形の高さ上限をカード高さの20-30%程度に制限し、ノート帯域を侵食させない。

- **固定fps化を怠ると波形・字幕・ノートの同期がずれる**  
  VFR素材、スマホ録音、動画から抽出した音声ではタイムスタンプが不安定になりやすい。`timeupdate` ベースのプレビューと ffmpeg 書き出しのfpsが違うと、短尺でも数フレームずれる。
  - 回避: 生成時に `fps=30` または `fps=60`、`setpts`, `aresample=async=1`、`-vsync` / `-fps_mode` を明示。全レイヤーを「秒」ではなく「サンプル index / hop size / fps」の変換表から描く。

- **`drawtext` のフォント差で日本語ピッチラベルが豆腐化する**  
  サーバーや端末に日本語フォントがないと、C#、Bb、ド、レ、ミ、オクターブ番号が欠落する。
  - 回避: Noto Sans JP / Noto Music 等を同梱し、ffmpeg `fontfile` を指定。絵文字や特殊記号に頼らない。

- **細線/低ビットレートでノートバーが潰れる**  
  1px罫線、薄いグリッド、細い現在位置ラインはSNS再エンコードで消える。
  - 回避: 線幅は出力1080px基準で2-4px以上、ラベル縁取り、半透明背景、ノートバー最小高さを確保する。

- **ffmpeg のフィルタグラフが複雑化して保守不能になる**  
  `overlay` と `drawtext` を大量に組み合わせると、後からレイアウトを変えるたびに壊れる。
  - 回避: ノート/ラベル/グリッドはSVGまたはPNG連番として別レンダリングし、ffmpeg は合成とエンコードに限定する。テンプレートごとに中間レイヤーを保存してデバッグ可能にする。

### 1.3 事前ピーク生成 + SVG / Canvas

利用候補:

- BBC audiowaveform: MP3/WAV/FLAC/Ogg/Opus から最小/最大ピークを生成し、DAT/JSON/PNGへ出力。`--pixels-per-second`、開始/終了、サイズ、バー表示などを指定できる。
- waveform-data.js: audiowaveform のJSON/DATをブラウザで読み、ズーム/セグメント操作に使える。
- `waveform-path`: 音声サンプルから SVG path を生成する軽量ライブラリ。
- 自前SVG: 解析済みピーク配列を `<path>` / `<rect>` として描画し、ピッチノートもSVGで重ねる。

失敗ケース:

- **SVGは静止画カードには強いが、動画ではフレーム大量生成が重い**  
  1フレームごとにSVGを作ってラスタライズすると、短尺でも数百枚になる。透明やフィルタを使うとCPU負荷が跳ねる。
  - 回避: 背景波形は静的SVG/PNGにし、動く要素は現在位置カーソル、強調ノート、字幕だけに限定する。長いピアノロールスクロールは canvas/Skia/Remotion で描く。

- **波形ピークの解像度が粗いとオンセット位置がノートより遅れて見える**  
  audiowaveform はNサンプルごとのmin/maxを出す。`--zoom` や `--pixels-per-second` が粗いと、アタックの見た目とPitchsieveのオンセットが一致しない。
  - 回避: 共有動画の横幅と時間長から必要ppsを逆算する。例: 1080pxで15秒なら72px/s以上。ノート同期確認用にオンセット縦線を表示できるデバッグモードを持つ。

- **ステレオ/位相の扱いで波形の印象が変わる**  
  audiowaveform はデフォルトでチャンネルをモノラル合成してピーク計算する。左右に分かれた楽器、位相反転、片チャンネルだけの録音では、見た目が実際の聴感とずれる。
  - 回避: `--split-channels` を検討し、SNSカードでは左右合成より「最大振幅包絡」や「RMS包絡」など意図を決める。

- **SVGのアンチエイリアス差でOGP画像がにじむ**  
  ブラウザ、librsvg、Sharp、Skia、ImageMagick で線の丸めが変わる。
  - 回避: 最終PNG/MP4は同じレンダラーで作る。SVGを配布物にせず、OGPは必ずラスタライズ済みPNG/JPEGを指定する。

### 1.4 Remotion / コード生成動画

利用候補:

- Remotion template-audiogram: podcast等の音声をSNS向けaudiogram動画にするテンプレート。
- Remotion `@remotion/media-utils`: `getAudioData()` / `useAudioData()` / `visualizeAudioWaveform()` により音声データを読み、Reactコンポーネントとして動画をレンダリングできる。

失敗ケース:

- **Reactで見た目を組みやすい反面、レンダリング時間とメモリが増える**  
  波形、ノート、字幕、スペクトラム、背景画像を全部Reactコンポーネント化すると、レンダリングが遅くなる。
  - 回避: 波形とノート密度の高い部分は事前ラスタライズ、テキスト/カーソルだけReactで動かす。テンプレート単位でキャッシュする。

- **プレビューと最終出力の差分が出やすい**  
  ブラウザプレビューはGPU/フォント/デバイスピクセル比に依存し、Remotion CLI出力と微妙にズレる。
  - 回避: 共有カードは「プレビュー = 最終レンダラーの低解像度版」にする。スクリーンショットではなく同一パイプラインで生成する。

## 2. 波形 + 音符オーバーレイの視認性・レイアウト失敗

### 2.1 オクルージョン / 密度

失敗ケース:

- **大きい波形ピークがノートバーやラベルを覆う**  
  ギターのストローク、ピアノの強打、ドラム混入などで波形が画面中央まで伸び、上に置いた C4 / F#5 ラベルが読めない。
  - 回避: 波形は専用レーンに閉じ込める。ノートバーと波形を完全同一Y領域に重ねる場合は、波形の不透明度を20-35%に落とし、ノートに縁取り/背景チップを付ける。

- **音数が多い区間でピッチラベルが団子になる**  
  速弾き、ビブラート、装飾音、和音でラベルが重なる。音名をすべて表示すると、波形もピアノロールも読めなくなる。
  - 回避: ラベル表示ルールを持つ。例: 現在音のみ大きく表示、長さが150ms未満の音はラベル省略、同一音名連続は最初だけ表示、重なり検出で優先度の低いラベルを隠す。

- **ピアノロールY軸と波形Y軸の意味が混ざる**  
  波形の上下は振幅、ピアノロールの上下は音高。両方を同じ高さに置くと、ユーザーが「波形の高い場所 = 高音」と誤読する。
  - 回避: ノートは明確なピッチグリッド上に置き、波形は背景帯または下部レーンに分ける。重ねる場合もピッチ軸ラベル、薄い鍵盤ガイド、または上下の意味差を示す視覚文法を入れる。

- **和音が垂直方向に詰まり、小さいカードで音程差が消える**  
  1:1や9:16の小さいプレビューでは、半音差のバーが1-2pxしか離れず、CとC#が同じ線に見える。
  - 回避: SNS用カードでは全音域を表示しない。検出ノートの範囲に合わせてピッチ窓を自動ズームし、最小レーン高を確保する。

- **オンセット縦線、拍グリッド、カーソル、ノート境界が全部同じ細線になる**  
  意味の異なる線が同じ太さ/色だと、どれが現在位置か分からない。
  - 回避: 線の役割ごとに階層を分ける。現在位置は太く高コントラスト、拍グリッドは薄い破線、ノート境界はバー形状で示す。

### 2.2 コントラスト / 色覚 / 圧縮耐性

失敗ケース:

- **色だけで音名や正誤を表す**  
  WCAGの「Use of Color」は、色だけで情報を伝えることを避ける。赤/緑や青/紫だけで音程、正誤、信頼度を表すと色覚多様性で破綻する。
  - 回避: 色に加えて形、線種、アイコン、ラベル、明度差を併用する。信頼度は彩度だけでなく透明度、ドット/斜線、バー高さ補助で示す。

- **通常テキストのコントラスト不足**  
  WCAG AAでは通常テキスト 4.5:1、大きいテキスト 3:1 が目安。波形の上に薄い白文字、背景写真の上に細い音名を置くと読めない。
  - 回避: ピッチラベルは常に背景チップまたは縁取り付きにする。波形、写真、グラデーション上の文字はスクリーンショットでコントラスト計測する。

- **非テキスト要素のコントラスト不足**  
  ノートバー、カーソル、選択範囲、鍵盤ガイドは「画像の一部」だが実質UI情報。WCAG non-text contrast の3:1を満たさないと小画面で消える。
  - 回避: 重要なノートバーと背景の明度差を3:1以上にする。波形は背景扱いにして主情報より低コントラストにする。

- **SNS再エンコードで赤/青の細線が色にじみする**  
  H.264のクロマサブサンプリング、低ビットレート、スマホ表示の縮小で、彩度の高い細線や小さい文字がにじむ。
  - 回避: 小さい音名は白/黒ベース + 色アクセントにする。彩度だけに頼らず、線幅、塗り、縁取り、余白を確保する。

- **背景写真やジャケット画像と波形/音符が競合する**  
  写真の細部、顔、明暗差が波形・ノートと同じ領域にあると読めない。
  - 回避: 背景はブラーではなく、暗幕/明幕の単純な面を敷く。主表示領域に写真の高周波ディテールを置かない。

### 2.3 小画面 / 共有サムネイル

失敗ケース:

- **1080pxでは読めるが、フィード内300px幅で読めない**  
  SNSフィードではカードが縮小表示される。ピッチ名、BPM、キー、信頼度、採譜タイトルを全部載せると潰れる。
  - 回避: 300px幅相当の縮小プレビューで判定する。共有カードには「曲名/短いフレーズ名」「現在音/主要ノート」「波形 + ノートの形」だけを残す。

- **縦動画で下部UIに音名や字幕が隠れる**  
  TikTok/Instagram/LINE VOOM では下部にキャプション、CTA、操作ボタンが乗る。ボトムにピアノロールや字幕を置くと見えない。
  - 回避: 9:16では重要情報を中央60-70%に置く。下部は余白または背景波形だけにする。

- **日本語、英字音名、シャープ/フラット混在で文字幅が読めない**  
  `C#4`, `Bb3`, `ソ#`, `ファ♯` は幅が異なる。カード幅が小さいと重なりやすい。
  - 回避: SNS表示は音名体系を1つに固定する。シャープ/フラットは ASCII `#` / `b` を基本にし、必要なら設定で日本語階名を選ぶ。

- **タップ対象や操作UIが小さすぎる**  
  生成前プレビューで範囲選択・テンプレ選択を行う場合、WCAG 2.2 の Target Size Minimum は24x24 CSS px。音符マーカーを小さくしすぎると編集できない。
  - 回避: 共有「画像」内のマーカーと、編集UIのタップ領域を別設計にする。編集UIは24px以上、カード内の視覚要素はSNS縮小耐性を優先する。

### 2.4 時間軸 / 採譜結果との同期

失敗ケース:

- **Pitchsieveのオンセットと波形ピークが数十msずれるだけで「採譜が間違って見える」**  
  AMT評価ではオンセット許容差として50ms程度がよく使われるが、視覚カードでは縦線が波形アタックから1-2フレームずれるだけで違和感が出る。
  - 回避: 解析時のhop size、サンプルレート、入力トリム、書き出しfpsをメタデータ化する。レンダリングでは `onsetSec = sampleIndex / sampleRate` を基準にする。

- **無音トリム/先頭パディングで全部ずれる**  
  入力時に無音除去、ノーマライズ、動画から音声抽出、mp3 encoder delay が入ると、音声ファイルと採譜結果の原点が変わる。
  - 回避: 解析前後の音声を同一ファイルIDで追跡し、トリム量/encoder delay/offsetを保存する。共有カード生成時に音声とノートJSONのduration差を検証して警告する。

- **ノートoffsetは曖昧で、バー長が不自然に見える**  
  AMTではpitch/onset/offsetが基本要素だが、offsetは曖昧で評価から省略されることもある。音が減衰する楽器では「音が続いているように見える/切れすぎる」問題が起きる。
  - 回避: 共有カードではバー長を厳密な音価として見せすぎない。信頼度が低いoffsetはフェードアウト、丸端、短い尾で表現する。

- **ビブラートやポルタメントを離散音符にしすぎて見た目が汚れる**  
  歌声、弦、管楽器ではピッチが連続的に揺れる。半音ごとのノートバーに量子化すると、細かい階段状ノイズが出る。
  - 回避: ボーカル/単旋律ではピアノロールバーではなくピッチカーブ表示を選べるようにする。音名ラベルは安定区間だけに出す。

- **ノイズ由来の誤検出をSNSカードで強調してしまう**  
  小さい誤ノートまで鮮やかに描くと、Pitchsieveの品質が悪く見える。
  - 回避: 信頼度・最小持続時間・音量閾値で共有カード専用にフィルタする。解析詳細画面とは別に「見せるための簡約」を行う。

## 3. SNS共有フォーマットの落とし穴

### 3.1 アスペクト比 / クロップ

推奨プリセット:

- Square: 1080x1080, 1:1。X/Instagram feed/LINE向けの汎用。
- Vertical: 1080x1920, 9:16。TikTok/Instagram Reels/Stories/Shorts/LINE VOOM向け。
- Landscape: 1920x1080 または 1280x720, 16:9。X、YouTube、埋め込み、横長OGP向け。
- OGP/Twitter Card用静止画: 1200x630 付近の 1.91:1 も別生成する。1:1や9:16をそのままOGPに使うとクロップされやすい。

失敗ケース:

- **1つのマスターから自動クロップして音符が切れる**  
  9:16で中央に置いた縦長ピアノロールを1:1に切ると上下情報が消える。16:9に切ると左右の時間軸が消える。
  - 回避: アスペクト比ごとにレイアウトを再計算する。クロップではなく「同じデータを別構図で再レンダリング」する。

- **OGPに正方形画像を指定してカードが小さくなる/切れる**  
  Xの `summary_large_image` は横長比率前提の実装が多く、正方形や縦長画像は期待通りに出ないことがある。
  - 回避: OGP/Twitter Cardは専用 1200x630 / 1200x628 を生成。`og:image:width`, `og:image:height`, `twitter:card=summary_large_image` を明示する。

- **縦動画のセーフゾーン外にタイトル/現在音/CTAを置く**  
  TikTok公式は9:16推奨、540x960以上、最大10分/500MBなどを示し、safe zoneは寸法やキャプション長、追加形式で変わると説明している。Instagram/MetaもStories/Reelsでテキスト・ロゴを端から離す必要がある。
  - 回避: 9:16では上部約14%、下部20-35%、左右6-13%程度を「危険帯」として扱い、重要情報を中央に寄せる。最終確認は各SNSのプレビューで行う。

- **LINE系では縦動画が3:4表示になり上下が隠れる場合がある**  
  LINE Ads Platform の資料では、縦動画は3:4表示時に上下が隠れ、タップ後に9:16全画面になるケースが示されている。
  - 回避: LINE向け縦動画は上下に重要情報を置かない。タイトルや音名は中央3:4内に収める。

### 3.2 再エンコード / 圧縮 / ファイル制限

失敗ケース:

- **SNS再圧縮で波形やラベルが読めなくなる**  
  X Media Studio はH.264、AAC、推奨5-8Mbps、最大60fpsなどを示す。TikTokは広告素材で.mp4/.mov等、500MB以下、516kbps以上など。Instagram Reels広告は最大4GBなど。アップロード後も各プラットフォーム側で再圧縮される。
  - 回避: 元動画は高めビットレートで出すが、細線に頼らない。`yuv420p`, H.264, AAC, progressive, fixed frame rate を基本にする。

- **音声波形なのに音声がミュート/自動再生されない**  
  Chromeのポリシーではmuted autoplayは許可されるが、音付き自動再生はユーザー操作やMedia Engagement等に依存する。SNSフィードでも最初はミュート再生が多い。
  - 回避: 音がなくても意味が伝わるように、現在音名、短い説明、必要なら字幕/キャプションを焼き込む。最初の1秒に視覚的な変化を置く。

- **ファイルサイズ上限に合わせるために低ビットレート化しすぎる**  
  ノートラベルは低ビットレートで真っ先に壊れる。波形の細いバーや薄いグリッドがモスキートノイズ化する。
  - 回避: 15秒以内の短尺を基本にし、余計な背景動画や粒状テクスチャを避ける。静止背景 + 限定的な動きで圧縮効率を上げる。

- **フレームレートが高すぎて再圧縮で劣化する**  
  60fpsは滑らかだが、同じファイルサイズなら1フレームあたりの品質が落ちる。
  - 回避: 波形/ノートカードは30fpsを標準にする。ピッチカーブやカーソルだけなら30fpsで十分。60fpsはアプリ内プレビューや高品質保存に限定する。

- **サムネイルの縦横比が動画と違い、再生前に不自然な余白や背面画像が出る**  
  LINE Messaging API は動画とプレビュー画像のアスペクト比が違うと、プレビュー画像が背面に見える場合があると説明している。X Media Studio も動画と異なるサムネイル比率は再生問題につながるとする。
  - 回避: 動画とサムネイルは同一アスペクト比で生成する。サムネイルもsafe zone対応済みのフレームから作る。

### 3.3 UIオーバーレイ / セーフゾーン

失敗ケース:

- **TikTokの右側ボタン列にピッチラベルが隠れる**  
  いいね、コメント、共有、音源表示が右側や下部に重なる。波形を右寄せ、ピッチ軸を右に置くと読めない。
  - 回避: 右端は装飾だけにする。ピッチ軸や凡例は左または中央寄りに置く。

- **Instagram Reels/Storiesのプロフィール名、キャプション、CTAで下部が隠れる**  
  Meta公式のsafe zone情報では、9:16広告の端にテキスト/ロゴを置かないよう案内されている。
  - 回避: 下部に音名一覧や字幕を置かない。字幕は中央下ではなく中央やや上、ピアノロールは中央帯に配置する。

- **Xタイムラインのクロップ/プレビューで縦動画が小さく見える**  
  Xは横長・正方形・縦長を扱えるが、タイムライン表示と詳細表示で見え方が変わる。
  - 回避: X向けは1:1または16:9を優先し、縦動画はTikTok/Instagram専用と割り切る。X用サムネイルを別生成する。

- **LINEチャット内プレビューで極端な縦横比がクロップされる**  
  LINE Messaging API は非常に広い/高い動画が一部環境でクロップされ得ると明記している。
  - 回避: LINE共有は1:1または16:9を標準にし、9:16はVOOM/広告等の用途に限定する。

### 3.4 OGP / Twitter Card / キャッシュ

失敗ケース:

- **画像を差し替えてもSNSカードが古いまま残る**  
  Facebook Sharing Debugger はOGタグのプレビュー/デバッグに使える。X/Twitter Card はキャッシュ更新が不安定という開発者フォーラム報告が多く、Card Validatorの挙動変更もある。
  - 回避: `og:image` / `twitter:image` のURLにコンテンツハッシュやversion queryを付ける。画像を上書きせず新URLにする。

- **相対URL、認証付きURL、WebP/AVIF、リダイレクト過多でクローラが画像を取れない**  
  SNSクローラはログイン必須URL、短時間署名URL、相対パス、サイズ過大、未対応形式で失敗する。
  - 回避: OGP画像は公開HTTPSの絶対URL、JPEG/PNG、5MB未満を目安にする。`curl -I` と各デバッガで確認する。

- **同じURLでユーザーごとに画像を変えるとキャッシュが混線する**  
  SNSクローラはURL単位でカードをキャッシュする。ユーザーAの採譜画像がユーザーBの共有に出るリスクがある。
  - 回避: 共有カードURLは成果物IDごとに一意にする。ユーザーごとの署名付きURLを `og:image` に使わない。削除/非公開時の挙動も設計する。

- **OGP静止画と投稿動画の内容が違って誤解を招く**  
  OGP画像が古い波形、動画が別テイクだと信頼を落とす。
  - 回避: 同じ render manifest から動画、サムネイル、OGP画像を生成し、manifest hashをURLに含める。

## 推奨アーキテクチャ

### MVP

- 入力音声を ffmpeg で標準化: AAC/MP3/WAV、サンプルレート固定、先頭offset記録。
- Pitchsieve のノートJSONに `sampleRate`, `hopSize`, `analysisOffsetSec`, `durationSec`, `confidence` を入れる。
- 波形ピークは audiowaveform または自前RMS/peakで事前生成。
- 共有カードは3プリセットを別レンダリング:
  - `square_1080`: feed汎用
  - `vertical_1080x1920`: Reels/TikTok/Shorts/VOOM
  - `og_1200x630`: OGP/Twitter Card
- ノート表示は「共有用簡約」を通す:
  - 最小長 120-150ms 未満はラベル省略
  - 低confidenceは薄くするか非表示
  - ラベル重なり時は現在音/長い音/高confidenceを優先
- 最終出力:
  - 静止画: PNG/JPEG
  - 動画: MP4 H.264 + AAC, 30fps, yuv420p, fixed frame rate

### 実装時チェックリスト

- 300px幅サムネイルでも主要音名が読めるか。
- 波形なし、ほぼ無音、過大音量、クリップ音源、片チャンネル音源で破綻しないか。
- 15秒、30秒、60秒でファイルサイズと生成時間が許容内か。
- C4-C6の狭い音域、C1-C8の広い音域、半音階連打、和音密集でラベルが破綻しないか。
- 1:1/9:16/16:9/1.91:1をクロップではなく再レイアウトしているか。
- 色覚シミュレーション、グレースケール、低輝度画面で意味が残るか。
- TikTok/Instagram/LINE/XのUIオーバーレイを模したsafe zoneプレビューがあるか。
- OGP画像URLがユニークで、公開HTTPS、JPEG/PNG、適正サイズか。
- 生成manifestから動画/サムネ/OGPを再現できるか。

## 参考URL

### 実装方式 / 波形生成

- WNYC / NY Public Radio Audiogram: https://github.com/nypublicradio/audiogram
- FFmpeg Filters Documentation: https://ffmpeg.org/ffmpeg-filters.html
- FFmpeg Waveform wiki: https://trac.ffmpeg.org/wiki/Waveform
- BBC audiowaveform: https://github.com/bbc/audiowaveform
- BBC waveform-data.js: https://github.com/bbc/waveform-data.js/
- BBC Peaks.js: https://github.com/bbc/peaks.js/
- wavesurfer.js docs: https://wavesurfer.xyz/docs/
- wavesurfer.js troubleshooting: https://wavesurfer.xyz/docs/troubleshooting/
- Remotion audiogram template: https://github.com/remotion-dev/template-audiogram
- Remotion audio visualization: https://www.remotion.dev/docs/audio/visualization
- Remotion visualizeAudioWaveform: https://www.remotion.dev/docs/media-utils/visualize-audio-waveform
- waveform-path SVG generator: https://github.com/jerosoler/waveform-path
- MDN AnalyserNode: https://developer.mozilla.org/en-US/docs/Web/API/AnalyserNode
- MDN requestAnimationFrame: https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame
- MDN HTMLMediaElement timeupdate: https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/timeupdate_event
- 中国語 wavesurfer.js 解説例: https://juejin.cn/post/6979191645916889095
- 中国語 FFmpeg showwaves 解説例: https://www.dayanzai.me/ffmpeg-create-waveform.html

### 視認性 / 採譜 / 評価

- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- WCAG Use of Color: https://www.w3.org/WAI/WCAG20/Understanding/use-of-color
- WCAG Contrast Minimum: https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html
- WCAG Non-text Contrast: https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast.html
- WCAG Target Size Minimum: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum
- Color Universal Design: https://jfly.uni-koeln.de/color/
- mir_eval documentation: https://mir-eval.readthedocs.io/
- mir_eval paper PDF: https://archives.ismir.net/ismir2014/paper/000320.pdf
- AMT perceptual validity paper: https://transactions.ismir.net/articles/10.5334/tismir.57
- Automatic Music Transcription overview PDF: https://labsites.rochester.edu/air/publications/benetatos19automaticmusic.pdf
- Data Object and Label Placement paper PDF: https://www.cs.umd.edu/~ben/papers/Li1998Data.pdf
- Clutter-Aware Label Layout PDF: https://shixialiu.com/publications/Clutter/paper.pdf

### SNS / OGP / 配信仕様

- X Media Studio FAQ: https://help.x.com/en/using-x/media-studio-faqs
- X Developer Community Cards: https://devcommunity.x.com/c/publisher/cards/8
- X Card cache discussion: https://devcommunity.x.com/t/without-validator-anymore-how-are-we-supposed-to-re-cache-a-links-card-image/183993
- Meta Sharing Debugger: https://developers.facebook.com/tools/debug/
- Meta Images in Link Shares: https://developers.facebook.com/documentation/sharing/webmasters/images
- Open Graph protocol: https://ogp.me/
- Instagram Reels size help: https://help.instagram.com/1038071743007909/
- Meta Instagram Reels Ads Guide: https://www.facebook.com/business/ads-guide/update/video/instagram-reels
- Meta safe zone help: https://www.facebook.com/business/help/980593475366490
- TikTok Auction In-Feed Ads specs: https://ads.tiktok.com/help/article/tiktok-auction-in-feed-ads?redirected=2
- LINE Messaging API reference: https://developers.line.biz/en/reference/messaging-api/nojs/
- LINE Ads Platform Media Guide PDF: https://vos.line-scdn.net/lbstw-static/images/uploads/download_files/81a1d9aa9642857e9693e5b718454022/EN_LINE%20Ads%20Platform%20Media%20Guide_2024%20ver..pdf
- Chrome Autoplay Policy: https://developer.chrome.com/blog/autoplay
