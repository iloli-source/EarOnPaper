# 根本原因分析：なぜ「消し忘れ・未使用の呼び出し・変更未反映」が大量に残るのか

**調査日:** 2026-07-21 / 対象: EarOnPaper（採譜）/ 契機: ユーザー指摘「そんなのが大量にどうして残っているのか原因も調べて」

## 0. 最重要の発見（動かぬ証拠）

**このセッションで実装した約25の新機能が、実採譜フロー `pipeline.py` から一度も呼ばれていない。**

`grep` で確認済み。`to_jianpu / to_leadsheet / to_movable_do / to_roman / simplify_density / render_jianpu_pdf / drums_to_musicxml / separate_voices / align_lyrics / diff_notes / to_llm_text / estimate_velocities / detect_drums / transpose_notes / cleanse_to_scale / interpret_ornaments / assign_fingering / render_visual_card / crop_region / apply_hints / time_stretch / run_batch / write_guitarpro / to_vocal_midi / detect_sustain` — いずれも `pipeline.py` に呼び出しが無い。

→ ユニットテストは緑・`__init__.py` にはエクスポート済みだが、**製品の end-to-end 採譜では使われていない＝「実装したが反映されていない」孤立機能**。ユーザーの直感は正確。

## 1. 根本原因

### 主因1: 並列化のため「実装」と「統合」を意図的に切り離した設計
44機能を高速に並列実装するため、各ワークフローエージェントへ **「新規モジュール1つ＋テスト1つだけ作成。`__init__.py`/`pipeline.py` は絶対に編集するな」** と明示指示した。これは並列エージェントが共有ファイル(`pipeline.py`)を同時編集して衝突するのを防ぐ正当な設計。しかし結果として:
- 各機能は「独立モジュール＋ユニットテスト」として完成するが、**実採譜フローに接続されない**。
- 私が事後に `__init__.py` へエクスポート配線はしたが、それは「呼べる状態」にしただけ。**「実際に呼ばれる」統合（pipeline.py/CLI/appからの呼び出し）は先送りされ、実施されなかった**。

### 主因2: 完了基準が「ユニット緑＋Issueクローズ」で、end-to-end統合を含めなかった
各バッチの完了判定に「実採譜フロー/CLI/appから実際に出力される」ことを入れていなかった。add-only（追加のみ）バイアス。

### 主因3: エージェントの局所視野
各エージェントはコードベース全体を見ず自分のモジュールだけ実装 → 未使用import残し（`musescore_handoff.py`/`visual_card.py` 実測）、「念のため」引数（未使用 `sr`）、既存機能の重複リスク。

### 主因4: 死コード/統合のゲートがループに無かった
`pytest`（振る舞い）は各モジュールを検証するが、「pipelineから呼ばれるか」「孤立エクスポートは無いか」「未使用import/変数は無いか」を検査するゲート（ruff/vulture/統合スモーク）をループに入れていなかった。今回初めて `ruff --select F` を全域で回して未使用import6件を検出・除去。

### 主因5（仕様側）: 前提転換の連鎖更新漏れ
`run_usertest.py` の `--engine poly` 強制（古い仕様残骸→かえるのうた二重音の原因）、要件の課金項目（OSS化で不要）残存。前提が変わっても既存の全参照箇所を追わなかった。

## 2. 対策

1. **孤立25機能を `pipeline.py`/CLI/app へ統合**（出力形式選択で実際に出せるように）＝「反映」の実施。← 最重要・別Issueで着手
2. **死コード除去**: 未使用import6件（済）・未使用引数・stale flag（run_usertest poly強制→auto、済）。
3. **ゲート追加**:
   - `ruff --select F` を CI とローカルループに常設。
   - **孤立エクスポート検査**: `__init__.py` の `__all__` 各要素は「pipeline/CLI/app からの実呼び出し」または「明示的公開API＋テスト参照」を持つこと。
   - **統合スモーク**: `transcribe` が各出力形式（简谱/リードシート/…）を実際に生成することを end-to-end で検証。
4. **完了基準の変更**: 「ユニット緑」→「ユニット緑＋pipeline/CLI/app統合＋統合スモーク緑」。並列は"実装"に使い、"統合"は直列で必ず行う。

## 3. 教訓

並列生成は速いが、**「実装済み」と「製品に反映済み」は別物**。並列で作った部品は、必ず直列の統合フェーズで pipeline/CLI/app へ結線し、統合スモークで「実際に呼ばれる」ことを確認するまで完了としない。
