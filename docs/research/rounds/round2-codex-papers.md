## 1. 自炊代行事件の正確な判例状況

- 対象判決は、知財高判平成26年10月22日・平成25年（ネ）10089号「著作権侵害差止等請求控訴事件」。
  原審は東京地判平成25年9月30日・平成24年（ワ）33525号。
  判決本文データベース: https://tyosaku.hanrei.jp/hanrei/cr/10864.html

- 判断の中核は、利用者ではなく自炊代行業者が「複製主体」だという点。
  知財高裁は、書籍を裁断しスキャンして電子ファイル化する物理的な複製行為を、サービス運営者が業務として行い、利用者はその作業に関与していないと見た。したがって、利用者が書籍を購入・送付し、対象書籍を選ぶとしても、複製行為それ自体は業者の管理・支配下にあると評価された。

- 著作権法30条1項の私的複製については、同条の「その使用する者が複製する」という要件を満たさないと判断。
  判決は、私的複製の趣旨を、閉鎖的な私的領域内の零細な複製に限定し、外部者の介入による複製量増大を抑えるものと捉えている。独立した複製代行業者が反復継続して電子化する場合、利用者の私的目的があっても30条1項の適用は否定される。

- 「営利性」「業として」は、30条1項の直接要件というより、外部の独立業者が事業として複製工程を担っていることを示す事情として効いている。
  つまり、単なる非営利の手助け一般まで同じ射程で違法とする判示ではなく、本件では「業者がサービスとして複製行為を遂行した」点が決定的。

- 評釈では田村善之教授が、知財高裁は地裁のような「枢要な行為」論よりも、物理的複製行為を誰が行ったかを重視したと整理している。
  評釈: Westlaw Japan「第40号 自炊代行控訴審判決」https://www.thomsonreuters.co.jp/ja/westlaw-japan/column-law/2015/150105/
  NDL書誌: 田村善之「重要知財判例評釈(第1回)…」IPマネジメントレビュー17号、2015年6月、p.36-46 https://ndlsearch.ndl.go.jp/books/R000000004-I026549420

- 最高裁段階は「最高裁判決」ではなく、上告受理申立ての不受理。
  小学館の当事者発表によれば、2016年3月16日付で上告受理申立不受理決定がされ、原告勝訴が確定した。
  出典: 小学館プレスリリース https://www.shogakukan.co.jp/news/137614

## 2. JASRAC音楽教室訴訟の使用料の正確な文脈

- 最高裁の結論は二段階。
  JASRAC発表によれば、教師の演奏・録音物再生については、音楽教室事業者側の上告受理申立てが2022年7月28日に不受理。生徒の演奏については、JASRACの上告が2022年10月24日に棄却された。
  出典: JASRAC「音楽教室における請求権不存在確認訴訟の最高裁の判断について」https://www.jasrac.or.jp/information/release/22/10_2.html

- 最高裁判決そのものは、令和3年（受）1112号・令和4年10月24日・最高裁第一小法廷・民集76巻6号1348頁。
  生徒の演奏について、音楽教室運営者は利用主体ではないと判断。
  裁判情報: https://legaldoc.jp/hanrei/hanrei-detail?c=1&id=91473

- 「年額750円」は、2025年2月28日にJASRACが文化庁長官へ届け出た新使用料規程の数字。
  旧来の「受講料収入算定基準額の2.5%」型から、楽器系音楽教室については「教師による楽器演奏等」に限定した別規程へ切り分けられた。
  JASRAC告知: https://www.jasrac.or.jp/information/topics/25/250228.html
  使用料規程抜粋PDF: https://www.jasrac.or.jp/information/topics/pdf/amended-tariffs.pdf

- 現行スキームの骨子:
  - 対象: 個人経営教室を除く音楽教室で、教師が著作物を楽器演奏等する場合。
  - 生徒による楽器演奏等は使用料支払いの対象外。
  - 年間包括許諾: 受講者1名につき年額750円。ただし中学生以下は1名につき年額100円。いずれも税別。
  - 年間包括によらない場合: レッスン1回あたり受講者1名につき60円。60分超は60分ごとに同額加算。
  - 曲別の場合: 1曲1回・5分まで受講者1名につき30円。5分超は5分ごとに同額加算。
  - 年間包括の受講者数は、年度内の算定基準月1か月間の在籍人数。
  - JASRACページ上の実務手続は、年1回の受講者数報告、3か月に1回の利用曲目報告、JASRACからの請求書払い。
  手続ページ: https://www.jasrac.or.jp/users/facilities/musiclesson.html
  規程抜粋: https://www.jasrac.or.jp/users/facilities/pdf/facility8.pdf

- 「和解」ではなく、より正確には、音楽教育を守る会とJASRACの「新たな音楽教室規定に関する合意」と、その後の使用料規程変更届出。
  PR Times上のJASRAC発表では、最高裁判決後2年かけて協議し、管理開始時期である2018年4月に遡って支払う運用と説明されている。
  出典: https://prtimes.jp/main/html/rd/p/000000079.000071197.html

