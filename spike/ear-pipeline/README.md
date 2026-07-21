# earpipe — Pitchsieve 採譜エンジン

音声ファイル → 五線譜 MusicXML（＋MIDI／PDF／ギターTAB譜 PDF）を**完全ローカル**で処理するパイプライン。
"絶対音感エミュレータ" のコア実装。ライセンス: Apache-2.0。

---

## クイックスタート

### 1. 前提

| 要件 | バージョン |
|---|---|
| Python（メインエンジン） | **3.12 以上**（3.14 推奨） |
| Python（多声検出 Basic Pitch） | **3.12 専用** ※ |
| OS | macOS / Linux（Windows は未検証） |

> ※ Basic Pitch は Python 3.14 未対応のため、3.12 の仮想環境を別途作成して subprocess 経由で呼び出します。多声検出（`--engine poly`）を使わない場合は不要です。

---

### 2. セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/iloli-source/EarOnPaper.git
cd EarOnPaper/spike/ear-pipeline

# メインエンジン用 venv（Python 3.12+）
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

#### 多声検出（`--engine poly`）を使う場合のみ

```bash
# Python 3.12 が必要（pyenv 等で用意してください）
python3.12 -m venv .venv312
.venv312/bin/pip install basic-pitch

# または環境変数で既存の Python 3.12 を指定
export EARPIPE_BP_PYTHON=/path/to/python3.12
```

---

### 3. 採譜してみる

```bash
# 単旋律（既定・高速）
.venv/bin/python -m earpipe.pipeline transcribe 音源.wav -o 楽譜.musicxml

# 多声 + MIDI も出力
.venv/bin/python -m earpipe.pipeline transcribe 音源.wav \
    --engine poly \
    -o 楽譜.musicxml \
    --midi 楽譜.mid

# フィールド録音（雑音まじり）
.venv/bin/python -m earpipe.pipeline transcribe 録音.wav \
    --engine poly \
    --field-mode \
    -o 楽譜.musicxml

# ギターTAB譜 PDF（コードネーム＋押さえ図つき）
.venv/bin/python -m earpipe.pipeline transcribe 音源.wav \
    -o 楽譜.musicxml \
    --tab 楽譜_tab.pdf
```

> **対応入力形式:** wav / mp3 / flac など librosa が読める形式

#### 出力

| ファイル | 内容 |
|---|---|
| `.musicxml` | 五線譜（MuseScore / Finale / Sibelius 等で直接開ける） |
| `.mid` | MIDI（DAW に取り込み可） |
| `--pdf` | 五線譜 PDF（Verovio 浄書） |
| `--tab` | ギターTAB譜 PDF（6弦標準EADGBE・コード帯つき。下記参照） |
| 標準出力 JSON | イベント数・音符数・推定 BPM・先頭無音カット秒・チューニングずれ・区間テンポ等 |

#### 前処理: 先頭無音の自動トリム

音源の頭の無音（曲前の空白）は楽譜の先頭を休符にして精度を落とすため、
**最初に音が鳴る位置まで自動で詰めてから採譜します**（ユーザー実測で精度向上を確認・2026-07-20）。
カットした秒数は JSON の `trimmed_leading_sec` で報告します。音の頭を削らないよう 0.05 秒のマージンを残します。

#### ギターTAB譜（出力プロファイル・NF-045）

- **運指割り当て**: ポジション（4フレット幅＋開放弦）単位の動的計画法で**手の移動が最小**になる弦・フレットを選ぶ（ローコード偏重を回避）
- **音域外の音**: オクターブ折り返しで収め、折り返した音数を正直に報告（`n_octave_shifted`）
- **コード帯**: クロマ・テンプレート相関でコードを推定し、変化点にコードネーム＋押さえ図を表示。確信度が閾値未満の区間は誤魔化さず **N.C.** と表示
- `--tab-plain` で押さえ図なし版（コードネームのみ）を同時生成、`--no-chord-diagrams` で図を無効化

---

### 4. オプション一覧

```
transcribe 音源 [オプション]

  -o, --output FILE      MusicXML 出力先（省略時: 入力名.musicxml）
  --midi FILE            MIDI 出力先（任意）
  --pdf FILE             五線譜 PDF 出力先（-o と同時に指定）
  --tab FILE             ギターTAB譜 PDF 出力先（6弦標準EADGBE・コード帯つき）
  --tab-plain FILE       押さえ図なしTAB（コードネームのみ）の出力先
  --no-chord-diagrams    TABのコード帯を押さえ図なしにする（既定は図あり）
  --engine mono|poly     mono=pYIN 単旋律（既定）/ poly=Basic Pitch 多声
  --sensitivity auto|normal|high
                         poly 検出感度（auto=密度適応・既定、high=弱音拾う）
  --field-mode           フィールド録音モード（SNR 適応・非音程成分を除去）
  --postfilter           幽霊音符除去フィルタ（既定 OFF）
  --timing grid|raw      MIDI タイミング（grid=楽譜整合/既定、raw=実タイミング）
  --title TEXT           楽譜タイトル（省略時: ファイル名）
  --stem NAME            ステム分離して指定楽器だけ採譜（vocals/drums/bass/other・要Demucs）
  --format KEY[=PATH]    追加の出力形式（複数可）: jianpu/leadsheet/ust/abc/lilypond/gp5
  --analysis KEY[=PATH]  解析テキスト（複数可）: movable_do（移動ド）/roman（度数）/nashville
  --emit KEY[=PATH][#k=v] 実装機能のオプトイン副次出力（複数可）。既定の記譜出力は不変。
                         例: --emit validate / --emit simplify#level=0.7 / --emit diagnose
                         （drums/velocity/sustain/transpose/handoff/profile 等 30種以上）
```

