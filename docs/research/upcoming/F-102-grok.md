# X調査報告：ピアノ音源からのサステインペダル（CC64）検出と記譜

**調査日**: 2026-07-21  
**対象**: X（旧Twitter）上の英語・中国語中心の実務者・研究者・開発者投稿  
**方針**: 実投稿のみ。投稿外の技術解説や論文本文からの推論は入れない。  
**スコープ注記**: 「音源→ペダル検出→楽譜記号（Ped.線）まで」を**同時に**語る投稿は極めて少ない。実際の議論は次の3層に分かれる。

| 層 | 内容 | X上の量 |
|---|---|---|
| A. 音源→MIDI（踏板含むAMT） | ByteDance系、研究論文bot | 中程度 |
| B. MIDI CC64の再生・編集・転送 | DAW/ハード/プラグイン実務 | 多め |
| C. 楽譜上のペダル記号（Ped.線） | 記譜ソフトの修正・チュートリアル | 少ない |

以下、収集軸ごとに**投稿ベース**で整理する。

---

## 1. 成功例

### 1-1. ByteDance系：踏板まで「いい感じに取れる」

| 知見 | 出典主旨 | アカウント種別 |
|---|---|---|
| ピアノ音声→MIDIで**踏板・強弱まで拾える**モデルがあり「挺好使的（かなり使える）」 | 字节开源模型能把钢琴音频直接转midi，踏板和强弱都能给扒出来 | @b1ackbinary（中国・技術者/オタク系実務者） |
| **踏板もよく認識**するAIピアノ扒譜として推奨。GUIは `azuwis/pianotrans`（ByteDance Piano Transcription with Pedals） | 非常准确，甚至踏板都可以很好识别 | @bocchi1chan（音楽プロデューサー） |
| アプリ内の piano audio→MIDI について、**ポリフォニー＋ペダル＋重なり音**は大抵のモデルを壊すが、実装できたのは印象的 | polyphony pedal and overlapping notes wreck most models… impressive | @irshit0（founding engineer）への称賛返信、対象は @ramonpiano_ / lumakeys 開発者 |
| 開発者側も難易度を認めつつ、実質は研究実装に依存していると自嘲 | yep it's really tough, thank god there's always some cracked chinese researcher… | @ramonpiano_（ピアノ学習アプリ開発者） |

### 1-2. 研究コミュニティ：サステイン検出を明示した論文の拡散

| 知見 | 出典主旨 | アカウント種別 |
|---|---|---|
| Streaming piano transcription が **onset/offset の一貫デコード＋サステインペダル検出** をタイトルに含む | arXiv:2503.01362 の紹介 | @ArxivSound / @MultimediaPaper（論文配信bot・研究フィード） |
| ペダル**深度**（continuous/half-pedal 方向）の高解像度推定と音楽的メトリクス評価 | arXiv:2510.03750 の紹介 | @ArxivSound（研究フィード） |

### 1-3. 記譜UI側：ペダル記号を「足す」成功（検出ではない）

| 知見 | 出典主旨 | アカウント種別 |
|---|---|---|
| 楽譜にペダルマークを付ける手順を公式が案内（**手動記譜**の成功例） | how to add pedal markings in Staventabs Pro | @staventabs（記譜ソフト公式） |

---

## 2. 失敗例・限界・不満（重点）

### 2-1. AMT本体：ペダル推論が良くてもノート側が崩れる

| 失敗・限界 | 投稿主旨 | アカウント種別 |
|---|---|---|
| **ペダル推論は完璧**なのに、**ノートが伸びきる** | bytedanceのpiano transcriptionのpedal推論完璧だった けどなぜノートが伸びきってるんですか | @ddPn08（開発者利用者） |
| 同スレ解説：ByteDance実装は**ペダルに焦点を当てた系**で、Onsets-and-Frames 系の理解が必要 | 実はバイトダンスのやつはペダルに焦点当てたやつ | @fkunn1326（技術ユーザー） |
| 実務上の総論：**ポリフォニー・ペダル・ノート重なりがモデルを壊す** | polyphony pedal and overlapping notes wreck most models | @irshit0（エンジニア） |

**解釈の境界（投稿内で言えていること）**  
「ペダルCC検出が正解でも、音の聴こえとしての sustain と、キーオフ（物理オフセット）が一致しないため、ロール上は異常に長いノートになる」——これは @ddPn08 の現象報告と、後述の研究側コメントが同じ問題を別角度から指している。

