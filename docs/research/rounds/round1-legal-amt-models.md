> 【歴史的記録】本書は作成時点の前提・知見に基づくスナップショットです。その後の決定により一部前提は更新されています。現在の前提は `README.md`・`docs/requirements/product-vision.md`・`docs/research/gate-execution-spec.md`(最新改訂) を参照してください。

調査が完了しました。以下、最終レポートです。

---

# 自動採譜(AMT)モデルの著作権論点と学習データ開示状況 調査レポート

**調査日: 2026-07-18 / 調査手段: WebSearch・WebFetch(英語・日本語)**

> **総論として重要な注意**: 「AIによる自動採譜」そのものを正面から扱った判例・行政解釈は日米とも見つからなかった。以下の法的評価は、(a)人間による採譜・耳コピに関する確立した法理、(b)AI学習一般に関する法制度(日本の著作権法30条の4、米国フェアユース判例)、(c)関連裁判例(バンドスコア事件等)からの組み合わせによる整理であり、採譜AI特有の確立した判例は乏しい。この点は事実として明記する。

---

## 1. 採譜は生成AIとどう違うか — 権利処理の観点

### 1-1. 出力の法的性質: 採譜結果は「新規生成物」ではなく原曲の複製・翻案

**確立している法理(人間の採譜に関するもの。AIが行っても結論は変わらないと考えられる):**

- **日本法**: 楽譜は「楽曲を一定のルールに従って書き起こしたもの」であり、**楽曲とは別個独立の著作物とは考えられていない**(骨董通り法律事務所・石井あやか氏コラム、バンドスコア事件解説)。したがって耳コピ・採譜による楽譜化は原曲の**複製**(場合により**翻案/編曲**)に該当する。私的使用(著作権法30条)の範囲なら許諾不要だが、公開・配布・販売には許諾が必要 — これはJASRAC公式FAQも明言(「個人的な勉強のための採譜は私的使用の複製として許諾不要。出版・配布には許諾必要」)。
- **米国法**: 録音から耳で起こした transcription/arrangement は **derivative work**(二次的著作物)であり、作成・販売・無償配布には権利者のライセンスが必要。個人学習目的はフェアユースで許容されうるが、完全な採譜の販売は公式楽譜市場を害するためほぼフェアユース不成立(That Great Composer解説、Avvo上の複数の弁護士回答)。

**採譜AIへの当てはめ(整理・一部は本調査による推論と明記):** 採譜モデルの出力は原曲の楽音構造をそのまま記譜するため、著作権侵害の要件である**類似性・依拠性がほぼ自明に成立する**(入力音源に依拠し、出力は原曲と実質同一)。生成AIで争点になる「出力が学習データに類似するか」という確率的な問題ではなく、**出力が原曲の複製/翻案であることが構造上確定している**点が最大の違い。ただし侵害が現実化するのは出力の利用態様次第(私的使用なら適法、公開・販売なら要許諾)。

### 1-2. 学習段階と出力段階の切り分け

**日本法(文化庁「AIと著作権に関する考え方について」令和6年3月・文化審議会著作権分科会法制度小委員会):**

| 段階 | 適用法理 | 採譜AIへの当てはめ |
|---|---|---|
| 開発・学習段階 | 30条の4(非享受目的の情報解析は原則許諾不要)。ただし書「著作権者の利益を不当に害する場合」は除外 | 音源から音高・オンセット等の特徴を統計的に抽出する行為は典型的な「情報解析」で、原則30条の4の射程内(STORIA法律事務所の解説等)。ただし「情報解析用データベースとして販売されている物」を無断利用する場合等はただし書に該当しうる |
| 生成・利用段階 | 通常の侵害判断(類似性+依拠性)。30条の4は出力段階を免責しない | 採譜出力は原曲との類似性・依拠性が明白なので、出力の公衆送信・販売は原曲の複製権/翻案権侵害となりうる。私的使用(30条)の範囲なら適法 |

**米国法:** 学習段階のフェアユース評価は流動的。*Thomson Reuters v. Ross Intelligence*(デラウェア連邦地裁、2025年判決)は「無許諾コンテンツでのAI学習はフェアユースでない」と判断した初期の重要判例。米国著作権局の2025年報告書もフェアユース判断は権利者側に傾きうるとの整理。音楽分野ではレーベルによる生成AI企業(Suno/Udio等)への訴訟が係属中。**採譜AIの学習が同様に扱われるかを直接判断した判例はない。**

