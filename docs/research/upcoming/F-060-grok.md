# 音楽採譜/記譜ソフトの「移調・キー変更」  
## X（旧Twitter）実務者・研究者・開発者投稿 調査レポート

**調査日:** 2026-07-21  
**収集範囲:** X 実投稿（英語中心、中国語は得られる範囲で補足）  
**対象機能:** 移調再生（playback transpose）／移調譜生成（score/part transpose）／移調楽器（written vs sounding / concert pitch）  
**収集軸:** 失敗例（厚め）／成功例／限界／ベストプラクティス／最新トレンド  

---

## 1. 調査サマリー（先に結論）

| 軸 | 現場で繰り返し出る論点 |
|---|---|
| **失敗** | 移調楽器（特にホルン）のピッチ崩れ、異名同音の自動簡略化、MusicXML往復、楽器差し替え時の自動移調の不安定、無料/クラウド版での移調ロック、AI/PDFからの移調失敗 |
| **成功** | concert pitch で書いてから transposed 表示に切替えるワークフロー、Dorico の score/part 整合、クラウド視聴側でのキー合わせ、スキャン→移調→MusicXML の新導線 |
| **限界** | 「C譜（実音）」主流化とパート抽出の衝突、無調音楽での移調譜視認性、異名同音の音楽的意味の喪失、DAW/MIDIと記譜の二重モデル |
| **BP** | 最初に正しい楽器定義、written/sounding の分離、best practices 準拠のレイアウト、検証済み MusicXML のみ信頼 |
| **トレンド** | クラウド移調ビューア、OMR/スキャン→即移調、コラボ記譜の移調楽器サポート、教育向け「簡譜+自動転調」 |

> **調査バイアス:** X上の「移調×記譜ソフト」深掘り投稿は英語の製譜家・開発者・奏者が中心。中国語は「転調/移調」自体の語は多いが、**ソフト機能トラブルの実務ログは相対的に薄い**（Weibo / B站 / 小红书 側に寄っている可能性が高い）。

---

## 2. 失敗例・摩擦・限界（厚め）

### 2.1 移調楽器まわりの致命的失敗

#### F.1 ホルンがどうしても合わない（Finale）
オペラ全曲スコアで、Score Manager で Horn in F のキーを合わせても**音高が間違う**。移調楽器そのものへの強い嫌悪感を表明。

> “I hate transposing instruments… no matter what I do, I can't get the French Horns right… the pitch is wrong”  
> — Sanford Schimel (@SanfordBaritone), 2023-01-05  
> https://x.com/SanfordBaritone/status/1610971561963421697

公式返信はサポート誘導のみで、現場の「なぜ壊れるか」は解消されていない。

#### F.2 バグパイプは移調対象外（Finale）
特定楽器で自動移調が効かない。理論知識がある人は自力で書けるが、**ソフトの保証範囲外**が露呈。

> “Just found out that #Finale doesn't transpose the #bagpipes.”  
> — Jamey Aston (@JameyAston), 2022-09-28  
> https://x.com/JameyAston/status/1574987771651190785

#### F.3 楽器差し替え＋自動移調が「当たり外れ」（MuseScore）
「楽器を置き換えて自動で移調・クレフ変更」こそ購入理由だったのに、**hit or miss** と断言。

> “The one big thing I bought it for, replacing instruments and having it automatically transpose and change clef, it only does hit or miss.”  
> — Populo Iratus (@astronomy89), 2025-08-23  
> https://x.com/astronomy89/status/1959110297878503519

#### F.4 移調楽器の装飾音再生がズレる（開発者自己報告）
ScoreTail が、クラリネット/サックス部で ornament playback が「おかしく聞こえる」問題を修正したと告白。**譜面移調と再生移調は別レイヤ**であり、片方だけ正しいと「耳が矛盾する」失敗が起きる。

> “If you've ever played back a clarinet or sax part… and thought ‘that turn sounds… off’ — you were right!”  
> — ScoreTail (@ScoreTail), 2026-07-19  
> https://x.com/ScoreTail/status/2078674652088647928

