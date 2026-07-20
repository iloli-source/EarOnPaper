# F-091 度数/ローマ数字/Nashville — 実装前リサーチ(10並列ワークフロー)

**取得日:** 2026-07-21 / Issue #74 / 実装コミット 5167a73
**方式:** 先行リサーチ(Web/論文・失敗例重視)→実装 の並列ワークフローのリサーチ段を保存

## 推奨アプローチ(approach)
自前の決定論的な度数写像で実装する（music21のromanNumeralFromChordには委譲しない）。理由: 仕様は「root_pcを主音からの度数へ写像しqualityを付す」タスクであり、機能和声解析ではない。またmusic21委譲はChord再構築が必要で、後述の短調6/7度補正バグを踏む。

コア設計（frozen dataclass不要—純関数2つ+定数表でよいが、内部の度数マッピングは module-level の frozen なタプル/辞書で持つ）:
1) `interval = (root_pc - key_tonic_pc) % 12` で主音からの半音距離を出す。
2) 半音距離→(度数番号1-7, 変化記号) の写像表を major/minor 別に持つ。長調: {0:('1',''),2:('2',''),4:('3',''),5:('4',''),7:('5',''),9:('6',''),11:('7','')}。表外の半音（1,3,6,8,10）は変化音として最近傍のダイアトニック度数に♭/♯を付す（例 長調で1半音→'♭2' あるいは'#1'。慣例は下方向優先で♭2、6半音は#4/♭5だがトライトーンはコンテキスト依存—既定は#4）。
3) ローマ数字: 度数番号1-7→I..VII のローマ字へ変換。quality由来で大小を決める—major/dom7/maj7/sus4→大文字、minor/min7→小文字、dim→小文字+'°'。7th系の接尾辞: dom7→上付き'7'（例 V7）、maj7→'maj7'（例 Imaj7）、min7→小文字+'7'（例 ii7）、dim→'°'（half-dim判定はtriadのdimのみ持つため'°'で十分、°7は構成音に無い）。sus4→'sus4'。変化記号はローマ数字の前に置く（例 ♭VII, #iv°）。N.C.(root_pc<0)は'N.C.'をそのまま返す。
4) Nashville: 度数番号(1-7)を数字文字列に。qualityで修飾—minor/min7→末尾に'-'（マイナス。例 '6-'）、dim→'°'、dom7/min7/maj7の7th→上付き'7'（例 '5-7','1maj7'）、sus4→'sus4'。変化記号は数字の前（例 '♭7','#4'）。N.C.は'N.C.'。

mode引数の扱い（最重要の設計判断）: mode='minor'のとき2方式がある。(A)相対長調ベース番号（実務のNashville標準: 短調曲は relative major の 6- として書く。ト短調→B♭メジャー基準で6-）。(B)トニック短調ベース（1-,4-,5-… 短調の自然な度数に♭3♭6♭7が付く学術ローマ数字寄り）。ローマ数字とNashvilleで慣例が食い違うため、mode='minor'では: ローマ数字は「トニック短調基準・和声的短音階のダイアトニック品質（i,ii°,III,iv,v,VI,VII）」を採用し、Nashvilleは実装の一貫性のため「与えられたkey_tonic_pcを主音とする度数（トニック基準・minorは'-'付与）」で統一する。どちらもkey_tonic_pcを主音として扱い、relative-major変換は行わない（親がkeyを渡す責務。二重変換を避ける）。この方針をdocstringに明記し、限界として「Nashville実務の relative-major 表記は採用しない」と正直に書く。

依存: 標準ライブラリのみで実装可能（music21不要）。ROMAN_NUMERALS=('I','II',...,'VII')等の定数表と純関数だけ。新規重依存追加なし。

テスト(AAA): ChordSpanを直接構築して検証。長調C(tonic_pc=0)で C→'I'/'1', Dm→'ii'/'2-', G7→'V7'/'5⁷' or '57', Em→'iii', F→'IV'/'4', Am→'vi'/'6-', Bdim→'vii°'/'7°'。変化音: E♭メジャー文脈でなくC長調でのB♭(root_pc=10)→'♭VII'/'♭7'。短調Am(tonic_pc=9,mode='minor')で Am→'i'/'1-', Dm→'iv', E(major)→'V'(和声的短音階のV)。N.C.→'N.C.'。空リスト→空リスト。root_pc<0の扱いも1ケース。

## 落とし穴・失敗例(pitfalls)
1) 【最重要】短調のローマ数字大小・変化記号: music21の既知バグと同種。c-mollのA♭は vi ではなく VI（♭6度上の長三和音）。root_pcとqualityから機械的に度数を出すと、変化度数（♭3,♭6,♭7）の番号付けを誤りやすい。短調は「和声的短音階＋♭記号」を明示表で持ち、quality由来の大小と度数由来の変化記号を分離して合成すること。music21 issue #437: RomanNumeralとromanNumeralFromChordで短調6/7度の既定が食い違う。correctRNAlterationForMinorは「音が和音のルートのときだけ」正しく働く。→委譲しない判断の根拠。

2) 【慣例衝突】Nashville minor: 実務では短調曲を relative major の 6- として書くのが標準（G minor→B♭基準で6-）。しかし仕様のto_nashvilleはkey_tonic_pcを主音に取る。relative変換を勝手に入れると親のkey推定と二重変換になり破綻する。→変換しない方針をdocstringで宣言し、テストもトニック基準で書く。

3) トライトーン(6半音)の綴り: #4か♭5か文脈依存。C長調のF#(#IV)かG♭(♭V)か一意に決まらない。既定#4/#IVに固定し限界を明記。同様に他の変化音も上行#・下行♭のどちらを既定にするか一貫させる（推奨: ダイアトニック度数への最近傍で下方向♭優先だがトライトーンのみ#例外、と明文化）。

