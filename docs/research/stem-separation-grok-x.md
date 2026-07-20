# X調査レポート：AI音源分離 × 分離後採譜の【失敗・限界・不満】

**調査日:** 2026-07-21（JST）  
**対象:** X（旧Twitter）上の実務者・研究者・音楽制作者の実投稿  
**言語:** 英語中心、日本語補助（中国語は実務失敗の一次投稿が少なく、マーケ投稿が大半）  
**方針:** 憶測禁止・実投稿ベースのみ。各知見に投稿リンク相当の出典を付す  

---

## エグゼクティブサマリー

X上で繰り返し出る不満は次の5クラスタに収束する。

1. **Bleed / Ghost**（ボーカルにギター/サックス、ベースにギター）  
2. **高域アーティファクト**（jangly / hi-end / metallic感）  
3. **位相・再合成問題**（再ミックス時に壊れる）  
4. **分離→ピッチ/MIDI連鎖の失敗**（分離が採譜を悪化）  
5. **ワークフロー回避**（Vo/Instのみ、原曲直接、再生成、RX後処理）

「完璧なステム分離」はマーケ表現として過大であり、実務者は**常に残滓がある前提**で運用している。

---

## 知見一覧（18件）

### 1. Demucs後のピッチ推定が汚染される／原曲直接の方が多声を拾う