---

### 2.2 異名同音・調号・コード記号の破壊

#### F.5 調内の E# を F に書き換え（Finale）
F# 調のコードで `F#/E#` が勝手に `F#/F` になる。**理論的に正しい異名同音をソフトが“簡略化”して壊す**典型。

> “Why when I’m writing chords in the key of F# does Finale 25 keep changing the E# in F#/E# to F#/F?”  
> — Micah Burgess (@micahburgess), 2020-07-14  
> https://x.com/micahburgess/status/1282848422148612098  
> 続報: “confused about enharmonics… this is IN the key!”  
> https://x.com/micahburgess/status/1282849258585161728

#### F.6 「C譜」主流化がパート制作を地獄化（製譜家）
実音（sounding）で書かれたスコアが増え、指揮者/作曲家には楽でも、**移調楽器パートでは E#/B# や Fb/Cb を避ける必要**があり、抽出時に巨大な問題になる。

> “scores today are written ‘in C’… as sounding, not as the player needs to read them.”  
> — Michele Galvagno (@m_galvagno), 2025-09-28  
> https://x.com/m_galvagno/status/1972194815556366713  
> “for transposing instruments, E#/B# and Fb/Cb should be avoided.”  
> https://x.com/m_galvagno/status/1972195066987811209

#### F.7 異名同音の“読みやすさ”と“調性感”のトレードオフ（中文・理論寄り）
C# major を Db に移調すれば視奏は楽だが、**調式の色彩が薄れる**——長期的には有害、という学習論的批判。

> “Bach 的 prelude… in C#major 移调到 Db 可能会更容易视奏，但长远看则有害。”  
> — @Noah607149441, 2023-12-20  
> https://x.com/Noah607149441/status/1737359740814971095

---

### 2.3 入出力・交換フォーマットの失敗

#### F.8 MusicXML で移調楽器が壊れる
Sibelius では key sig なしのホルンが、Finale に import するとキーが付き、**音符が不正**になる報告。

> “bug related to export / import of transposing instruments w/o a key signature… On import into @finaleofficial , key is shown, notes are incorrect”  
> — Robert Puff (@robertpuff), 2020-03-01  
> https://x.com/robertpuff/status/1234251912402198530

#### F.9 PDF→移調は依然として実用に耐えない
シートミュージック PDF を取り込み、使える形で移調させることに **Claude も完全失敗**、という2026年時点の不満。

> “still can’t ingest a sheet music PDF and transpose the music in a usable manner… Claude completely failed”  
> — @SturgePow, 2026-03-23  
> https://x.com/SturgePow/status/2036219083952193957

#### F.10 転写物への不信 → 結局手打ち
PDF は「そのまま演奏」、調整・移調が必要なら MuseScore/MusicXML 希望だが、**検証されていない転写は信用せず自分で書く**。

> “If I need to make adjustments, transposition… musescore file pr MusicXML… I don't trust the transcribers”  
> — Magnus Tipsmark (@MagnusTipsmark), 2026-02-20  
> https://x.com/MagnusTipsmark/status/2024802667780866226

---

### 2.4 UX・課金・プラットフォーム分断

#### F.11 移調が有料壁（MuseScore.com / Premium）
間違ったキーで覚えてしまったのに、**移調のためだけに Premium を払いたくない**。

> “learnt a piece… in the wrong key… not willing to pay for musescore premium to transpose it”  
> — Lou (@pollutedriver), 2025-10-02  
> https://x.com/pollutedriver/status/1973654547383066815

#### F.12 Web に Transpose ボタンがあるのに Web では使えない
サイト上の Transpose が、実際はモバイル限定——**UI の嘘/レガシー**。

> “Why is there a transpose button on the musescore website when we can only transpose a piece on mobile? … quite janky”  
> — Sinéad O'Donnell-Stolz (@TheHooseMoose), 2023-06-09  
> https://x.com/TheHooseMoose/status/1667202512452026373

