# 採譜プロジェクト (AI Music Transcription)

AI採譜（音楽音源 → 楽譜/TAB/MIDI変換）のリサーチ・検証・ツール開発・事業化検討を行うプロジェクト。

## 現在地（2026-07-19）

| フェーズ | 状態 | 成果物 |
|---|---|---|
| 1. リサーチ | **完了** | [結論v5](docs/research/conclusions-v5.md)（No-Go継続・4ゲート検証へ）＋[封緘版実行仕様書](docs/research/gate-execution-spec.md) |
| 2. 要件定義 | **v2.4確定水準** | [機能一覧109件](docs/requirements/functional-requirements.md)・[非機能一覧50件](docs/requirements/non-functional-requirements.md)・[HTMLビューア](docs/requirements/requirements-viewer.html)・[プロダクトビジョン](docs/requirements/product-vision.md) |
| 3. UI/UX方針 | **確定** | [デザイン方針書](docs/requirements/uiux/uiux-direction.md)（静かな工房60% × 進化する下書き30% × 弾ける歓び10%） |
| 4. 実測検証（テストフェーズ） | **着手待ち** | G0'（MuseScoreβ/MuScriptor半日実測）から開始。Issue #1 参照 |
| 5. ツール開発・事業判断 | 未着手 | 4ゲート通過時のみ。出力形は確定済み（デフォルト五線＋TAB含む全形式オプション）。G0'実測後に磨き込み順序を決定 |

## 確定済みの主要判断

- **事業判定: No-Go継続**。当初仮説・代替3仮説はすべて棄却。残る問いは「安く・小さく・成果物非関与で勝てる崩れ方が競合出力に実在するか」のみ（結論v5）
- **プランB採択**: 4ゲート逐次検証（G0'半日実測 → G2需要 → G1本ベンチ → G3弁護士4問）。判定ルールは事前封緘・デフォルト撤退
- **出力形: デフォルト五線譜＋TAB含む全形式をオプションで網羅**（F-104・プラグイン型出力層NF-045）。TAB対応能力はMust（弦/フレット割当・チューニング/カポ・奏法検出・TAB品質KPI）だが「TAB特化」ではない
- **成果物非関与構造**（ユーザー音源・成果物にサーバーが触れない、ローカル処理中心）が法務上の必須条件
- 対応楽曲長は**2時間保証・最大24時間**、出力は**全形式オプション対応**（プラグイン型出力層）を目指す

## 検証プロセス

結論・要件はすべて多モデル批判ループで鍛えてある:

- リサーチ: 批判→調査→改善を4周（批判34本・調査16本、grok/codex/Claude/一部gemini）
- 要件: 3モデル批判2巡＋網羅ギャップスキャン2巡（中英X・論文規格・Web）→「構造的欠落なし・飽和点」判定
- UI/UX: 3モデル調査→相互レビュー打ち合わせ→全員一致で方向性確定

## ディレクトリ

```
docs/
├── research/          # リサーチフェーズ（完了）
│   ├── conclusions-v5.md        # 最終結論（v1〜v4も履歴として保存）
│   ├── gate-execution-spec.md   # 封緘版実行仕様書（4ゲート）
│   ├── critique/                # 批判ループ Round1-4
│   ├── rounds/                  # 深掘り調査レポート
│   ├── youtube-survey.md        # YouTube網羅調査
│   └── naming-clearance.md      # 命名クリアランス（Otohiki第1推奨・決定は保留）
└── requirements/      # 要件定義（v2.2）
    ├── functional-requirements.md       # 機能104件（MoSCoW・フェーズ・出典つき）
    ├── non-functional-requirements.md   # 非機能45件（IPA準拠＋固有カテゴリ）
    ├── requirements-viewer.html         # フィルタ・検索つきビューア
    ├── critique/                        # 要件への批判・ギャップスキャン2巡
    └── uiux/                            # UI/UX調査・打ち合わせ・デザイン方針書
```

## 運用メモ

- 要件はJSON単一ソースからMD/HTMLを自動生成（内容乖離防止）
- 調査は多モデル分担: grok=X実ユーザー / codex=論文・規格 / Claude=Web・統合 / gemini=補完（クォータ回復時）
- 定点観測: MuseScore audio2scoreβの品質を週次15分で実測（kill switch 3条件はspec §7）
