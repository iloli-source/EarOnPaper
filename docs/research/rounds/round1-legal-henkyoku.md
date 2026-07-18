> 【歴史的記録】本書は作成時点の前提・知見に基づくスナップショットです。その後の決定により一部前提は更新されています。現在の前提は `README.md`・`docs/requirements/product-vision.md`・`docs/research/gate-execution-spec.md`(最新改訂) を参照してください。

Slackへの作業ログ投稿も完了しました。以下、統合調査レポートです。

---

# 日本の音楽著作権「編曲権」実務 徹底調査レポート

調査日: 2026-07-18 / 方法: Web検索・公式サイト直接取得(日本語・英語)。**事実**(ソースで文言確認済み)と**推定/不明**を明確に区別して記載。

---

## 1. 編曲許諾の手続き・費用・期間 / JASRACは編曲権を管理していない

### 1-1. JASRACは編曲権を管理していない【確定事実】

JASRAC公式サイトに明記:

> 「JASRACでは編曲権・翻案権の譲渡を受けていないため、編曲することなどについて許諾することはできません。編曲などをする場合は、直接、著作者（もしくは音楽出版社）にお問い合わせください。」

- ソース: https://www.jasrac.or.jp/aboutus/copyright/ (英語版 https://www.jasrac.or.jp/en/about/copyright/ も同旨)

JASRACが信託を受けて管理するのは演奏権・公衆送信権・録音権(複製権)等の支分権であり、**著作権法27条の翻案権(編曲権)は信託範囲外**。理由は、①譲渡契約で27条・28条を特掲しない限り譲渡人に留保と推定される(著作権法61条2項)、②編曲は同一性保持権(20条)=譲渡不能の著作者人格権(59条)に関わるため。

- 管理委託範囲ガイドライン: https://www.jasrac.or.jp/creators/contract/pdf/contract-guideline.pdf
- 管理委託契約約款: https://www.jasrac.or.jp/aboutus/public/pdf/contract.pdf
- JASRAC「事前に権利者への確認が必要な利用」: https://www2.jasrac.or.jp/eJwid/info/jizenkakunin.html — 「改変を無断で行うと、同一性保持権(第20条)、翻案権(第27条)の侵害となるおそれ」「音楽出版者(いない場合は著作者)に連絡の上、利用の可否等を確認」と明記

### 1-2. 法的根拠【確定事実】

- **著作権法27条**: 「著作者は、その著作物を翻訳し、**編曲し**、若しくは変形し、又は脚色し、映画化し、その他翻案する権利を専有する」(条文に「編曲」明示)
- **著作権法20条1項**: 同一性保持権。「意に反する改変」は翻案権の許諾を得ても別途侵害になりうる(二重構造)
- e-Gov: https://laws.e-gov.go.jp/law/345AC0000000048/

### 1-3. 実際の許諾申請フロー【複数ソース一致】

1. JASRAC作品DB **J-WID** で対象曲の音楽出版社(O.P.)を特定
2. 音楽出版社へ編曲許諾申請(利用目的・編成・掲載媒体・編曲後の譜面等を提出)
3. 出版社が著作者本人(作詞・作曲者)の意向を確認 ※人格権は本人に残るため
4. 許諾書(またはメール承認)発行
5. **その後**、複製・配信についてJASRAC/NexToneへ通常の利用申込 — 「編曲許諾が先、複製許諾が後」の順序をCARSが明示

- CARS(楽譜コピー問題協議会): https://www.cars-music-copyright.jp/column/post-134/
- ヤマハ編曲許諾申請案内(PDF): https://retailing.jp.yamaha.com/library/shop/ginza/studio/henkyoku-shinsei.pdf

### 1-4. 費用と期間

| 項目 | 内容 | 種別 |
|---|---|---|
| 許諾料本体 | **統一相場なし**。出版社・楽曲・利用態様ごとに個別設定(無償例あり) | 事実(相場は不明) |
| 実例 | Sony Music PublishingへPiascore販売用の編曲許諾をWebフォーム申請 → **約4日で承認・無料**(個人の体験談) | 個人ブログ: https://nishimurahiroya.com/楽譜販売のために編曲許諾をソニーミュージック/ |
| 申請代行手数料 | musicstore.jp: 国内作品 **8,800円/曲(税抜)**、権利者不明ケース **11,000円/曲** ※権利者へ払う許諾料とは別 | https://www.musicstore.jp/shop/getting_the_permission.php |
| 海外作品 | 事務手数料 **2万円(税抜)〜** の例(ロケットミュージック) | https://www.gakufu.co.jp/pages/permission |
| 期間 | 「数週間から数ヶ月を要することも珍しくない」(弁護士解説)。ヤマハ案内も同旨+「**許諾されるとは限らない**」 | https://media-law.jp/info/楽曲のカバー・アレンジを行う際の著作権処理と/ |