#### F.13 Sibelius 無料版で Transpose すら封じ
PDF 書き出しも Transpose ボタンも不可。**サブスク強制**への強い反発。

> “Sibelius free version not letting you export as PDF or even use the transpose button is criminal.”  
> — Evan Shay (@evanallenshay), 2025-08-29  
> https://x.com/evanallenshay/status/1961540091949506703

#### F.14 concert pitch / sounding 入力の表示バグ（Dorico）
Input Pitch を Sounding にしているのに、プレビュー灰色音符が written で出る。**再起動しても持続**するとの報告。

> “Input PitchをSounding Pitchにしてるのに、灰色音符がwritten pitchで出てくるバグっぽい現象”  
> — 八谷誠人 (@m_yatani), 2024-10-13  
> https://x.com/m_yatani/status/1845519808672247911

#### F.15 layout 間の clef 変更 × 移調式が地獄（Dorico・製譜家）
score/part は原則堅牢でも、**concert pitch と notated pitch で同じ移調式を共有する clef 変更**は痛い。

> “clef changes in different layouts are a pain, especially if they are using the same transposing formula (concert pitch vs notated pitch).”  
> — Michele Galvagno (@m_galvagno), 2025-09-21  
> https://x.com/m_galvagno/status/1969658352054780416

---

### 2.5 認知・教育・ワークフロー上の失敗

#### F.16 「移調楽器の記譜は地獄」
DTM 作曲者側の率直な悲鳴。

> “Transposing instruments notation is hellll”  
> — Heosmin (@HeoMusic), 2024-09-27  
> https://x.com/HeoMusic/status/1839506853648118016

#### F.17 無調音楽では「移調譜をプロが読める」が通用しない
調性音楽ならまだしも、**無調では指揮スコアは concert pitch 一択**、という音楽理論・教育側の強い主張。

> “For atonal music it’s a gigantic pain… you should just give the conductor a score in concert pitch”  
> — Robert Komaniecki (@Komaniecki_R), 2024-03-25  
> https://x.com/Komaniecki_R/status/1772365942095306882

#### F.18 絶対音感と移調の衝突
無伴奏でトニックがずれると、**楽譜の音と頭の中の音が衝突して歌えなくなる**。移調機能の「正しさ」以前に、人間のピッチ認知がボトルネック。

> “When we sang unaccompanied & shifted the tonic she couldn’t sing & read off the score”  
> — @terrawuzhere, 2024-09-18  
> https://x.com/terrawuzhere/status/1836395362187161777

#### F.19 concert pitch でパート印刷＝「チート」自覚
移調スキル不足を、**実音印刷で回避**している自己批判。再生・譜面は合っても、教育的には失敗モード。

> “Printing trumpet and horn parts in concert pitch is a bit of a cheat!”  
> — @teepeemusic, 2026-06-17  
> https://x.com/teepeemusic/status/2067291728315322635

#### F.20 UX のレガシー深淵（Tantacrul / MuseScore）
パートの移調設定が「右クリック → Stave/Part properties の下の方」——**発見不能な UX** を本人が認める。

> “It's a legacy thing and I know the UX is miserable”  
> — Tantacrul (@Tantacrul), 2024-08-27  
> https://x.com/Tantacrul/status/1828460182315139095

#### F.21 中文圏：五線譜の調号と首調/固定調の混乱
「1=bA を C=do に書き換えると調号だらけで眩暈」「F調の数字譜と五線の対応が分からない」——**記譜法切替＝広義の移調**でつまずく層が厚い。

- 五線の絶対Cと首調転写の混乱: https://x.com/Pp88i/status/2048992350735925495  
- 調号・指法・数字の解釈失敗: https://x.com/tube1925/status/2050193747875651878  

---

## 3. 成功例・効いている使い方

### S.1 MuseScore の Concert Pitch チェックボックス
移調楽器を扱う奏者/編曲者から「神機能」級の感謝。

> “May all the gods rain eternal blessings upon he who implemented the Concert Pitch checkbox.”  
> — @AKermodeBear, 2024-11-05  
> https://x.com/AKermodeBear/status/1853673506199781469

