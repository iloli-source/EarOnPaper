> 【歴史的記録】本書は作成時点の前提・知見に基づくスナップショットです。その後の決定により一部前提は更新されています。現在の前提は `README.md`・`docs/requirements/product-vision.md`・`docs/research/gate-execution-spec.md`(最新改訂) を参照してください。

# AI採譜（Automatic Music Transcription）Web調査レポート — 学術動向・日本市場

## 1. 学術研究動向

AMTは音声信号を楽譜/MIDI等の記号表現に変換するMIRタスク。倍音構造が重なる複雑さゆえ、依然として人間の専門家の精度には未達というのが2024年サーベイの総括（[Jamshidi et al., 2024, arXiv:2406.15249](https://arxiv.org/abs/2406.15249)）。

### モデル系譜と精度指標

| モデル | 発表 | 特徴 | 精度 |
|---|---|---|---|
| **Onsets and Frames** | 2017 Google Magenta | CNN+LSTM。オンセット検出→フレーム単位ピッチの二目的学習。ピアノ採譜のブレイクスルー | 当時SOTA |
| **High-resolution (Regressing Onset/Offset)** | 2020 ByteDance | オンセット/オフセット時刻を回帰、ペダル検出（[arXiv:2010.01815](https://arxiv.org/pdf/2010.01815)） | Note F1 高精度化 |
| **MT3 (Multi-Task Multitrack)** | 2021 Google | 音楽イベントをトークン化しseq2seq Transformer。マルチ楽器統一フレームワークの先駆け | MAESTRO Onset-Offset F1 **0.80**、低資源データで最大+263%（[arXiv:2111.03017](https://arxiv.org/pdf/2111.03017)） |
| **hFT-Transformer** | 2023 河合楽器・外山ら（日本） | 二階層の周波数-時間Transformer。Frame/Note/Note+Offset/+Velocity全F1でSOTA（[arXiv:2307.04305](https://arxiv.org/abs/2307.04305)） | ピアノSOTA |
| **Transkun** | 2023-24 Yujia Yan | Neural Semi-CRF（半マルコフCRF）。音符を区間として扱う。V2は非階層Transformer（[GitHub](https://github.com/yujia-yan/transkun)、[arXiv:2404.09466](https://arxiv.org/html/2404.09466)） | MAESTRO v3 全サブタスクSOTA |
| **Basic Pitch** | 2022 Spotify | 17,000パラメータ未満・20MB未満の超軽量OSS。マルチ楽器・ピッチベンド対応（[Spotify Eng](https://engineering.atspotify.com/2022/6/meet-basic-pitch)） | 軽量ゆえ複雑ポリフォニーで精度トレードオフ |
| **MR-MT3** | 2024/3 | MT3の記憶保持強化・楽器混同低減 | — |
| **YourMT3+** | 2024 Queen Mary Univ. | MT3系トークン復号＋時間-周波数階層アテンション＋Mixture of Experts＋クロスデータセット拡張（[arXiv:2407.04822](https://arxiv.org/pdf/2407.04822)） | マルチ楽器で前進 |
| **D3RM** | 2025/1 | 離散拡散リファインメントでピアノ採譜（[arXiv:2501.05068](https://arxiv.org/pdf/2501.05068)） | — |

評価指標: Frame F1 / Onset F1 / **Onset-Offset F1**（最も厳格）。加えて Velocity 込みの精度も報告される。

### 主要データセット

| データセット | 内容 | 規模 |
|---|---|---|
| **MAESTRO** | Piano-e-Competition由来のクラシックピアノ。音声とMIDIを高精度同期 | 約199時間 / 1,276ファイル |
| **MusicNet** | クラシックのマルチトラック。ピアノ以外・多様な録音環境 | 約34時間 / 330ファイル |
| **Slakh2100** | Lakh MIDIをプロ級音源で合成した2,100曲、34楽器クラス | 約145時間 |
| **MAPS** | シーケンサMIDIの合成音声＋Disklavier録音。演奏の自然さはMAESTROに劣る | ピアノ標準ベンチ |

### ISMIR/MIREX動向（2024-2026）

- **2025 AMT Challenge**: マルチ楽器採譜ベンチ。8チーム参加、2チームがMT3ベースラインを上回る。ただし密なポリフォニー・音色の似た楽器・データ多様性不足が弱点として露呈。「進歩はアーキテクチャ革新と同程度に、より豊かな訓練データに依存」と結論（[arXiv:2603.27528](https://arxiv.org/html/2603.27528v1)）。今後ジャズ・ポピュラーへ拡張予定。
- **ISMIR 2025**: 弱教師あり学習が潮流。**CountEM/Count The Notes**（音符出現回数のヒストグラムのみを教師にEM法で精緻化、アライメント不要。ピアノ・ギター・マルチで既存弱教師法に匹敵/凌駕、[poster](https://ismir2025program.ismir.net/poster_10.html)）、クロスバージョン一貫性で堅牢性を測る研究、音楽教育向け譜面整合採譜＋誤り検出システム等。
- **リアルタイム採譜/スコアフォロー**が近年のトピック（[arXiv:2503.01362](https://arxiv.org/pdf/2503.01362)、[arXiv:2505.05078](https://arxiv.org/pdf/2505.05078)）。

**要点**: 音高検出はかなり成熟。**リズム・拍子・オフセット・記譜の意味的解釈**と**マルチ楽器ポリフォニー**が最大の残課題。ソロピアノは実用域、表情ある演奏・多楽器は未解決。

## 2. 日本市場特有の情報

### 耳コピ・採譜代行の需要と相場

ココナラは楽譜制作・耳コピ譜面カテゴリで**実績5.1万件超**の一大市場（[ココナラ カテゴリ](https://coconala.com/categories/675)、[ココナラマガジン](https://coconala.com/magazine/15273)）。価格例:

- アカペラ5パート/1分まで基本 **2,000円**、15秒追加ごと+500円、パート追加+125円/15秒
- 単音メロディ1分（約16小節）**1,500円**、ピアノ譜 **3,000円**
- ギター/ベース1パートフルコーラス **2,500円**
- 最短1時間納品の出品者も存在

専門業者:

- **USCORE（ユースコア）**: 1曲 **2,980円〜**。楽譜/コード譜/TAB譜対応、既存曲・オリジナル両対応。納期3日〜（特急相談可）、**納品後30日間無料修正保証**。銀行振込/カード対応（[uscore.jp](https://uscore.jp/)）
- **WINDS SHEET MUSIC**: 採譜・編曲・浄書・MIDI製作をメニュー化。パート譜3,000円〜、コード譜3,000円〜（[windssheetmusic.com](https://www.windssheetmusic.com/list.htm)）
- 他に mimicopy、ドリームスコア、Kanon Und Gigue 等が料金表を公開

需要背景: 弾いてみた/歌ってみた文化、吹奏楽・合唱アレンジ需要、耳コピの手間の大きさから「AIで下書き→人手仕上げ」or「最初からプロ外注」の二極。低価格帯（1曲2,000〜3,000円）の人手代行が成立。

### 国内サービス・アプリと日本語圏の評判

- **スコアメーカーZERO**（カワイ、日本製）: 譜面作成・編集特化、仕上がり美麗・詳細編集可、買い切り（[みはまクラブ比較](https://mihamaclub.org/audio-to-score-app-comparison-2/)）
- **Chord Tracker**（ヤマハ）: iOS/Android無料、弾き語り向けコード解析中心
- 学術面でも河合楽器の外山らの **hFT-Transformer** が世界SOTA。日本勢は研究・製品両面で存在感
- 日本語レビューでは **Melody Scanner**（仏MWM）が「精度・簡単さ・対応力のバランス最良」との記事が複数。無料・高精度の **Basic Pitch** も高評価
- 共通見解: 「音質が良いほど精度が上がるが、完璧な譜面はまだ難しく自分で微調整が必要」（[あずきのブログ 2026](https://azuki02.hatenablog.com/entry/2026/05/14/001038)）

## 3. 採譜サービスに必要な機能の網羅カタログ

**入力**
- 音源ファイル（MP3/WAV/FLAC/AAC/M4A）
- YouTube等のURL取り込み
- ブラウザ/アプリ内録音、鼻歌・歌唱入力
- 楽譜画像OCR（Scan2Notes型、紙譜のデジタル化）

**前処理**
- 音源分離（Demucs v4 / Spleeter でボーカル・ドラム・ベース・伴奏に分離。分離後に採譜すると複雑ミックスで精度向上。Demucs v4はHybrid Transformer方式で波形+スペクトログラム両ドメイン、[GitHub](https://github.com/facebookresearch/demucs)）
- ノイズ除去・正規化
- テンポ/拍の前処理（BPM・ダウンビート）

**解析**
- ピッチ推定（多重音・ポリフォニー対応）
- オンセット/オフセット検出（音の開始・終了、音価）
- ベロシティ（強弱）・ペダル検出
- テンポ・拍子・小節線推定
- キー（調）検出
- コード進行・コードタイミング認識
- 歌詞認識（リリック採譜）
- ドラム採譜（Drum2Notes型）
- ギターTAB化・ストローク方向認識
- 運指推定（ピアノ/ギター）
- 楽器識別（マルチ楽器の分類・分離採譜）

**出力**
- MusicXML（Sibelius/Finale/MuseScore互換の記譜標準）
- MIDI（量子化/非量子化）
- 楽譜PDF
- Guitar Pro（GP5等、TAB）
- 移調・キー変更
- パート別出力（スコア/パート譜）
- 難易度別アレンジ（初級/中級への簡略化）、リードシート化

**編集**
- 人手修正UI（音符・音価・拍子の手直し。全ツール共通で「AIの下書きを人が直す」が前提）
- スペクトログラム/ピアノロール表示（AnthemScore型）
- 再生・可聴化プレビュー
- DAW連携（プラグイン、Cubase/FL Studio/Logic Pro）、MuseScore/Sibelius/Finaleへのエクスポート

**事業面**
- 著作権処理（下記）
- API提供（Klangioが先行。バルク採譜でバックカタログ処理、開発者が自社製品へ組込み、[Klangio API](https://klang.io/api/)）
- 課金モデル（買い切り / サブスク / 従量・秒課金 / フリーミアム=短尺プレビュー無料）
- モバイルアプリ、バッチ処理

### 著作権（日本・事業化で最重要）

- **採譜自体**は「複製」に当たるが、私的使用の範囲（著作権法30条1項）なら許諾不要。個人の勉強用はOK（[JASRAC FAQ](https://secure.okbiz.jp/faq-jasrac/faq/show/458)）
- **公表・配布・販売**の段階で権利者許諾が必要。無許諾での採譜・編曲楽譜の販売は違法（[JASRAC 楽譜配信](https://www.jasrac.or.jp/users/internet/score/)）
- **編曲・替え歌など改変**はJASRAC管理外のため、作詞・作曲者本人（音楽出版社経由）の意向確認・許諾が別途必要
- 販売PF **Piascore** はJASRAC・NexToneと利用許諾契約済みで、出品者が個別契約せず管理楽曲の楽譜を販売可（編曲・替え歌は別途権利者許諾必要、[Piascore](https://publish.piascore.com/rights/intro)）
- **事業設計への含意**: 「ユーザー個人の私的複製ツール」として提供するか、「配布・販売代行」まで踏み込むかで必要な権利処理が根本的に変わる。SaaSでユーザーが自分の音源を採譜する形は私的複製に収まりやすいが、既存商用曲の採譜結果を提供・販売する形は許諾スキーム必須

## 補足: 商用ツール比較（要点）

| サービス | 対応楽器 | 出力 | 価格 | 精度評判 |
|---|---|---|---|---|
| **AnthemScore** | 汎用（ピアノ得意） | 楽譜PDF・MIDI編集可 | 買い切り Lite$31/Pro$42/Studio$107、サブスク無 | ソロピアノ良好、リズム/拍崩れやすく手直し必須 |
| **Klangio**（Piano2Notes/Guitar2Tabs/Sing2Notes/Drum2Notes/Studio/Scan2Notes） | ピアノ・ギター・ベース・ボーカル・ドラム（楽器別特化） | PDF・MIDI・MusicXML・GuitarPro | Piano2Notes$9.99/月〜、統合約$15/月 | **API・DAWプラグイン・モバイル**で事業展開最広 |
| **Songscription** | ピアノ最強・アコギ・ドラム・弦・管・ベース・ボーカル | PDF・MIDI・MusicXML・GuitarPro | 無料30秒プレビュー、有料約$8/月 | 音高高精度だがリズム解釈と多楽器で崩れる |
| **ScoreCloud** | 単旋律・鼻歌〜 | 楽譜・MIDI・MusicXML | 数曲無料→有料 | 録音だけで楽譜化、単旋律に強い |
| **Chordify/Moises/AudioJam** | コード検出・練習系 | コード/分離音声（記譜せず） | サブスク | コード進行特化、Moisesはステム分離→コード検出 |
| **Songsterr** | ギターTABライブラリ | コミュニティTAB＋AI生成 | Plus AI $9.95/月 | 既存曲学習・スロー再生向き |

（出典: [Songscription blog](https://www.songscription.ai/blog/best-music-transcription-software-2026)、[Klangio](https://klang.io/)、[AnthemScore reviews](https://aitoptools.com/tool/anthemscore-by-lunaverus/)）

## 補足: ユーザー実体験

- **プロレビュー（MusicRadar/Songscription）**: 音高は装飾音まで正確だが、リズム/拍子が致命的（「全体が8分音符1つ分遅れ」、単純な4/4を「3/4→4/4→11/8」と誤判定）。バイオリンは表情部でタイミング脱線、フルートはブレスを長音符化。結論「当面、本格的な採譜は人間がやる」（[MusicRadar](https://www.musicradar.com/music-tech/humans-will-be-doing-all-the-serious-music-transcription-for-the-foreseeable-future-songscription-review)）
- **フォーラム（MuseScore/Piano World）**: AnthemScoreはソロピアノで「完璧でないが良い出発点」。定番ワークフローは **Basic Pitchで音声→MIDI→MuseScoreで記譜**。複雑曲は今も手動耳コピの方が信頼されるとの声（[MuseScore forum](https://musescore.org/en/node/272456)）

## 総括

音高検出はソロ/単一楽器で実用域に到達したが、**リズム・拍子・記譜の意味解釈**と**マルチ楽器ポリフォニー**が学術・商用ともに最大の壁。現状ベストプラクティスは「音源分離→AI採譜→人手仕上げ」の半自動ワークフロー。日本市場は研究（hFT-Transformer等の世界SOTA）と低価格な人手代行（1曲2,000〜3,000円）の両輪が成立。事業化には著作権処理の設計（私的複製に留めるか許諾スキームを組むか）が決定的に重要。
