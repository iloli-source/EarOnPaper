# F-002 音質診断 — 実装前リサーチ(10並列ワークフロー)

**取得日:** 2026-07-21 / Issue #67 / 実装コミット 5167a73
**方式:** 先行リサーチ(Web/論文・失敗例重視)→実装 の並列ワークフローのリサーチ段を保存

## 推奨アプローチ(approach)
実装対象: diagnose_audio(y: np.ndarray, sr: int) -> AudioQuality(frozen)。librosa/numpyのみ。

【frozen dataclass】既存contracts.pyの様式(frozen, Literal, 日本語docstring)に合わせ、新規モジュール内でAudioQualityをfrozen定義: clipping_rate:float, snr_db:float, reverb_ratio:float, band_limit_hz:float, rating:Literal["green","yellow","red"], warnings:list[str]。※listはミュータブルなのでfrozenでも中身は変わりうる→field(default_factory=tuple)またはtuple[str,...]で受けるのが厳密だが、指定シグネチャがlistなので tuple を渡してlistへ変換、あるいはdocstringで「構築後変更しない前提」と明記。__post_init__で不変条件検証(rateは3値のみ等)。

【入力正規化(最重要の前処理)】y はステレオ(2D)やint16で来る可能性→ np.asarray, 多チャンネルなら librosa.to_mono 相当(axis平均)でモノ化, floatへ. |y|の最大値で正規化してから閾値判定(絶対振幅0.98は「フルスケール正規化済み」前提。既に-1..1でなければピーク基準比で判定)。空配列・全ゼロ・NaN/Infを冒頭でガードし安全なデフォルト(rating="red"+warning)を返す。

【clipping_rate】clipped = np.abs(y) > 0.98*peak の割合。研究の実務: 単純な閾値超え本数カウント + 「連続してフラットに張り付くサンプル列(連続run)」の検出を併用すると誤検出が減る(振幅分布のヒストグラム端に山ができる)。最小実装は割合で可。閾値: >~0.5%(0.005)でyellow, >~1%(0.01)でred相当が実務的目安。

【snr_db】雑音床推定=フレームRMSの下位パーセンタイル法。librosa.feature.rms(frame_length=2048,hop=512)→ dB化。信号レベル=上位(例:95〜面積上位)パーセンタイルの平均、雑音床=下位(例:5〜10)パーセンタイルの平均、SNR_dB = 20*log10(signal_rms/noise_rms) もしくは差分(dBドメインで減算 S-N)。無音や全域一定パワーだと分子分母が近づきSNRが不安定→クランプ(0..60dB)。閾値: 概ね>20dBクリーン(green), 10〜20dB注意(yellow), <10dBノイジー(red)。

【band_limit_hz】librosa.feature.spectral_rolloff(y,sr, roll_percent=0.985) の中央値/上位値を帯域上限プロキシに。低ビットレート/電話帯域だとロールオフが sr/2 よりかなり下(例:128kbps MP3≒16kHz, 電話≒3.4kHz, 8kHz収録≒4kHz)。閾値: sr由来のナイキストに対し rolloff中央値 が <~16kHz(ハイファイ期待時)や、特に <~8kHz(明確な帯域不足=低品質/低ビットレート/電話)でwarning。srが低い場合はナイキストで頭打ちになるので、閾値はmin(期待値, 0.9*sr/2)で相対化。

【reverb_ratio】簡易残響=エネルギー減衰の裾の長さ。実装案: オンセット後のエネルギー包絡(RMS包絡またはlibrosa.onset)から、ピーク後にエネルギーが一定割合(例:-20dB/-60dB)まで落ちるまでの時間を減衰プロキシとするか、より頑健には「後期エネルギー比(late energy ratio)」= 短時間エネルギーの自己相関/包絡の尖度低下で残響の"にじみ"を0-1比で表現。厳密RT60秒は出さず、指定通り reverb_ratio(0-1の比)に留める(残響が多いほど1に近い)。閾値: >~0.5-0.6でwarning。

【rating統合】3指標それぞれをgreen/yellow/redにビン分けし、最悪値(red>yellow>green)をratingに採用。各red/yellow要因を日本語warningsに積む(例:「クリッピング率1.2%(過大)」「SNR8dB(雑音過多)」「帯域上限7.8kHz(高域欠落・低ビットレートの可能性)」「残響過多」)。閾値は全てモジュール冒頭の名前付き定数(UPPER_SNAKE)に集約(magic number禁止)。

