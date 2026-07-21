"""記譜層: 手直し済み拍グリッド＋音符を可搬JSONで往復させる中間資産I/O(F-096・Issue #98)。

目的: 手直し(量子化・グリッド校正)に時間をかけた「拍グリッド＋音符」を、
プロジェクト固有形式に閉じ込めず、別プロジェクト・別DAW・別記譜ソフトへ
持ち出せる素直なJSONで保存/復元する。export_asset で書き出し、import_asset で
読み戻すと、往復(round-trip)で音符とテンポ情報が不変であることを保証する。

先行研究(docs/research/upcoming/F-096-grok.md)の失敗モードを反映して堅牢化:

1. 固定BPMデフォルト落ち(特に120): AI転写MIDIやMusicXMLを別プロジェクトへ
   持ち込むと BPM が失われ 120 に落ちる事故が繰り返される(@whatdotcd, @DJ_OMKT)。
   → bpm を JSON の第一級フィールドとして必ず明示保存し、読み戻し時に検証する。
   欠落・不正値を黙って 120 で埋めない(投げる)。
2. tick vs 実時間の単位不一致(失敗カタログ#8): グリッド解像度を暗黙にすると
   拍位置の解釈が受け側でズレる。→ grid_per_beat(1拍あたり分割数)を明示保存する。
3. 拍グリッドは音より壊れやすい / 累積誤差の不可逆性(@miumcii): 手直しグリッドを
   別形式へ変換するとテンポや拍位置が壊れる。→ MIDI/MusicXML を経由せず、
   QuantizedNote のフィールドを損失なく(格子側 start_beats/dur_beats と
   実側 onset_sec/offset_sec の C3二重表現を両方)そのまま JSON 化する。
4. round-trip 保証(@kennethreitz42 PyTheory の "tempo maps now round-trip"):
   export→import で list[QuantizedNote]・bpm・grid_per_beat が元と一致することを
   受入条件とする(test_asset_io.py の往復不変テスト)。

移植不整合の注記(正直な限界):
- 実側(onset_sec/offset_sec)は既定 NaN を取り得る(C3二重表現・旧4引数互換)。
  JSON は NaN を素直に表現できないため null で書き、読み戻しで float("nan") に
  復元する。よって NaN 同士は == で等しくならない(contracts.py の注意書きどおり)。
  往復不変テストは NaN を個別に math.isnan で照合し、格子側キーで同一性を判定する。
- 本形式は EarPipe 内部の可搬中間資産(IR)であり、MIDI/MusicXML そのものではない。
  DAW/記譜ソフトへ渡す際は別途 write_midi/write_musicxml を用いる(用途別に形式を
  分ける原則: 演奏=MIDI・記譜=MusicXML・手直し資産の往復=本JSON)。
- テンポは単一 bpm のみを持ち、可変テンポマップ(テンポチェンジ列)は本バージョンの
  対象外(要件は「手直し済み拍グリッド・音符の往復」)。可変テンポは将来拡張。
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from earpipe.contracts import QuantizedNote

# JSONスキーマの版。将来の破壊的変更を検出できるよう先頭に埋める。
SCHEMA_VERSION: int = 1
# スキーマ識別子(他のEarPipe JSONと取り違えないための署名)。
_SCHEMA_NAME: str = "earpipe.asset_io"
# grid_per_beat の下限(1拍を最低1分割=四分音符解像度)。0や負は不正。
_MIN_GRID_PER_BEAT: int = 1


def _note_to_dict(note: QuantizedNote) -> dict[str, Any]:
    """QuantizedNote を JSON 化可能な dict にする(NaN の実側は null で書く)。

    格子側(start_beats/dur_beats/midi/confidence)は必ず数値。実側
    (onset_sec/offset_sec)は NaN を取り得るため、NaN は null に落とす
    (JSON は NaN を標準表現できない。allow_nan=False で書けるようにする)。
    """
    return {
        "start_beats": float(note.start_beats),
        "dur_beats": float(note.dur_beats),
        "midi": int(note.midi),
        "confidence": float(note.confidence),
        "onset_sec": _sec_to_json(note.onset_sec),
        "offset_sec": _sec_to_json(note.offset_sec),
    }


def _sec_to_json(value: float) -> float | None:
    """実タイミング秒を JSON 値へ。NaN は null(None)にして round-trip 可能にする。"""
    fvalue = float(value)
    return None if math.isnan(fvalue) else fvalue


def _sec_from_json(value: Any) -> float:
    """JSON の実タイミング秒を float へ。null は NaN に復元(C3二重表現の未設定)。"""
    if value is None:
        return float("nan")
    return float(value)


def _note_from_dict(raw: dict[str, Any]) -> QuantizedNote:
    """dict を QuantizedNote に復元する。必須の格子側キー欠落は KeyError で弾く。

    実側(onset_sec/offset_sec)は任意(欠落時は NaN)。値の存在は信頼せず
    入力境界として検証し、格子側が欠ければ黙って 0 埋めせず例外にする。
    """
    return QuantizedNote(
        start_beats=float(raw["start_beats"]),
        dur_beats=float(raw["dur_beats"]),
        midi=int(raw["midi"]),
        confidence=float(raw["confidence"]),
        onset_sec=_sec_from_json(raw.get("onset_sec")),
        offset_sec=_sec_from_json(raw.get("offset_sec")),
    )


def export_asset(
    notes: list[QuantizedNote],
    bpm: float,
    grid_per_beat: int,
    path: str | Path,
) -> Path:
    """手直し済み拍グリッド＋音符を可搬JSONへ書き出す(F-096)。

    テンポ(bpm)と拍グリッド解像度(grid_per_beat)を第一級フィールドとして
    明示保存し、音符は QuantizedNote の格子側・実側フィールドを損失なく JSON 化する。
    これにより import_asset で往復不変(音符・bpm・grid_per_beat が一致)を保証する。

    Args:
        notes: 量子化済み音符列。空リストも可(ヘッダのみの空資産)。
        bpm: テンポ(1分あたり拍数)。有限の正値のみ許可。研究の「BPM 120 落ち」
            事故を防ぐため、必ず明示保存する(欠落・不正は書かず ValueError)。
        grid_per_beat: 1拍あたりのグリッド分割数(例: 4 なら16分音符解像度)。
            tick と実時間の単位不一致を避けるため明示保存する。1 以上の整数のみ。
        path: 書き出し先パス(文字列または Path)。親ディレクトリは存在前提。

    Returns:
        書き出したファイルの Path。

    Raises:
        ValueError: bpm が非有限・非正、または grid_per_beat が 1 未満のとき。
    """
    _validate_bpm(bpm)
    _validate_grid_per_beat(grid_per_beat)

    payload: dict[str, Any] = {
        "schema": _SCHEMA_NAME,
        "version": SCHEMA_VERSION,
        "bpm": float(bpm),
        "grid_per_beat": int(grid_per_beat),
        "notes": [_note_to_dict(n) for n in notes],
    }

    out_path = Path(path)
    # allow_nan=False: NaN を書けない標準JSONに固定(実側は既に null 化済み)。
    text = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2)
    out_path.write_text(text, encoding="utf-8")
    return out_path


def import_asset(path: str | Path) -> tuple[list[QuantizedNote], float, int]:
    """可搬JSONから手直し済み拍グリッド＋音符を読み戻す(F-096)。

    export_asset の出力を損失なく復元し、(音符列, bpm, grid_per_beat) を返す。
    往復不変を保証するため、格子側フィールドの欠落・不正なメタ情報は黙って
    補正せず例外にする(研究の「BPM 120 落ち」を境界検証で防ぐ)。

    Args:
        path: 読み込むJSONファイルのパス(文字列または Path)。

    Returns:
        (notes, bpm, grid_per_beat) のタプル。export_asset に渡した値と一致する
        (実側 NaN は NaN のまま復元。NaN 同士は == で等しくならない点に注意)。

    Raises:
        ValueError: スキーマ署名/版が不一致、または bpm・grid_per_beat が
            欠落・不正なとき。
        KeyError: 音符の必須格子側キー(start_beats 等)が欠落しているとき。
        json.JSONDecodeError: ファイルが妥当なJSONでないとき。
    """
    in_path = Path(path)
    payload = json.loads(in_path.read_text(encoding="utf-8"))

    _validate_schema(payload)

    if "bpm" not in payload:
        raise ValueError("bpm フィールドが欠落(研究: BPM 欠落の 120 落ちを防ぐため必須)")
    bpm = float(payload["bpm"])
    _validate_bpm(bpm)

    if "grid_per_beat" not in payload:
        raise ValueError("grid_per_beat フィールドが欠落(拍グリッド解像度は必須)")
    grid_per_beat = int(payload["grid_per_beat"])
    _validate_grid_per_beat(grid_per_beat)

    raw_notes = payload.get("notes", [])
    if not isinstance(raw_notes, list):
        raise ValueError("notes フィールドはリストである必要がある")
    notes = [_note_from_dict(raw) for raw in raw_notes]

    return notes, bpm, grid_per_beat


def _validate_schema(payload: Any) -> None:
    """スキーマ署名と版を検証する(他のEarPipe JSONとの取り違えを防ぐ)。"""
    if not isinstance(payload, dict):
        raise ValueError("JSON ルートはオブジェクトである必要がある")
    if payload.get("schema") != _SCHEMA_NAME:
        raise ValueError(
            f"スキーマ署名が不一致(期待={_SCHEMA_NAME!r}, 実際={payload.get('schema')!r})"
        )
    if payload.get("version") != SCHEMA_VERSION:
        raise ValueError(
            f"スキーマ版が非対応(期待={SCHEMA_VERSION}, 実際={payload.get('version')!r})"
        )


def _validate_bpm(bpm: float) -> None:
    """bpm が有限の正値であることを検証する(NaN/inf/0/負を弾く)。"""
    fbpm = float(bpm)
    if not math.isfinite(fbpm) or fbpm <= 0.0:
        raise ValueError(f"bpm は有限の正値である必要がある(実際={bpm!r})")


def _validate_grid_per_beat(grid_per_beat: int) -> None:
    """grid_per_beat が 1 以上の整数であることを検証する(単位不一致を防ぐ)。"""
    if int(grid_per_beat) < _MIN_GRID_PER_BEAT:
        raise ValueError(
            f"grid_per_beat は {_MIN_GRID_PER_BEAT} 以上である必要がある(実際={grid_per_beat!r})"
        )