`transcribe` 以外のサブコマンド:

```
separate-transcribe 音源 --out-dir DIR   ステム分離して楽器毎に別譜面（F-003）
chunk 音源 --out-dir DIR [--max-sec N]   長尺音源を無音優先で複数wavに分割（F-004）
diff A音源 B音源 [-o FILE]               2音源を採譜し音符列の意味論的差分を出力
compare 原音 transcription [--report F]  AIの耳（ai-ears）で比較評価
record --out FILE [--seconds N] [--transcribe]  マイク/ライン録音（F-005・要sounddevice）
rights                                   採譜物の権利ガイダンス（配布/販売前の著作権注意・F-073）
```

> **実装機能はすべて CLI から到達可能**（孤立0・#109）。「ユニット緑だが未配線」を機械ゲート
> （`scripts/check_orphan_exports.py`・CI常設）で検出し、85件の債務を全消化済み。

---

### 5. 音質と限界（正直な記録）

| 指標 | 値 | 条件 |
|---|---|---|
| Note F1@100ms（raw） | **0.765** | PD 正解付き 15 曲・多声 auto |
| score_rhythm（楽譜レベル） | **0.410** | 同上 |
| キー主調正解率 | **86.7%** | PD 15 曲 |
| 基準ピッチ補正精度 | **±5 cents** | A=440 ±50 cents の変則音源 |
| フィールド録音（雑音のみ） | 誤発火 **0.000** | 27 条件すべて |

**既知の限界:**
- テンポは一定テンポを仮定（ルバート・途中変速には追従しない）
- 拍子推定はアクセント周期から L/4 を推定（確証が弱い場合は 4/4 に退避）
- 転調追従は未実装（曲全体で単一調を推定）
- 高速トリル・装飾音は min_dur の下限で消失する場合あり

---

### 6. テスト

```bash
# エンジン全テスト（1165 件）
.venv/bin/python -m pytest tests/ -q

# 並列実行（pytest-xdist）
.venv/bin/python -m pytest tests/ -n 20 -q

# カバレッジつき
.venv/bin/python -m pytest tests/ --cov=earpipe --cov-report=term-missing

# AI の耳（審判ハーネス・64 件）
cd ../../tools/ai-ears
.venv/bin/python -m pytest tests/ -q
```

---

### 7. 正解付きベンチ（PD コーパス）

`tools/ai-ears/testdata/pd-corpus/` に正解 MIDI を配置した上で実行します（詳細は `bench/README`・著作権消滅 PD 曲のみ対象）。

```bash
# 基本ベンチ
.venv/bin/python bench/bench_pd.py

# 密度適応の受入測定（C1/C3 合格確認）
.venv/bin/python bench/bench_pd.py --adaptive

# キー・綴り計測（C4 合格確認）
.venv/bin/python bench/bench_key_spelling.py

# 拍子整合・譜面検査（C3/#57 / C5/#59 合格確認）
.venv/bin/python bench/bench_score_checks.py
```

---

### 8. ディレクトリ構成

```
spike/ear-pipeline/
├── earpipe/
│   ├── pipeline.py          # CLI + オーケストレータ
│   ├── contracts.py         # 契約 IF（PitchEvent / QuantizedNote 等）
│   └── services/
│       ├── stem/            # 前処理・フィールド分類
│       │   └── preprocess.py # ロード・先頭無音トリム
│       ├── ear/             # 音高検出（mono=pYIN / poly=Basic Pitch）
│       │   ├── tuning.py    # 基準ピッチ補正（A=440±50cents）
│       │   └── adaptive.py  # 密度適応の自動感度選択
│       ├── rhythm/          # テンポ推定・量子化・拍子推定
│       │   ├── quantize.py  # 格子量子化・estimate_grid
│       │   ├── tempo_map.py # 区間別テンポ系列
│       │   └── meter.py     # 拍子推定（アクセント周期）
│       └── notate/          # 記譜・出力プロファイル（NF-045）
│           ├── score.py     # music21 Score 構築
│           ├── spelling.py  # キー推定・異名同音スペリング
│           ├── engrave.py   # Verovio → 五線譜 PDF
│           ├── tab.py       # ギターTAB譜 PDF（運指DP・重なり検査）
│           ├── chord.py     # コード推定（クロマ・テンプレート相関）
│           └── chord_shapes.py # コード押さえ図（開放形＋バレー計算）
├── tests/                   # pytest（1165 件）
├── bench/                   # PD 正解付きベンチ
├── usertest/                # 体験テスト（採譜→聴き比べビューア。音源は非公開）
└── requirements.txt
```

---

### 9. 設計原則

- **完全ローカル**: 採譜〜出力の全経路でネットワーク送信ゼロ（ソケット遮断テストで実証）
- **二層構造**: 耳（楽器非依存）と記譜（出力プロファイル）を分離。TAB / 简谱等はプラグイン層（NF-045）で追加可能
- **依存は一方向**: stem → ear → rhythm → notate。循環依存は静的テストで禁止
- **正直な退避**: 格子で説明できない入力はデフォルト値を返し、黙って誤った結果を返さない

---

### 10. ライセンス

Apache-2.0。Basic Pitch（Spotify）も Apache-2.0。Verovio は LGPL-3.0（配布形態に注意・[ADR-004](../../docs/architecture/ADR-004-verovio.md) 参照）。