4) ローマ数字の接尾辞と大小の相互作用: dom7は「大文字＋7」(V7)、min7は「小文字＋7」(ii7)、maj7は「大文字＋maj7」(Imaj7)。qualityごとに (case, suffix) を分けて表管理しないと V7 を v7 と書く等の誤りが出る。dimは常に小文字＋°。

5) 変化記号の位置: ローマ数字は記号を前置(♭VII, #iv)、Nashvilleも数字前置(♭7)。ローマ数字本体は常に大文字表で持ち、qualityで小文字化する順序を固定（記号付与→大小変換の順序を誤ると'♭vii'が'♭VII'化しない等）。

6) N.C.(root_pc=-1)とquality=''の分岐漏れ: chord.pyはN.C.をroot_pc<0/quality=''で表す。degree計算前に必ず早期return。(root_pc-tonic)%12を負のtonicや-1のrootで計算すると不正インデックス。

7) sus4/augの度数品質: sus4は3度を持たないため大小判定不能→慣例で大文字（属機能想定）。CHORD_TEMPLATESにaugは無いが将来追加時に'+'接尾辞（ローマ大文字＋+）が要る点に注意。現状テンプレート7種(major/minor/dom7/min7/maj7/dim/sus4)のみ網羅すれば十分。

8) mode引数のLiteral検証: 'major'/'minor'以外が来たら明示エラー（黙って長調にフォールバックしない）。入力境界検証。

9) 上付き数字文字（'⁷'）を使うとテスト比較・MusicXML往来で崩れる。ASCIIの'7'を使い、表示上の上付きはレンダラ責務にする（捏造の見た目を避ける）。

## 参考(prior_art)
【規則の一次情報】
- Open Music Theory「Roman Numerals」(viva.pressbooks.pub/openmusictheory): 大文字=長三和音、小文字=短三和音、小文字+° =減三和音、大文字+ + =増三和音。7thは上付き7を付す。7thの和音品質はトライアド由来（例外は半減・全減で第7音由来）。→英語圏の標準規則。実装のcase/suffix表はこれに準拠。
- Nashville Number System (Wikipedia / Sweetwater / Stringjoy): 数字1-7=長音階の各度数、既定は長三和音、マイナスは短、+は増、°は減。短調曲は relative major の 6- として書くのが実務標準（G minor→B♭major基準, Gm=6-）。数字は移調しても不変（相対表記）。中文圏では「纳什维尔数字系统」、ローマ数字は「罗马数字级数标记」と呼ばれ規則は同一（大写=大三和弦, 小写=小三和弦, °=减三和弦）。

【prior art / 委譲候補と却下理由】
- music21 roman モジュール romanNumeralFromChord(chord, key): ほぼ任意の和音に対しローマ数字を生成。ただし preferSecondaryDominants 等のオプションがあり、短調6/7度の既定が RomanNumeral と食い違う既知の不整合(GitHub cuthbertLab/music21 issue #437, correctRNAlterationForMinor)。Chord再構築が必要でChordSpanのroot_pc/qualityから直接使えない。→本タスク（度数写像）には過剰かつバグ源。自前実装を推奨。
- 既存chord.py: root_pc/qualityの表現、_SHARP_NAMES/_FLAT_NAMES、CHORD_TEMPLATES(7 quality)、N.C.=root_pc<0/quality=''の規約。これに完全整合させる。spelling.estimate_keyはmusic21.key.Key(.mode/.tonic.pitchClass)を返すので、親がkey_tonic_pc=key.tonic.pitchClass, mode=key.modeを渡す配線が自然。

【要点(中英)】
- 英: uppercase=major, lowercase=minor, °=diminished(lowercase), +=augmented(uppercase), superscript 7 for sevenths; chromatic roots get ♭/♯ prefix on the diatonic degree.
- 中: 罗马数字大写为大三和弦、小写为小三和弦、加°为减三和弦；纳什维尔用数字1-7、减号表示小和弦、°表示减和弦；小调常按关系大调记为6-。
- 実装は key_tonic_pc を主音とする決定論的度数写像に統一し、relative-major変換とmusic21委譲は行わない（限界をdocstringに明記）。

## 実装上の限界・正直な注記(notes)
- 対象2ファイル(earpipe/services/notate/roman_nashville.py, tests/test_roman_nashville.py)は着手時点で既にリサーチ設計どおり完全実装済みだった。当方は内容がcontracts.py/chord.pyの実型(ChordSpan: start_beats/end_beats/name/root_pc/quality、N.C.=root_pc<0 & quality==""、quality7種 major/minor/dom7/min7/maj7/dim/sus4)と一致することを確認し、テストを実行して緑を検証した。既存ファイルの編集・新規ファイル作成は行っていない(要件どおり)。
- 実装上の限界(docstringにも明記済み): (1)トライトーン6半音は #4/#IV に固定(♭5/♭V との文脈依存曖昧性は解決しない)。(2)ナッシュビル実務の「短調曲を平行長調の6-で書く」慣例は非採用(key_tonic_pc基準に統一)。(3)上付き数字は使わずASCII "7"(上付き表示はレンダラ責務)。(4)aug(+)や°7は現状 CHORD_TEMPLATES 7種に無く未対応。(5)mode は major/minor のみ、それ以外は ValueError(dorian等は親側で正規化が必要)。
- 短調のローマ数字大小は quality 由来(music21 #437 の変化度数番号付けバグを回避するため、度数由来の変化記号と quality 由来の大小を分離合成)。V(E major)が短調で長三和音になる点は quality の major から大文字 V として正しく表現される。
