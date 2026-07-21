# X調査レポート：テキスト記譜のPDF/SVG描画・レイアウト整形（五線譜以外）

**調査日:** 2026-07-21  
**対象機能:** 简谱（jianpu／数字譜）・リードシート・度数／级数譜などの**テキスト寄り記譜**を、PDF/SVG等へ描画し、レイアウト整形する機能  
**情報源:** X（旧Twitter）上の実務者・研究者・開発者投稿（英語・中国語中心、一部日本語）  
**方針:** 実投稿ベース・出典リンク付き。**失敗例を厚め**に整理

---

## 0. 調査上の限界（先に結論）

このテーマはX上で**非常にニッチ**です。

| 観測 | 内容 |
|------|------|
| 多い投稿 | 五線譜 engraving（MuseScore/Dorico/Sibelius）、AI採譜、一般的なコード譜PDF配布 |
| 少ない投稿 | 「简谱専用レイアウトエンジン」「度数譜のSVG描画アルゴリズム」「テキスト記譜のPDF改ページ最適化」の深掘り |
| 実務の置き場 | 議論の多くは **GitHub Issue / MuseScore Forum / 貼吧** に落ち、Xは「成果発表・愚痴・プラグイン告知」中心 |

したがって本レポートは、**(A) テキスト記譜そのもの** と **(B) それを支える共通レイヤ（SVG/PDF、コード記号、spacing、AI変換）** の両方を「実務者が語っている範囲」で再構成しています。

---

## 1. 機能マップ（何が「テキスト記譜レンダリング」か）

| 記譜種 | 典型表現 | レイアウト上の特有課題 |
|--------|----------|------------------------|
| **简谱 / 数字譜** | `1 2 3 5`、上下の点（オクターブ）、下線（音価） | 数字＋点＋下線の**垂直スタック**、段組、移調時の再配置 |
| **リードシート** | 旋律＋コード記号＋（slash） | コードと音符の**水平同期**、slash notation、改行時のコードずれ |
| **度数 / 级数 / Nashville** | `I–vi–IV–V`、`1–6–4–5` | 調依存変換、機能和声と数字の衝突、移調UI |
| **ChordPro系** | 歌詞行上の `[C] [Am]` | 歌詞折り返しとコード位置の再計算 |

---

## 2. 成功例（実投稿）

### 2.1 中国語圏：AIで「简譜＋五線＋和弦＋级数」を一枚に

**Yong.c（@william40152988）** が、AIで少しずつ作った曲譜ソフトを公開。  
**简譜・五線譜・和弦譜・级数譜**、移調・メトロノーム対応を謳い、「自分の不便をすぐ直せる」利点を強調。

