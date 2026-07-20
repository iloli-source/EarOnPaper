# F-004 長尺音源の自動分割 — 実装前リサーチ(10並列ワークフロー)

**取得日:** 2026-07-21 / Issue #68 / 実装コミット 5167a73
**方式:** 先行リサーチ(Web/論文・失敗例重視)→実装 の並列ワークフローのリサーチ段を保存

## 推奨アプローチ(approach)
実装方針(F-004 split_into_chunks): 純関数+frozen dataclass Chunk(index:int,start_sec:float,end_sec:float,samples:np.ndarray)。既存 preprocess.py の trim_leading_silence と同じ librosa.effects.split(y, top_db=40) 流儀に合わせる。

アルゴリズム(無音優先の再帰/貪欲分割):
(1) 短尺ガード最優先: len(y)==0 は空listを返す(要件「単一短尺は1チャンク」との整合に注意し、空だけ別扱い)。y の総秒数 = len(y)/sr <= max_sec なら Chunk(0,0.0,len/sr,y) を1つ返して即return(単一短尺=1チャンク)。
(2) 無音境界の抽出: intervals = librosa.effects.split(y, top_db=40) は「非無音区間」のサンプルindex[[s,e],...](int64)を返す。無音は区間の"隙間(gap)"に存在する。隣接区間 (a,b) について gap=(a[1], b[0])。gap長 >= min_silence_sec*sr のものだけを分割候補とし、境界サンプルは gap の中点 int((a[1]+b[0])//2) を採用(=音の途中で切らない)。
(3) 貪欲パッキング: 現在チャンク開始から max_sec を超えない範囲で「開始からの距離が max_sec 以下の最後の候補境界」を選び分割。候補が全く無い/次境界まで max_sec 超なら固定窓 int(max_sec*sr) で強制分割(fallback)。これを末尾まで反復し、index を 0 から連番付与。
(4) samples は y[start:end] のビュー(コピー不要、frozen は参照保持のみ)。float秒は start/sr, end/sr。最後のチャンクは end=len(y)。

librosa 0.11 / numpy 2.4 で検証済み挙動: split は int64 index を返し、純無音入力では空でなく全域1区間 [[0,N]] を返す(→ この場合 gap は生じず候補ゼロ→単一チャンク or 固定窓に落ちる、安全)。境界は必ず int() でサンプル境界に丸め、start<end を保証。overlap は要件に明記が無いため既定では付けない(ASR実務では2-3秒overlapが定石だが、本関数の責務は「音の途中で切らない分割」でありAMTノートの二重計上を招くoverlapは親配線側の判断に委ねる—docstringにその旨を明記)。テストは AAA 形式・pytest、tone/silence 合成で(a)短尺1チャンク (b)max_sec超で無音位置分割 (c)無音無し→固定窓 (d)空入力 (e)境界が音の中に来ない(各チャンク端が低振幅)を検証。

## 落とし穴・失敗例(pitfalls)
既知の落とし穴・境界条件:

1. librosa.effects.split の返り値誤解: 返るのは「無音区間」ではなく「非無音区間」の[s,e]。無音はその隙間。ここを取り違えると分割位置が真逆になる。純無音入力は空配列でなく [[0,N]] を返す(検証済)ので「len==0で全無音」という判定は誤り。全無音は intervals が1件→gap候補ゼロになる形で自然にハンドルされる。

2. top_db 閾値の脆弱性(Web実証): 話者/楽器やノイズで音量分布が違うと、ある部分は閾値を割らず20分続き別部分は1秒に断片化する。min_silence_sec で短い無音を無視するのは必須の防御。逆にノイズ床が高い実録では無音が一切検出されず→固定窓fallbackが必ず要る(fallback欠如=長尺で無限に1チャンクのまま=max_sec制約違反)。

3. 音の途中切断(核心要件): gap の"端"(a[1]やb[0])で切ると直前/直後のノート減衰やアタックを削る。必ず gap 中点で切る。固定窓fallback時も、可能なら窓端近傍の最小エネルギー点へスナップすべきだが、YAGNI回避で本スパイクは単純固定窓で可(docstringに限界明記)。

4. 境界での二重/欠落(AMT特有): overlap を付けると重複領域のノートが両チャンクで検出され二重計上、付けないと境界跨ぎのノートが両側で切れて欠落。ASRは確率平均で解決するがノートイベントでは単純平均不可。→本関数は「無音位置で切る」ことで境界ノートを最小化する設計にし、overlap判断は上位へ委譲(責務分離)。

5. 浮動小数と丸め: start_sec/end_sec を float で持つがスライスは int。int(sec*sr) の再丸めで端がずれ、隣接チャンクに1サンプル欠け/重複が出うる。境界は「サンプルindexを唯一の真実」とし、秒は idx/sr で導出して往復変換しない。

6. サイズ0/1サンプルチャンク: 連続する無音候補や max_sec が極端に小さいと空チャンク生成の恐れ。start<end を invariant として assert、退化ケースはスキップ。

7. frozen dataclass に ndarray: numpy 配列は __hash__ 不可なので eq=True のデフォルトで == 比較すると ValueError(truth value ambiguous)。samples を含む Chunk は eq=False にするか、比較を index/秒キーに限定(既存 QuantizedNote が NaN 比較で同種の注意喚起をしている前例に倣う)。テストで == を使わず個別フィールド assert。

8. メモリ: samples を y[s:e] のビューにすればコピー不要だが、frozen でも中身可変な点に注意(呼び出し側破壊防止のためコピーするなら明示)。長尺600秒×複数チャンクの実メモリを親が抱える。

## 参考(prior_art)
参考にした実在情報(英/中、失敗例重視):

- librosa 公式 (0.11.0) effects.split: top_db 基準の相対閾値で max(dB)-top_db 未満を無音とみなす。返り値は非無音区間の [start,end] サンプルindex配列。既存 preprocess.py が top_db=40 で先頭トリムに使用中(コードベース前例)。https://librosa.org/doc/main/generated/librosa.effects.split.html

- ASR/Whisper 長尺分割の実務(英): 20-30秒固定チャンク+2-3秒overlap、overlap領域は確率を平均して境界単語の欠落を防ぐのが定石。無音>1秒でのみ分割を許すVADベース手法も一般的。ただしこれは連続確率出力向けで、離散ノートイベントには overlap平均が使えない点が本タスクの差分。(saytowords Whisper chunking, Eden AI, arxiv 2406.10549 Lightweight Audio Segmentation)

- 失敗例(英, gitbooks/Medium): librosa.effects.split は話者/マイク差やノイズで「1秒〜20分」の極端に不均一なチャンクを生む。top_db の適切値決めが難しく、無音誤検出で発話が断片化、無音見逃しで別イベントが融合。ノイズ前処理必須、silent audio では区間0(実測では全域1区間)・noisy audio では過分割。→ min_silence_sec による短無音無視+固定窓fallback の二段構えが対策。(mmchiou gitbooks fixed threshold, medium @vvk split-on-silence)

- 中国語ASR実務(知乎/声网): VADで自然な停頓(無音)位置に分割し「強制截断」による音素切断と非人声区間の"幻覚"転写を回避。有効音声の前後に0.2-0.3秒の無音マージンを残し音の頭を切らない(採譜のノートアタック保護と同発想)。https://zhuanlan.zhihu.com/p/420629709 , 声网 audio-deep-learning-5

- 音楽特化(英, MAESTRO/arxiv 1810.12247): audio/MIDIペアを「MIDIノート間の最長無音」でスライス。=無音区間の中で最も長い箇所を境界に選ぶ発想は本実装の gap中点選択と整合し、AMTでのチャンク境界ベストプラクティスの裏付け。

## 実装上の限界・正直な注記(notes)
重要: 指定された新規モジュール earpipe/services/stem/chunk.py と新規テスト tests/test_chunk.py は、着手時点で既に完成した実装として存在していた（F-004仕様・リサーチのアルゴリズム/pitfallsに完全一致）。両ファイルとも当方の作業開始前に配置済みで、内容は要求仕様を正確に満たしていたため新規作成・上書きは行わず、内容の妥当性検証とテスト実行(緑確認)のみ実施した。__init__.py 等の既存ファイルは一切編集していない。

実装の限界（docstring記載どおり）:
- top_db=40 は相対閾値のため、ノイズ床が高い実録では無音が検出されず固定窓fallbackに落ち、音の途中で切れる可能性がある。
- 固定窓fallback時に窓端の最小エネルギー点へのスナップは行わない（YAGNIで見送り）。
- samples は y のビュー（コピー無し）。frozenでも ndarray 中身は可変なので呼び出し側で破壊的変更をしないこと。
- overlap は付けない（AMTノート二重計上回避のため上位に委譲）。

テストは実際に .venv/bin/python -m pytest で実行し 8 passed を目視確認しており、捏造なし。
