# F-052 MusicXML妥当性検証 — 実装前リサーチ(10並列ワークフロー)

**取得日:** 2026-07-21 / Issue #66 / 実装コミット 5167a73
**方式:** 先行リサーチ(Web/論文・失敗例重視)→実装 の並列ワークフローのリサーチ段を保存

## 推奨アプローチ(approach)
【検証済み環境】music21 10.5.0 / lxml 6.1.1 が .venv に導入済み。以下は実機で実際に動作確認した結果に基づく。

【validate_musicxml(path)->ValidationReport の実装骨子】
1) parse段: music21.converter.parse(str(path)) を try/except で囲む。例外(SyntaxError/Music21Exception/その他)は is_valid=False + errors に型名+メッセージを追記して即return(以降の検査はスキップし roundtrip_ok=False)。捕捉例外は広め(Exception)にしつつ型名をerrorに残す。
2) 構造検査: sc.parts が空 → errors「パート無し」。全パート走査で recurse().notes が0 かつ Rest も0 → warnings(空譜面)。各Measureの barDuration と実音価合計の乖離(小節整合)は warnings 止まりにする(music21のmakeNotationで概ね整合するが端数許容)。small tolerance(例 1/2048拍)で比較。
3) note_count: len(list(sc.recurse().notes)) を採用。★重要: 和音(chord.Chord)は .notes で「1要素」として数えられる(実測: C-E-G和音+単音=.notes 2, pitch数4)。pitch総数(sum(len(n.pitches)))はラウンドトリップで壊れやすいので使わない。note_count は要素数で固定する。
4) roundtrip: sc.write('musicxml', fp=一時ファイル(tempfile+finally削除)) → converter.parse で再読込 → 再度 len(recurse().notes)。元と一致で roundtrip_ok=True、差分ありなら False + errors に「N→M」。実測で単純譜面は要素数保存を確認済み。書き出しは makeNotation デフォルト(True)で行う(Falseは小節が無いと MusicXMLExportException)。write/再parseのどちらかで例外→roundtrip_ok=False + errors。
5) XSD段(ある場合のみ): lxml.etree.XMLSchema でスキーマ検証。★核心の落とし穴対策(下記pitfalls)としてカスタム Resolver 必須。スキーマは tests/schemas/musicxml40/ に musicxml.xsd + xml.xsd + xlink.xsd が同梱済み。実測で Resolver 経由なら XMLSchema ロード成功&music21出力が valid 判定。XSD が使えない/ロード失敗時は warnings に「XSD未実行(構造検証にフォールバック)」と明記し is_valid は構造検査結果で決める(要件どおり)。

【安全なlxmlパース設定】ET.XMLParser(no_network=True, resolve_entities=False, load_dtd=False)。music21出力の先頭には <!DOCTYPE score-partwise PUBLIC ... "http://www.musicxml.org/dtds/partwise.dtd"> が入る(実測)ため、DTDを引きに行かせない/外部実体を解決しない設定でXXE・ネットワーク待ちを防ぐ。XSD検証時は resolve_filename でローカルxsdへ差し替えるResolverを parser.resolvers.add() する。

【ValidationReport】@dataclass(frozen=True)。errors/warnings は field(default_factory=list) ではなく呼び出し側でtupleでなくlistを渡す設計にするか、frozen+listの可変性に注意(リスト自体は再代入不可だが中身は可変)。イミュータブル厳守なら tuple[str,...] に寄せるのが安全だが、要件が list[str] 指定なので list を使い「構築時に完成させる」方針(構築後は触らない)。

【テスト(AAA・pytest)】新規テスト1本のみ。(a)有効な最小Score→to_score等で作りwrite→validate: is_valid=True, roundtrip_ok=True, note_count一致。(b)壊れたXML(不正タグ/空ファイル)→is_valid=False かつ errors非空・例外を投げない。(c)和音を含む譜面で note_count が要素数(pitch数でない)であることを固定。(d)lxml/XSD無い状況の擬似(XSDロード失敗パス)で warnings に未実行注記が入ることを確認(monkeypatch or 不在時分岐)。テスト実行: .venv/bin/python -m pytest tests/<新規> -q -p no:cacheprovider で緑を確認。

