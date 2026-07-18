> 【歴史的記録】本書は作成時点の前提・知見に基づくスナップショットです。その後の決定により一部前提は更新されています。現在の前提は `README.md`・`docs/requirements/product-vision.md`・`docs/research/gate-execution-spec.md`(最新改訂) を参照してください。

**調査結果**
検索日: 2026-07-19 JST。論文・出版社ページ・PubMed・J-STAGE中心に確認しました。

## 0. 総括

AI採譜アプリの「絶対音感エミュレータ」は、人間APをそのまま「全ての音を常時音名化する超能力」と捉えるより、次のモデルで設計するのが妥当です。

- 確立: APは「参照音なしで孤立音の音名/ピッチクラスをラベル化する能力」。ただし音色、音域、白鍵/黒鍵、文脈で精度が変わる。
- 確立: 人間はF0を連続量として聴くだけでなく、注意・音源分離・カテゴリ・長期記憶・言語ラベルを使って音を扱う。
- 論争中: 臨界期は強いが、成人でも訓練で一部AP的判断を獲得できる。自然APと同質かは未決着。
- 見つからず: ヒンディー語圏話者を対象にしたAP保有率・AP訓練の直接研究は、今回のWeb調査範囲では確認できなかった。

## 1. 絶対音感の認知科学・神経科学

**確立した知見**

