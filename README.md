# EarOnPaper — 採譜プロジェクト (AI Music Transcription)

> *Transcribing the world into music.* エンジンのコードネーム: **Pitchsieve**

**絶対音感エミュレータ** — 雑音を含む日常録音から、絶対音感を持つ人のように音程成分だけを選択的に抽出して楽譜にする。非音楽家がターゲット。詳細: [プロダクトビジョン](docs/requirements/product-vision.md)

## エンジンを使ってみる

採譜エンジン（Pitchsieve）は `spike/ear-pipeline/` にあります。**セットアップ・使い方は [`spike/ear-pipeline/README.md`](spike/ear-pipeline/README.md) を参照してください。**

```bash
# クローン後、3 コマンドで試せます
cd spike/ear-pipeline
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m earpipe.pipeline transcribe 音源.wav -o 楽譜.musicxml
```

出力の `.musicxml` は MuseScore（無料）でそのまま開けます。

## なぜ全部公開するのか

AI を使った自動採譜は **ニッチ中のニッチ** だ。「音声を渡したら楽譜が出てくる」を本気で作ろうとした人なら、すぐにわかる。

- 論文はあるが実装がない
- 実装はあるが評価がない
- 評価があるが再現できない
- 有料ツールはブラックボックスで、なぜそう出力するのかが全くわからない

このプロジェクトはその壁を全部体験した。文献をかき集め、試して、失敗して、また試した記録をすべてそのままここに置いてある。批判ループ・ベンチ設計・No-Go判定・精度向上の泥臭い実験ログ、ぜんぶ。

**同じ問題に取り組む誰かの足場になれば、それだけで十分な価値がある。**  
だから丸ごと公開した。もし役に立ったら、[GitHub Sponsors](https://github.com/sponsors/tadahappy) で応援してもらえると嬉しい。

---

## 現在地（2026-07-20）

※「フェーズ」は機能実装の P1スパイク/P2 MVP/P3将来構想 を指す（要件一覧参照）。下表はそれとは別の**プロジェクト工程**。

| 工程 | 状態 | 成果物 |
|---|---|---|
| 1. リサーチ | **完了** | [結論v5](docs/research/conclusions-v5.md)（No-Go継続・4ゲート検証へ）＋[実行仕様書 改訂3](docs/research/gate-execution-spec.md) |
| 2. ビジョン | **確定** | [絶対音感エミュレータ](docs/requirements/product-vision.md)（科学・当事者・市場の3方向で裏づけ済み・判定哲学含む） |
| 3. 要件定義 | **v2.7確定水準** | [機能一覧117件](docs/requirements/functional-requirements.md)・[非機能一覧50件](docs/requirements/non-functional-requirements.md)・[HTMLビューア](docs/requirements/requirements-viewer.html)（批判3巡＋トレーサビリティ監査済み） |
| 4. UI/UX方針 | **確定** | [デザイン方針書](docs/requirements/uiux/uiux-direction.md)（静かな工房60% × 進化する下書き30% × 弾ける歓び10%＋波形・計器・懐かしさ追補） |
| 5. 評価基盤 | **実装済み** | [AIの耳ハーネス](tools/ai-ears/)（4指標・自己検証合格・pytest 49件） |
| 6. 実測検証（G0'〜） | **着手可能** | [G0'実施キット](docs/research/g0-prime-kit.md)完備。必要なのはユーザーの音源3曲＋聴き比べ20-30分のみ（Issue #13） |
| 7. ツール開発・事業判断 | 未着手 | 4ゲート通過時のみ。磨き込み順序はG0'実測後に決定 |

## 確定済みの主要判断