### 1-3. 「作風の模倣」「市場競合」論点は採譜に当てはまるか

**専門家・法律事務所による「採譜AIは生成AIと違ってこの問題が当てはまりにくい」と正面から論じた見解は、英日いずれの検索でも発見できなかった**(この点は「見つからなかった」ことが調査結果)。そのうえで、調査で得られた材料からの整理:

- 生成AI固有の論点(特定アーティストの**作風=アイデアの模倣**、類似コンテンツ大量生成による**創作市場との競合**)は、採譜AIには構造的に生じにくい。採譜AIは新規楽曲を生成せず、スタイル抽出・再合成を行わないため。
- ただし採譜には**別の市場競合**がある: 出力が公式楽譜・バンドスコア市場と直接代替関係に立つ。米国の弁護士回答は「公式楽譜市場を害する完全採譜はフェアユース不成立」と指摘しており、日本でも**バンドスコア事件(東京高裁令和6年6月19日判決、上告中)**が、耳コピ採譜スコアの模倣を「採譜にかける時間・労力・費用へのフリーライド」として著作権法上の保護がない部分についても**一般不法行為**の成立を認めた(骨董通り法律事務所コラム)。採譜結果そのものは著作物でなくても、採譜事業の投下労力が法的保護の対象になりうることを示す重要裁判例。
- 商用採譜サービスのKlangioは、**権利者が自作品の採譜表示の削除を請求できる窓口(retract@klangio.com)** を利用規約に設けており、採譜出力が権利者の利益と衝突しうることを事業者自身が前提にした実務対応をしている。

---

## 2. 既存採譜モデルの学習データ開示状況

| モデル | 開発元 | 学習データ | 開示状況 | コード/モデルライセンス | 論文 |
|---|---|---|---|---|---|
| **MT3** (Multi-Task Multitrack Music Transcription) | Google Magenta | MAESTRO v3, Slakh2100, Cerberus4(Slakh派生), GuitarSet, MusicNet, URMP の6種 | **完全開示**(ICLR 2022論文に明記) | Apache-2.0 (github.com/magenta/mt3) | arXiv:2111.03017 (ICLR 2022) |
| **Basic Pitch** | Spotify | GuitarSet, iKala, MAESTRO, MedleyDB-Pitch, Slakh の5種 | **完全開示**(Hugging Faceモデルカード・論文に明記) | Apache-2.0 (github.com/spotify/basic-pitch) | "A Lightweight Instrument-Agnostic Model for Polyphonic Note Transcription and Multipitch Estimation" arXiv:2203.09893 (ICASSP 2022) |
| **Klangio** (klang.io) | Klangio GmbH(独・カールスルーエ、KIT発) | **非開示**。ただし共同創業者Murgul氏がインタビューで「最大の課題は学習データの入手可能性。音楽著作権は複雑で繊細な問題。だから**数百万の合成音楽サンプルを生成するプロセスを開発し、それでモデルを学習している**」と発言 | 具体的データセットは非開示/不明 | 商用・非公開 | 査読論文としての公開なし(不明) |
| **Onsets and Frames** | Google Magenta | 学習: MAESTRO(初期版は独自Disklavier収録+MAPS)。テスト: MAPS Disklavier部 | **開示** | Apache-2.0 (magenta/magentaリポジトリ) | Hawthorne et al. 2018 / MAESTRO論文 arXiv:1810.12247 (ICLR 2019) |
| **Omnizart** | Music and Culture Technology Lab(台湾・中央研究院系) | MAESTRO, MusicNet, Pop(ポップス), McGill Billboard, MIR-1K, MedleyDB, **A2MD(YouTubeからダウンロードした1,454曲のポップス音源、自作データセット)** | **開示** | MIT系OSS(GitHub公開) | "Omnizart: A General Toolbox for Automatic Music Transcription" JOSS 2021 / arXiv:2106.00497 |

**特記事項:**

