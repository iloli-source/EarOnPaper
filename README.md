# EarOnPaper — 採譜プロジェクト (AI Music Transcription)

> *Transcribing the world into music.* エンジンのコードネーム: **Pitchsieve**

**絶対音感エミュレータ** — 雑音を含む日常録音から、絶対音感を持つ人のように音程成分だけを選択的に抽出して楽譜にする。**ターゲットは採譜に関わる全ての人**。専門知識のない**非音楽家でも音源から楽譜を得られる**アクセシビリティを主眼にしつつ、音楽家向けの理論系出力（簡譜/度数/Nashville/GP5等）も用意する。詳細: [プロダクトビジョン](docs/requirements/product-vision.md)

## エンジンを使ってみる

採譜エンジン（Pitchsieve）は `spike/ear-pipeline/` にあります。**セットアップ・使い方は [`spike/ear-pipeline/README.md`](spike/ear-pipeline/README.md) を参照してください。**

```bash
# クローン後、3 コマンドで試せます
cd spike/ear-pipeline
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m earpipe.pipeline transcribe 音源.wav -o 楽譜.musicxml
```

出力の `.musicxml` は MuseScore（無料）でそのまま開けます。

> **AI にセットアップを任せる:** Claude Code / Cursor などの AI コーディングエージェントにこのリポジトリを渡し、[エンジン README のセットアップ手順](spike/ear-pipeline/README.md#2-セットアップ) にある「AI エージェントにセットアップさせる」プロンプトを貼れば、必要な仮想環境（メイン／多声検出／ステム分離）と依存を自動で用意させられます。

> **エンジンは既定 `auto` で音源に応じて自動選択されます（Issue #64 で実装）。** 音源のポリフォニーを推定し、伴奏を含む混合音源は `poly`（basic-pitch 多声）、弾き語り・口笛・鼻歌などの単旋律は `mono`（pYIN 単音）を選びます。ノイズは音符化しません。明示指定したい場合のみ `--engine mono|poly` を付けてください。`poly` の利用には basic-pitch 用 Python（`EARPIPE_BP_PYTHON`）が必要で、無い環境では `mono` に正直にフォールバックします。

## なぜ全部公開するのか

AI を使った自動採譜は **ニッチ中のニッチ** だ。「音声を渡したら楽譜が出てくる」を本気で作ろうとした人なら、すぐにわかる。

- 論文はあるが実装がない
- 実装はあるが評価がない
- 評価があるが再現できない
- 有料ツールはブラックボックスで、なぜそう出力するのかが全くわからない

このプロジェクトはその壁を全部体験した。文献をかき集め、試して、失敗して、また試した記録をすべてそのままここに置いてある。ベンチ設計・精度評価・泥臭い実験ログ、ぜんぶ。

**同じ問題に取り組む誰かの足場になれば、それだけで十分な価値がある。**  
だから丸ごと公開した。もし役に立ったら、[GitHub Sponsors](https://github.com/sponsors/tadahappy) で応援してもらえると嬉しい。

---

## 現在地（2026-07-23）

※「フェーズ」は機能実装の P1スパイク/P2 MVP/P3将来構想 を指す（要件一覧参照）。下表はそれとは別の**プロジェクト工程**。

| 工程 | 状態 | 成果物 |
|---|---|---|
| 1. リサーチ | **完了** | [調査結論](docs/research/conclusions-v5.md)・[実行仕様書](docs/research/gate-execution-spec.md) |
| 2. ビジョン | **確定** | [絶対音感エミュレータ](docs/requirements/product-vision.md)（科学・当事者・市場の3方向で裏づけ済み） |
| 3. 要件定義 | **v2.7確定** | [機能一覧117件](docs/requirements/functional-requirements.md)・[非機能一覧50件](docs/requirements/non-functional-requirements.md)・[HTMLビューア](docs/requirements/requirements-viewer.html) |
| 4. UI/UX方針 | **確定** | [デザイン方針書](docs/requirements/uiux/uiux-direction.md) |
| 5. 評価基盤 | **実装済み** | [AIの耳ハーネス](tools/ai-ears/)（4指標・pytest 49件） |
| 6. エンジン開発 | **実装済み** | [Pitchsieve](spike/ear-pipeline/)。既定出力は五線譜/TAB PDF・MIDI・MusicXML（自動評価ハーネス「AIの耳」の**合成データ採点**で満点＝実曲精度の完成ではない）。簡譜/リード/度数/移動ド・GP5・音質診断・ドラム譜・移調/簡略化ほかは**オプトイン副次出力**（`--emit`/`--analysis`/`--format`・既定譜面/GUIには非反映）。孤立検査ゲート(#111)で本番未到達関数を厳密検出し理由付きで凍結。ステム分離は4-stem（vocals/drums/bass/other）と6-stem（ギター/ピアノを個別分離）。BPM・拍子・キーは自動検出に加え任意上書き対応 |
| 7. デスクトップアプリ | **MVP動作（楽器選択対応）** | [app/](app/)（Electron）。ドラッグ&ドロップまたは**YouTube等のURL貼付**（yt-dlpローカル実行・私的利用前提・F-006裁定変更2026-07-23）→**Demucsで楽器分離→ギター/ピアノ/ボーカル/ベースを選んで採譜**→PDFアプリ内表示（ギターはTAB/五線譜切替・GP風リズム表記/休符/和音囲み #127）→エクスポート。**BPM/拍子/キーの任意指定**（分かる人は指定・未指定は自動）。処理画面は宇宙背景。解析ビュー（信頼度ハイライト＋波形）あり。楽譜エディタ・スペクトログラムは今後（#125） |

## 確定済みの主要判断

- **ビジョン: 絶対音感エミュレータ**。耳（解析エンジン）は楽器非依存、楽器・記譜法は出力プロファイルの選択肢（二層アーキテクチャ原則 NF-050）
- **出力形: デフォルトは五線譜（一次画面含む・ユーザー裁定）＋TAB含む全形式をオプションで網羅**（F-104・プラグイン型出力層NF-045）。「TAB特化」ではない
- **評価: 客観指標＋聴感の二段判定** — 自動採点（AIの耳4指標）＋非音楽家による聴き比べ。数値の飽和より「同じ曲に聞こえる」を最終ゴールとする
- **品質ループは自走**: 合成データで正解付き自動採点ループを回す。人手レビューなしに精度を改善できる
- **完全ローカル処理**: 音源・生成楽譜はネットワークに送信しない。サーバーが成果物に触れない構造を設計原則として維持
- **対応楽曲長**: 現行GUIでの2時間保証・24時間対応は未実証。`chunk` サブコマンドはあるが、GUIの標準採譜経路には未接続（D4M-021・結線と実測完了までこの表示とする）

## 検証プロセス

結論・要件はすべて複数モデルによる批判ループで鍛えてある:

- リサーチ: 批判→調査→改善を4周
- 要件: 批判3巡＋網羅ギャップスキャン＋トレーサビリティ監査（資料40本×要件）
- ビジョン: 絶対音感を論文・当事者証言・市場の3方向から科学的に裏づけ
- UI/UX: 複数モデルで調査→相互レビュー→方向性確定

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

## コントリビューション

- **Issue駆動**: 開発作業はIssueを立ててから着手し、結果つきでクローズ
- 前提が変わったら関連ドキュメントを連鎖更新する

