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

## テスト方針

- バグ修正では、可能なら再発防止テストを追加してください。
- 採譜エンジンの変更は `spike/ear-pipeline/tests/` を優先して検証してください。
- 評価ハーネスの変更は `tools/ai-ears/tests/` を優先して検証してください。
- 音源依存の重い検証は、PR 本文に再現手順と結果を書いてください。

## ローカル処理とプライバシー

EarOnPaper は完全ローカル処理を設計原則にしています。音源・生成楽譜・解析結果を外部サーバーへ送信する変更は、事前に Issue で設計・リスク・ユーザー同意の扱いを明記してください。

