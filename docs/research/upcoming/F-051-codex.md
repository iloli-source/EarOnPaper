# Guitar Pro形式TABエクスポートに関する論文・WEB調査報告（codex担当）

**調査日:** 2026-07-21
**対象:** 採譜/記譜ソフト機能「Guitar Pro（`.gp` / `.gp5` / `.gpx`）形式でのTAB譜エクスポート」
**担当:** codex（論文＋WEB検索、**特に失敗例を最大限**）
**調査手段:** OpenAI Codex（読取り専用）による公開ドキュメント/Issue調査 ＋ WebSearch / WebFetch による一次情報確認
**方針:** 実在情報のみ・URL併記・捏造禁止。未確認は「未確認」と明記。英語中心（中国語圏の深い仕様談義は乏しく、FOSS/GitHub側に情報が偏在）。

---

## 0. 調査範囲と限界（重要）

| 項目 | 内容 |
|------|------|
| 学術論文 | **Guitar Pro形式のエクスポート実装そのものを扱う査読論文はほぼ皆無。** 採譜（AMT: Automatic Music Transcription）論文はMIDI/ピアノロール出力が主流で、GP形式は「実装詳細」としてFOSS側に蓄積されている。よって本報告は**技術ドキュメント・GitHub/SourceForge Issue・リバースエンジニアリング記事**が主軸。 |
| プロプライエタリ性 | `.gp5`/`.gpx`/`.gp` はArobas Music社の独自仕様。公式仕様書は非公開で、**GP4.06の古い仕様書＋テストファイルからのリバースエンジニアリング**が全実装の土台。 |
| 「開く≠忠実」 | 「エクスポートしたファイルが開ける」ことと「データが忠実に往復する」ことは別問題。多くのライブラリが多数の要素を**暗黙にドロップ**する。 |

---

## 1. フォーマット仕様と実装ライブラリ

### 1-1. 3つのフォーマット世代

| 形式 | 世代 | 実体 | 備考 |
|------|------|------|------|
| `.gp3/.gp4/.gp5` | GP3〜5（レガシー） | **独自バイナリ**。リトルエンディアン。文字列は8bitエンコード（PyGuitarProの既定は `cp1252`） | GP4.06仕様書＋テストファイルから解析。全実装の基準。 |
| `.gpx` | GP6 | **BCFZ**（独自圧縮コンテナ）内に `score.gpif`（GPIF XML）等 | BCFZは独自ビットストリーム圧縮。TestDisk等は先頭マジック `BCFZ` で識別。 |
| `.gp` | GP7/GP8 | **標準ZIPアーカイブ**。`VERSION` / `Content/score.gpif`（XML） / `Preferences.json` / `BinaryStylesheet` / `PartConfiguration` / `LayoutConfiguration` | GP8はGP7の拡張。audioトラック・パスワードロック等が追加。 |