### 2-2. データセット／表現論：オフセット＝音価にならない

| 失敗・限界 | 投稿主旨 | アカウント種別 |
|---|---|---|
| MAESTROはサステイン多用で、**note offset がノートの持続時間を正しく表さない** | MAESTRO includes extensive use of the sustain pedal, which makes note offset not representing note duration properly | @DasaemJ（大学助教・MIR研究者） |
| GiantMIDIは **elongated duration** があり、踏板処理の有無で train/test ドメインがズレる | if you tested it with GiantMIDI, which has elongated duration, then there will be mismatch… | @DasaemJ（MIR研究者） |

これは「検出失敗」ではなく、**検出結果をどう符号化・評価・生成に使うか**の根本限界として重要。

### 2-3. パイプライン：MIDIに踏板が入っても、記譜／DAW側で消える・効かない

| 失敗・限界 | 投稿主旨 | アカウント種別 |
|---|---|---|
| MuseScore の MIDI で **sustain pedal を Logic 再生に載せたい**が方法が分からない | export a MuseScore midi file with the sustain pedal captured in Logic Pro playback | @theartsymathie（利用者） |
| Logic で録音すると、**実際の長さや sustain 有無に関係なく 64分音符の極短ノート**になる | recording all MIDI notes as tiny 64th notes… whether the sustain pedal was in use | @jerdencooke（作曲家） |
| Logic で CC64 の編集タブが見つからない | can’t find the tab to edit sustain pedal midi data in logic | @otherdavis（利用者） |
| Logic 12.3：サスティンON/OFFで CC64 127/0 と同時に、**オフ時に別chへ CC64=0 が余計に出る** | オフ時にMIDI ch2にCC64=0も出力…バグ？ | @masa_akita（プロ作曲家） |
| Logic の CC64 挙動がバグった（効かないのではなく壊れた） | LogicのCC64の挙動がバグった | @Sound_Aquarium（作編曲家） |
| CC64 をコピーすると **サスティン入れっぱなし**で鳴り続ける | CC64入れっぱなしになっててサスティン効いちゃうあるある | @yamazoo（作曲家） |
| オンラインMIDIエディタ **signal は当時サステイン未対応** | doesn’t support sustain pedal at the moment | @signalmidi（製品公式） |
| Keystep Pro が **CC64 を通さず内部ホールド**する不満 | doesn't pass CC64 and instead keeps notes held internally | @triskadecaepyon（技術/音楽ユーザー） |
| ハード：momentary の踏み込みを検出できず **toggle しか拾わない** | couldn't ever detect pedal presses, only switch toggles | @puheenix（AIエンジニア兼ピアニスト） |
| MIDIキーボード＋踏板で **極性反転（踏まない時だけ延音）** | 不踩踏板才延音了？ | @KaguraAiri_QWQ（中国語ユーザー） |
| シンセ側：sustain中の再トリガーで **stuck notes**、panic で sustain が残る | stuck notes… sustain pedal active / panic not fully clearing sustained notes | @discodsp（音源ベンダー公式・バグ修正告知） |

### 2-4. 中国語実務：成功報告の裏にある運用制約

| 失敗・限界 | 投稿主旨 | アカウント種別 |
|---|---|---|
| PianoTrans は神器だが **純ピアノ独奏のみ**。**量化校准**が必要 | 仅限纯钢琴独奏。建议配合编曲软件量化校准 | @ishowproduct（ツール紹介アカウント） |
| Pianotrans **裸導出**で譜を出すが、細部は未調整のまま公開 | 音頻用Pianotrans裸導，細節沒仔細摳 | @Zygarde925（改編・投稿者） |
| 延音CCを足すと自然だが、**次音と重なりポリ数を食う**（古い音源32声で枯渇） | 延音会和下一个音符事件重合占更多复音数 | @DraTohru_XLN（中国・MIDI/技術オタク） |
| 自扒譜で延音踏板＋アルペジオが譜面を**見た目だけ難しく見せる** | 琶音和延音踏板所以看上去可能有点唬人 | @uranyl_acetate（中国語・自扒譜ユーザー） |

### 2-5. half-pedal／深度の実務的不満（検出以前の「感じない」問題）