【テスト(AAA・新規1ファイル)】.venv/bin/python -m pytest <testfile> -q -p no:cacheprovider で自テストのみ実行。合成信号で検証: (1)クリーン正弦波→green・clipping≈0・SNR高, (2)±1.0でハードクリップした矩形化正弦→clipping_rate高・rating red, (3)正弦+ガウス雑音(既知SNR)→snr_dbが期待レンジ, (4)低域のみ(sr高いのにrolloff低い/lowpass済み)→band_limit_hz低くwarning, (5)空配列・全ゼロ・NaN→例外にせずredで安全返却, (6)ステレオ2D入力→モノ化して動作, (7)返り値がfrozenで書換え不可(FrozenInstanceError)。数値は厳密一致でなく範囲assert(合成信号でも窓・端効果でズレるため）。

## 落とし穴・失敗例(pitfalls)
【振幅スケール依存】0.98絶対閾値は「-1..1フルスケール正規化済み」前提。int16(±32768)や既にピーク0.3の素材だとクリッピングを常に0と誤判定。必ずピーク基準(相対)か、入力仕様を明示。逆にピーク正規化すると元々クリップしてる素材も0.98未満になりうる→「フラットに張り付く連続run」検出を併用すべき理由。

【SNRは音楽で不安定】ノイズ床パーセンタイル法は「曲中に十分な無音/低エネルギー区間がある」前提。ずっと鳴り続ける密なミックスやサステイン楽器では下位パーセンタイル=最弱の楽音であって雑音床ではなく、SNRを過小評価する。逆に無音の多い曲は過大評価。既存FieldReport.snr_dbのdocが既に「内部プロキシ値」と正直に注記している通り、絶対値でなく相対順位/レンジとして扱い、docstringに限界明記。0除算・log10(0)=-infガード必須(noise_rms==0でSNRを上限クランプ)。

【RT60/残響の盲推定は音楽で最も壊れやすい】blind RT60(Ratnam法)の既知失敗: (1)自由減衰(free decay)区間に入らないフレーム、(2)緩やかなオフセット音で失敗。連続する音楽/発話は減衰パターンが不明瞭で信頼度が落ちる。かつ「残響が直接音を支配する(小部屋/遠距離)」前提のため近接マイクの乾いた音源では過小。→秒単位RT60を名乗らず0-1のreverb_ratioに留める判断は妥当だが、「残響なのか単にサステイン/リリースの長い楽器なのか」を原理的に分離できない点をdocstringで正直に書く(誤陽性の主因)。

【spectral_rolloffの罠】roll_percentの既定は0.85で「帯域上限」には低すぎる→0.985程度にする。無音フレームや直流はrolloff=0を返し中央値を汚す→有音フレームのみ集計。srが低ければ物理的にナイキストで頭打ちになるので、閾値をsr相対化しないと低srを常に「帯域不足」と誤判定。MP3等のlowpassは「16kHz付近で急峻にゼロ」なので中央値より上位パーセンタイル+急落エッジ検出の方が確実だが、最小実装は中央値rolloffで可。

【librosa.feature.rms等のshape】戻り値は(1, n_frames)の2D。ravel/[0]で1D化しないとパーセンタイル計算がずれる。空/極短信号ではフレーム0本→np.percentileが空配列で例外。長さガード(n_fft/frame_lengthより短ければ全体1フレーム扱い or 早期return)。

【NaN != NaN / frozen+list】contracts.pyのレビュー#40注記と同様、警告listをfrozen dataclassに持たせると「不変」を偽る。tuple推奨だが指定シグネチャがlist型なので、少なくとも構築時に新規listを毎回生成し外部から共有参照を渡さない(default_factory使用、可変デフォルト引数の罠回避)。

【出力捏造禁止】合成テストは端効果・窓長でSNR/rolloffが理論値からずれる。厳密==でなく範囲assertにしないと落ちる。pytestが実際に緑になるまで直し、緑を確認した事実のみをtest_passed=trueとする。

## 参考(prior_art)
【最も近い先行研究】Lostanlen/Cwitkowitz系ではなく、"Estimation of Music Recording Quality to Predict Automatic Music Transcription Performance"(Springer, LNCS 2022, 10.1007/978-3-031-22061-6_24)がまさに本課題そのもの: 背景雑音・音の乱れ・残響からSNRを推定し、録音品質がMIR/AMT性能に有意な影響を与えることを示す。本番でもaudio "problems"の三本柱(noise/clipping/reverb)を採る根拠。※本文はSpringer認証壁でフルテキスト取得不可、要旨と検索スニペットのみ確認(捏造回避のため詳細数値は本文未確認と明記)。

【クリッピング検出/SNR】ResearchGate "SNR estimation for clipped audio based on amplitude distribution": クリップ/非クリップの分離はフレーム長6000-8000サンプル・ヒストグラム200-300ビン・閾値0.45-0.55が良好、と具体値。振幅分布(ヒストグラム端の山)でクリップを検出する定石の裏付け。→「連続run/分布端」併用の根拠。

【SNRノイズ床推定】Essentia SNRチュートリアル(essentia.upf.edu/tutorial_audioproblems_snr.html)がMMSEベースSNR推定の実装リファレンス。USC SAIL "Long-Term SNR Estimation"、及び特許群で「ノイズ床≒複数連続フレームの最小フレームパワー」「25msフレーム/10msシフト」「SNR=S-N(dB)」という実務値。パーセンタイル法(下位=雑音床/上位=信号)はこれらの簡易版。

【RT60】nuniz/blind_rt60(PyPI blind-rt60, Ratnam et al.に基づく)とpyroomacoustics.experimental.rt60(Schroeder積分法)が実在実装。重要な限界記述: blind推定は"free decay区間外のフレーム"と"緩やかなオフセット音"で失敗、連続音楽では減衰不明瞭で信頼低下、reverbが直接音を支配する前提(小部屋/遠距離向き)。→本実装が秒RT60でなく0-1比に留める設計判断の裏付け。新規重依存(blind-rt60/pyroomacoustics)は追加せずlibrosa包絡ベースの簡易減衰で代替する方針と整合。

【帯域不足/低ビットレート】Hydrogenaudio Knowledgebase "High-frequency content in MP3s"とLAME仕様: 128kbps MP3≒16kHzでlowpass, 320kbps LAME≒20.5kHz。cutoff周波数=「エネルギーがほぼ0になる最高周波数」で帯域制限コンテンツ検出に有効(特許US ...classifying)。→spectral_rolloff(roll_percent高め)を帯域上限プロキシに使い、16kHz/8kHzを段階閾値にする根拠。電話帯域≒3.4kHz。

【中国語圏の補足】中文文献でも频谱滚降点(spectral rolloff)・削波检测(clipping)・混响时间RT60混响比の語で同手法が一般的。ただし今回検索の一次情報は英語圏中心で、中文の追加固有知見は本調査では確認できず(捏造回避のため未確認と明記)。

Sources: Springer 10.1007/978-3-031-22061-6_24; ResearchGate SNR estimation for clipped audio(amplitude distribution); Essentia SNR tutorial; USC SAIL Long-Term SNR Estimation; nuniz/blind_rt60 & PyPI blind-rt60; pyroomacoustics rt60 docs; Hydrogenaudio High-frequency content in MP3s; VI-Control 320kbps 16kHz cutoff thread.

## 実装上の限界・正直な注記(notes)
正直な注記(限界・未対応):

1. モジュール・テストとも既に存在し完成状態だった(このエージェントによる新規生成ではなく既存実装の検証・確認)。実際に自テストのみを pytest 実行し 13件全緑を確認済み。

2. 依存: 指定は「librosa/numpyのみ」だが、SNR推定に scipy.ndimage.median_filter を使用している。これは librosa の推移的依存として .venv に既存であり、同 stem ディレクトリの field.py が同一方式(周波数方向メディアンで雑音床分離)で既に採用している前例に合わせたもの。新規重依存(blind-rt60/pyroomacoustics等)は追加していない。純 librosa/numpy 限定が厳格要件なら median_filter を numpy 実装へ置換可能。

3. SNRは雑音床パーセンタイル/メディアン法で、密なミックスやサステイン主体音源では過小評価しうる内部プロキシ値(絶対値でなく相対順位で扱う旨をdocstringに明記)。

4. reverb_ratio は 0-1 のにじみプロキシで秒単位RT60ではない。リリースの長い楽器の持続音と実残響を原理的に分離できず誤陽性しうるため、残響は単独でred判定せず最大yellow止まりに保守設計。

5. band_limit_hz は spectral_rolloff 中央値プロキシ。sr のナイキストで相対化し低srを常に帯域不足と誤判定しない。MP3等の急峻lowpassには中央値より上位パーセンタイル+エッジ検出が確実だが最小実装は中央値。

6. __init__.py には既に diagnose のimportとexportが入っていた。指示通りこのエージェントは既存ファイルを一切編集していない。