出版社の対応はまちまちで、返信が来ない場合は販売見送りが安全という実務者の見解あり(https://note.com/m0chikinak0m0chi/n/n9c0601aef1c7)。

---

## 2. Piascore等の楽譜販売サービスの権利処理

### 2-1. Piascoreの包括許諾は「編曲」には効かない【公式ページで確認済み・最重要】

Piascore公式(https://publish.piascore.com/rights/intro):

> 「Piascore ストアはJASRACや株式会社NexToneと管理楽曲利用許諾契約を締結しており、各販売者が個別に各著作権管理団体と契約を結ぶ必要がなく、楽譜を販売することができる」

一方で同ページに:

> 「編曲や替え歌のように元の楽曲を改変する場合、著作権法(第20条1項『同一性保持権』、第27条『編曲権・翻案権・翻訳権』)に従って、**あらかじめ権利者からの許諾を得る必要があります**」

無許諾改変は**販売停止**対象。つまり **包括許諾がカバーするのは複製・配信(販売)のみで、編曲(Arrangement)には効かない**。なお包括契約が「複製権」「公衆送信権」をカバーすると明記した文言自体はページ上になく、業態からの推定(契約の具体的権利範囲は非公開・不明)。

### 2-2. 出品可能楽曲とクリエイターの責任【公式規約】

- 販売登録できるのは ①保護期間満了曲 ②自身が権利を持つオリジナル ③**「権利者の出版・編曲の許諾を取得した楽曲」** の3類型(https://publish.piascore.com/rights)
- クリエイター利用規約第7条: 出品者が権利非侵害を保証し、紛争は「クリエイターが自らの責任と費用負担で解決」(https://publish.piascore.com/term) → **編曲許諾の取得責任は出品者側**
- 販売収益率(https://publish.piascore.com/profit): パブリックドメイン/オリジナル 80%(Web)、JASRAC/NexTone管理曲 70%、外国曲 60%(アプリ内購入は各20pt減)。「著作利用料の支払いは当サービスが行います」
- 実務補足(個人ブログ・要公式確認): Piascoreの許諾「代理申請」はジブリ・ディズニー等一部出版社の管理曲に限定。ピアノアレンジ等「編成の異なるアレンジ」やJASRAC非管理曲は出品者自身の個別申請が必要(https://coconala.com/blogs/375221/221585/ 、https://note.com/m0chikinak0m0chi/n/n9c0601aef1c7)

### 2-3. 類似サービス

- **mucome**: 出品ガイドに「当サイトは出品者に替わってJASRAC/NexToneへ著作権処理・著作権料支払いを行う」が、「編曲・替歌・訳詞等により改変する場合は、あらかじめ**出品者様ご本人の責任で**必要な許諾手続きを」と明記。Piascoreと同一構造(https://mucome.fc2.net/)
- **@ELISE**: JASRAC許諾番号9009834009Y37019等を取得済みだが、出版社既刊譜の配信モデルが中心。個人出品時の編曲許諾ルールの明文は確認できず**不明**(https://www.at-elise.com/)

---

## 3. 正規楽譜出版社(ぷりんと楽譜・フェアリー等)の権利処理

### 3-1. ぷりんと楽譜(ヤマハ)

- 運営: ヤマハミュージックエンタテインメントホールディングス(https://www.print-gakufu.com/about/1007/)
- 出版社と音楽出版社間の個別編曲許諾契約の中身は**非公開・不明**。ただしヤマハ側FAQで「既存曲の編曲は作詞者・作曲者の意思確認が必要、通常は音楽出版社を通じて行う。JASRACは編曲権を管理していない」旨が示されており、標準フロー(出版社許諾+JASRAC出版使用料)で処理していると**推定**(https://www.ymm.co.jp/ec/product_inquiry.php?ua=pc)
- 購入者向けには「フレーズの追加・削除やアレンジ等の変更は行わず、楽譜記載どおり演奏する」ことを要求(https://www.print-gakufu.com/help/3103/)

### 3-2. フェアリー

- 1965年設立の独立系ピース楽譜出版社(https://fairysite.com/company)。**「全音系列」という関係は確認できず**(公式に記載なし)。社内の権利処理フローも非公開・**不明**(商業出版継続の事実から標準フロー処理と推定)
- 参考: **全音楽譜出版社**は自社管理曲について「編曲=オリジナル作品に何らかの手を加えること(**楽器編成の変更や移調等も該当**)」と定義し、用途別編曲申請書による事前申請を要求(https://www.zen-on.co.jp/publishing/cr/copyright/)

### 3-3. JASRAC出版使用料(楽譜)の具体的料率【公式規程】

- 内国作品: **(税抜定価 × 10% × 発行部数) ÷ 収載作品総数 = 1件単価**(1円未満切捨て)
- 最低使用料: **12円/件**
- 外国作品: サブパブリッシャー指定料率(シミュレーションページに**20%**・最低5,000円/10,000円の例示)
- 事前申込で部数控除あり(1,000部超〜5,000部の部分10%、5,000部超15%控除)
- ソース: https://www.jasrac.or.jp/users/calculation/pdf/pub-calculation1.pdf 、https://www.jasrac.or.jp/info/create/calculation/publish/score.php 、規程原文 https://www.jasrac.or.jp/aboutus/public/pdf/tariff.pdf

### 3-4. 出版社が編曲を許諾する/しないの実務

- 財産権(27条)は出版社が持っても、同一性保持権は著作者本人に一身専属 → 最終判断は著作者の意向に依存
- CARSは「**楽器編成の変更や移調すら許諾しない作曲家が実在する**」と明記(https://www.cars-music-copyright.jp/column/post-134/)

---

## 4. 個人の耳コピ(採譜)楽譜販売に必要な許諾 — 「複製」と「編曲」の区別

### 4-1. 法的整理【弁護士解説+JASRAC】

| 行為 | 該当条文 | 許諾ルート |
|---|---|---|
| 原曲に忠実な採譜(音→楽譜の媒体変換) | **複製**(21条) | JASRAC/NexTone または包括許諾サイト |
| ピアノソロ化・簡略化・別編成化など創作性を伴うアレンジ | **編曲**(27条)+同一性保持権(20条)リスク | 音楽出版社へ個別許諾 |
| 個人練習用の採譜(公表なし) | 私的使用(30条1項) | 許諾不要。**販売・配布・公開した時点で30条の範囲外** |

- 採譜=複製: JASRAC FAQ(https://secure.okbiz.jp/faq-jasrac/faq/show/458?site_domain=jp ※検索結果経由確認、原文全文は未取得)
- 複製/編曲の線引き: 弁護士解説によれば、編曲=原曲の「表現上の本質的な特徴」を維持しつつ**新たな創作的要素を加える**こと。単なる書き直し・移調・楽器転記だけでは理論上「編曲」に該当しない(https://chosakukenhou.jp/音楽の著作物における編曲と著作権の考察/)
- **ただし理論と実務に幅あり**: 全音は移調・編成変更も「編曲」と定義し、CARSは移調でも著作者が拒否しうるとする。実務は保守的に許諾を取る運用が共通推奨

### 4-2. 販売時に必要な許諾の全体像

1. **忠実な耳コピ譜** → 複製権処理のみ。Piascore等の包括許諾サイト経由なら個別契約不要で合法販売可能。自力販売ならJASRACへ出版/配信利用申込(定価10%×部数、許諾番号発行約3営業日: https://www.jasrac.or.jp/users/product/ 、https://www.jasrac.or.jp/park/procedure/procedure_p_6.html)
2. **アレンジ入り** → 音楽出版社の編曲許諾が別途必須(JASRACもPiascoreも出せない)。順序は「編曲許諾→複製・配信許諾」
3. 「採譜がどこから編曲になるか」の明確な線引きはPiascore規約・JASRAC公式のいずれにも記載なし(**不明**)。実務上ピアノソロアレンジ等は「編曲」として申請対象扱い

### 4-3. 関連判例: バンドスコア耳コピ模倣事件(東京高裁 2024年6月19日)

弁護士解説によれば、音源から忠実に採譜した耳コピ譜は**忠実ゆえ創作性がなく著作物として保護されない**と判断。一方、他社の耳コピ譜を組織的に模倣・無料公開した行為は民法709条の一般不法行為として**約1.66億円**の賠償が認容(誤記の一致、90%超の一致率等が証拠)。

- 示唆: 自作の耳コピ譜は著作権では守れないが不法行為での救済余地あり。市販スコアの写しを「耳コピ」と称して売る行為は著作権以外でも違法になりうる
- ソース: https://chosakukenhou.jp/バンドスコア耳コピ模倣は不法行為？東京高裁が/ (日経記事 https://www.nikkei.com/article/DGXZQOSG21ARH0R20C25A5000000/ は有料のため未検証)

---

## 結論サマリー

| 論点 | 結論 |
|---|---|
| JASRACの編曲権管理 | **管理していない**(公式明言)。編曲許諾はJ-WIDで特定した音楽出版社へ直接申請 |
| 手続き・費用・期間 | 統一相場なし。実例: Sony系で約4日・無料承認。一般に数週間〜数ヶ月、不許諾もある。代行手数料8,800円/曲〜 |
| Piascoreの包括許諾 | **複製・配信のみカバー。編曲には効かない**(公式規約に明記)。編曲許諾は出品者責任 |
| 正規出版社 | 音楽出版社への編曲許諾+JASRAC出版使用料(定価10%×部数、最低12円/件)の二段処理。個別契約条件は非公開 |
| 耳コピ販売 | 忠実採譜=複製→包括許諾サイトで販売可。アレンジ入り=編曲→出版社許諾が別途必須。私的使用(30条)では販売不可 |

## ソースURL一覧

**公式・団体**
- https://www.jasrac.or.jp/aboutus/copyright/
- https://www.jasrac.or.jp/en/about/copyright/
- https://www.jasrac.or.jp/aboutus/public/pdf/contract.pdf
- https://www.jasrac.or.jp/creators/contract/pdf/contract-guideline.pdf
- https://www2.jasrac.or.jp/eJwid/info/jizenkakunin.html
- https://www.jasrac.or.jp/users/internet/score/
- https://www.jasrac.or.jp/users/product/
- https://www.jasrac.or.jp/park/procedure/procedure_p_6.html
- https://www.jasrac.or.jp/users/calculation/pdf/pub-calculation1.pdf
- https://www.jasrac.or.jp/info/create/calculation/publish/score.php
- https://www.jasrac.or.jp/aboutus/public/pdf/tariff.pdf
- https://secure.okbiz.jp/faq-jasrac/faq/show/458?site_domain=jp
- https://laws.e-gov.go.jp/law/345AC0000000048/
- https://www.cars-music-copyright.jp/column/post-134/
- https://mpaj.or.jp/faq
- https://note.com/nextone_corp/n/n74678731ee19

**Piascore・販売サービス**
- https://publish.piascore.com/rights/intro
- https://publish.piascore.com/rights
- https://publish.piascore.com/term
- https://publish.piascore.com/profit
- https://mucome.fc2.net/
- https://www.at-elise.com/
- https://www.musicstore.jp/shop/getting_the_permission.php

**出版社**
- https://www.print-gakufu.com/about/1007/ ・https://www.print-gakufu.com/help/3103/ ・https://www.print-gakufu.com/help/7001/
- https://www.ymm.co.jp/ec/product_inquiry.php?ua=pc
- https://fairysite.com/company
- https://www.zen-on.co.jp/publishing/cr/copyright/
- https://www.shinko-music.co.jp/corporate/copyright/
- https://www.gakufu.co.jp/pages/permission
- https://retailing.jp.yamaha.com/library/shop/ginza/studio/henkyoku-shinsei.pdf
- https://www.shoeidogakki.com/wp-content/uploads/arrange_manual.pdf

**弁護士・専門家解説**
- https://chosakukenhou.jp/音楽の著作物における編曲と著作権の考察/
- https://chosakukenhou.jp/バンドスコア耳コピ模倣は不法行為？東京高裁が/
- https://media-law.jp/info/楽曲のカバー・アレンジを行う際の著作権処理と/
- https://shinohara-law.com/blog/2016/04/21/翻訳権、編曲権、変形権、翻案権（著作権法２７/
- https://www.nikkei.com/article/DGXZQOSG21ARH0R20C25A5000000/ (未検証)

**実務者・個人の見解**
- https://nishimurahiroya.com/楽譜販売のために編曲許諾をソニーミュージック/
- https://note.com/m0chikinak0m0chi/n/n9c0601aef1c7
- https://mirymh.mirymiry.com/2021/06/05/arrangement-right/
- https://coconala.com/blogs/375221/221585/
- https://kujira.office-isana.jp/blog/20200421/
- https://www.with-bright-web.com/single-post/musiccopy
- https://wellen.jp/music-production/ear-copy-copyright/
- https://copyright-topics.jp/topics/arrangement-copyright/
- https://dtm-play.com/1040
- https://triokini.com/triolab/entries/72