| 失敗・限界 | 投稿主旨 | アカウント種別 |
|---|---|---|
| アコースティックは half-pedal が美しいが、デジタルは **ダンパーが浮く瞬間が手に伝わらない** | unlike an acoustic you do not feel the moment… | @inkblobdev（学習者/開発者） |
| upright と digital では pedal depth が **信頼できない** | Pedal depth I find it unreliable in: uprights and digitals | 同上 |
| half-pedaling は色を大きく変えるが、**表記・検出の連続量問題**と接続する（演奏実務の声） | tiny changes in depth = huge changes in color | @PianoManiak（ピアニスト系アカウント） |

### 2-6. 「検出→記譜」そのものへの不満が少ない、というメタ失敗

X上では **「CC64をPed.線に変換したら汚くなる／誤記譜される」** を直接罵る英語・中国語の濃いスレは、今回の検索範囲では**ほとんど見つからなかった**。  
代わりに起きているのは：

1. 踏板は取れるが **ノート長が破綻**（@ddPn08）  
2. 取れたMIDIが **DAW/エディタで欠落・残留・誤ch**（Logic/MuseScore/Keystep等）  
3. 楽譜側は **手動でPed.を足す世界**（@staventabs）  
4. 研究側は **オフセット定義と深度推定**の議論（@DasaemJ, arXiv bot）

つまり市場不満の中心は「Ped.記号の美しさ」より **(a) 音価汚染 (b) ツール間CC64不整合 (c) 半ペダル非対応** にある。

---

## 3. ベストプラクティス（投稿から抽出できる運用）

| 実践 | 投稿での根拠 | アカウント種別 |
|---|---|---|
| **純ピアノ独奏**に限定してAMT | PianoTransは独奏限定 | @ishowproduct |
| 出力後は **編曲ソフトで量化・校准** | 建议配合编曲软件量化校准 | 同上 |
| 裸導出のまま公開せず **細部を手で直す**（逆説的に定石） | 細節沒仔細摳＝手直し前提の文化 | @Zygarde925 |
| ペダル問題切り分けは **MIDI MonitorでCC64を目視**（Note On誤送信チェック） | If you see Note On… not CC64, wrong signals | @paul_d_vaughan（トラブルシュート投稿） |
| DAW停止時は **使用chのみに CC64/66/123 解除**を送る（全chパニックしない） | ペダル解除を使用チャネルのみに | @mewlist（MIDIシーケンサ開発者・midiom） |
| ノート持続と踏板を混同しない（研究・生成パイプライン設計） | sustain で offset≠duration | @DasaemJ |
| GiantMIDI等の **elongated duration データと学習分布を揃える** | domain mismatch 警告 | @DasaemJ |
| ハード障害時は極性・momentary/toggle・ファーム・別ペダルで切り分け | 極性両試行・toggleのみ反応等 | @puheenix |

**明示されにくいが投稿群から一貫する示唆**  
- 「ペダル推論が良い」≠「譜面が良い」。**ノート・オフセット正規化とCCレイヤ分離**が必須。  
- 成功報告の中核はほぼ **ByteDance High-res piano transcription with pedals 系**に集中。

---

## 4. 最新トレンド／新手法（X上で観測できるもの）

| トレンド | 投稿での現れ方 | アカウント種別 |
|---|---|---|
| **Streaming** 転写＋ **consistent onset/offset decoding** ＋ **sustain pedal detection** を一体で扱う | arXiv:2503.01362（2025-03頃拡散） | 研究フィード |
| 二値CC64から **pedal depth（連続量）推定** と **musically informed metrics** | arXiv:2510.03750（2025-10〜2026-02再掲） | 研究フィード |
| 製品アプリへの **AMT埋め込み**（学習用ピアノアプリ内で audio→MIDI） | lumakeys の機能発表と「中国研究が難しい部分をやっている」発言 | アプリ開発者 |
| 中国語圏での **PianoTrans/ByteDance 系の再配布・紹介の継続** | 2022の成功談〜2026のツール紹介まで長期 | プロデューサー／ツール紹介 |
| iOS音源・MIDIビューアの **Hold/Sustain support 追加**（検出ではなく再生側対応の底上げ） | Fingerlab / MIDI Lens 等の更新告知 | ベンダー／開発者 |
| 記譜ソフトは **pedal line hooks のバグ修正**など表示品質の微調整 | MuseScore系アップデート文言の共有 | 利用者共有 |

