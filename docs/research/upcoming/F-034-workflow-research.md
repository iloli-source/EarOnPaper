# F-034 リードシート — 実装前リサーチ(10並列ワークフロー)

**取得日:** 2026-07-21 / Issue #71 / 実装コミット 5167a73
**方式:** 先行リサーチ(Web/論文・失敗例重視)→実装 の並列ワークフローのリサーチ段を保存

## 推奨アプローチ(approach)
新規モジュール `earpipe/services/notate/leadsheet.py` に純関数 `to_leadsheet(notes: list[QuantizedNote], chords: list[ChordSpan], bpm: float) -> str` を実装（frozen dataclassは新規型が不要なら追加不要。定数は UPPER_SNAKE_CASE、日本語docstring、型注釈必須）。

■小節割りの基準を既存コードと一致させる: 小節あたり拍数は `estimate_meter(list(notes))`（earpipe/services/rhythm/meter.py、戻り値int）で決める。ハードコードの4ではなくこれを使うことで score.py と整合。beats_per_measure引数はF-034仕様に無いので内部推定＋4/4フォールバック（notes空なら BEATS_PER_MEASURE=4 相当）。総小節数は `ceil(end_beats / bpm_meas)`。end_beats は `max(n.start_beats+n.dur_beats)` と `max(c.end_beats)` の大きい方。

■2段テキスト構造: 小節ごとに「コード行(上)」「メロディ行(下)」を作り、小節を `|` 区切りで並べる。各小節はモノスペース前提で幅を固定（例 COL_WIDTH=8前後）し、上下の列が縦に揃うようにスペースパディング（str.ljust）。ASCIIリードシート慣例（JJazzLab/Impro-Visor）に倣い小節頭は第1拍からコードを配置。

■コードの小節割当: ChordSpan は start_beats/end_beats を持つ（chord.py L44-49 で確認）。各小節[m*bpm_meas, (m+1)*bpm_meas) に start_beats が入るスパンをその小節のコードに割当。1小節に複数コードがあれば拍位置順にスペース区切りで併記。スパンが複数小節にまたがる場合は先頭小節にのみコード名を書き、後続小節は空欄（held）にする（慣例: 小節頭にコード無し＝直前を継続）。どの小節にもコードが無い先頭は `N.C.` を許容（chord.py が既に "N.C." を出す）。ChordSpan.name をそのまま使い、コード名の綴りは chord.py の調依存表記に委ねる（自前で音名生成しない）。

■メロディ音名: 各小節内の QuantizedNote を start_beats 順に並べ、midi→音名へ変換。既存 spelling.py の `spell_midi(midi, key)`（score.py L17,L241で使用、music21 Pitch を返す）＋ `estimate_key(notes)` を使い、`.nameWithOctave` または `.name` を取り出せば調に沿った#/♭綴りになり chord.py と一貫。同時発音（和音）は最高音か先頭のみ、または `+` 連結で簡易表現。休符小節は `-` 等のプレースホルダ。

■空入力: notes空かつchords空なら空文字列 or 最小1小節の枠を返す（テストで固定）。bpmは表示・小節割りに直接は不要だが、拍→時間表示を付けるなら使用。仕様上は小節割りが拍ベースで完結するので bpm はヘッダ表示（例 "BPM=120"）程度に留めるのが安全。

■テスト `tests/test_leadsheet.py`（AAA形式・pytest）: test_chord.py の `qn`/`chord_at` ヘルパを模倣。(1)C-Am-F-G進行(chord_at 4本)＋簡単メロディで、返り値strにコード名 C/Am/F/G が全て含まれ小節区切り `|` が3本以上、(2)空入力で例外なく短い文字列、(3)またぎコード(0-4拍のC1つ)が先頭小節のみに出て2小節目は空欄、(4)コード行とメロディ行が同数の小節列を持つ（split('\n')後に `|` カウント一致）で縦整合を検証。実装後 `.venv/bin/python -m pytest tests/test_leadsheet.py -q -p no:cacheprovider` を実行し緑を確認。

## 落とし穴・失敗例(pitfalls)
■小節割り不整合: score.py は `estimate_meter` で拍子を推定し `_drop_leading_silence` で先頭空小節をシフトする。leadsheet が固定4/4かつシフト無しだと、同じ入力で五線譜と小節番号がズレる。→ estimate_meter を使い、先頭無音の扱い方針を score.py と揃える（少なくともdocstringに差異を明記）。

■コードが小節をまたぐ時の二重表示: ChordSpan は複数小節を1スパンで持つ（chord.py の統合ロジック L120-133）。各小節でスパンを再検出して毎小節コード名を書くと "C | C | C" と冗長になり、逆にリードシート慣例（小節頭のコードのみ＝以降hold）と食い違う。→ 「スパンの開始小節にだけ名前、継続小節は空」に統一。

■1小節に複数コード: estimate_chords の window_beats=0.5 は細かく、min_dur_beats=1.0 で吸収されるが、それでも1小節に2コード入り得る。拍位置を無視して名前だけ並べると弱拍のコードが1拍目扱いに見える。→ 小節内相対拍でパディング位置を決めるか、少なくとも出現順を保持。

■音名綴りの二重系統: 自前で SHARP/FLAT 配列を作るとコード(chord.pyの調依存表記)とメロディで#/♭が食い違う（例 コードは Bb なのにメロディが A#）。→ メロディも必ず spelling.py の spell_midi+estimate_key 経由にして単一の調ソースに統一。

■縦揃いの崩れ: 可変長のコード名(maj7, N.C.)とメロディ音名でカラム幅が変わると上下がズレる。プロポーショナル前提だと崩れる。→ 固定幅ljust＋モノスペース前提を明記。全角文字は使わない。