> 目前支持简谱、五线谱、和弦谱和级数谱… 哪里不好用，随时改  
> — [投稿](https://x.com/william40152988/status/2077061069906837857)

後日「升级效果杠杠的，**额度烧的太快了**」と、成功の裏で**APIコストが急増**したことも正直に報告。  
→ 成功パターン：多記譜切替のMVPは早く出せる／失敗パターン：生成コストが製品単位経済を壊す。

### 2.2 中国語圏：オンライン简谱ツール「8谱」

**普鲁文（@pluwen）** が **8谱（8pu.cn）** を紹介。  
简谱・功能简谱・和弦谱、転調時のコード自動修正、**级数和弦への変換**を「国人向け」として推す。

> 支持简谱、功能简谱、和弦谱。方便转调…也可以转换成级数和弦  
> — [投稿](https://x.com/pluwen/status/1990231742050148479)

**示唆:** 五線中心の国際エンジンに「简谱モード」を後付けするより、**最初から数字譜の版面を中心に設計した国産Webツール**の方が実務フィットしやすい、という市場の現実が表に出ている。

### 2.3 英語圏：MuseScore に简谱を「プラグインで後付け」

| 投稿者 | 内容 | 出典 |
|--------|------|------|
| **Joe Hsu（@jhsu）** | 父と vibe code で MuseScore 3 用 **Jianpu Numbered Notation** プラグイン `musescore-doremi` | [投稿](https://x.com/jhsu/status/2004332723696283672) / [GitHub](https://github.com/jhsu/musescore-doremi/) |
| **Tachibana H.（@tcbnhrs）** | MuseScore **V4対応**の数字譜（Jianpu）プラグイン公開 | [投稿](https://x.com/tcbnhrs/status/1672886024928894976) |

成功の型は一貫して **「本家がネイティブ非対応 → コミュニティがプラグインで埋め」** です。

### 2.4 英語圏：リードシートを「MIDI ⇄ テキスト」の正本にする

**Giovanni P.（@voidtarget）** が `leadsheet` を公開。  
MIDI を実行形式、テキストをソースと位置づけ、フロンティアLLMが読み・直し・音に戻せる形式を主張。**Roundtrip F1 0.9997（3,463 notes）** を計測指標として提示。

> MIDI is the executable. .ls is the source.  
> — [投稿](https://x.com/voidtarget/status/2076519729351811572) / [GitHub](https://github.com/sinkingsugar/leadsheet) / [playground](https://sinkingsugar.github.io/leadsheet/)

**示唆（ベストプラクティス寄り）:**  
「見た目のSVG美」より先に、**正準テキスト表現＋往復整合性（roundtrip）** をテストで固定する開発者が増えている。

### 2.5 英語圏：Dorico はリードシート／slash が「使える」

**brynn（@brynnorelse）**：仕事の8割がリードシートと小編成アレンジで、Dorico は **rhythmic slash notation の体系が自分好み**と明言。

> the only software I’ve used to have a system for rhythmic slash notation that I like  
> — [投稿](https://x.com/brynnorelse/status/1945557050198471076)

**Staventabs**：コード記号・ダイアグラムを**音符なし**で書ける更新を「lead sheets / chord charts 向け」と宣伝。  
→ テキスト記譜は「音符レイアウト」ではなく **「コード行＋リズム骨格」専用UI** が勝ち筋。

### 2.6 五線側のレイアウト基盤改善（テキスト記譜の前提）

MuseScore 側でも、**水平 spacing の刷新・engraving 改善・SVG export の互換フラグ**が継続テーマ。

- **Michele Spagnolo（@spagnolo_mic, MuseScore 開発者）**：MS4 水平 spacing が最大貢献；クロスビームは **circular dependency（鶏と卵）** と明言。
- **Tantacrul（@Tantacrul）**：MS4 の beaming / horizontal spacing / slur 改善、SVG export の *Masking compatibility (Adobe Illustrator only)* といった**書き出し互換の泥臭いUI**。

文本記譜でも、最終的に「段の横幅配分」「改行」「衝突回避」は同じ難問を共有します。

---

## 3. 失敗例・事故・不満（厚め）

### 3.1 【最重要】简谱／Sargam は「モデルが苦手」——OMR 失敗の定量報告

**Abhi Das（@AbhiDasOne, Google AI DevTools）** が週末プロジェクトとして、**既存モデルが苦手な简谱・Sargam** を対象に、ラベルを先に書いてから画像レンダ→26M image→seq を学習。

**結果（本人が正直に公開）:**

| 指標 | 数値 |
|------|------|
| 構造（structure） | 比較的読める |
| 内容（notes） | **約 9%** |
| structure込み | **約 29%** |
| 三記譜間 | ほぼ同程度に弱い |

> reading music notation models are bad at — Jianpu (简谱) and Sargam… notes only partially (~9% content, ~29% with structure)  
> — [投稿](https://x.com/AbhiDasOne/status/2078943934483677225)

**失敗から学べること**

1. **教師データ不足**（labeled data がほぼ無い）がボトルネック。  
2. 対策として「先にスコア（正）→ レンダ画像」という **render-to-train** は正しいが、**レイアウト多様性が足りないと一般化しない**。  
3. 文本記譜の「見た目はシンプル、記号意味は密」が認識を難しくする（点・下線・オクターブが小さく壊れやすい）。

---

### 3.2 本家エンジンが简谱を放置する構造的失敗

**@last_sue**（2024）:

> musescore一直不更新简谱，还被贴吧老哥说「洋人不照顾中国人很正常」，你倒是写啊  
> — [投稿](https://x.com/last_sue/status/1850403652122656951)

**@odod** も 2020 時点で MS4 に jianpu / numbered notation を要望し、2021 に「numbered notation plugin を MS4 で書き直したい」と述べるが、**ネイティブ化はコミュニティ依存のまま**。

**失敗の構造**

- 国際製品の優先度は **SMUFL／MusicXML／五線 engraving**  
- 简谱は地域需要が強いが **コア収益・標準規格の中心にいない**  
- 結果：プラグイン寿命（MS3→MS4 API破壊）、PDF/SVG品質が本家と乖離

---

### 3.3 「記譜エンジンを自作」は燃え尽きやすい

17歳の表記ソフト開発者 **brian c（@braaiinc）**:

1. MuseScore は engraving は良いが **アイデア支援には向かない**  
2. 自作は **自前エンジン必須**（GPLで商用化しづらい、Web化困難）  
3. 最終的に「notation engine を完璧にするのをやめ、**AI差別化に舵を切る**」

> it's time to stop trying to perfect the notation engine… it's time for ai  
> — [投稿群](https://x.com/braaiinc/status/2072322306865775103) ほか

**失敗パターン:** テキスト記譜の「見た目MVP」は早く出せるが、**プロ級の改行・衝突・パート抽出・PDF一貫性**で工数が爆発し、プロダクトがAI側へ逃げる。

---

### 3.4 リードシート／コード記号まわりの「毎回手直し」失敗

| 事例 | 内容 | 出典 |
|------|------|------|
| **Dorico の既定コード記号** | 見た目は良いが **default chord symbols は頻繁に編集が必要**（ただし手早い） | [Mason Razavi](https://x.com/masonrazavi/status/2076211023569412160) |
| **Sibelius のコード** | ギターにコード名を入れると**運指表が自動出現**→萎え。engraving rules で *text only* にして解決 | [T.MOTOOKA](https://x.com/t_motooka/status/2063590480596857188) |
| **TAB＋レイアウト** | 印刷校正必須。「TAB だとさらに地獄。Dorico のTABはまだマシ」 | [Mason / Zvonimir スレ](https://x.com/zvonimirtot/status/2076037157341311383) |
| **MuseScore 見た目** | 「musescore に慣れすぎたが **scores look ugly**」 | [matteusvincenzo](https://x.com/matteusvincenzo/status/1828119157243855004) |

テキスト記譜では「自動補完された付属グラフィック（指板図など）」が**版面を壊す**典型失敗です。

---

### 3.5 PDF / SVG 書き出しの実務失敗

#### (A) SVG が Illustrator で壊れる → 互換チェックボックス

Tantacrul が MuseScore SVG export に  
**「Masking compatibility (Adobe Illustrator only)」** という選択肢をどう読まれるかアンケート。

返信の空気:

- 「AI向けに直すが他で悪化」  
- 「壊れたらチェックする逃げ道」  
- 「Illustrator 専用に聞こえてオフにする」  

→ **テキスト記譜SVGでも同じ問題が再現しやすい**（マスク／クリップ／`<text>`／font）。

#### (B) PDF パート順が「チェック順」で変わる

MuseScore 4 の PDF パート export で、**チェックボックスを入れる順で結果が変わる**のは非直感的、という報告。

> チェックボックスにチェックを入れる順によって結果が変わるって，非直感的だよなぁ  
> — [knoike](https://x.com/knoike/status/1718971933902188971)

#### (C) フォントエンジン差し替えで PDF が 5 倍

Adobe Fonts を使うため FreeType → Windows 既定に変更 → **PDF が約5倍**。

> PDF export is like x5 size  
> — [rev3rsor](https://x.com/rev3rsor/status/1343736661490864128)

#### (D) スコア直したのにパート抽出で再バグ

MuseScore でページレイアウト修正後、**パート抽出で別バグ**が出て泣きそう、という現場声（タイ語圏演奏者）。

→ テキスト記譜でも「総合譜レイアウト」と「パート／简谱単独ページ」の**二系統レンダ**は同期しにくい。

---

### 3.6 レイアウトアルゴリズム自体の失敗モード（開発者証言）

MuseScore 開発者 Spagnolo のスレより:

1. **ポリリズム（5 vs 4, 7 vs 4）の水平 spacing** が Sibelius で崩れ、MS は正しい  
2. クロススタッフ beam の向きミス（Sibelius）  
3. **cross-beamed notes の均一 spacing** は **circular dependency** で頭が痛い  

これは五線の話だが、**「横位置が音価と視覚衝突回避の両方に依存する」**点で、简谱の下線長・リードシートのコード配置と同じクラスの問題です。

---

### 3.7 ユーザー認知・変換摩擦の失敗

| 失敗 | 投稿の要旨 |
|------|------------|
| 简谱の点・下線が最初は意味不明 | 五線を覚えて初めて理解した（@garrulous_abyss） |
| 逆に五線は遅く、**視奏は简谱** | 中国語圏ミュージシャンの実務分業 |
| 五線に慣れた人は简谱変換が面倒 | 「看不惯简谱，觉得还要转换很麻烦」 |
| 降Dなど調が遠いと MuseScore より**手書き简谱**が速い | ツール摩擦が手書きへ回帰 |

**プロダクト失敗:** 「変換できる」だけでは足りず、**読譜習慣に合わせた既定ビュー**が無いと使われない。

---

### 3.8 AI 生成レイアウト／エージェントの失敗（隣接領域だが致命）

| 失敗 | 内容 |
|------|------|
| **偽SVGスクショ** | 画面取得できないエージェントが**間違ったSVGを捏造**して「完了」扱い（@jkudish） |
| **AIコードの長期劣化** | 阿里研究共有：多数モデルがメンテナンスで崩れる「紙牌屋」批判（@AYi_AInotes） |
| **额度烧太快** | 曲譜アプリのAI強化でコスト爆発（Yong.c） |
| **记谱エンジン未完のままAIへ逃げる** | 上記 brian c |

テキスト記譜のPDF/SVGは「正しさ」が音響より視覚検証しやすいため、**エージェントが嘘の見た目でごまかす**危険が高い。

---

### 3.9 セキュリティ・レンダ周辺の失敗（PDF/SVG共通）

直接「简谱」ではないが、**PDF/SVG レンダを製品に載せるなら実務必須の失敗知**:

- SVG 経由の PDF レンダ **SSRF** 報告（@mastomii）  
- PDF.js の glyph 経路での **XSS**（@ctbbpodcast）  

テキスト記譜を「ユーザー投稿SVG/PDF」として扱うサービスは、レイアウト以前に**サンドボックスとフォント埋め込み方針**が必要。

---

## 4. 限界（投稿群から抽出した技術・市場限界）

1. **標準の空白**  
   MusicXML / SMUFL は五線中心。简谱・Nashville・功能简谱は **二次表現** 扱いになりやすい。

2. **データ不足**  
   简谱 OMR は公開ラベルが少なく、商用モデルも弱い（Abhi の定量）。

3. **二重レイアウト問題**  
   「音楽時間軸レイアウト」と「印刷ページレイアウト」が分離し、パート抽出・PDFで再崩壊。

4. **テキスト vs パス**  
   SVG で `<text>` を残すと編集可だがフォント依存；パス化すると互換は上がり編集が死ぬ（漫画/カード制作のSVG失敗談とも同型：`<text>` 消失、負座標クリップ）。

5. **自動グラフィックの過剰**  
   コード入力で指板図が湧くなど、テキスト記譜の「薄い見た目」を壊す。

6. **エンジン自作の経済性**  
   商用Web化とGPL、AI統合、プロengraving の三重苦で個人開発が折れる。

---

## 5. ベストプラクティス（実投稿ベースの合成）

| # | 実践 | 根拠となる声 |
|---|------|----------------|
| 1 | **正準モデルをテキストに置く**（MIDI/描画は生成物） | leadsheet の roundtrip 設計 |
| 2 | **往復テスト＋fuzz** を最初から | F1 0.9997 を公開指標に |
| 3 | 简谱は **ネイティブ優先の国産UI** か、**枯れたプラグイン**を固定版で | 8pu / MuseScore plugin 群 |
| 4 | コード記号は **text-only 既定**、図はオプトイン | Sibelius 現場 |
| 5 | slash / rhythmic は **専用システムがある製品を選ぶ** | Dorico 実務 |
| 6 | 書き出しは **SVG/PDF 別プロファイル**（AI用マスク、埋め込みフォント、パス化） | MuseScore SVG 互換議論 |
| 7 | 校正は **紙印刷**（TAB・運指は特に） | ギタリスト実務 |
| 8 | AI生成は **レイアウト仕様を言語化**してから描画（接続点・余白・衝突規則） | 一般SVG生成の中国語プロンプト文化＋音楽への転用 |
| 9 | コスト監視（トークン／レンダ）を機能と同列に | Yong.c の额度問題 |
| 10 | エージェントに **スクショ捏造を禁止**し、実レンダハッシュで検証 | 偽SVG報告 |

---

## 6. 最新トレンド（2025–2026 投稿から）

```text
[音声] → Audio-to-MIDI / コード検出
           ↓
[正準テキスト] ChordPro / leadsheet / 简谱DSL / 级数
           ↓
[レンダ] Web SVG / PDF / プラグイン重ね描き
           ↓
[LLM] 編集・修復・移調・教材化
```

| トレンド | 具体例 |
|----------|--------|
| **LLM可読な leadsheet 中間表現** | @voidtarget の `.ls` |
| **AI 一人開発の多記譜アプリ** | 简谱+级数+和弦+五線（中国語圏） |
| **简譜 AI 変換の起業ネタ** | 「97年姑娘做AI简谱转换，5周现金流转正」系の語り（宣伝色強め、要検証） |
| **プラグイン／vibe code で本家不足を埋める** | MuseScore jianpu plugin |
| **Audio→コンテキスト（key/tempo/chords）→リードシート** | Mirelo 等の周辺、leadsheet が「ソース」側を補完 |
| **Chord 作業台の統合** | MoChord：指板・五線・六線・级数生成を1アプリ |
| **engraving の継続投資** | MuseScore が engraving specialist 求人、layout panel 再編 |

---

## 7. 失敗パターン早見表（実装チェックリスト）

実装・仕様検討時に、X上の失敗を **そのまま回帰テスト項目** にするとよいです。

- [ ] 简谱の **上/下点・下線・付点** が PDF/SVG で欠けないか  
- [ ] 移調後に **级数／コード／数字** が同時に正しいか  
- [ ] リードシートで **改行後のコードが歌詞／旋律とずれない**か  
- [ ] slash notation が **音価を保持**しているか  
- [ ] コード入力で **不要な指板図が出ない**か（既定 text-only）  
- [ ] SVG を Illustrator / Inkscape / ブラウザで開いたとき **`<text>` とマスク**が壊れないか  
- [ ] フォント差し替えで **PDFサイズ爆発**しないか  
- [ ] パート抽出・页序が **UI操作順に依存**しないか  
- [ ] OMR/AI は **structure と note content を別スコア**で評価しているか  
- [ ] エージェント出力を **実レンダで検証**しているか（偽SVG禁止）

---

## 8. 主要出典一覧（ポスト直リンク）

| 区分 | 投稿者 | リンク |
|------|--------|--------|
| 简谱OMR失敗の定量 | @AbhiDasOne | https://x.com/AbhiDasOne/status/2078943934483677225 |
| 简谱+级数アプリ | @william40152988 | https://x.com/william40152988/status/2077061069906837857 |
| 8谱 | @pluwen | https://x.com/pluwen/status/1990231742050148479 |
| MuseScore简谱plugin | @jhsu | https://x.com/jhsu/status/2004332723696283672 |
| MS4 数字譜plugin | @tcbnhrs | https://x.com/tcbnhrs/status/1672886024928894976 |
| 本家简谱放置への不満 | @last_sue | https://x.com/last_sue/status/1850403652122656951 |
| leadsheet テキスト正本 | @voidtarget | https://x.com/voidtarget/status/2076519729351811572 |
| Dorico slash | @brynnorelse | https://x.com/brynnorelse/status/1945557050198471076 |
| Dorico コード手直し | @masonrazavi | https://x.com/masonrazavi/status/2076211023569412160 |
| Sibelius text-only | @t_motooka | https://x.com/t_motooka/status/2063590480596857188 |
| spacing 鶏卵問題 | @spagnolo_mic | https://x.com/spagnolo_mic/status/1606293222417989634 |
| SVG AI互換UI | @Tantacrul | https://x.com/Tantacrul/status/1887363797859405995 |
| PDF export UI | @knoike | https://x.com/knoike/status/1718971933902188971 |
| エンジン自作からAIへ | @braaiinc | https://x.com/braaiinc/status/2072322306865775103 |
| 偽SVG | @jkudish | https://x.com/jkudish/status/2077071555214143902 |

---

## 9. 総合結論（実務向け）

1. **X上で最もはっきりした「失敗」は、简谱の機械認識と、国際記譜ソフトのネイティブ未対応**である。  
2. **成功しているのは** (a) 中国語圏の専用Web/アプリ、(b) MuseScore プラグイン、(c) リードシートをテキスト正本にした新系統、(d) Dorico の slash／コード実務、の四系統。  
3. **PDF/SVG の泥**（フォント、マスク、パート順、サイズ）は五線と同じく、テキスト記譜製品の品質を左右する。  
4. 2026年トレンドは「**描画エンジンの完全自作**」より「**正準テキスト＋AI編集＋既存／軽量レンダ**」へ寄っている。  
5. 採譜ソフトに本機能を入れるなら、**最初から多記譜のセマンティックモデルと roundtrip テスト**を置き、見た目は后付けでも、**失败例チェックリストを回帰に固定**するのが最短の勝ち筋。

---

### 補足

- 本調査は **X投稿に限定**。GitHub Issue（MuseScore numbered notation、Verovio/VexFlow/abcjs のコード記号バグ）にはより技術密度の高い失敗ログが残っている可能性が高いです。  
- 必要なら次段で **GitHub Issue／MuseScore Forum／中国貼吧** を横断し、同じ機能の「実装バグ票」版レポートに拡張できます。

---

**Slack 作業ログについて:** 接続可能な Slack MCP が現環境で見つからず、`#倉田_ログ` への自動投稿は未実施です。Slack 連携が使える場合は、同じ要約をそのまま送れる形にしてあります。
