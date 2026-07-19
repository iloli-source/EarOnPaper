# earpipe — 採譜エンジン spike v0

音声ファイル → 音程イベント → 拍格子量子化 → **五線譜MusicXML**（＋MIDI）を端末内で完結するパイプライン。ユーザーゴール「テストがオールグリーンになるまで開発して実行」の成果物。

## 使い方

```bash
.venv/bin/python -m earpipe.pipeline transcribe input.wav -o out.musicxml --midi out.mid
# または
.venv/bin/python earpipe/pipeline.py transcribe input.wav
```

出力: MusicXML（MuseScore等でそのまま開ける五線譜）・MIDI・JSONサマリー（イベント数/音符数/推定BPM）。

## テスト

```bash
.venv/bin/python -m pytest tests/ --cov=earpipe --cov-report=term-missing
```

**現状: 32件 全パス・カバレッジ98%**（2026-07-19）

- ユニット: テンポ推定・量子化・記譜・タイ処理
- 合成E2E: 正解既知の合成メロディ（単純/付点/テンポ違い）で Note F1 ≥ 0.8・MusicXML再読込・小節整合
- 統合: 出力を AIの耳（`tools/ai-ears/ears.py`）にかけ総合スコア ≥ 0.8
- ネガティブ: 無音・ノイズ入力で**音符ゼロを正直に返す**（絶対音感エミュレータの設計原則）

## 二層構造との対応（NF-050）

| 層 | モジュール | 内容 |
|---|---|---|
| 耳（楽器非依存） | `earpipe/ear.py` | pYINで音声→音程イベント＋信頼度。楽器固有の分岐なし |
| 変換 | `earpipe/quantize.py` | テンポ推定（confidence重み付け・和音クラスタ化・IOI無次元フィット・音価/テンポ事前分布による倍半処理。Issue #34）＋16分格子量子化 |
| 記譜（出力プロファイル） | `earpipe/notate.py` | music21で五線譜MusicXML/MIDI。TAB/简谱等はNF-045プラグイン層の将来拡張 |

## v0の正直な限界

- **単音（モノフォニック）のみ。** 多声対応の basic-pitch は Python 3.14 でビルド不能のため見送り（`pip install basic-pitch` が `setuptools.build_meta` 不能で失敗）。和音・伴奏つき実曲はまだ扱えない — 多声化が次の最重要課題
- 拍子は4/4固定・アウフタクトなし・調号推定なし（F-081ピッチスペリングは未実装）
- テンポは一定と仮定（テンポマップF-017未対応。ルバート・テンポ変化曲に追従しない。区分定テンポ推定は将来課題）
- 格子は16分のみで**三連符・複合拍子は未対応**（例: 三連符アルペジオ曲は1.5倍テンポの8分として誤整合する。Romanze実測で確認。三連格子対応は#31-33系の将来課題）
- 合成音源（sine）で検証済み。実録音（雑音・残響・実楽器）への頑健性は未検証 — G0'/G1ベンチの領域
- AIの耳統合スコア0.8は合成音源での値。実曲では下がる想定

## 依存

`requirements.txt`（librosa 0.11 / music21 10.5 / numpy 2.4 ほか）。venv: `.venv/`（Python 3.14）。


---

## v0.2（2026-07-19）: 多声対応

- **耳層(多声)**: `earpipe/ear_poly.py` — basic-pitch を別インタプリタ（`tools/ai-ears/.venv312`、Python 3.12）の `bp_worker.py` 経由で実行（JSON契約のsubprocess。Python 3.14本体からの利用のため）。`EARPIPE_BP_PYTHON` で差し替え可
- **モデルはTFLite（nmp.tflite）固定**: TF SavedModel=環境非互換、**ONNX=出力が壊れる（無音でnote事後確率0.60）ため使用禁止**。検証記録は bp_worker.py 冒頭コメント参照
- **量子化**: `quantize_events(..., mono=False)` で同時発音を許可。**記譜**: 同一開始拍をChord化（長さはメンバー最長に簡略化。声部分離は将来課題）
- **CLI**: `pipeline.py transcribe in.wav --engine poly`
- **テスト**: 37件全パス・カバレッジ95%（bp_worker は3.12側実行のため計測外、E2Eで検証）
- **実曲ベンチ（対BP素点）**: リズム(出だし)を3曲全てで改善（+0.10〜0.15、precision向上主導）。詳細は `docs/research/g0-ledger.md` §7
- **既知の限界**: ~~テンポ推定が密な多声で高BPMに張り付く~~（#34で解消: 幽霊混入時の145-150固着と倍半誤りを修正。格子で説明できない入力はデフォルト120へ正直に退避）／和音の長さ簡略化／ライセンス: basic-pitch はコード・モデルとも Apache-2.0

## v0.3 (#31/#32): 感度可変と後処理フィルタ

- `--sensitivity high`: 低閾値検出(#32)。PD15曲の楽譜レベルKPIで唯一BP素点超え(0.402 vs 0.387)。高速・高密度曲で劇的改善(トルコ行進曲F1 2.9倍)。疎な曲では逆効果=密度適応が将来課題
- `--postfilter`: 幽霊除去(#31)。**既定OFF** — 実曲で本物のオクターブ重ねを誤除去し平均逆効果と実測されたため(bench/results-pd.md参照)。合成ケースでは設計どおり動作(テストで保証)

## 構成（ADR-001 サービス分割・#35）

```
earpipe/
├── contracts.py          # 契約IF: PitchEvent / QuantizedNote(frozen dataclass)
├── pipeline.py           # オーケストレータ + CLI(transcribe)
├── services/
│   ├── stem/             # 前処理(ロード。将来: ステム分離F-003・音質診断F-002)
│   ├── ear/              # 耳: mono(pYIN)・poly(Basic Pitch TFLite)・postfilter
│   ├── rhythm/           # テンポ推定・量子化
│   ├── notate/           # 五線譜MusicXML/MIDI出力
│   └── quality/          # AIの耳(tools/ai-ears)への薄いクライアント(本体非依存)
└── ear.py 等             # 後方互換シム(旧importパス維持)
```

依存方向は一方向(stem → ear → rhythm → notate)。qualityはエンジン本体に依存しない。
静的検査: `tests/test_services_contract.py` がimportのAST走査で強制する。