## 落とし穴・失敗例(pitfalls)
【最大の落とし穴: XSDが標準ロードで壊れる(実測FAIL)】music21同梱 .venv/.../music21/musicxml/musicxml.xsd(v2.0 Strict Beta)も tests/schemas/musicxml40/musicxml.xsd(v4.0)も、そのまま ET.XMLSchema(ET.parse(xsd)) すると失敗する。実エラー: "attribute 'ref': The QName value '{http://www.w3.org/XML/1998/namespace}lang' does not resolve" (line 1323付近)。原因は musicxml.xsd 冒頭の <xs:import ... schemaLocation="http://www.musicxml.org/xsd/xml.xsd"/> と xlink.xsd が死んだ/到達不能なリモートURLを指すこと。オフラインでは xml名前空間のxml:langが解決できずスキーマ構築自体が失敗する。→対策: os.path.basename(url) を tests/schemas/musicxml40/ 内のローカル同名ファイル(xml.xsd, xlink.xsd が実在・単体ロードOK確認済み)へ差し替える lxml.etree.Resolver を実装し parser.resolvers.add() する。これで XMLSchema ロード&検証成功を実測確認。この対策無しでXSD検証を書くと「常に例外→常にwarningフォールバック」になり、XSD検証が事実上死ぬ。

【落とし穴2: note_count の定義揺れ】pitch総数 vs 要素数で値が違う(和音C-E-G=要素1/pitch3)。ラウンドトリップ差分判定を pitch数でやると、music21が和音を分解/再結合した際に誤検知しやすい。要素数(len(recurse().notes))で統一し、それを note_count にもroundtrip比較にも使う。

【落とし穴3: DOCTYPE経由のネットワーク/XXE】music21のwrite出力は partwise.dtd へのリモートDOCTYPEを含む。素のlxmlパースやvalidateでネットワーク待ち・XXEリスク。no_network=True, resolve_entities=False, load_dtd=False を必ず設定。converter.parse自体はDTDを取りに行かない(実測パスOK)が、lxml側検証では明示設定必須。

【落とし穴4: write(makeNotation=False)】小節が無いScoreに対し makeNotation=False で書くと MusicXMLExportException。ラウンドトリップ書き出しはデフォルト(True)を使う。ただしTrueはdeepcopy+記譜補正を行うため、元Scoreを破壊しない代わりに音符が補正で増減しうる(端数音価が分割される等)。roundtrip差分は「一致必須」でなく差分をerrorsに記録して roundtrip_ok で表現する設計が堅牢(厳密一致を is_valid の必須条件にしない方が実務的)。

【落とし穴5: 一時ファイルの後始末】roundtripで tempfile を使うなら try/finally で必ず削除。tempfile.mktemp は競合リスクがあるため NamedTemporaryFile(delete=False)+finally unlink か mkstemp が安全。

【落とし穴6: 空/最小入力】'<score-partwise/>' は例外を投げず notes=0 でパースできる(実測)。空譜面を is_valid=False にするか warnings 止まりにするかは要件解釈。要件「パート/音符の存在を検査」に従い、パート0はerror、パートありで音符0はwarningが穏当。

【落とし穴7: 例外型の広さ】music21のparse失敗は SyntaxError, music21.exceptions21.Music21Exception, ValueError, ET系など多岐。狭く捕捉すると想定外例外でクラッシュ→堅牢性のため except Exception で捕捉しつつ型名をerrorに残す(握り潰さない)。

【落とし穴8: frozen dataclass + list】frozen でも list フィールドは中身が可変。「イミュータブル厳守」を字義通り取るなら本来tupleだが、要件が list[str] 指定なので、構築時に確定させ以後mutateしない運用で担保する(docstringに明記)。

## 参考(prior_art)
【英】"Validating MusicXML files without the tears" (Karim Ratib, blog.karimratib.me/2020/11/17): MusicXML XSD検証の実務的注意をまとめた定番記事。XSDの xs:import が壊れており事前パッチ/XMLカタログが必要、リモートschemaLocationよりローカルコピー参照が大幅に高速、という2点が核心。本タスクのResolverによるローカル差し替え方針と一致。

