# F-100 移動ド記譜 — 実装前リサーチ(10並列ワークフロー)

**取得日:** 2026-07-21 / Issue #75 / 実装コミット 5167a73
**方式:** 先行リサーチ(Web/論文・失敗例重視)→実装 の並列ワークフローのリサーチ段を保存

## 推奨アプローチ(approach)
to_movable_do(notes, key_tonic_pc, style="solfege") の実装方針:

■ コア: 各音の相対度数を pc_rel = (int(n.midi) % 12 - key_tonic_pc) % 12 で 0-11 に正規化し、テーブル引きで階名へ。frozen dataclass は入力側のみ(戻り値は list[str])。純関数で副作用なし・イミュータブル。

■ 半音階名テーブル(移動ド、Wikipediaソルフェージュ準拠・確定):
- 全音階7音: 0=Do 2=Re 4=Mi 5=Fa 7=Sol 9=La 11=Ti(英語式「Ti」「Sol」を採用。「Si」「So」は不可)
- 半音5つの綴りは melodic direction 依存(下記pitfall)。上行(raised)= Di(1) Ri(3) Fi(6) Si(8) Li(10)、下行(lowered)= Ra(1) Me(3) Se(6) Le(8) Te(10)。
- 既定は「上行(raised, iベース)」を採用しつつ、直前音との音高差の符号で分岐する実装が堅牢: 直前実音より低ければ lowered 綴り、そうでなければ raised。先頭音・同高は raised を既定にする。この方向判定は int(n.midi) の生値(pc化前)で行う(オクターブ跨ぎの向きを正しく取るため)。

■ style="numeric"(简谱/首調 numbered notation 準拠): 全音階は "1".."7"(0→1,2→2,4→3,5→4,7→5,9→6,11→7)。半音は数字の前に # / b を付す(jianpu 慣習: 上行 "#1" 等、下行 "b2" 等)。方向判定は solfege と同一ロジックを共有(DRY: 内部で _semitone_direction を1本に)。

■ 定数は UPPER_SNAKE_CASE のモジュール定数テーブル(DIATONIC_SOLFEGE, RAISED_SOLFEGE, LOWERED_SOLFEGE, DIATONIC_NUMERIC 等)。style は Literal["solfege","numeric"] で受け、未対応値は ValueError で fail-fast(境界入力検証)。key_tonic_pc は %12 で正規化しつつ範囲外は明示エラーにしない(丸めるのが実用的、docstringに明記)。

■ 関数分割: 度数計算 _degree_from_tonic、方向判定 _is_lowered、綴り選択 _spell_degree を小関数化(各<50行)。to_movable_do は反復して list を組むだけ。

■ 既存資産との整合: 呼び出し側は estimate_key(spelling.py) が返す music21.key.Key の key.tonic.pitchClass を key_tonic_pc として渡す想定。本関数自体は music21 非依存(pc算術のみ)で軽量・テスト容易にする。chord.py の _SHARP_NAMES/_FLAT_NAMES と同じ「テーブル引き」流儀を踏襲。