- **Klangioが唯一の「学習データ非開示」商用サービス**だが、著作権問題を回避するため**合成データ主体**と自ら説明している(karlsruhe.digitalインタビュー、2025年9月)。利用規約では、ユーザーのアップロード音源の権利はユーザーに帰属し、**アップロード音源をモデル学習に使う旨の条項は存在しない**(規約に明示的な学習利用許諾文言なし)ことも確認した。
- **Omnizartのドラム採譜用A2MDデータセットはYouTube由来の市販楽曲音源**であり、権利処理の説明は論文・リポジトリ上で確認できなかった。研究利用(台湾/各国のTDM例外・フェアユース相当)を前提にしていると推測されるが、これは**推測**である。
- MT3・Basic Pitchはいずれも「研究コミュニティの公開データセットのみで学習」という構成で、独自にライセンス取得した商用音源を使った形跡はない(論文記載ベースの事実)。

---

## 3. 主要学習データセットの権利状況

| データセット | 内容・由来 | ライセンス | 商用利用 |
|---|---|---|---|
| **MAESTRO** (v1-v3) | International Piano-e-Competition(旧Yamaha e-Piano Competition)のDisklavier演奏約200時間。クラシック中心(大半はパブリックドメイン楽曲の演奏)。Google Magentaがコンペ主催者と提携して公開 | **CC BY-NC-SA 4.0** | **不可**(非商用限定) |
| **MAPS** | Telecom ParisTech制作。仮想ピアノ音源+Yamaha Disklavierによる約31GBの録音 | **CC BY-NC-SA 2.0 FR** | **不可**(非商用限定) |
| **Slakh2100** | Lakh MIDI Dataset由来のMIDIをサンプルベース音源でレンダリングした**合成音源**2,100トラック | **CC BY 4.0**(Zenodo) | 可。ただし元となるLakh MIDIはウェブ収集のMIDIファイル群であり、元MIDI自体の権利処理には議論の余地がある(既知の論点として付記) |
| **MusicNet** | クラシック録音330曲+100万超の音符ラベル。音源はIsabella Stewart Gardner Museum・European Archive Foundation・Musopen由来の**CCライセンス/パブリックドメイン録音のみ** | 音源はCC/PD。ラベルは録音とともに再配布可と明言 | 音源の個別CC条件による |
| **GuitarSet** | NYU MARL制作。ヘキサフォニックピックアップによる**自主録音**のギター演奏 | **CC BY 4.0**(Zenodo) | 可 |
| **URMP** | ロチェスター大学制作。44曲の多重奏を**個別に自主録音**(クラシック小品) | Dryadで配布(DryadのポリシーはCC0)。※データセット固有の追加条件は要個別確認 | 実質的に可(自主録音・古典曲) |
| **MedleyDB** (Pitch) | NYU制作のマルチトラック(royalty-free multitrack と説明) | 公式サイトにライセンス明記なし。Zenodoで**許可リクエスト制**配布。研究コミュニティでは非商用CC(CC BY-NC-SA)扱いが通例とされるが、一次ソースで確定できず | **不明瞭** |
| **iKala** | 台湾発のボーカル/伴奏分離・歌声採譜用データセット(Mandarin pop) | **研究目的限定**で配布されていたと理解されるが、公式の一次ソースを今回確認できず。現在は配布終了との報告あり | 不可とみられる(未確定) |

**権利処理パターンの整理:** 採譜研究のデータセットは、(1)**自主録音**(GuitarSet, URMP, MAPS)、(2)**演奏コンペ等との提携によるMIDI+音源同時収録**(MAESTRO)、(3)**CC/PD録音の収集**(MusicNet)、(4)**合成音源**(Slakh, Klangioの合成サンプル)、の4パターンでほぼ説明でき、生成AIのような大規模ウェブスクレイピング音源への依存は主流モデルでは見られない(例外: OmnizartのA2MD)。一方、**MAESTRO・MAPS・MedleyDBが非商用ライセンス**である点は、これらで学習したモデル(Apache-2.0のBasic Pitch含む)を商用利用する際の「学習データのNC条件が学習済みモデルに及ぶか」という未解決論点(モデルはデータの派生物か)を残す。この論点への確定的な法解釈は存在しない。

---

## 4. 結論(要旨)