- `.gp5` バイナリの並び順（PyGuitarPro仕様）: スコア情報 → 歌詞/RSE/テンポ/調号/MIDIチャンネル → 小節数 → トラック数 → 小節ヘッダ → トラック → 小節/トラックデータ。
- トラックはフラグ・名前・弦数・**チューニング（7個のint、高→低の順）**・MIDIポート/チャンネル/エフェクトチャンネル・フレット数・**カポ位置**・色を保持。音符は弦のビットマスク＋音符/エフェクトフラグで格納。
- 出典: [PyGuitarPro File Format docs](https://pyguitarpro.readthedocs.io/en/stable/pyguitarpro/format.html) / [alphaTab GP3-5](https://alphatab.net/docs/formats/guitar-pro-3-5) / [GP4.06 format description](https://dguitar.sourceforge.net/GP4format.html)
- BCFZ解説・GP6/7圧縮差: [alphaTab GP6](https://alphatab.net/docs/formats/guitar-pro-6) / [rust-gpx-reader](https://github.com/Antti/rust-gpx-reader)

### 1-2. 主要ライブラリの対応状況（★エクスポート可否が重要）

| ライブラリ | 言語 | 読込 | **書出（export）** | 注意 |
|-----------|------|------|-------------------|------|
| **PyGuitarPro** | Python | GP3/4/5 | **GP3/4/5のみ**。GPX/GP7は対象外 | PyPIでベータ扱い。GPX非対応は[Issue #19](https://github.com/Perlence/PyGuitarPro/issues/19)で明言。 |
| **alphaTab** | JS/C# | GP3-5, GPX, GP7, GP8 | **GP7 `.gp` のみ**（1.2.0〜）＋ alphaTex（1.7.0〜）。**GP5/GPXエクスポート不可** | GP8は「GP7相当まで」互換。audio/パスワードロックは非対応。 |
| **TuxGuitar** | Java | GP3/4/5, GPX, GP7 | **GP3/4/5のみ**。GPX/GP7は読めるが書けない | 公式は保存用に独自の `.tg` を推奨。 |
| **guitarpro (slundi, Rust)** | Rust | GP3/4/5, GPX, GP7+（README主張） | README上は読書対応主張 | ただしロードマップに「High-fidelity GP5 parsing」「Initial GP6/7 support」が**未完として残存**。実測前は要検証。 |
| parse-gp5 / knasan/parsegp 等 | JS/Go | GP3/4/5(/GPX) | 主にパーサ（読取専用） | [parsegp (Go)](https://pkg.go.dev/github.com/knasan/parsegp) |

**設計上の最重要含意:** 「PythonでGP7/GPXを書きたい」は現状**手段がほぼ無い**。PyGuitarProはGP5止まり、GP7書出しはalphaTab（JS/C#）に限られる。採譜エンジンがPythonなら、**現実的な出力ターゲットはGP5**、あるいはGP7が要るならalphaTabをサブプロセス/別プロセスで挟む構成になる。

---

## 2. エクスポート失敗例・非互換（★本報告の主眼）

### 2-1. TuxGuitar: GP5保存でファイルがゼロバイトになる（MIDIチャンネル枯渇）

- **現象:** トラックを追加/削除した後にGP5保存すると、**出力ファイルが0バイト（破損）** になる。
- **根本原因:** TuxGuitarは通常トラック1本あたりMIDIチャンネルを**2本**消費（通常音＋ピッチベンド用）。MIDIは16チャンネル上限。枯渇して無効/nullチャンネルが割り当たるとGP保存が失敗する。
- **回避策:** MIDIチャンネルを手動共有/再設定する、または独自 `.tg` で保存。
- 出典: [TuxGuitar Bug #66](https://sourceforge.net/p/tuxguitar/bugs/66/) / [Help: wiping files after adding tracks](https://sourceforge.net/p/tuxguitar/discussion/522985/thread/98288d70/) / [Help: file corrupted when adding a track](https://sourceforge.net/p/tuxguitar/discussion/522985/thread/ad23798a55/)

### 2-2. TuxGuitar: 「Save As」でGP保存できない（Windows/Linux）

- Bug #105 として「Windows/Linuxで Guitar Proファイルとして Save As できない」報告。
- 出典: [TuxGuitar Bug #105](https://sourceforge.net/p/tuxguitar/bugs/105/)

### 2-3. TuxGuitar: GP5インポータ由来のクラッシュ・非互換（歴史的）

- ArrayIndexOutOfBoundsでGP5が開けない（#39）、**UTF-8 BOM付きGP5**が開けない（#40）、GP5小節データの読取り順誤り（#42）。
- 変更履歴（1.6.1）で **GP5の調号保存バグ修正 / GP5ハーモニクス入出力改善 / GP5の反復（alternative repeats）修正** が確認できる＝過去に往復バグが実在した証跡。
- 反復/複数エンディングで保存タブが破損し古いTuxGuitarが「非対応」と拒否する報告（#113、ユーザー報告・修正未確認）。

### 2-4. alphaTab: GP7エクスポータがNullReferenceExceptionでクラッシュ

- **[Issue #1025](https://github.com/CoderLine/alphaTab/issues/1025)**: null/undefinedの歌詞データが原因でGP7エクスポータが `NullReferenceException` を投げエクスポート失敗。PR #1026で修正。
- 含意: **歌詞など任意フィールドがnullのまま渡ると書出しが落ちる。** エクスポート前のフィールド正規化が必要。

### 2-5. alphaTab: GP5読込での型付き配列長エラー（反復エンディング誤読）

- **[Issue #1023](https://github.com/CoderLine/alphaTab/issues/1023)**: あるGP5が `RangeError: Invalid typed array length: -2` で読込失敗。alternate endings（複数エンディング）の誤読が原因。PR #1028で修正。
- 関連: 2つの反復＋alternate endingsで**2番目の本体がplaybackでスキップ**される（Issue #1046、1.3系で修正）。
- **教訓:** 反復・alternate endingは全実装で最も壊れやすい領域。

### 2-6. PyGuitarPro: 書出し→読戻しで全ビートが1つに潰れる

- **[Issue #4](https://github.com/Perlence/PyGuitarPro/issues/4)**: 自作GP5を `song.write()` すると**全ビートが1つに圧縮**され、全音符が同じ値・開始時刻になる。「生成直後のオブジェクトは正常だが、書出し→parseで再現」＝**シリアライズ/デシリアライズ工程の不整合**。
- Issueはクローズだが根本原因/公式修正の記載なし＝**未解決アーカイブの可能性**。手組みでScoreを構築する場合の要注意点。

### 2-7. PyGuitarPro: repeatAlternativeが8bitに切り詰められる等の往復データ欠損（歴史的）

- 変更履歴に実在した往復/忠実度バグ: **`MeasureHeader.repeatAlternative` がGP5書出し時に8bitへ切詰め**、コード情報の欠落（PR #10で修正）、付点連符duration生成の修正、GP3→新版変換時のビブラート/ハーモニクス修正。
- **[Issue #18](https://github.com/Perlence/PyGuitarPro/issues/18)相当**: GP7.5では開けるがPyGuitarProでは不正な `ChordExtension` で失敗 → 未知のfingering/note/chord列挙値を寛容に扱う修正が入った。
- 出典: [PyGuitarPro CHANGES.rst](https://github.com/Perlence/PyGuitarPro/blob/master/CHANGES.rst)

### 2-8. 生成GPXがモバイル版Guitar Proで「破損」と表示され開けない

- **[RocksmithToTab Issue #17](https://github.com/fholger/RocksmithToTab/issues/17)**: 生成した**GPXがGuitar Pro Android版で「file is corrupted」**。デスクトップGPや他のGPXは開けるのにモバイルだけNG。原因は不正なヘッダ等と推測。**GP5形式で出力すればモバイルでも開ける**ため回避。
- 関連: [Issue #38](https://github.com/fholger/RocksmithToTab/issues/38)「GP6が生成GPXを開けない」。
- **教訓:** GPX（BCFZ独自圧縮）の自前生成は破損リスクが高い。**互換重視ならGP5、モダン機能重視ならGP7 zip**が相対的に安全。

### 2-9. セキュリティ面の失敗例（参考）

- TuxGuitarのファイル読込に**XXE（XML外部実体）でローカルファイル窃取**の脆弱性報告。GPIF/XML系フォーマットを扱う実装は**XMLパーサの外部実体を無効化**すべき。
- 出典: [LogicalTrust: TuxGuitar XXE](https://logicaltrust.net/blog/2020/06/tuxguitar.html)

### 2-10. GP8ロックファイル（参考）

- GP8はパスワードロック付きファイルを出せる。alphaTab等は非対応。リバースエンジニアリング記事あり（[Unlocking Guitar Pro 8](https://wangyi.ai/blog/2026/01/16/unlocking-guitar-pro-8/)）。**ロック済みファイルは往復対象外**と割り切る。

---

## 3. 奏法記号・チューニング・カポの表現の落とし穴

### 3-1. 奏法記号は「構造レベル」が異なる → 貼り間違いで再生/表示崩れ

- GPバイナリは **ビートエフェクト**（whammy/tremolo bar、brush/pick stroke、tap/slap/pop、wah、rasgueado 等）と **ノートエフェクト**（bend、hammer/pull-off、slide、let-ring、grace、harmonics、trill、palm mute、staccato 等）を**別階層**で持つ。**どちらの階層に置くかを誤ると挙動が変わる。**
- 出典: [PyGuitarPro format docs](https://pyguitarpro.readthedocs.io/en/stable/pyguitarpro/format.html)

### 3-2. ベンドはbool値ではない

- GPのベンドは**type＋value＋複数ポイント（position/value/vibrato）** を保持。「Nセミトーン上げる」に平坦化すると**タイミングとリリース形状が失われる**。tremolo bar（ワーミー）も同様に複数ポイント表現。

### 3-3. ハーモニクスはバージョン間で最も脆い

- GP4/5は複数のハーモニクス種別/コードを持ち、TuxGuitar・PyGuitarPro双方に**ハーモニクスの入出力/変換修正の履歴**がある（§2-3, §2-7）。natural/artificial/pinch/tapped/semi の取り違えが起きやすい。

### 3-4. カポの落とし穴

- GP5は**トラックごとに単一のカポフレット**しか持たない。
- alphaTabはGP7/8で通常カポは扱うが、**パーシャルカポ（partial capo）は非対応**と明言 → GP7+のパーシャルカポは往復で欠落。
- **開放弦チューニングとカポの二重適用**（採譜時にカポ分をチューニングにも織り込むと二重にシフト）に注意。
- 出典: [PyGuitarPro format docs](https://pyguitarpro.readthedocs.io/en/stable/pyguitarpro/format.html) / [alphaTab GP3-5](https://alphatab.net/docs/formats/guitar-pro-3-5)

### 3-5. チューニングの落とし穴

- チューニングは**7個のint配列を高→低の順**で格納（弦数が6でも配列は7）。順序・弦数・未使用スロットの扱いを誤ると音高が総崩れ。

### 3-6. 「開ける」≠「忠実」：暗黙ドロップされる要素

alphaTabのGP3-5対応表では、**ページ設定・トラック名/色描画・カポ表示・マーカー/セクション描画・コード名/ダイアグラム描画・テキスト描画・ピックストローク描画・ミックステーブル変更（音量/パン/楽器）・テンポ描画・スコア情報/歌詞のaudio** 等が「ignored（データは保持するが表示/再生しない）」または非対応。「Diagrams In the Score」「MIDI Channels and Ports（alphaTex）」等は完全非対応。
- 出典: [alphaTab GP3-5](https://alphatab.net/docs/formats/guitar-pro-3-5)（総合互換96%と自称するが、**残り数%が実務では致命的になりうる**）

### 3-7. 文字エンコーディング

- PyGuitarProは文字列を8bit（既定 `cp1252`）で書く → **日本語/多バイト文字が化ける/落ちる**恐れ。GP7.0.4リリースノートでもGP5テキストエンコード改善に言及。UTF-8 BOM付きGP5が開けなかった事例（§2-3）もある。**日本語曲名/歌詞を扱う本プロジェクトでは特に要検証。**

---

## 4. ベストプラクティス

1. **出力ターゲットを意図的に最低限で選ぶ。** GP5世代の機能で足りるなら`.gp5`、モダン機能が必須で消費側が対応するなら GP7 `.gp`（GPIF/zip）。**GPX（BCFZ独自圧縮）の自前生成は破損リスクが高く避ける**（§2-8）。
2. **ユーザーのファイルを直接上書きしない。** 一時ファイルへ書出し → **書いた後に自分で読み戻し** → 非ゼロサイズ・トラック数/小節数の一致を検証 → アトミックに置換。TuxGuitarゼロバイト事件が教訓（§2-1）。
3. **書出し前バリデーション:** 各ボイスの小節長・連符・反復グラフ/alternate ending・弦番号・フレット範囲・チューニング順・カポ範囲・MIDIチャンネル（**16ch上限・トラック2ch消費を意識**）・エフェクトpayloadの完全性。
4. **任意フィールドのnull正規化:** 歌詞などがnullだとGP7エクスポータが落ちる（§2-4）。空文字/既定値に正規化。
5. **能力マトリクスを持ち、ダウングレード時に警告:** パーシャルカポ・audioトラック・RSE詳細・一部stylesheet/layout・コードダイアグラム配置・GP6/7限定構文はGP5書出しで消える。
6. **ゴールデンフィクスチャ群:** 全奏法・変則チューニング・カポ有無・8トラック超・パーカッション・反復/alternate ending・**歌詞/非ASCII（日本語）**・連符・複数ポイントのベンド・スライド・ハーモニクス・多声部小節を網羅。
7. **複数リーダで往復検証:** 自前exporter → PyGuitarPro/alphaTab/TuxGuitar でパース → 自モデルとdiff。加えて商用互換が要るなら**Guitar Pro 5/7/8で手動オープンテスト**。
8. **XMLセキュリティ:** GPIF系を読む場合は外部実体を無効化（XXE対策、§2-9）。

---

## 5. 主要出典一覧

- PyGuitarPro File Format: https://pyguitarpro.readthedocs.io/en/stable/pyguitarpro/format.html
- PyGuitarPro CHANGES: https://github.com/Perlence/PyGuitarPro/blob/master/CHANGES.rst
- PyGuitarPro Issue #4（ビート潰れ）: https://github.com/Perlence/PyGuitarPro/issues/4
- PyGuitarPro Issue #19（GPX非対応）: https://github.com/Perlence/PyGuitarPro/issues/19
- alphaTab GP3-5（非対応/ignored一覧）: https://alphatab.net/docs/formats/guitar-pro-3-5
- alphaTab GP6（BCFZ）: https://alphatab.net/docs/formats/guitar-pro-6
- alphaTab GP7 / GP8: https://alphatab.net/docs/formats/guitar-pro-7 , https://alphatab.net/docs/formats/guitar-pro-8
- alphaTab Exporter guide: https://alphatab.net/docs/guides/exporter
- alphaTab Issue #1025（GP7 null歌詞クラッシュ）/ #1023（GP5配列長）: https://github.com/CoderLine/alphaTab/issues/1025 , https://github.com/CoderLine/alphaTab/issues/1023
- TuxGuitar Bug #66（ゼロバイト）/ #105（Save As不可）: https://sourceforge.net/p/tuxguitar/bugs/66/ , https://sourceforge.net/p/tuxguitar/bugs/105/
- TuxGuitar file formats help: https://www.tuxguitar.app/files/devel/desktop/help/file_formats.html
- RocksmithToTab Issue #17 / #38（GPX破損）: https://github.com/fholger/RocksmithToTab/issues/17 , https://github.com/fholger/RocksmithToTab/issues/38
- GP4.06 format description: https://dguitar.sourceforge.net/GP4format.html
- rust-gpx-reader（BCFZ実装）: https://github.com/Antti/rust-gpx-reader
- TuxGuitar XXE（セキュリティ）: https://logicaltrust.net/blog/2020/06/tuxguitar.html
- Unlocking Guitar Pro 8（GP8ロック）: https://wangyi.ai/blog/2026/01/16/unlocking-guitar-pro-8/

---

**注記:** Guitar Pro形式のエクスポートを主題とする**査読付き学術論文は確認できなかった**。本領域の実務知はFOSS実装のIssue/変更履歴とリバースエンジニアリング記事に集約されており、本報告はそれらの一次情報に基づく。