## 3. 合成データ学習の研究

- Slakh2100は、Lakh MIDI Dataset由来のMIDIをプロ仕様のサンプルベース音源でレンダリングした、マルチトラック音源・ステム・MIDIの合成データセット。
  公式説明では、2100曲・145時間のミックス、187パッチ・34クラス。
  論文: Manilow et al., “Cutting Music Source Separation Some Slakh,” WASPAA 2019, DOI: 10.1109/WASPAA.2019.8937170
  MERL: https://www.merl.com/publications/TR2019-124
  Slakh: https://www.slakh.com/

- Slakhはもともと音源分離研究向けだが、MT3では多楽器自動採譜データセットの一つとして利用されている。
  MT3論文は、MAESTRO、Slakh2100、Cerberus4、GuitarSet、MusicNet、URMPを混合学習し、統一Transformerで多楽器採譜を行う。
  論文: Gardner et al., “MT3: Multi-Task Multitrack Music Transcription,” ICLR 2022 / arXiv:2111.03017, DOI: 10.48550/arXiv.2111.03017
  https://arxiv.org/abs/2111.03017

- MT3のSlakh2100上の主な精度:
  - Full mixture学習: Slakh2100のOnset F1 = 0.76、Onset+Offset+Program F1 = 0.57。
  - Slakh2100/Cerberus4を訓練から外すゼロショット条件: Slakh2100のOnset F1 = 0.14、Onset+Offset+Program F1 = 0.02。
  これは「合成データを含めるとその合成ドメインでは効くが、当該ドメインを外すと楽器識別込み採譜が大きく落ちる」ことを示す。

- 実録音とのドメインギャップについては、Slakh論文・公式ベンチマークが音源分離で定量化している。
  MUSDB18実録音テストで、Slakhのみ43時間学習はBass SI-SDR -2.4 dB / Drums -0.7 dB。一方、MUSDB18 5時間のみはBass -0.5 / Drums 2.2、MUSDB18+Slakh 48時間はBass 1.3 / Drums 3.6。
  つまり、合成のみは実録音に弱いが、実録音に合成を足す拡張は有効。

- NoteEMは「合成データで初期学習し、未整列スコアと実録音をEM的に整列して学習」する方式。
  MAPSでnote-level F1 87.3%を報告し、教師あり手法86.4%を上回ると主張。MAESTRO訓練データなしのクロスデータセット評価でnote F1 89.7%、frame F1 77.0%も報告している。
  論文: Maman & Bermano, “Unaligned Supervision for Automatic Music Transcription in the Wild,” ICML 2022, PMLR 162:14918-14934
  https://proceedings.mlr.press/v162/maman22a.html

## 4. 整譜・rhythm quantization・score engravingの教師データ問題

- ASAPは、整譜・拍節推定・リズム量子化に最も近い公開データセットの一つ。
  MusicXML/MIDIの楽譜、演奏MIDI/音声、拍・小節頭・拍子・調号アノテーションを持つ。GitHubの現行READMEでは、222譜面、1067演奏、519音声演奏を掲げる。
  公式: https://github.com/fosfrancesco/asap-dataset
  論文: Foscarin et al., “ASAP: a dataset of aligned scores and performances for piano transcription,” ISMIR 2020, pp.534-541

- ライセンスはCC BY-NC-SA 4.0。商用学習・商用プロダクト組込みにはそのまま使いにくい。
  ASAP公式README: https://github.com/fosfrancesco/asap-dataset

- ASAPは「人間の演奏を人間的な楽譜へ戻す」研究には有用だが、完全な商用整譜教師データとしては不足がある。
  README自身が、スコアは非専門家作成由来で修正済みだが問題が残る、pickup/rubato/装飾音などで拍位置を厳密に決められないケースがある、beaming/tuplet creationやexpressive performance renderingは未検証と明記している。

- OMR領域にはDeepScores、MUSCIMA++、PrIMuS、DoReMi、OpenScoreなど多数のデータセットがあるが、主目的は画像から記号・譜面構造を読むこと。
  これらは「音声/MIDI演奏から、人間の記譜慣習に沿ったMusicXMLを出す」教師データとは別物。
  OMR-Datasets一覧: https://apacha.github.io/OMR-Datasets/

- 結論として、整譜モデルのボトルネックは「音高・オンセット正解」よりも、声部分離、拍子推定、小節割り、連桁、タイ/スラー、付点/三連符、休符の補完、読みやすさの規範を含む教師データ。
  ASAPは有力な研究起点だが、商用AI採譜で必要な多ジャンル・多楽器・商用利用可の人間校訂MusicXML教師データは、公開領域ではまだ薄い。

## 5. 非西洋記譜の自動採譜研究の成熟度