採譜AIは、学習段階では日本の30条の4等により生成AIと同様の法的整理が可能な一方、**出力段階の性質が生成AIと根本的に異なる**。生成AIの争点(作風模倣・確率的類似・市場氾濫)に代わり、採譜では**出力=原曲の複製/翻案が構造的に確定**しており、リスクの所在は「モデルや事業者」よりも「出力をどう利用するか(私的使用か、公開・販売か)」に集中する。この特性を正面から論じた専門家見解・判例は現時点で見当たらず、人間の採譜に関する法理(JASRAC見解、米国derivative work法理、バンドスコア事件)からの類推が実務上の拠り所となる。学習データについては、主要OSSモデル(MT3, Basic Pitch, Onsets and Frames, Omnizart)は完全開示、商用のKlangioは非開示だが合成データ主体と自認、という対照的な状況である。

---

## ソースURL一覧

**法的論点(日本語)**
- 骨董通り法律事務所コラム(バンドスコア事件・東京高裁令和6年6月19日判決): https://www.kottolaw.com/column/250226.html
- 虎ノ門法律特許事務所(バンドスコア事件解説): https://chosakukenhou.jp/バンドスコア耳コピ模倣は不法行為？東京高裁が/
- BUSINESS LAWYERS(バンドスコア事件): https://www.businesslawyers.jp/articles/1436
- JASRAC FAQ(個人的な勉強のための採譜): https://secure.okbiz.jp/faq-jasrac/faq/show/458?site_domain=jp
- STORIA法律事務所(30条の4の射程): https://storialaw.jp/blog/12050
- 文化庁「AIと著作権について」: https://www.bunka.go.jp/seisaku/chosakuken/aiandcopyright.html
- イノベンティア(考え方・生成利用段階の解説): https://innoventier.com/archives/2024/07/17087

**法的論点(英語)**
- That Great Composer "Is It Legal to Transcribe and Sell Sheet Music?": https://www.thatgreatcomposer.com/blog/is-it-legal-to-transcribe-and-sell-sheet-music
- Avvo弁護士回答(採譜とderivative work): https://www.avvo.com/legal-answers/is-it-ok-to-transcribe-a-musical-recording-without-335835.html / https://www.avvo.com/legal-answers/is-transcribing-songs-into-tabluature-considered-a-162421.html
- Music Business Worldwide (Thomson Reuters v. Ross判決): https://www.musicbusinessworldwide.com/using-copyrighted-content-to-train-ai-without-permission-is-not-fair-use-us-court-rules-in-precedent-setting-thomson-reuters-case/
- The Vocal Market "Is It Legal to Train AI on Scraped Music?": https://thevocalmarket.com/blogs/enterprise/is-it-legal-to-train-ai-on-scraped-music

**モデル**
- MT3論文: https://arxiv.org/abs/2111.03017 (ICLR 2022版: https://openreview.net/pdf?id=iMSjopcOn0p)
- Basic Pitch論文: https://arxiv.org/abs/2203.09893 / GitHub: https://github.com/spotify/basic-pitch / モデルカード: https://huggingface.co/spotify/basic-pitch / 解説: https://engineering.atspotify.com/2022/06/meet-basic-pitch
- Klangio利用規約(retract窓口): https://klang.io/terms/ / 創業者インタビュー(合成データ発言): https://karlsruhe.digital/en/2025/09/klang-io-ki-musik/
- Onsets and Frames: https://magenta.withgoogle.com/onsets-frames / https://github.com/magenta/magenta/tree/main/magenta/models/onsets_frames_transcription
- Omnizart論文: https://arxiv.org/abs/2106.00497 / JOSS: https://www.theoj.org/joss-papers/joss.03391/10.21105.joss.03391.pdf

**データセット**
- MAESTRO(CC BY-NC-SA 4.0): https://magenta.withgoogle.com/datasets/maestro / 論文: https://arxiv.org/abs/1810.12247
- MAPS(CC BY-NC-SA 2.0 FR): https://adasp.telecom-paris.fr/resources/2010-07-08-maps-database/
- Slakh2100(CC BY 4.0): https://zenodo.org/records/4599666 / http://www.slakh.com/
- MusicNet(CC/PD録音): https://zenodo.org/records/5120004 / 論文: https://arxiv.org/abs/1611.09827
- GuitarSet(CC BY 4.0): https://zenodo.org/records/3371780
- URMP(Dryad配布): https://datadryad.org/dataset/doi:10.5061/dryad.ng3r749 / https://labsites.rochester.edu/air/projects/URMP/URMP_doc.pdf
- MedleyDB(許可制): https://medleydb.weebly.com/
