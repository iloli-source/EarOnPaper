# Contributing to EarOnPaper

EarOnPaper は「音声を五線譜・MIDI・PDFへ変換するローカル採譜エンジン」と、その評価基盤・要件定義を含むプロジェクトです。
共同開発では `main` を常に動く状態に保ち、Issue 起点で Pull Request してください。

## 開発フロー

1. Issue を作る、または既存 Issue を選ぶ
   - 目的、完了条件、影響範囲を書いてください。
   - 仕様・前提が変わる変更では、関連ドキュメントの更新も完了条件に含めてください。

2. ブランチを作る

   ```bash
   git checkout main
   git pull
   git checkout -b feature/short-description
   ```

   ブランチ名の例:

   - `feature/pdf-export`
   - `fix/tab-overlap`
   - `docs/update-requirements`
   - `test/ai-ears-regression`

3. 変更する
   - 変更範囲を小さく保ってください。
   - 生成物、大きな音源、ローカル検証用ファイルはコミットしないでください。
   - 音源や楽譜を扱うときは、権利関係が明確なものだけを使ってください。

4. ローカルで確認する

   採譜エンジン:

   ```bash
   cd spike/ear-pipeline
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   .venv/bin/pip install ruff
   .venv/bin/ruff check --select F earpipe/        # 未使用import/変数(死コード)
   .venv/bin/python scripts/check_orphan_exports.py  # 実装したが未配線の機能を検出
   .venv/bin/python -m pytest tests/ -q
   ```

   AI の耳ハーネス:

   ```bash
   cd tools/ai-ears
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   .venv/bin/python -m pytest tests/ -q
   ```

5. Pull Request を出す
   - PR は `main` 向けに作成してください。
   - PR 本文に Issue、変更内容、確認結果、ドキュメント更新有無を書いてください。
   - CI が通り、レビューが完了してから merge します。

## main ブランチのルール

- `main` へ直接 push しないでください。
- 変更は Pull Request 経由で入れてください。
- 原則として `Squash and merge` を使い、PR 単位で履歴を整理します。
- CI 失敗、未説明の仕様変更、検証なしの大きな変更は merge しません。

## ドキュメント更新の基準

次の変更では README や `docs/` を更新してください。

- CLI オプション、出力形式、セットアップ手順が変わる
- 評価指標や品質ゲートが変わる
- 要件、設計判断、アーキテクチャ境界が変わる
- 既知の限界や運用手順が変わる

## 完了基準（重要）

機能追加は「ユニットテストが緑」だけでは完了ではありません。**実採譜フロー（`pipeline.py`／CLI／app）から実際に呼ばれ、出力される**ところまでを完了とします（根拠: `docs/debug/root-cause-analysis.md` — 並列実装した機能が製品に反映されず孤立した反省）。

完了の条件:

1. ユニットテストが緑
2. `pipeline.py`／CLI／app へ結線され、実際に呼び出される（新しい出力形式なら CLI オプションから到達できる）
3. `spike/ear-pipeline/tests/test_integration_smoke.py` に end-to-end で「実際に出せる」ケースを追加して緑
4. `python scripts/check_orphan_exports.py` が緑（結線したシンボルは `scripts/orphan_allowlist.txt` から削除する）

並列作業は「実装」に使い、「統合（結線）」は必ず直列フェーズで Issue 化して実施してください。

## テスト方針

- バグ修正では、可能なら再発防止テストを追加してください。
- 採譜エンジンの変更は `spike/ear-pipeline/tests/` を優先して検証してください。
- 評価ハーネスの変更は `tools/ai-ears/tests/` を優先して検証してください。
- 音源依存の重い検証は、PR 本文に再現手順と結果を書いてください。
- `__init__.py` の `__all__` に足したシンボルは、実採譜フローから到達できるようにするか、意図的にライブラリ止まりなら `scripts/orphan_allowlist.txt` に登録してください（`check_orphan_exports.py` が未登録の孤立を落とします）。

## ローカル処理とプライバシー

EarOnPaper は完全ローカル処理を設計原則にしています。音源・生成楽譜・解析結果を外部サーバーへ送信する変更は、事前に Issue で設計・リスク・ユーザー同意の扱いを明記してください。