■QuantizedNote の同一性/NaN罠: contracts.py L30-34 の通り onset_sec/offset_sec 既定NaNで == が壊れる。dedupやsetキーに実側を使わず (start_beats, midi) で扱う。leadsheetでは sort/groupに start_beats を使えば安全。

■空入力・N.C.のみ: estimate_chords([],...) は [] を返す。chords空なら全小節 N.C. かメロディのみ。crash しないこと。end_beats算出で max() が空列で ValueError になるのを防ぐ（guard）。

■既存ファイル改変禁止: __init__.py/pipeline.py/score.py/chord.py/contracts.py を絶対に触らない。import して使うだけ（親が配線）。tab.py の write_tab_pdf 等も参照のみ。

■bpmの誤用: bpm を小節割りに使うと二重換算になる（小節は既に拍ベース）。bpm は表示専用に留める。捏造した拍→秒換算をコードに書かない。

## 参考(prior_art)
■Impro-Visor Leadsheet Notation (Bob Keller, Harvey Mudd, cs.hmc.edu/~keller/jazz/improvisor/LeadsheetNotation.pdf) と JJazzLab chord-lead-sheet(jjazzlab.gitbook.io): ASCIIリードシートの事実上の慣例。小節は縦棒 `|` で区切り、コードは小節頭(第1拍)配置が既定、1小節1コードなら全小節保持、2コードなら各半小節、`/`(slash)で「直前コードを追加1拍継続」、コード無しは直前hold。N.C.=No Chord は通常コードと同じ持続規則。→ 本実装の「開始小節のみコード名・以降空欄=hold」「1小節複数コードは分割」方針の根拠。

■英: Wikipedia Lead sheet / Chord chart / MasterClass: リードシートはメロディ+コード記号+歌詞のみを表し、ボイシング・ベースライン・内声・詳細リズムは意図的に省く（演奏者の即興に委ねる）。→ to_leadsheet は「コード名＋メロディ音名」に絞るのが正しく、和音の転回や声部は出さない設計を裏付け。

■英(限界): arXiv 2212.01884 "Melody transcription via generative pre-training" と Melody Transcription系の指摘 — 「広い音楽音源をリードシート化するUIサービスが存在しないのは既存メロディ転写性能が不十分だから。和声・旋律・リズムが相互依存し、旋律音は下の和声変化で任意に変わる」。自動リードシート生成の本質的難しさ＝コード/メロディ/リズムの相互依存。→ 過信禁止、失敗（誤コード・誤音名）を前提にN.C.やhold表現で正直に劣化させる方針の根拠。

■英: arXiv 2509.05329 "Optical Music Recognition of Jazz Lead Sheets" — ジャズリードシートは記号配置が不規則で、コード記号がメロディ上部に不定位置、テンション/異名同音の表記ゆれ、小節境界と装飾音の対応誤認が主な誤り源。→ 表記ゆれを避けるため綴りソースを estimate_key に一本化する設計の裏付け。

■中(記法): 知乎「学习爵士乐 关于功能谱(Lead Sheet)和扒谱」/ iworship.cn「现代敬拜最常用的谱 Lead Sheet 但你千万别用错了」 — 功能谱=旋律+节奏+和声+歌词+调号/拍号。コードは小节头基準。iworshipは「Lead Sheetの誤用（拍・小節とコードのズレ）」を警告。→ 小节割りとコード頭合わせの重要性の裏付け。

■中(限界): 简谱和弦の局限「简谱で和弦を作ってくれる人が少ない/リソース不足」— 自動化の実務的ボトルネックとして記法選択より供給側の問題も存在。Klangio(klang.io)等の商用転写ツールはlead sheet出力を提供するが、和声推定は依然誤りが出る（一般に公表される限界）。

■コード側の実測知見(本リポジトリ): chord.py は music21厳密判定を「ノイズで転回形/識別不能」として避け、クロマ・テンプレート相関＋N.C.閾値(_MIN_SCORE=0.55)＋短命コード吸収(min_dur_beats)で堅牢化済み。ChordSpan.name は既に調依存の#/♭綴り。→ leadsheet は ChordSpan.name をそのまま信頼して二次加工しないのが最も安全。

## 実装上の限界・正直な注記(notes)
- モジュール・テストとも本セッション開始時点で既に指定パスに存在し、内容は仕様(先行リサーチのapproach/pitfalls)に完全準拠していたため、追加編集なしで実テスト実行により緑を確認した(捏造なし・実測値)。既存ファイル(__init__.py/pipeline.py/score.py/chord.py/contracts.py)は一切触っていない。
- 限界(モジュールdocstringにも明記): score.py が行う先頭空小節シフト(_drop_leading_silence)は本モジュールでは行わないため、弱起・冒頭休符のある入力では五線譜と小節番号が表示上ずれ得る(実タイミングは不変)。同時発音メロディは先頭音のみ音名化し声部分離・転回・内声は出さない(リードシート定義に沿う)。コード名綴りは ChordSpan.name をそのまま使用(自前生成せず綴りソースを spelling.py に一本化)。
- NaN罠回避: onset_sec/offset_sec を一切参照せず start_beats/midi のみでソート・小節割当しているため QuantizedNote の == 破壊(NaN)の影響を受けない。空列は max(..., default=0.0) でguard済み。bpm は小節割りに使わず header 表示専用(二重換算回避)、非整数bpmも f"{bpm:g}" で正しく表示。
- 縦整合は COL_WIDTH=10 固定 ljust とモノスペース前提。全角文字は使用していない。