| 項目 | 内容 |
|------|------|
| **出典** | [@rrherr](https://x.com/rrherr/status/1894129902745485389)（MLエンジニア／音楽家）。Ray Charles *Hard Times* 実験スレ |
| **失敗内容** | ボーカル分離のためにDemucs→pestoに渡したところ、**サックスがボーカル茎に大量bleed**。後で**原曲ポリフォニックmixを直接pesto**にかけると、sax・vo・一部pianoまで取得できた |
| **技術的原因（投稿内）** | 「demucs fault」——分離モデルがsaxをvocalに誤分類／漏出 |
| **回避策（投稿内）** | 分離せず原曲直接でピッチ輪郭を取る；分離は必須前提にしない |

---

### 2. Demucs単体ではVoが他ステムに漏れる（htdemucs_ft）

| 項目 | 内容 |
|------|------|
| **出典** | [@yonagip](https://x.com/yonagip/status/2053176652252008661)（AI音楽／DTM制作者） |
| **失敗内容** | **Demucs単体だとVoが他（drums/bass/other）に漏れる**。一発処理ではクリーン度が不足 |
| **技術的原因（投稿内）** | 一段階分離ではVo除去が不完全→楽器分離にノイズが乗る |
| **回避策（投稿内）** | **二段処理**：① MelBand RoformerでVo/Inst ② Instを`htdemucs_ft`で Drums/Bass/Other |

---

### 3. 全ステム分離より Vo/Inst の方が「使える音」になる

| 項目 | 内容 |
|------|------|
| **出典** | [@wat_fuh](https://x.com/wat_fuh) の [@yonagip](https://x.com/yonagip/status/2053176652252008661) への返信 |
| **失敗内容** | SUNO曲で**全部門分離するより、オケとボーカル分離の方が『使えそうな音』**になる感覚 |
| **技術的原因（投稿内）** | 多ステムほど品質劣化・実用性が落ちるという体感 |
| **回避策（投稿内）** | **2-stem（Vo/Inst）で止める** |

---

### 4. 密なミックスでDemucsが位相を smear する

| 項目 | 内容 |
|------|------|
| **出典** | [@aias_0](https://x.com/aias_0/status/2051992150423011547)（中国語圏エンジニア／AI実践） |
| **失敗内容** | ローカル推論はクラウド待ちはないが、**「Demucs still smears phase on dense mixes」** |
| **技術的原因（投稿内）** | 密なミックスでの位相 smear（具体アルゴリズム断定なし） |
| **回避策（投稿内）** | 投稿単体では未提示（問題認識の一次証言） |

---

### 5. Demucs / BS-RNN / BS-RoFormer のアーティファクト嫌いでマッシュアップ断念

| 項目 | 内容 |
|------|------|
| **出典** | [@oomfatuated](https://x.com/oomfatuated/status/1843309355611095413) |
| **失敗内容** | 自分を **「number one demucs/bsrnn/bs roformer artifact hater」** と称し、**アーティファクトがなければマッシュアップを大量に作れていた**と表明 |
| **技術的原因（投稿内）** | 当該系列モデル共通の聴感アーティファクト |
| **回避策（投稿内）** | **マッシュアップ制作自体を抑制／断念** |

---

### 6. 高域の「jangly」アーティファクトが残る

| 項目 | 内容 |
|------|------|
| **出典** | [@pthelo](https://x.com/pthelo/status/1792945392029429829)（ミュージシャン） |
| **失敗内容** | 分離は進歩したが、**高域に残る jangly artifacts がまだ気になる** |
| **技術的原因（投稿内）** | 高周波数帯の残滓（詳細モデル名なし） |
| **回避策（投稿内）** | 投稿単体では未提示（不満の一次証言） |

---

### 7. 「プロ録音でも常にアーティファクト」——分離の本質的限界

| 項目 | 内容 |
|------|------|
| **出典** | [@thecollegehill](https://x.com/thecollegehill/status/1991524829519048722)（プロデューサー／DJ） |
| **失敗内容** | **プロ録音にstem separationをかけてもアーティファクトが出る**と断言。AI生成音に分離をかけるならなおさら。Spleeter旧版はさらに悪かった、とも言及 |
| **技術的原因（投稿内）** | 分離AI自体が原理的にアーティファクトを生む |
| **回避策（投稿内）** | **lo-fiを受け入れる**；古いモデルはよりアーティファクトが多いので避ける |

---

### 8. 分離ステムの位相問題でポストミックスが困難〜不可能

| 項目 | 内容 |
|------|------|
| **出典** | [@philliplanos](https://x.com/philliplanos/status/1916954146890256519) |
| **失敗内容** | Suno曲を後から分離すると **phasing issues と stem separation artifacts** で再利用が **difficult or impossible** |
| **技術的原因（投稿内）** | 後段分離による位相／アーティファクト |
| **回避策（投稿内）** | **最初から各トラックを独立生成**してほしい、という要望 |

---

### 9. バランスの取れたmixが「muddy and wonky」なデジタルゴミに

| 項目 | 内容 |
|------|------|
| **出典** | [@EuroBaboKarl](https://x.com/EuroBaboKarl/status/1707846951754961340)（Wishkah系音源議論） |
| **失敗内容** | AI stem separationが下手だと、**well balanced board mix → muddy and wonky mess plagued by digital artifacts** |
| **技術的原因（投稿内）** | 実行品質の低さ（poorly executed） |
| **回避策（投稿内）** | 「やる意味があるのか」——**使わない選択**への傾き |

---

### 10. 「ゴースト」は常に残る／真のアンパックは不可能

| 項目 | 内容 |
|------|------|
| **出典** | [@jakepalumbo](https://x.com/jakepalumbo/status/1775184148455436382) ほか同スレ（プロデューサー／ミックスエンジニア） |
| **失敗内容** | MPC stems等で **backgroundに music の ghost** が残る苦情が常態。**真のstem unpackは不可能**で、常に他楽器のアーティファクトが残る |
| **技術的原因（投稿内）** | 高度な位相キャンセル相当であり、アルケミーではない；企業はtrue separationと売り過ぎ |
| **回避策（投稿内）** | **Filter & EQで最善を尽くして先に進む** |

---

### 11. ボーカル抽出の「random ducking」とアーティファクト

| 項目 | 内容 |
|------|------|
| **出典** | [@lyghtmare](https://x.com/lyghtmare/status/1941267881917919267)（Sunoユーザー） |
| **失敗内容** | 歌い手抽出で **lots of artifacts and random ducking**。マスタリングで一部は直るが別問題が連鎖 |
| **技術的原因（投稿内）** | 抽出処理のアーティファクト＋ducking |
| **回避策（投稿内）** | 抽出後にマスタリング再試行（不完全；別バグで破綻） |

---

### 12. Auto Split系は「messy / practically useless」、ギターがボーカルに混入

| 項目 | 内容 |
|------|------|
| **出典** | [@willdeschepper](https://x.com/willdeschepper/status/2065871687342850403) / [同](https://x.com/willdeschepper/status/2065893484280615313)；[@K4Climate](https://x.com/K4Climate/status/2077531086985236714)（Suno公式ステム更新スレ） |
| **失敗内容** | 旧/Auto stemは **terrible / messy and scrambled / practically useless**。Proのauto extractでは **ギター等がvocal stemに混入** |
| **技術的原因（投稿内）** | frequency isolation／Auto Splitの限界（公式も「isolating frequencies」から「regenerating」へ移行を宣言） |
| **回避策（投稿内）** | Advanced Split（再生成）へ。ただしプラン制限への不満あり |

---

### 13. クラシック分離＝drum bleed + pad ghostが必然

| 項目 | 内容 |
|------|------|
| **出典** | [@IhorSkiba](https://x.com/IhorSkiba/status/2077367072200548682) |
| **失敗内容** | 旧方式は周波数をほどこうとして **never did**。**isolated guitarには常に drum bleed と pad ghost** |
| **技術的原因（投稿内）** | frequency unbraiding の原理的失敗 |
| **回避策（投稿内）** | **再生成型（regeneration）stem** へのシフト（Suno Advanced Splitの文脈） |

---

### 14. ギターがボーカルに混ざる／Udioでもbleed、Sunoはさらに悪い印象

| 項目 | 内容 |
|------|------|
| **出典** | [@francolli](https://x.com/francolli/status/2075344588433227917) / [同](https://x.com/francolli/status/2025993700178866424) |
| **失敗内容** | stem divisionが **artifact litter** を残し **guitar mixed with the vocal**。Udioは比較的きれいでも **vocalにguitar bleed**、Sunoはより悪い印象 |
| **技術的原因（投稿内）** | 不完全分離の残滓 |
| **回避策（投稿内）** | 既分離vocalをさらに再分割して **leftover junk** を別stemへ |

---

### 15. 男女デュエットの声は分離できない

| 項目 | 内容 |
|------|------|
| **出典** | [@Prince_Opie](https://x.com/Prince_Opie/status/2065932344008097863)（Suno stem更新への質問） |
| **失敗内容** | male/female duetをstem separationしても **両方同じトラックに残る**。**Doesn't work** |
| **技術的原因（投稿内）** | 同クラス（vocal）内の話者分離ができない |
| **回避策（投稿内）** | 投稿時点では未解決のまま（機能要求として表明） |

---

### 16. Hybrid Demucs v4 でもRX後処理が必要

| 項目 | 内容 |
|------|------|
| **出典** | [@tallbrowndude](https://x.com/tallbrowndude/status/1617062613057245184) |
| **失敗内容** | ローカル hybrid transformer demucs v4 を使っても **artifact control のために iZotope RX が必要**と明記 |
| **技術的原因（投稿内）** | Demucs出力に制御が必要なアーティファクトが残る前提 |
| **回避策（投稿内）** | **Demucs → RX 後処理** |

---

### 17. Bleedと本体の区別が難しく、reverb washは修復不能級

| 項目 | 内容 |
|------|------|
| **出典** | [@entrepeneur4lyf](https://x.com/entrepeneur4lyf/status/2068370013048758625)（ステム分離ツール開発者） |
| **失敗内容** | 本体音とbleedの数理分離はMRI級の難しさ。**中〜高域がwonky**になりやすく、**reverb washは修復不能**と感じる |
| **技術的原因（投稿内）** | bleedと本信号の周波数交差；残響の非可逆性 |
| **回避策（投稿内）** | IRマッチ／ピッチ検出でwonky帯域だけマスクする試み（開発中） |

---

### 18. Demucs→ピッチ検出→ノートバー生成が「still sucks」（採譜連鎖失敗）

| 項目 | 内容 |
|------|------|
| **出典** | [@duball97](https://x.com/duball97/status/2008015381563122171)（歌唱ゲーム開発） |
| **失敗内容** | **Demucsで歌声分離→pitch detectorでノート化**しても **note bars generation が still sucks**。原因が分離／pitch／groupingのどれか不明なまま |
| **技術的原因（投稿内）** | 作者自身も特定できず（分離品質 or 検出 or グループ化） |
| **回避策（投稿内）** | 継続試行のみ（決定的回避策なし）＝**分離前処理が採譜を救わない例** |

---

### 19. SUNO Studio：BASSにギターが混じりEQが道連れにする

| 項目 | 内容 |
|------|------|
| **出典** | [@Stingray_tks](https://x.com/Stingray_tks/status/2071870033865896063)（SUNOユーザー） |
| **失敗内容** | Stem精度の低さがしんどい。**(1) Vocal dynamicsがよれる (2) BASS stemにGuitarががっつり混じる→Bass EQするとGuitarも道連れ**。外れstemを引くと繰り返し同じ症状 |
| **技術的原因（投稿内）** | 低域ステムへのギター漏出＋帯域共有 |
| **回避策（投稿内）** | 投稿時点では明確な回避なし（再試行でも再発） |

---

### 20. 「stem-level MIDI from mixed recording is half-broken forever」

| 項目 | 内容 |
|------|------|
| **出典** | [@helloLizZhang](https://x.com/helloLizZhang/status/2075614551895314717) |
| **失敗内容** | ミックス録音からのstem-level MIDIは **half-broken forever**。**drums bleed into everything**。密なミックスで帯域共有時の挙動に懐疑 |
| **技術的原因（投稿内）** | 帯域共有とドラムbleed |
| **回避策（投稿内）** | 新モデル評価中（投稿は問題認識） |

---

### 21. 業界側の回避：分離せずフルミックスからMIDIへ（Demucs前処理を捨てる）

| 項目 | 内容 |
|------|------|
| **出典** | [@virtualmep](https://x.com/virtualmep/status/2075729283297980788)（Kyutai/Mirelo Audio-to-MIDI発表への反応） |
| **失敗内容** | 当週トークンの半分以上を **wav→MIDI をステム分離経由で組む**試行に費やした直後、**Demucs/HT-Demucs作者側が「分離せず一気にMIDI化」**を出した、と驚き |
| **技術的原因（投稿内）** | 分離→採譜の二段が非効率／限界ありという文脈 |
| **回避策（投稿内）** | **stem separationをスキップする直接MIDI化**への関心（研究・製品の潮流） |

---

### 22. 実務者がstem separation自体をやめた

| 項目 | 内容 |
|------|------|
| **出典** | [@chamerliVEVO](https://x.com/chamerliVEVO/status/2075887237074432231) |
| **失敗内容** | **「i dont use stem seperation anymore」**、**「it just sounds like shit」** |
| **技術的原因（投稿内）** | 聴感品質が許容外（詳細モデル未特定） |
| **回避策（投稿内）** | **使用停止** |

---

### 23. 無料ライブラリ品質不足→有料LALAL.ai依存（品質ギャップ）

| 項目 | 内容 |
|------|------|
| **出典** | [@DariuszChynek](https://x.com/DariuszChynek/status/2079212219196137604)（VU Studio開発者） |
| **失敗内容** | 無料ライブラリはあるが **「quality I’m looking for」ではない**。1–2年LALAL.aiを使用しAPI統合 |
| **技術的原因（投稿内）** | 無料/OSS分離の品質不足（体感） |
| **回避策（投稿内）** | **有料クラウド（LALAL.ai）＋必要な区間だけ分離** |

---

### 24. UVR系：きれいなisolated vocalが無い時代の「dogshit」品質からの改善史

| 項目 | 内容 |
|------|------|
| **出典** | [@shaunpocalypse](https://x.com/shaunpocalypse/status/2079170229226094718) |
| **失敗内容** | isolated vocalが無いとき、分離前の品質は **better-than-dogshit** が目標線だった、という実務経験 |
| **技術的原因（投稿内）** | 当時の分離／入手可能なacapella品質の低さ |
| **回避策（投稿内）** | **UVRを大量使用**（オフライン） |

---

### 25. 中国語圏マーケ投稿が示す「消不干净／楽器も糊」という市場常識

| 項目 | 内容 |
|------|------|
| **出典** | [@gyqgtgt](https://x.com/gyqgtgt/status/2071045172088156649) 等（Pure Spleeter宣伝） |
| **失敗内容** | 「网上的消音软件**消不干净**，**乐器也跟着糊**」——ネット消音が不十分で伴奏が濁る、という**市場が共有する失敗前提**を広告が前提にしている |
| **技術的原因（投稿内）** | 不十分な人声除去＋伴奏劣化（宣伝側の問題設定） |
| **回避策（投稿内）** | ローカルAI分轨製品を推す（宣伝） |
| **注** | 一次失敗レポートではなく**市場の不満を反映した二次証拠**。単独の技術検証としては弱く、1–22と合わせて読む |

---

## 論点マップ（ユーザー指定テーマへの対応）

| 論点 | 該当知見 | 結論（投稿根拠のみ） |
|------|----------|----------------------|
| Demucs/Spleeter/htdemucs/MDX系アーティファクト | 1,2,4,5,6,7,16 | bleed・phase smear・高域jangly・RX必須 |
| Moises/LALAL/RipX | 23（LALAL依存）；RipX固有失敗投稿は今回検索で**有意ヒット少** | LALALは「無料では足りない」側の回避先として言及 |
| 分離後採譜の精度劣化 | 1,18,20,21 | Demucs後pitch汚染、ノートバー生成失敗、stem MIDI half-broken |
| other内ギター/ピアノ個別分離 | 2,3,13,19 | other/多ステムは汚れやすい；Vo/Instで止める派；bassにguitar混入 |
| 分離が採譜を下げる／原音直接が良い | **1（最重要）**, 21 | 原曲直接のpestoがより多くのパートを捕捉；直接MIDI化の潮流 |
| 実務者が諦めた/回避したWF | 3,5,10,12,16,17,21,22,23 | 使用停止、2-stemのみ、RX、再生成、有料API、分離スキップ |

---

## 実務者の「回避パターン」まとめ（実投稿から）

1. **分離しない**（原曲直接ピッチ／直接Audio-to-MIDI）  
2. **2-stemで止める**（Vo/Instのみ）  
3. **二段分離**（Roformer → htdemucs_ft）  
4. **後処理で隠蔽**（iZotope RX、EQ/Filter）  
5. **再生成型stem**（抽出ではなく生成し直す）  
6. **有料クラウド**（LALAL.ai等）  
7. **使うのをやめる**

---

## 調査上の限界（透明性）

- **中国語（简体/繁体）**の「失敗一次体験」投稿は、キーワード検索では**広告・チュートリアルが支配的**で、英語・日本語より一次証言が薄い。  
- **RipX** 固有の失敗談は、本調査のX検索では有意な実務不満投稿を十分回収できず。  
- X検索ノイズ（「Moises」人名、「MDX」トレーダー、「UVR」ユーザ名）が多く、**ツール名はフレーズ検索が必須**。  
- 「技術的原因」は**投稿者が述べた範囲のみ**。論文レベルの因果は断定していない。

---

## 代表リンク集（深掘り用）

| 投稿者 | リンク |
|--------|--------|
| Ryan Herr（分離が採譜を汚染） | https://x.com/rrherr/status/1894129902745485389 |
| 夜凪P（Demucs漏れ・二段処理） | https://x.com/yonagip/status/2053176652252008661 |
| Jake Palumbo（ghostは常在） | https://x.com/jakepalumbo/status/1775184148455436382 |
| pthelo（高域jangly） | https://x.com/pthelo/status/1792945392029429829 |
| thecollegehill（常にartifact） | https://x.com/thecollegehill/status/1991524829519048722 |
| duball（Demucs+pitch失敗） | https://x.com/duball97/status/2008015381563122171 |
| STINGRAY（BassにGuitar） | https://x.com/Stingray_tks/status/2071870033865896063 |
| willdeschepper（Auto stem useless） | https://x.com/willdeschepper/status/2065871687342850403 |
| francolli（guitar in vocal） | https://x.com/francolli/status/2025993700178866424 |
| oomfatuated（artifact hater） | https://x.com/oomfatuated/status/1843309355611095413 |

---

**件数:** 具体知見 **25件**（うち一次実務失敗 **22件**、市場常識の二次 **1件**、回避ツール選択 **2件**）。最低15件を満たしています。

必要なら次の段として、(a) 特定ツール（RipX / Moises / MDX-Net）に絞った再検索、(b) 研究者アカウント限定の文献連動投稿、(c) 採譜専用（Basic Pitch / AnthemScore / Melodyne + stem）の失敗だけを深掘り、にも進めます。
チマークに興奮 |
| **失敗（課題設定として）** | 実世界分離では **bleeding** とラベル汚染が問題になることが研究コミュニティで明示 |
| **技術的原因（投稿が言及）** | bleeding／不完全ラベル |
| **回避策** | bleeding を想定した学習・評価データセット |

---

## 横断パターン（投稿群から帰納できる傾向）

### A. アーティファクトの類型（投稿で実際に名指しされたもの）

| 類型 | 投稿での言及例 |
|------|----------------|
| 音漏れ / bleeding | Voが他ステムへ（yonagip）、インストに声が残る（OpiumLATAM）、従来型の音漏れ（capy_ito1a） |
| 位相 smear / 再合成位相問題 | dense mix の smear（aias_0）、ストレッチ時の位相崩れ（reharmonize_net）、recombine 位相（gyqgtgt） |
| リバーブ異常 | アカペラで過多 or 切れ（OpiumLATAM）、reverb wash 修復不能（entrepeneur4lyf） |
| スペクトラル mess / 金属的・デジタル劣化の周辺 | dogshit spectral mess（saephbass）；アーティファクト全般の嫌悪（oomfatuated, bocchitrue） |
| 楽器混同・マージ | 弦のごちゃ混ぜ・シンセ一括（norick）、パートがマージのまま（val_yukibee）、viola/violin 区別不能（olhos_livres） |

### B. 分離が採譜を下げる／分離が前提になるケース

- **Songscription は分離済み必須**（tanigon）→ 分離失敗が採譜の入口で詰む  
- **MIDI化は分離後も精度不足**（Alias_55555 8割、CabbageLettuce1 10–50%、ga_ya_kamo 調整中）  
- **「参考にはなるがそのまま使えない」**（SlowxWorks）— 原音耳コピの代替として限定利用  
- 投稿群の中で「分離したせいで採譜が原音直より悪くなった」と**数値比較で断言した投稿は今回の検索範囲では希少**。一方で「分離品質が採譜の前提条件になっている」「A2M自体が実用外」という形での**間接的な劣化・足かせ**は多数。

### C. 実務者が選んだ回避ワークフロー

1. **二段分離**（Roformer Vo除去 → Demucs 楽器）  
2. **2ステムで止める**（Vo/Inst のみ）  
3. **後処理必須**（iZotope RX 等）  
4. **参考用のみ／DAW再構築**（MIDI・ステムをそのまま使わない）  
5. **使用停止**（chamerliVEVO；Moises 課金拒否）  
6. **完全パラ分け・男女ボーカル分離を要求しない**  

---

## 言語別・ツール別のカバレッジメモ

| 言語 | 傾向 |
|------|------|
| **英語** | アーティファクト嫌悪、使用停止、bleed指紋、位相、商用課金拒否が厚い |
| **日本語** | UVR/Demucs実務tips、Suno限界、弦楽器困難、Songscription前提、A2M精度数値が出やすい |
| **中国語** | 今回のキーワード網では「失敗ログ」よりツール紹介・Suno「无伪影」ニュース転載が中心。失敗の一次愚痴は英語・日本語より薄くヒット |
| **ポルトガル語** | RipX+MT3 の弦楽器識別失敗など、ニッチだが強い一次証言あり |

| ツール | 投稿上の不満の出方 |
|--------|---------------------|
| Demucs / htdemucs | Vo漏れ、位相 smear、キック/シンセ混同、アーティファクト後処理 |
| BS-RoFormer / Mel-RoFormer | マッシュアップ阻害レベルの artifact；一方で二段処理の前段としては評価 |
| UVR 系 | 二段始末のホストとして言及（失敗そのものよりワークアラウンド文脈） |
| Moises | 価格 vs Pro品質 |
| RipX | 不完全分離・類似楽器誤認 |
| Suno 内蔵分離 | 使えない／マスタ後無理／MIDI不可 |
| LALAL.ai | 今回の検索窓では失敗一次投稿より「神器」紹介が中心（失敗ログは薄） |
| Spleeter | 製品比較で「古い／歪み」前提の言及はあるが、2026時点の愚痴は Demucs/RoFormer に移行 |

---

## 限界と注意

1. **憶測禁止**のため、投稿が言っていない因果（例: 「STFTマスクの位相再構成が原因」など）は**技術解説として補っていない**。  
2. X検索はノイズが多く（「Moises」「MDX」「UVR」が人名／車／他義語と衝突）、**ツール名＋失敗語のAND**で一次投稿を拾った。  
3. 中国語の「失敗ログ」は相対的に少なく、**英語・日本語の実務者投稿が厚い**。繁体中心の追加収集は別ラウンドが必要。  
4. 製品宣伝（phase-accurate 訴求等）は**市場が認める問題の間接証拠**として扱い、利用者の体験談より弱い一次資料と明記した。  
5. Slack `#倉田_ログ` への自動投稿は、**本環境に Slack MCP が接続されておらず未実施**。必要なら投稿文をそのまま転送できる。

---

## 参考リンク（主要一次投稿）

- https://x.com/oomfatuated/status/1843309355611095413  
- https://x.com/yonagip/status/2053176652252008661  
- https://x.com/aias_0/status/2051992150423011547  
- https://x.com/donnaken15/status/1626949028603654144  
- https://x.com/tallbrowndude/status/1617062613057245184  
- https://x.com/bocchitrue/status/2035560630137086355  
- https://x.com/chamerliVEVO/status/2075887237074432231  
- https://x.com/OpiumLATAM__/status/2013093553904156690  
- https://x.com/reharmonize_net/status/2066160990681796772  
- https://x.com/Alias_55555/status/2066028877936509274  
- https://x.com/tanigon/status/2069451967542538594  
- https://x.com/DonShunny/status/2071961356991955384  
- https://x.com/SlowxWorks/status/2066532919003447413  
- https://x.com/norick_tzr250/status/2078011130686116201  
- https://x.com/val_yukibee/status/2065964410435477743  
- https://x.com/olhos_livres/status/2078591636024508745  
- https://x.com/EAethelbald/status/2053095603563798765  
- https://x.com/Prince_Opie/status/2065932344008097863  
- https://x.com/entrepeneur4lyf/status/2068370013048758625  
- https://x.com/CabbageLettuce1/status/2078348054697246827  
- https://x.com/saephbass/status/2019071887423238243  
- https://x.com/ga_ya_kamo/status/2075891044403859495  

---

必要なら次のラウンドで、(1) 繁体中文キーワード拡張、(2) Reddit/YouTubeコメントとの突合、(3) 「分離あり vs 原音直採譜」の**明示比較投稿**だけを狙い撃ち、まで掘れます。