**トレンドの方向性（投稿が示す事実関係のみ）**  
1. 研究：ON/OFF検出 → **深度・ストリーミング・オフセット一貫性**へ拡張  
2. 実務：モデルは「踏板付きMIDI」まで出せるが、**譜面用に人間が量化・整形**する前提が残る  
3. ツール：検出より **CC64のサポート漏れ修正**（エディタ・シンセ・コントローラ）が日常の火消し

---

## 5. 横断サマリ（意思決定向け）

### 何が「できている」と投稿されているか
- ピアノ**独奏**音源から、**ノート＋ペダル（＋強弱）付きMIDI**を取る流れは、ByteDance系を中心に**成功談が複数言語で存在**する。  
- 研究はさらに **streaming** と **depth** に進んでいる。

### 何が「できていない／壊れる」と投稿されているか（失敗が厚い領域）
1. **ペダル正解 × ノート過伸長**（聴こえ sustain と key-off の乖離）  
2. **offset＝音価とみなす表現**の破綻（MAESTRO/GiantMIDIコメント）  
3. **MIDI↔DAW↔記譜**のCC64欠落・残留・誤ch・極性  
4. **half-pedal / 連続深度**のハード・評価・記譜すべてが未成熟  
5. **複音楽器混在・非ピアノ**は公式にもユーザーにも制限として繰り返し出る  

### 記譜ソフト機能として設計するなら、X実務が示唆する優先度
| 優先 | 機能 | 根拠投稿群 |
|---|---|---|
| P0 | ペダルCCとノート長の**分離表示／正規化オプション**（pedal-aware offset） | @ddPn08, @DasaemJ |
| P0 | CC64の **import/export 可視性**（レーン・MIDI monitor） | Logic/MuseScore/Keystep不満群 |
| P1 | 独奏限定の明示と **量化後編集UI** | PianoTrans運用投稿 |
| P2 | Ped.線自動生成（しきい値・ヒステリシス付き） | 記譜は手動案内が主流＝自動化需要は間接的 |
| P3 | half-pedal/深度の段階記号 | 深度論文＋演奏家の depth 不満 |

---

## 6. 調査限界（正直な範囲宣言）

- X上で「**採譜ソフトがCC64を誤記譜した**」という**高エンゲージメント英語炎上**は、今回のキーワード探索では**ほぼ捕捉できなかった**。  
- 中国語は **ByteDance/PianoTrans 成功談**が目立つ一方、失敗は「裸導出の粗さ」「量化必須」「ポリ数」など**運用メモ型**が多い。  
- 日本語投稿も混在ヒットしたが、依頼どおり**英語・中国語を主**に扱った（@ddPn08 等の開発者日本語はAMTコア現象として例外的に採用）。  
- 論文botは「存在とタイトル」まで。**精度数値・失敗モードの詳細は投稿本文に無い**ため、ここでは数値を推測で補っていない。

---

## 主要ソース一覧（投稿ID / 種別）

| 投稿者 | 種別 | 役割 |
|---|---|---|
| @b1ackbinary | 技術実務 | 成功：踏板・強弱付き扒谱 |
| @bocchi1chan | 音楽プロデューサー | 成功：PianoTrans推奨 |
| @ddPn08 / @fkunn1326 | 開発者利用者 | 失敗：pedal良・note過伸長 |
| @irshit0 / @ramonpiano_ | エンジニア／アプリ開発 | 難易度総論＋製品成功 |
| @DasaemJ | MIR研究者 | データセット限界（offset/持続） |
| @ArxivSound 等 | 研究フィード | ストリーミング検出・深度推定トレンド |
| @theartsymathie, @jerdencooke, @masa_akita 等 | 作曲・利用者 | DAW/記譜間のCC64失敗 |
| @ishowproduct, @Zygarde925, @DraTohru_XLN | 中国語実務 | 制約・手直し文化・ポリ数 |
| @staventabs | 記譜ソフト公式 | 手動ペダル記譜の成功UX |

---

必要なら次ステップとして、(1) 上記失敗軸ごとの**機能要件チェックリスト**化、(2) ByteDance/Streaming/Depth 論文の**非X（arXiv本文）突合**、(3) 日本語圏フォーラム（Twitter以外）との差分調査、のいずれかに展開できます。