### S.2 クラリネット奏者：サイト譜で苦労せずソフト移調
バッハ合唱を MuseScore に入れ、**クラリネット用に移調してから視奏・録音**。現場の成功パターン。

- https://x.com/Yerevrir/status/2027076609732395414  
- https://x.com/Yerevrir/status/1988340436327621118  

### S.3 Dorico：concert で書き、transposed タブで完成
楽器を最初に正しく選び、**書きは concert / 出しは transposed** で、クレフも調号も正しく出る——乗り換え後に「移調楽器で一切悩まなくなった」。

> “まずconcert pitchで書いておいて…transposedタブに切り替えるだけで声部記号も調号も正しく変換される”  
> — 横丁の隠居 (@xi_124C41), 2025-11-23  
> https://x.com/xi_124C41/status/1992554634880381425

### S.4 Dorico の clef/transposition overrides
同一音楽に対し、**異なるクレフ/移調の複数パート**を持て、原譜を変えれば全部更新。バンド仕事向け成功機能。

> “multiple parts that show the same music, but with different clefs and/or transpositions”  
> — Lillie Harris (@lilliepharris), 2021-09-04  
> https://x.com/lilliepharris/status/1434141401743253507

### S.5 Sibelius Cloud：視聴側での移調
演奏/歌唱レンジに合わせてクラウド共有ビューアで移調——**配布後のキー合わせ**という成功ユースケース（公式）。

- https://x.com/AvidSibelius/status/1828447399800430753  
- deep link + playback position + transposition: https://x.com/Avid/status/1834698606214848621  

### S.6 Flat 系 Opuscan：スキャン→再生→移調→MusicXML
紙/PDF を取り込み、再生・移調・MusicXML/MIDI/PDF/MP3 出力まで一本化（2026）。

> “Scan… play it back, transpose it, and export it as MusicXML, MIDI, PDF, or MP3.”  
> — Flat (@flat_io), 2026-07-01  
> https://x.com/flat_io/status/2072289359978463713  

### S.7 独立記譜ツールの「移調楽器サポート」出荷
Bb clarinet / horn in F / alto sax を「奏者が期待する読み方」で——**未実装だとプロダクトとして未完成**という indiedev 認識。

> “Shipped transposing instrument support… the parts finally read the way players expect”  
> — ScoreTail (@ScoreTail), 2026-07-14  
> https://x.com/ScoreTail/status/2077029659062235143  

### S.8 DAW 側の「MIDIスコア移調」（Logic）
Bb と Eb を行き来する現場で、**MIDI トラックのスコア移調**が有用。

> “Logic Pro… transpose the score of your midi tracks. Very nice if you move between Bb and Eb”  
> — @CleverDanMusic, 2026-05-24  
> https://x.com/CleverDanMusic/status/2058634247750205927  

### S.9 中文：簡譜ツールの「転調が売り」
オンライン簡譜ツール「8譜」——**転調でコード自動修正**、级数和弦変換まで。

> “方便转调（会自动修改和弦），也可以转换成级数和弦。”  
> — @pluwen, 2025-11-17  
> https://x.com/pluwen/status/1990231742050148479  

### S.10 中文：OMR＋調号構造化（教育）
NoteLite：スキャン→OMR→調号/拍号構造化→標準譜 diff→MIDI 試聴。**移調そのものより「調号をデータとして扱う」成功基盤**。

- https://x.com/gaoren7716/status/2055868411884802221  

---

## 4. 限界（投稿から抽出した構造的制約）