■ テスト(AAA形式): C=0 の上行全音階→Do..Ti、下行→同じ、上行半音階(C C# D D# E)→Do Di Re Ri Mi、下行半音階(E Eb D Db C)→Mi Me Re Ra Do、numeric で 1 #1 2、非C主音(key_tonic_pc=7=G)で G基準の相対階名、空リスト→空リスト、不正style→ValueError、を検証。pytestは .venv/bin/python -m pytest tests/<new> -q -p no:cacheprovider。

## 落とし穴・失敗例(pitfalls)
■ 【最重要】上行/下行の異名同音あいまい: 半音(相対度数1,3,6,8,10)は「上のraised綴り(Di/Ri/Fi/Si/Li)」と「下のlowered綴り(Ra/Me/Se/Le/Te)」の2通りがあり、Wikipediaソルフェージュ表も両方併記するのみで単一正解を規定しない。これを固定値でハードコードすると音楽的に誤る。堅牢化には「直前音との旋律方向」で決めるが、これは前段のピッチスペリング(spelling.py の実際のシャープ/フラット綴り)と食い違う恐れがある。理想は QuantizedNote だけでなく綴り済み情報を使うことだが本関数はmidiのみ受けるため、方向ヒューリスティックの限界を docstring に正直に明記する(spelling.py が「半音は調号方向の単純規則」と限界を明記しているのと同じ姿勢)。

■ pc算術の符号: (midi%12 - key_tonic_pc) は負になり得る。必ず (... % 12) で 0-11 に再正規化。Python の % は非負を返すが、途中で int化を怠ると float 混入で dict キー不一致。int(n.midi) を徹底。

■ 方向判定にpc化した値を使うと誤る: オクターブ上のドへ跳躍(midi 60→72)は「上行」だが pc は 0→0 で差0。方向は生 midi 差で判定し、綴り選択の度数だけ pc化する。先頭音は直前が無いので raised 既定(または例外扱い)。

■ QuantizedNote の onset_sec/offset_sec は NaN 既定でソート・順序の根拠に使えない(contracts.py 明記: NaN!=NaN)。旋律順は入力list順 or start_beats を用いる。midi のみで方向を見るなら list 順を信頼。

■ 「Sol/So」「Ti/Si」表記ゆれ: 固定ド(特に羅・伊・仏語圏)は Si を使うが、移動ドの英語式は Ti。混在すると Si(=raised Sol) と衝突し致命的バグ。英語式 Ti を単一採用と決め打ち、docstringで宣言。

■ numeric(简谱)と固定ド/音名の混同: numeric は首調(movable, 1=主音)であって固定ピッチではない。key_tonic_pc を無視して midi%12 をそのまま 1-7 に割るのは固定ド化の誤り。必ず主音相対で算出。

■ style 未知値の握り潰し禁止(共通ルール: 静かに失敗しない)。ValueError を投げる。

■ 空入力・単音: notes 空は [] を返す(estimate_key が空でC調を返すのと整合的に、無理に推定しない)。

■ music21 を安易に import しない: 本関数は pc 算術で完結でき、重依存追加禁止の制約にも合う。music21.pitch 経由の綴り変換は方向あいまいを解決しないうえ遅い。

## 参考(prior_art)
■ Wikipedia「Solfège」(en) — 移動ド半音階名の確定表(実データで確認): 全音階 Do Re Mi Fa Sol La Ti、raised=Di(#1) Ri(#2) Fi(#4) Si(#5) Li(#6)、lowered=Ra(b2) Me(b3) Se(b4) Le(b5) Te(b6)。3度(Mi)と7度(Ti)は raised 綴りを持たない(表に「—」)点に注意。英語式は Si でなく Ti を使う、と明記。ただし「melodic direction が Di か Ra を決める」規則は Wikipedia は明示せず両論併記=単一正解なしという限界を確認(これがpitfall筆頭の根拠)。

■ muted.io / learnmusictheory.net / music-theory-practice.com 等の移動ドチャート — 同一の i(上行)/e・a(下行)母音規則を裏付け。Re だけ既に末尾eのため lowered が Ra になる不規則を複数ソースが指摘。

■ 简谱(jianpu, numbered notation)= 首调 movable-do system(en.wikipedia「Numbered musical notation」, domisol.app, easonmusicschool): 数字 1-7 が do-re-mi-fa-sol-la-si に対応し「1」は常に調の主音(1=C で C major、6=A で A minor の la-based minor 慣習)。半音は数字前置の # / b。固定ド(固定调, fixed do)との本質差は「1 が調で動くか固定ピッチか」。中: 唱名(movable/相対)vs 音名(絶対ピッチC D E)の区別。本仕様の style="numeric" はまさに首调 jianpu 準拠。

■ 既存コードベースの流儀を踏襲(prior art in-repo): earpipe/services/notate/chord.py の _SHARP_NAMES/_FLAT_NAMES による pc→音名テーブル引き、spelling.py の「限界を docstringに正直に列挙」する文化、tests/test_spelling.py の _mel ヘルパ+合成メロディ+AAA形式。これらに揃えるのが最も安全。

■ 失敗パターン(実務報告・successmusicstudio 等 chromatic solfege 教材): 初学者・実装者が「C#は常にDi」と一律固定して下行文脈で不自然になる/固定ド Si と移動ド raised Sol=Si を取り違える、が典型。本関数は midi 情報しか持たないため完全な音楽的正解は原理的に不可能で、方向ヒューリスティック+限界明記が現実解。

## 実装上の限界・正直な注記(notes)
- 指定された新規モジュール1つ・新規テスト1つは既に作成済みの状態で存在しており、いずれも本タスク要件(F-100仕様、リサーチのpitfalls、PEP8・型注釈・日本語docstring・frozen dataclass入力・AAA pytest)を正確に満たしていた。追加編集は不要と判断し、pytestで実際に緑(15 passed)であることを検証した上で test_passed=true とした。__init__.py 等の既存ファイルは一切編集していない。
- 音楽的限界(docstring・honest記録済み): 半音の上行/下行綴りは直前音との生midi差による方向ヒューリスティックであり、Wikipediaソルフェージュ表も単一正解を規定しないため原理的に完全な正解は不能。前段 spelling.py の実綴り(調号方向規則)と食い違う場合がある。3度(Mi)/7度(Ti)はraised綴りを持たない前提で全音階音はそのまま扱う。
- 英語式 Ti/Sol を単一採用(固定ド Si/So は不採用、raised Sol=Si との衝突回避)。
- key_tonic_pc は %12 で丸め、範囲外でも明示エラーにしない実用方針(docstring明記)。
- 追加の重依存なし(numpy/music21等をimportせずpc算術のみで完結)。