- **ビジョン: 絶対音感エミュレータ**。耳（解析エンジン）は楽器非依存、楽器・記譜法は出力プロファイルの選択肢（二層アーキテクチャ原則 NF-050）
- **出力形: デフォルトは五線譜（一次画面含む・ユーザー裁定）＋TAB含む全形式をオプションで網羅**（F-104・プラグイン型出力層NF-045）。「TAB特化」ではない
- **評価: 二段判定** — 事前封緘した客観指標（AIの耳4指標）＋非音楽家聴感（聴き比べ）。音楽家の「手直し苦痛」基準は演奏者向け出力オプションのQA専用に降格。**人間の専門家レビューはユーザーテスト段階（五線譜PDF出力実現後）のみ**
- **チューニング・回帰は自走**: 合成データ（正解が構成的に既知）の自動採点ループで、人間の耳なしに品質を測定・改善
- **法務: OSS AS-IS免責スタンス** — 作成物の利用責任はユーザー。成果物非関与・ローカル処理は設計原則として維持
- **成果物非関与構造**（ユーザー音源・成果物にサーバーが触れない、ローカル処理中心）が法務上の必須条件
- 対応楽曲長は**2時間保証・最大24時間**
- 原則「**情報は保存するが、固定は証拠が来るまで最低段**」（要件行/受入条件/観測リスト/方針書の4段で管理）

## 検証プロセス

結論・要件はすべて多モデル批判ループで鍛えてある:

- リサーチ: 批判→調査→改善を4周（批判34本・調査16本、grok/codex/Claude/一部gemini）
- 要件: 3モデル批判3巡＋網羅ギャップスキャン2巡（中英X・論文規格・Web）＋トレーサビリティ監査（資料40本×要件、5並列）
- ビジョン: 絶対音感の3方向網羅調査（論文DOI・X当事者証言・Web）で科学的に裏づけ
- UI/UX: 3モデル調査→相互レビュー打ち合わせ→全員一致で方向性確定

## ディレクトリ

```
docs/
├── research/          # リサーチ・実行準備
│   ├── conclusions-v5.md        # 事業リサーチ最終結論（v1〜v4も履歴保存）
│   ├── gate-execution-spec.md   # 実行仕様書 改訂3（4ゲート・二段判定）
│   ├── g0-prime-kit.md          # G0'実施キット（自走可能）
│   ├── g0-reviewer-brief.md     # 製品レビュー依頼書（PDF出力実現後に使用・温存）
│   ├── absolute-pitch-*.md      # 絶対音感の3方向調査
│   ├── waveform-*.md / instruments-ui-*.md  # 波形・計器UI調査
│   ├── critique/ rounds/        # 批判ループ・深掘り調査（履歴）
│   ├── youtube-survey.md        # YouTube網羅調査
│   └── naming-clearance.md      # 命名クリアランス（Otohiki第1推奨・決定は保留）
├── requirements/      # 要件定義（v2.7）
│   ├── product-vision.md                # プロダクトビジョン（最上位文書）
│   ├── functional-requirements.md       # 機能117件（MoSCoW・フェーズ・出典つき）
│   ├── non-functional-requirements.md   # 非機能50件（IPA準拠＋固有カテゴリ）
│   ├── requirements-viewer.html         # フィルタ・検索つきビューア
│   ├── critique/                        # 要件への批判3巡・監査レポート
│   └── uiux/                            # UI/UX調査・打ち合わせ・デザイン方針書
tools/
└── ai-ears/           # AIの耳評価ハーネス（音高一致・出だし・テンポ・譜面健全性）
```

## 運用メモ

- 要件はJSON単一ソースからMD/HTMLを自動生成（内容乖離防止）
- 調査は多モデル分担: grok=X実ユーザー / codex=論文・規格 / Claude=Web・統合
- 定点観測: MuseScore audio2scoreβの品質を週次15分で実測（kill switch 3条件はspec §7）
- 前提が転換したら既存文書を連鎖更新する（「仕様に書いてある」を防衛根拠にしない）
- **Issue駆動開発**: 開発作業はIssueを立ててから着手し、進捗・検証結果をIssueに記録、完了時に結果つきでクローズ（devラベル）