| 限界 | 内容 | 根拠投稿 |
|---|---|---|
| **二重ピッチモデル** | written / sounding を一貫して持つ必要がある。片方だけ合わせると再生 or 譜面が破綻 | ScoreTail, Dorico 入力バグ |
| **楽器定義の前提** | 最初の楽器選択を誤ると後段が全滅しやすい | Dorico 乗り換え成功談の裏返し |
| **異名同音のポリシー** | ソフトの「簡略化」は音楽的に誤りになり得る | Finale E#→F |
| **フォーマット往復** | MusicXML の移調楽器表現は実装差が大きい | Robert Puff |
| **C譜 vs 移調譜** | 作曲/指揮の楽さとパート可読性がトレードオフ | Galvagno, Komaniecki |
| **ペイウォール** | 移調が「基本機能」なのに課金対象になると離脱 | MuseScore Premium, Sibelius free |
| **AI/OMR の精度** | 2026でも PDF 実用移調は失敗例が残る | Claude PDF fail |
| **認知限界** | 絶対音感・首調/固定調未統合はソフトでは解決不能 | 中文教育投稿、perfect pitch 投稿 |
| **開発者の関心の違い** | 「音楽そのものの移調」と「楽譜の移調」は別プロダクト | 中文開発者 @syeerzy |

> 開発者視点（中文）: 打譜ソフトではなく「改调移调转调变调の app」を作るなら、**楽譜ではなく音楽自体を表現する**必要がある、と明言。  
> https://x.com/syeerzy/status/1626227267096690688

---

## 5. ベストプラクティス（実務投稿から帰納）

1. **書きは concert（sounding）、出しは transposed（written）**  
   - Dorico 利用者の定石。最初に正しい楽器を選ぶ。  
   - 出典: https://x.com/xi_124C41/status/1992554634880381425  

2. **score / part layout の best practices を守る**  
   - Dorico は原則 watertight だが、前提を破ると clef×移調で痛い。  
   - 出典: https://x.com/m_galvagno/status/1969658352054780416  

3. **同一ソースから複数移調パートを生成（override）**  
   - 手でコピーして移調しない。更新同期を失う。  
   - 出典: https://x.com/lilliepharris/status/1434141401743253507  

4. **無調・複雑スコアの指揮譜は concert pitch**  
   - 出典: https://x.com/Komaniecki_R/status/1772365942095306882  

5. **移調楽器パートでは極端な異名同音を避ける**  
   - E#/B#/Fb/Cb の扱いを proofreading 項目に入れる。  
   - 出典: https://x.com/m_galvagno/status/1972195066987811209  

6. **調号チェックリストをルーチン化**  
   - cautionary/hidden 変更、移調楽器、無調は Open Key。  
   - 出典: https://x.com/m_galvagno/status/1783752877561061565  

7. **未検証の PDF/転写は信用しない。MusicXML でも手で聴く**  
   - 出典: https://x.com/MagnusTipsmark/status/2024802667780866226  

8. **再生（耳）と譜面（目）を別検証**  
   - 装飾音・移調楽器の playback は別バグ層。  
   - 出典: https://x.com/ScoreTail/status/2078674652088647928  

9. **中文ポピュラー現場：簡譜の自動転調＋首調/固定調の両建て**  
   - 歌手のキー下げを五線スペシャリストが拒否しない、など運用面。  
   - 出典: https://x.com/pluwen/status/1990231742050148479  
   - https://x.com/fngfng78/status/1944320574307922269  

10. **DAW と記譜の橋渡しが必要なら「concert pitch モード」を明示要求**  
    - MIDI でピアノ→サックス移調を書きたい、という未充足ニーズ。  
    - 出典: https://x.com/oneizzyjones/status/2009803746340196784  

---

## 6. 最新トレンド（2024–2026 投稿ベース）

| トレンド | 内容 | 投稿例 |
|---|---|---|
| **クラウド側移調** | 編集権がなくても視聴者/奏者がキー合わせ | Sibelius Cloud Sharing |
| **スキャン→移調ワンストップ** | OMR/PDF スキャナアプリが「再生・移調・MusicXML」をセットで訴求 | Flat Opuscan (2026) |
| **コラボ記譜の移調楽器必須化** | 新参ツールが「未実装だと使えない」と公言して出荷 | ScoreTail |
| **C譜（実音）執筆の標準化** | 作曲側は楽、パート抽出が製譜家の主戦場に | Galvagno Ep.102 |
| **AI 採譜への期待と幻滅** | 「音源→自動採譜→移調」の需要は強いが、実用失敗も続く | MuseScore格闘 + Claude PDF fail |
| **教育/OMR の構造化** | 調号を diff 可能なデータとして扱う | NoteLite |
| **中文：簡譜エコシステムの転調** | 五線より簡譜での自動転調・级数和弦が生活圏 | 8譜 |
| **Finale 終焉の文脈** | ソフト終了ショックと並行し、Dorico 等への移調ワークフロー移行語りが増える | Finale death 言及（周辺） |