【英】w3c/musicxml Issue #259 "Adding a XML catalog file" / Discussion #445 "Failed to load external entity": MusicXML公式リポジトリで、xml.xsd・xlink.xsdの外部import参照がオフライン検証を壊す問題が議論され、v4.0で標準XMLカタログ(catalog.xml)を同梱する対応が入った。→ローカルにxml.xsd/xlink.xsdを置きカタログ or resolverで解決するのが公式推奨解。本プロジェクトは tests/schemas/musicxml40/ に3ファイル同梱済みで、この推奨に沿える。

【英】lxml公式 validation.html / resolver ドキュメント: ET.Resolver を parser.resolvers.add() で登録し resolve_filename でローカルファイルへ差し替える手法。XMLSchema構築時のimport解決に適用可能。実機でこの手法によりmusicxml.xsd(v4.0)のロード成功を確認。

【英】music21公式ドキュメント(m21ToXml / xmlToM21 / converter): write() の makeNotation=False は測定小節が無いと MusicXMLExportException を投げる。MIDI由来など「録音入力」から作った譜面は異名同音情報を欠き、記譜ソフト作成ファイルより往復で崩れやすいと明記。→本タスクのroundtripは「厳密一致を強制せず差分を記録」する設計が妥当という裏付け。

【中/英】stringsync/musicxml(TypeScriptラッパ)やw3c musicxml XSD Reference: MusicXMLのXSDはDTDより厳格で、要素の並び順・必須属性(version等)を強制する。music21のデフォルト出力は version="4.0" 付きで、実測ではローカルv4.0 XSDに valid 判定される(Resolver適用時)。つまり「自前生成の妥当な譜面はXSDを通る」ことを確認済みで、XSD検証を回帰ガードとして使える。

【実測ローカル知見(本リポジトリ)】既存 tests/test_score_checks.py が check_score/check_time_signature 等でヘッダ妥当性・小節数・連桁を検査するパターンを確立済み。ValidationReport のフィールド設計(is_valid/errors/warnings/note_count/roundtrip_ok)はこの既存検査の延長として自然に配線できる。既存の score.py write_musicxml(score, path) が出力口なので、テストは to_score→write_musicxml→validate_musicxml の流れで組める(親のpipeline配線を待たずテスト単体で閉じる)。

## 実装上の限界・正直な注記(notes)
重要: 当タスクのモジュールとテストは着手時点で既に両方存在し完成していた。当方は新規作成・編集を一切行っていない(指示どおり既存ファイルを編集せず、__init__.py も既に配線済みだった)。行ったのは既存実装の読解と検証のみ。

検証で確認した事実(捏造なし・実測):
- 6テスト全緑を実機で確認。
- リサーチ最大の落とし穴(XSD標準ロード失敗)への対策が実装済みかつ実際に機能: _load_schema() が lxml Resolver 経由で musicxml.xsd(v4.0)のロードに成功(schema loaded: True)。有効な最小Scoreに対し XSD検証が実際に実行され(フォールバックでなく)is_valid=True/errors空/warnings空を実測。lxml 6.1.1。
- note_count は要素数固定(pitfall 2 対策)。ラウンドトリップは makeNotation=デフォルトで tempfile.mkstemp + try/finally 削除。lxmlパースは no_network=True/resolve_entities=False/load_dtd=False。except Exception で広く捕捉しつつ型名を errors に残す。

限界・注記:
- frozen dataclass だが errors/warnings は list のため中身は技術的に可変(pitfall 8)。docstringに「構築時に確定させ以後mutateしない運用で担保」と明記されており、公開関数は構築後に touch しない。字義通りのイミュータブルにするなら tuple[str,...] が安全だが、仕様が list[str] 指定のため list を採用している。
- 空譜面(パートありで音符0)は is_valid=False にせず warning 止まり。パート0のみ error(is_valid=False)。要件「パート/音符の存在を検査」の穏当な解釈。
- ラウンドトリップ差分は is_valid の必須条件にしていない(roundtrip_ok で表現)。makeNotation の記譜補正で音符が増減しうるため厳密一致を強制しない設計(pitfall 4)。
- 小節整合の乖離は warning 止まり(端数許容 tolerance = 1/2048拍)。
