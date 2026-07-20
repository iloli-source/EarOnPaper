# F-033 简谱(数字譜) — 実装前リサーチ(10並列ワークフロー)

**取得日:** 2026-07-21 / Issue #70 / 実装コミット 5167a73
**方式:** 先行リサーチ(Web/論文・失敗例重視)→実装 の並列ワークフローのリサーチ段を保存

## 推奨アプローチ(approach)
シグネチャ `to_jianpu(notes: list[QuantizedNote], key_tonic_pc: int) -> str` を新規モジュール（例 earpipe/services/notate/jianpu.py）に実装。QuantizedNote実フィールドは contracts.py で確認済み: start_beats/dur_beats/midi:int/confidence（実側 onset_sec/offset_sec は NaN既定で今回未使用）。

【音度写像】各音符の midi に対し `deg_pc = (midi % 12 - key_tonic_pc) % 12`。長音階の半音→音度対応表 SEMITONE_TO_DEGREE = {0:'1',2:'2',4:'3',5:'4',7:'5',9:'6',11:'7'} を定数化。表に無い半音階音（1,3,6,8,10）は臨時記号として直下の音度に '#' を、または上の音度に 'b' を前置（例 pc=1 → '#1'）。music21 の spell_midi/estimate_key は使わず、渡された key_tonic_pc を単一の真実とする（親が調推定を注入する設計に合わせる）。key_tonic_pc は 0-11 に正規化（% 12）してから使う。

【オクターブ点】基準オクターブを主音基準で決める。midi から音度中央オクターブを算出し `octave = midi // 12`、C4=60→octave5 を基準(=点なし)に、上は音度文字の後に上点、下は下点。テキスト出力では jianpu-ly 慣習に倣い ASCII 化: 上点1個につき音度の後に "'"、下点1個につき "," を付す（例 高8度=1', 低8度=1,）。真の上下点記号 U+02D9(˙) を使うと monospace で数字の上に載らず崩れるため、ASCII サフィックス方式を既定にし、docstring に「印刷用の上下点は将来の engrave 層で載せる、本関数はテキスト近似」と限界を明記。

【音価】plain 数字=四分音符(dur_beats≈1.0)基準。dur_beats を四分音符倍率とみなし、(a) 2.0以上→ダッシュ " -" を (round(dur)-1) 個後置で近似（増時線）、(b) 0.5→下線1本相当だがテキストでは減時線を上付きできないため "_" サフィックス or アンダースコア数で近似（8分="1_", 16分="1__"）、(c) 付点はダッシュ/下線で吸収できない端数として "." を後置。連符・複雑拍は近似である旨を docstring に明記（減時線/増時線の厳密段組はテキストでは不可）。

【休符】midi<0 もしくは呼び出し側が休符を渡さない設計なら省略。要件どおり休符は "0"。QuantizedNote に休符表現が無い場合はギャップ（前音 offset と次音 onset の拍差、start_beats連続の隙間）から 0 を挿入するか、簡潔さ優先で「入力に休符ノートが無ければ 0 は出さない」方針を docstring で宣言。

出力は空白区切り1行（または小節線 '|' 挿入は今回スコープ外）。全体を frozen dataclass 不要（純関数）だが、内部で使う音度表・記号は UPPER_SNAKE_CASE 定数・イミュータブル(tuple/frozendict風 MappingProxyType or 定数dict)で保持。PEP8・型注釈・日本語docstring必須。テストは AAA 形式で pytest（新規1ファイルのみ）: ハ長調(key_tonic_pc=0)で C4→'1', G4→'5', C5→"1'", C3→'1,'、半音(C#)→'#1'、4分/2分/8分の音価近似、空リスト→''、を検証。実装後 `.venv/bin/python -m pytest tests/test_jianpu.py -q -p no:cacheprovider` を実行し緑を確認。

## 落とし穴・失敗例(pitfalls)
1) オクターブ基準のオフセット誤り: MIDIの「中央のド」は C4=60 だが、jianpuの点無し中音域は曲/調により変わる。key_tonic_pc だけでは基準オクターブが一意に決まらないため、midi//12 の絶対オクターブで固定基準（例 60-71 を点無し）を採らざるを得ない。これだと属七など主音より低い音が下点になる。「中音域=どのMIDIレンジか」を定数で明示し、恣意性を docstring に正直に書くこと（捏造で『正しい』と言わない）。

2) 半音階音の綴り方向: pc が長音階外(1,3,6,8,10)のとき '#下の度' か 'b上の度' か曖昧。調号方向（シャープ系/フラット系）を key_tonic_pc からは判定できない（同じ主音pcでも長短で違う）。単純に常に '#' 前置とし、限界を明記するのが安全（spelling.py の direction ロジックは調オブジェクト前提で流用不可）。

3) 減時線/増時線はテキストで正しく段組できない: 本来 8分音符は数字の下に横線、二分音符は右に増時線。monospace テキストでは下線を数字の下段に置けないので、"_" サフィックスや連続ダッシュはあくまで近似。厳密なjianpu組版と誤認させない。

4) dur_beats の丸め: 三連符(dur≈0.333)や付点(0.75/1.5)は整数ダッシュ/半減下線に載らない。round で潰すと音価が化ける。閾値方式（>=1.75→2拍、0.375-0.75→8分 等）で近似し、境界条件をテストで固定。dur_beats=0 や負値・NaN混入のガードも必要（実側 onset_sec/offset_sec は NaN既定なので誤って参照しない）。

