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
| 変換 | `earpipe/quantize.py` | テンポ推定（秒単位誤差の格子フィット・遅テンポ優先）＋16分格子量子化 |
| 記譜（出力プロファイル） | `earpipe/notate.py` | music21で五線譜MusicXML/MIDI。TAB/简谱等はNF-045プラグイン層の将来拡張 |

## v0の正直な限界

- **単音（モノフォニック）のみ。** 多声対応の basic-pitch は Python 3.14 でビルド不能のため見送り（`pip install basic-pitch` が `setuptools.build_meta` 不能で失敗）。和音・伴奏つき実曲はまだ扱えない — 多声化が次の最重要課題
- 拍子は4/4固定・アウフタクトなし・調号推定なし（F-081ピッチスペリングは未実装）
- テンポは一定と仮定（テンポマップF-017未対応。ルバートに追従しない）
- 合成音源（sine）で検証済み。実録音（雑音・残響・実楽器）への頑健性は未検証 — G0'/G1ベンチの領域
- AIの耳統合スコア0.8は合成音源での値。実曲では下がる想定

## 依存

`requirements.txt`（librosa 0.11 / music21 10.5 / numpy 2.4 ほか）。venv: `.venv/`（Python 3.14）。