### 需要の声（機能ロードマップ示唆）

- 「オーディオ自動採譜 **＋** 移調が一体のアプリが欲しい」  
  https://x.com/hahahdead/status/2048616464370835550  
- 「VST/DAW に concert pitch で MIDI 記譜したい」  
  https://x.com/oneizzyjones/status/2009803746340196784  

---

## 7. 失敗パターンの類型マップ（プロダクト設計向け）

```
移調・キー変更の失敗
├─ データモデル
│  ├─ written ≠ sounding の不整合
│  ├─ 異名同音の過剰正規化
│  └─ 楽器定義（移調量・クレフ）の誤り
├─ 再生レイヤ
│  ├─ 移調譜は正しいが MIDI/playback がズレる
│  └─ 装飾音・特殊奏法が移調後に破綻
├─ 交換レイヤ
│  ├─ MusicXML import/export でキー/音が崩壊
│  └─ PDF/OMR が構造を取れず移調不能
├─ UX / ビジネス
│  ├─ 移調の有料壁
│  ├─ ボタンがあるのに非対応（プラットフォーム分断）
│  └─ 設定が深いレガシーUI
└─ 人間側
   ├─ 絶対音感 / 首調・固定調の未統合
   └─ 理論不足で concert 印刷に逃げる
```

---

## 8. 出典一覧（主要ポスト）