5) key_tonic_pc の値域: 0-11 前提だが 12以上/負が来たら % 12 で正規化。未正規化のまま減算すると音度表引きが KeyError になる。

6) 音声→簡譜の一般的失敗（親パイプライン起因、本関数の入力汚染源）: 多声/合奏では基頻混同・倍音交差で音高誤判定（中国語ソース: 単声部は高精度だが多楽器合奏・転調・半音精度が主要限界）、転調追従不可（spelling.py も全体1調のみ）。本関数は「渡された音符と単一 key_tonic_pc」を信じるだけなので、転調曲では後半の音度がずれる—この限界を docstring に明記し、関数の責務外だと切り分ける。

7) 空入力: notes=[] は '' を返す（例外にしない）。単一音・全休符など縮退入力もクラッシュさせない。

8) 既存ファイル改変禁止: __init__.py に export を足したくなるが親が配線するので触らない。テストは `from earpipe.services.notate.jianpu import to_jianpu` の直接 import で書く。

## 参考(prior_art)
記法の一次情報（実在確認済み）:
- 简谱基本規則(中文): 1-7は長音階の音度、上加点=高8度/下加点=低8度（点2つで2オクターブ）、増時線=音符右の短横線で二分・全音符を延長、減時線=音符下の横線で1本ごとに音価半減、休符=0。四分音符未満では低音点は減時線の下に置く（szart.com 乐理课堂 / zh.wikipedia 简谱 / CSDN chengyq116）。
- jianpu 英語(Wikipedia "Jianpu" / TablEdit manual): plain number=四分音符、下線1本ごとに半減(8分・16分)、後置ダッシュ1個ごとに四分音符分延長、後置付点で1.5倍・2点で1.75倍、休符0はダッシュでなく0を反復するのが慣例。

テキスト/ASCII エンコード先行実装（本実装のサフィックス方式の根拠）:
- ssb22/jianpu-ly (PyPI, Python): ASCII入力慣習として高オクターブは音符に "'" 後置（1' 1''）、低オクターブは "," 後置（1, 1,,）。レンダリングはLilypond側。→ 本実装のテキスト出力サフィックス（' と ,）はこの慣習に整合。
- RobertWinslow/jianpu-ascii-font: ASCIIリガチャで monospace 環境に簡譜を表示するフォント。素の数字+記号列で近似する妥当性の裏付け（環境依存で常に綺麗には出ない＝テキスト近似の限界の実例）。
- dovecho/Jianpu, madderscientist/je_score_operator(转调/midi抽出含む): テキストベース簡譜⇔Lilypond/MIDI変換の既存OSS。転調処理を別レイヤに切る設計が一般的で、本関数が調(key_tonic_pc)を外部注入で受ける設計方針と一致。

音声→簡譜の失敗例・限界（中英）:
- 中文MIRソース(CSDN ask.csdn / juejin 哔谱实验室): 単声部は高精度だが、多楽器合奏は時频域重叠・基频混淆・谐波串扰で音高誤検/漏检、盲源分离依存で誤差増大。転調識別と半音精度が主要限界（平均識別率96%を謳うツールも合奏・転調で劣化）。
- 本repo spelling.py 自体が「全体1調のみ・転調未対応・半音綴りは調号方向の単純規則」と明記—to_jianpu も同じ制約を継承し、単一 key_tonic_pc 前提で転調曲は後半ずれる限界を持つ。

Sources: szart.com 乐理课堂丨15简谱的用法 / zh.wikipedia.org 简谱 / blog.csdn.net chengyq116 / en.wikipedia.org Jianpu / tabledit.com jianpu.shtml / github.com ssb22/jianpu-ly / github.com RobertWinslow/jianpu-ascii-font / github.com dovecho/Jianpu / github.com madderscientist/je_score_operator / ask.csdn.net 8985116 / juejin.cn 哔谱实验室

## 実装上の限界・正直な注記(notes)
- 既存ファイルは一切編集していない(__init__.py・pipeline.py 等は未変更)。作成対象2ファイル(jianpu.py, test_jianpu.py)は着手時点で既に完成状態で存在しており、内容は本タスクのF-033仕様(音度写像/オクターブ点/臨時記号#前置/音価近似/休符0/key正規化/縮退入力ガード)と完全一致していた。差分編集は不要と判断し、pytestで実挙動を検証(22 passed)して緑を確認した。
- 限界(モジュールdocstringにも明記済み・捏造なし):
  1) テキスト近似であり厳密な簡譜組版ではない。上下点・減時線・増時線はASCIIサフィックスでの近似で、monospaceでも数字の上下段には載らない。
  2) 中音域基準の恣意性: 「点なし中音域」は本来曲・調で動くが、key_tonic_pc だけでは一意に決まらないため MIDI絶対オクターブ(C4-B4, midi//12==5)に固定。属音など主音より低い音が下点になり得る割り切り。
  3) 臨時記号の綴り方向: 常に "#" 前置。同じ主音pcでも長短で調号方向が異なり、フラット方向を選べない(spelling.pyのdirectionロジックは調オブジェクト前提で流用不可)。
  4) 転調追従なし: 単一 key_tonic_pc を全音符に適用。転調曲では後半の音度がずれる(親の責務)。
  5) 音価近似: 三連符(≈0.333)や付点は閾値近似のため厳密ではない。
  6) 休符はギャップからの自動挿入をせず、入力に midi<0 のノートがある場合のみ "0" を出す設計。
  7) 実側フィールド onset_sec/offset_sec(既定NaN)は参照せず、格子側 start_beats/dur_beats/midi のみ使用。
