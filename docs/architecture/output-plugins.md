# 出力層プラグインインターフェース（NF-045）

**最終更新:** 2026-07-21
**目的:** 二層アーキテクチャ（NF-050: 耳＝解析／記譜＝出力）の**出力側を差し替え可能な
プラグイン**として正式化する。新しい出力形式・解析注釈を、コア（`pipeline.py`）を
編集せず 1 ファイル追加だけで結線できる。

## 3 系統の出力口

| 口 | 対象 | 実体 | CLI |
|---|---|---|---|
| **FORMAT_REGISTRY 形式** | 楽譜フォーマット | `services/notate/format_registry.py` ＋ `dispatch.py` の adapter | `--format KEY` |
| **解析注釈** | 採譜結果の派生テキスト | `services/notate/analysis_dispatch.py` | `--analysis KEY` |
| **汎用エミッタ** | 実装済み機能のオプトイン副次出力 | `services/emitters/<key>.py`（自動発見） | `--emit KEY` |

いずれも**既定の五線譜/MIDI/PDF/TAB 出力を変えない**（オプトイン）。

## 汎用エミッタの追加（最も軽量なプラグイン）

`services/emitters/` に **1 ファイル置くだけ**でレジストリが自動発見する
（`register` の手編集は不要 ＝ 並列開発でも競合しない）。契約は
`services/emitters/base.py`:

```python
# services/emitters/myformat.py
from pathlib import Path
from earpipe.services.emitters.base import EmitContext

KEY = "myformat"          # --emit myformat のキー（一意）
EXT = "txt"               # 既定出力の拡張子
NEEDS_MUSICXML = False    # True なら -o(MusicXML) 必須
NEEDS_AUDIO = False       # True なら入力音声パス必須

def emit(ctx: EmitContext, out_path: Path) -> Path:
    # ctx.notes / ctx.bpm / ctx.title / ctx.musicxml_path / ctx.audio_path / ctx.params
    out_path.write_text("...", encoding="utf-8")
    return out_path
```

- レジストリ（`services/emitters/__init__.py`）が `pkgutil` 走査で `KEY` を持つ
  モジュールを自動登録する。`KEY` 重複・必須入力欠如は明示的に失敗（黙って握りつぶさない）。
- パラメータは `--emit myformat#level=0.5` の形で渡り、`ctx.param_float("level", 0.5)` 等で取得。

## 到達性の保証（偽成功の防止）

出力プラグインは実装しただけでは意味がない（`root-cause-analysis.md`「ユニット緑≠製品反映」）。
本リポジトリは **孤立エクスポート検査ゲート**（`scripts/check_orphan_exports.py`・CI 常設・#111）で、
`__all__` にあるのに実採譜フローから到達不能な機能を機械検出する。`emitters/*.py` は
レジストリが実行時に全 import するため、ゲートはこのディレクトリを到達性の起点として扱う
（新エミッタは手編集なしで「配線済み」判定になる）。

> **設計原則:** 出力形式の追加は「コア改修」ではなく「プラグイン追加」。
> 差し替え可能性（NF-045）と、実装＝到達の保証（#109/#111）を両立させる。