| ID | 日付 | 著者 | 分類 | URL |
|---|---|---|---|---|
| 1610971561963421697 | 2023-01 | @SanfordBaritone | 失敗・ホルン | https://x.com/SanfordBaritone/status/1610971561963421697 |
| 1574987771651190785 | 2022-09 | @JameyAston | 失敗・バグパイプ | https://x.com/JameyAston/status/1574987771651190785 |
| 1282848422148612098 | 2020-07 | @micahburgess | 失敗・異名同音 | https://x.com/micahburgess/status/1282848422148612098 |
| 1234251912402198530 | 2020-03 | @robertpuff | 失敗・MusicXML | https://x.com/robertpuff/status/1234251912402198530 |
| 1959110297878503519 | 2025-08 | @astronomy89 | 失敗・楽器置換 | https://x.com/astronomy89/status/1959110297878503519 |
| 1973654547383066815 | 2025-10 | @pollutedriver | 失敗・課金壁 | https://x.com/pollutedriver/status/1973654547383066815 |
| 1667202512452026373 | 2023-06 | @TheHooseMoose | 失敗・Web UX | https://x.com/TheHooseMoose/status/1667202512452026373 |
| 1961540091949506703 | 2025-08 | @evanallenshay | 失敗・Sibelius free | https://x.com/evanallenshay/status/1961540091949506703 |
| 1845519808672247911 | 2024-10 | @m_yatani | 失敗・Dorico入力 | https://x.com/m_yatani/status/1845519808672247911 |
| 1969658352054780416 | 2025-09 | @m_galvagno | 限界・clef×移調 | https://x.com/m_galvagno/status/1969658352054780416 |
| 1972194815556366713 | 2025-09 | @m_galvagno | 限界・C譜 | https://x.com/m_galvagno/status/1972194815556366713 |
| 1972195066987811209 | 2025-09 | @m_galvagno | 限界・E#/B# | https://x.com/m_galvagno/status/1972195066987811209 |
| 1772365942095306882 | 2024-03 | @Komaniecki_R | 限界・無調 | https://x.com/Komaniecki_R/status/1772365942095306882 |
| 1839506853648118016 | 2024-09 | @HeoMusic | 失敗・記譜地獄 | https://x.com/HeoMusic/status/1839506853648118016 |
| 2036219083952193957 | 2026-03 | @SturgePow | 失敗・AI/PDF | https://x.com/SturgePow/status/2036219083952193957 |
| 2078674652088647928 | 2026-07 | @ScoreTail | 失敗→修正・再生 | https://x.com/ScoreTail/status/2078674652088647928 |
| 1828460182315139095 | 2024-08 | @Tantacrul | UXレガシー | https://x.com/Tantacrul/status/1828460182315139095 |
| 1853673506199781469 | 2024-11 | @AKermodeBear | 成功・Concert Pitch | https://x.com/AKermodeBear/status/1853673506199781469 |
| 1992554634880381425 | 2025-11 | @xi_124C41 | 成功・Dorico | https://x.com/xi_124C41/status/1992554634880381425 |
| 1434141401743253507 | 2021-09 | @lilliepharris | BP・overrides | https://x.com/lilliepharris/status/1434141401743253507 |
| 1828447399800430753 | 2024-08 | @AvidSibelius | トレンド・Cloud | https://x.com/AvidSibelius/status/1828447399800430753 |
| 2072289359978463713 | 2026-07 | @flat_io | トレンド・Scan | https://x.com/flat_io/status/2072289359978463713 |
| 2077029659062235143 | 2026-07 | @ScoreTail | トレンド・移調楽器 | https://x.com/ScoreTail/status/2077029659062235143 |
| 1990231742050148479 | 2025-11 | @pluwen | 中文・簡譜転調 | https://x.com/pluwen/status/1990231742050148479 |
| 1737359740814971095 | 2023-12 | @Noah607149441 | 中文・異名同音 | https://x.com/Noah607149441/status/1737359740814971095 |
| 1626227267096690688 | 2023-02 | @syeerzy | 中文・開発者 | https://x.com/syeerzy/status/1626227267096690688 |
| 2055868411884802221 | 2026-05 | @gaoren7716 | 中文・OMR | https://x.com/gaoren7716/status/2055868411884802221 |

---

## 9. 調査上の注記

1. **X は記譜プロの主戦場だが「移調バグの長文ログ」は散発的**。深い失敗談は Forum（MuseScore / Dorico / Avid）や Reddit に流出しやすい。  
2. **中国語**は「転調/移調」キーワードだと教育・練習・簡譜が多数ヒットし、**MuseScore/Sibelius の機能障害ログは少なかった**。  
3. 公式アカウント投稿（Avid, Flat）はトレンド把握に有用だが、失敗談はユーザー発が本丸。  
4. 本レポートは **実投稿ベース**。投稿の技術的正しさは二次検証していない（「現場がそう感じた」事実として扱う）。

---

## 10. プロダクト示唆（調査からの短結）

移調機能を「半音シフト」だけと捉えると失敗する。現場が求めるのは少なくとも次の **5層** の同時正しさ：

1. **ピッチモデル**（written / sounding / concert 表示）  
2. **記譜結果**（調号・異名同音・クレフ）  
3. **再生結果**（MIDI・装飾音・音域クランプ）  
4. **交換結果**（MusicXML/MusicXML経由の他ソフト）  
5. **配布結果**（パート抽出・クラウド視聴者のキー変更・課金境界）

失敗投稿が最も多いのは **1↔2 のズレ（ホルン等）**、**2 の異名同音破壊**、**4 の往復破壊**、**5 の有料壁と UI 嘘**。  
成功投稿が収束するのは **「concert で書き、transposed で出す」** と **「同一ソースから複数移調パートを生成」** の二点。

---

必要なら次の拡張もできます：

- **Forum（Dorico / MuseScore / Avid）側の失敗チケット突合**  
- **機能要件書向けの失敗ケース一覧（Given/When/Then）**  
- **中国語圏を Weibo / B站 まで広げた二次調査設計**