APの古典的定義は、外部参照なしで音高を同定/産出する能力。Takeuchi & Hulseの総説は今も基礎文献です。一般人口の「1万人に1人」推定はよく引用されますが、近年の体系的レビューでは、AP判定課題の閾値・音色・音域・半音誤差許容が研究ごとに大きく異なるため、保有率比較はかなり不安定です。  
出典: Takeuchi & Hulse 1993, DOI: [10.1037/0033-2909.113.2.345](https://pubmed.ncbi.nlm.nih.gov/8451339/) / Bairnsfather et al. 2025, DOI: [10.3758/s13428-024-02577-z](https://link.springer.com/article/10.3758/s13428-024-02577-z)

神経科学的には、左側頭・上側頭溝、planum temporale、左背外側前頭前野、聴覚-言語ラベル連合が関与するという見方が強いです。APは単なる高精度F0検出ではなく、音高カテゴリと verbal label の連合記憶です。  
出典: Zatorre 2003, DOI: [10.1038/nn1085](https://pubmed.ncbi.nlm.nih.gov/12830161/) / Schulze et al. 2013, DOI: [10.1002/hbm.22010](https://pmc.ncbi.nlm.nih.gov/articles/PMC6870281/) / Keenan et al. 2001, DOI: [10.1006/nimg.2001.0925](https://www.sciencedirect.com/science/article/pii/S1053811901909255)

遺伝要因は「ある」が、単一遺伝子ではない。家族集積、双生児一致率、8q24.21連鎖などは支持材料ですが、環境・早期訓練・偶然性も絡む複合形質です。  
出典: Baharloo et al. 1998, DOI: [10.1086/301704](https://pmc.ncbi.nlm.nih.gov/articles/PMC1376881/) / Theusch et al. 2009, DOI: [10.1016/j.ajhg.2009.06.010](https://pubmed.ncbi.nlm.nih.gov/19576568/) / Theusch & Gitschier 2011, DOI: [10.1375/twin.14.2.173](https://pubmed.ncbi.nlm.nih.gov/21425900/)

**論争中**

成人習得は「不可能」から「一部可能」へ変わっています。2019-2025年の訓練研究では、成人が数十時間の訓練でAP的音名判断を改善し、一部は高精度に到達。ただし、音色・オクターブ・文脈への汎化が弱い例があり、自然APと同質かは未決着です。  
出典: Van Hedger et al. 2019, DOI: [10.1371/journal.pone.0223047](https://pubmed.ncbi.nlm.nih.gov/31550277/) / Wong et al. 2020, DOI: [10.3758/s13414-019-01869-3](https://link.springer.com/article/10.3758/s13414-019-01869-3) / Wong et al. 2025, DOI: [10.3758/s13423-024-02620-2](https://link.springer.com/article/10.3758/s13423-024-02620-2)

**設計示唆**

NF-050二層原則は妥当です。第1層はF0/倍音/音源候補の連続推定、第2層は音名カテゴリ・調律体系・文脈ラベル化。最初からMIDI音符へ丸めると、人間APの「カテゴリ化前の曖昧さ」と「注意選択」を失います。

## 2. 声調言語との相関

**確立した知見**

Deutschらは、北京語・ベトナム語話者が発話時に安定した絶対的F0パターンを保つこと、また中国の音楽院学生でAP率が高いことを報告しました。声調言語経験が音高ラベル化に有利に働く可能性は強い候補です。  
出典: Deutsch, Henthorn & Dolson 2004, DOI: [10.1525/mp.2004.21.3.339](https://cir.nii.ac.jp/crid/1363107370041035776) / Deutsch et al. 2006, DOI: [10.1121/1.2151799](https://cir.nii.ac.jp/crid/1361981470827678976)

**論争中**

「声調言語がAPを直接生む」とまでは言えません。早期音楽教育、固定ド教育、選抜、文化圏、テスト方法が交絡します。近年の個人差研究では、声調言語背景の効果が単純な優位として出ない条件もあります。  
出典: Hedger et al. 2018, DOI: [10.1016/j.actpsy.2018.10.007](https://www.sciencedirect.com/science/article/pii/S0001691818301409)

**設計示唆**

声調言語的な「F0輪郭カテゴリ」は、録音中の声・環境音の分離に有用。ただし音名化は西洋12平均律固定ではなく、話者・楽器・文化文脈ごとのカテゴリ辞書を差し替え可能にするべきです。

## 3. AP者の音処理メカニズム

**確立した知見**

AP者でもピアノ音が最も得意、純音・声・弦などで低下します。音色依存性はかなり堅い知見です。Miyazakiはピアノ > 純音、Vanzella & Schellenbergは声で成績低下、Liは上海音大生でピアノ音優位を報告。  
出典: Miyazaki 1989, DOI: [10.2307/40285445](https://cir.nii.ac.jp/crid/1360574094906667904) / Vanzella & Schellenberg 2010, DOI: [10.1371/journal.pone.0015449](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0015449) / Li 2021, DOI: [10.1177/0305735619893437](https://journals.sagepub.com/doi/10.1177/0305735619893437)

APは自動的ラベリングを伴いますが、「世界の全音を常に音名化する」とまでは一般化できません。Auditory Stroopでは音名ラベル干渉が見られ、P300研究ではAP者は音高テンプレートにより作業記憶更新負荷が小さい可能性が示されます。  
出典: Klein et al. 1984, DOI: [10.1126/science.223.4642.1306](https://pubmed.ncbi.nlm.nih.gov/17759367/) / Schulze et al. 2013, DOI: [10.1002/hbm.22010](https://pmc.ncbi.nlm.nih.gov/articles/PMC6870281/)

雑音・非楽音では、音源分離、倍音性、ピッチ強度、時間的手がかりが重要です。  
出典: Fujisaki & Kashino 2005, DOI: [10.3758/BF03206494](https://pubmed.ncbi.nlm.nih.gov/15971694/) / Micheyl & Oxenham 2010, DOI: [10.1016/j.heares.2009.09.012](https://www.sciencedirect.com/science/article/pii/S0378595509002366)

**設計示唆**

F-108フィールド録音モードは「全周波数を音符化」ではなく、`音源候補 → ピッチ強度 → 倍音性 → 注意ゲート → 音名化` の順にする。低信頼フレームは休符/ノイズ/不明として残す方が、人間APに近いです。

## 4. インド音楽圏

**確立した知見**

北インド音楽の知覚研究は、固定絶対音よりも tonic/sa を中心にした相対的階層、raga、thaat、tambura drone の影響を扱うものが中心です。  
出典: Castellano, Bharucha & Krumhansl 1984, DOI: [10.1037/0096-3445.113.3.394](https://pubmed.ncbi.nlm.nih.gov/6237169/) / Vaughn 1993, DOI: [10.1080/07494469300640321](https://www.tandfonline.com/doi/abs/10.1080/07494469300640321)

工学系では、raga認識、svara分布、shrutiを含む特徴量、shadja検出の研究があります。これは「インド音楽版AP」ではなく、可動Saを基準にした相対ピッチ/旋律文脈のモデル化です。  
出典: Koduri et al. 2012, DOI: [10.1080/09298215.2012.735246](https://www.tandfonline.com/doi/full/10.1080/09298215.2012.735246) / Koduri et al. 2014, DOI: [10.1080/09298215.2013.866145](https://www.tandfonline.com/doi/full/10.1080/09298215.2013.866145) / Swaragram 2023, DOI: [10.1016/j.simpa.2022.100462](https://www.sciencedirect.com/science/article/pii/S2665963822001464)

**見つからなかった領域**

ヒンディー語話者、ヒンディー語圏音楽家、またはインド古典音楽家を対象にしたAP保有率の直接調査は、今回のWeb検索では確認できませんでした。

**設計示唆**

インド音楽対応では、A4=440固定のAP分類より、`推定Sa`、ragaごとのsvara分布、shruti/装飾音の連続ピッチを保持する必要があります。MIDI化も12平均律固定だけでは不十分です。

## 5. 日本の研究

**確立した知見**

日本の音大生・音楽学生ではAP率が高い報告があります。日本-ポーランド比較では、95%正答基準の正確APが日本30%、ポーランド7%。背景として早期ピアノ、固定ド、ヤマハ等の幼児教育が挙げられています。  
出典: Miyazaki, Makomaska & Rakowski 2012, DOI: [10.1121/1.4756956](https://cir.nii.ac.jp/crid/1050282814215146368)

江口式/Chord Identification Methodは、2-6歳児への長期訓練でAP獲得を報告。ただし、ランダム化対照試験としての強さや外部再現性には限界があり、「幼児なら誰でも保証」とは言えません。  
出典: Sakakibara 1999, DOI: [10.5926/jjep1953.47.1_19](https://www.jstage.jst.go.jp/article/jjep1953/47/1/47_19/_article) / Sakakibara 2014, DOI: [10.1177/0305735612463948](https://journals.sagepub.com/doi/abs/10.1177/0305735612463948)

東西比較では、日本学生はAPが高い一方、相対音感は低い分類もあり、APは音楽能力全体の代替指標ではありません。  
出典: Miyazaki et al. 2018, DOI: [10.1525/mp.2018.36.2.135](https://cir.nii.ac.jp/crid/1873398392872304768)

**設計示唆**

アプリは「絶対音名が出る」だけを価値にしない。相対音感的な機能、調性感、移調、コード機能、可動ドも並行表示するべきです。

## 6. 工学的示唆

**確立した技術知見**

機械のF0推定は連続周波数を追う処理です。YIN/pYIN/CREPE/Basic Pitch系は有力ですが、人間APのカテゴリ・注意・言語ラベル処理とは別物です。  
出典: YIN, DOI: [10.1121/1.1458024](https://pubmed.ncbi.nlm.nih.gov/12002874/) / pYIN, DOI: [10.1109/ICASSP.2014.6853678](https://humlab-speech.github.io/superassp/reference/pyin.html) / CREPE, ICASSP 2018: [GitHub/論文情報](https://github.com/marl/crepe) / Basic Pitch, ICASSP 2022: [Spotify Engineering](https://engineering.atspotify.com/2022/6/meet-basic-pitch)

**見つからなかった領域**

「人間の絶対音感を、雑音混じり日常録音から選択抽出して音符化する計算モデル」として直撃する研究は見つかりませんでした。近いのは、AP認知モデル、F0推定、AMT、auditory scene analysis、raga/svara特徴量です。

**F-108 / NF-050への具体実装方針**

- F-108: フィールド録音は `voicing / harmonicity / pitch strength / onset / source separation` で候補抽出し、音名化しないノイズを明示的に捨てる。
- NF-050: 第1層に連続F0・倍音・信頼度・音源IDを保持し、第2層で12平均律/可動Sa/raga/調性へ写像する。
- 音色別キャリブレーションを入れる。ピアノ、声、弦、環境音で別モデルまたは別閾値。
- 出力は単一MIDIではなく、`候補音符 + confidence + pitch bend + non-note event` を持たせる。
- 「APらしさ」は高精度F0ではなく、注意ゲートとカテゴリ化。UIにも「音符化した理由/捨てた理由」を出す。

Slack作業ログ: Slack connector のインストールを要求しましたが `user_confirmed=false` で、現在の環境に `send_message` 直接送信ツールが公開されていないため未投稿です。