- 今回確認できた範囲では、sargam、簡譜、箏譜について、MAESTRO/Slakh/ASAP級の「音声・演奏・記譜が整列し、ライセンスが明確で、ベンチマーク精度が蓄積している」公開データセットは見当たらない。
  研究実装は散発的にあるが、実運用可能なAMT基盤としては西洋五線譜・ピアノ・ギター・一部多楽器に比べて未成熟。

- インド古典音楽では、採譜そのものより、raga/tonic/歌唱特性など高次属性のデータセットが目立つ。
  例: KritiSamhitaは南インド古典音楽のtonic classification用音声データセットで、Open Access / Creative Commons license。20秒スニペットとtonicラベルを提供するが、sargam記譜への詳細採譜教師データではない。
  DOI: 10.1016/j.dib.2024.110730
  https://www.sciencedirect.com/science/article/pii/S2352340924006978

- 簡譜/Jianpuについては、OMR・画像抽出寄りの研究が出ている。
  2026年の “Multi-Source Melody Pipeline” は、MIDI/MusicXML/Jianpu画像/五線譜画像をイベント表現へ寄せるプロトタイプを報告し、Jianpu画像ではVLMを使う。292ページで80.1%の構造受理率、50ページ手動GTで拍子 exact 95.8%、調性 pitch-class 77.1%、テンポ±5 BPM一致100%などを報告。ただし、これは構造受理・メタ情報精度であり、完全な採譜精度ではない。
  DOI: 10.3390/computers15050298
  URL: https://www.mdpi.com/2073-431X/15/5/298

- 箏譜については、少なくとも英語・日本語Web検索で、ライセンス明記の大規模公開データセットや標準ベンチマークは確認できなかった。
  プロダクト化するなら、独自収集・専門家校訂・権利処理が前提になる可能性が高い。

- したがって非西洋記譜対応は、既存AMTモデルの出力をそのまま変換するだけでは不十分。
  必要なのは、各記譜体系ごとの音高表現、装飾、拍節、旋法、奏法記号、教育現場での表記慣習を教師データ化する工程。

## 6. 市場レポートの信頼性検証

- “Music Learning Apps market $2.1B→$6.8B CAGR 13.7%” という完全一致の一次出典は、今回のWeb検索では確認できなかった。
  近い数字として、DataInsightsReportsに「Music Learning Apps market」「CAGR 13.7%」「2026年 $1.73B / グラフ上 $1.95B」のような記載があるが、出典方法・サンプル・推計式が公開ページ上で検証できず、典型的なSEO型マーケットレポート販売ページとして扱うべき。
  https://www.datainsightsreports.com/reports/music-learning-apps-market-101563

- ResearchAndMarkets上のAstute Analyticaレポートでは、Kids Music Learning Appsについて、2021年 $198.76M → 2030年 $584.90M、CAGR 12.9%と記載。
  ただし、これは「kids」に限定された市場であり、AI採譜や大人向け音楽学習アプリ全体のTAMとは一致しない。
  https://www.researchandmarkets.com/reports/5638901/global-kids-music-learning-apps-market-by

- ResearchAndMarkets上のExpert Market Researchレポートでは、Online Music Education Marketについて、2024年 $3.77B → 2034年 $13.03B、CAGR 13.20%。
  これはアプリ単体ではなくオンライン音楽教育全体。
  https://www.researchandmarkets.com/reports/6111875/online-music-education-market-growth-analysis

- Mordor Intelligenceは、Online Music Education Marketについて、2025年 $3.9B、2026年 $4.61B、2031年 $9.36B、CAGR 15.23%を提示。
  これも音楽学習アプリ単体ではなく、オンライン音楽教育市場。
  https://www.mordorintelligence.com/industry-reports/online-music-education-market

- Statistaは、音楽学習単体ではなくEducation Apps全体の推計として、2026年世界収益 $29.69B、2031年 $50.19B、CAGR 11.07%を提示。
  定義はアプリストア由来のIAP/有料アプリ/広告収益で、アプリ外サブスクは除外。
  https://www.statista.com/outlook/amo/app/education/worldwide/

- 信頼性の扱い:
  - “$2.1B→$6.8B CAGR 13.7%” は、現時点では投資資料にそのまま載せるには弱い。出典名、発行者、調査対象、地域、期間、売上定義を確認するまで「未検証の市場レポート値」と明記すべき。
  - 代替としては、TAMを「Online Music Education」から上限推計し、SAMを「Music learning apps / kids music learning apps / ear training / sheet music / transcription tools」に分解する方が堅い。
  - 最も使いやすい公開代替値は、StatistaのEducation Apps全体、ResearchAndMarkets/MordorのOnline Music Education、AstuteのKids Music Learning Apps。ただし、いずれもAI採譜市場そのものではないため、AI採譜プロジェクトの市場規模にはボトムアップ推計を併用すべき。
