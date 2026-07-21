"""汎用エミッタの契約(#109 B-2 結線基盤)。

孤立した実装済み機能(docs/debug/root-cause-analysis.md)を、実採譜フローへ
**衝突なく並列に**結線するための最小契約。各機能は `emitters/<key>.py` に
独立した1ファイルとして置かれ(互いに素なパス=並列生成で競合しない)、
`KEY` を持つことでレジストリに自動発見される(__init__.py の register 手編集不要)。

エミッタは transcribe の中間物(EmitContext)から **副次成果物を1ファイル生成する**
純粋な出力口。既定の五線譜/MIDI/PDF/TAB 出力は一切変えない(オプトイン。
既存挙動不変)。これにより「実装済みだが未到達」の機能を、本体記譜を壊さずに
CLI から到達可能・スモーク可能にする。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from earpipe.contracts import QuantizedNote


@dataclass(frozen=True)
class EmitContext:
    """採譜中間物。各エミッタはここから必要な材料だけ取り出す。

    Attributes:
        notes: 量子化済みノート列(旋律順は list 順を信頼)。
        bpm: 推定テンポ。
        title: 譜面タイトル(メタデータ用)。
        musicxml_path: MusicXML 出力先(-o 指定時)。musicxml を要する機能が使う。
        audio_path: 入力音声パス。生波形を要する機能(音質診断等)が自分で load する。
        params: エミッタ固有の調整値(例 {"semitones": 2, "level": 0.5})。
            CLI からは --emit KEY:name=value... で渡す(base の parse_params 参照)。
    """

    notes: list[QuantizedNote]
    bpm: float
    title: str
    musicxml_path: Path | None = None
    audio_path: Path | None = None
    params: dict[str, str] = field(default_factory=dict)

    def param_int(self, name: str, default: int) -> int:
        raw = self.params.get(name)
        return default if raw is None else int(raw)

    def param_float(self, name: str, default: float) -> float:
        raw = self.params.get(name)
        return default if raw is None else float(raw)

    def param_str(self, name: str, default: str) -> str:
        return self.params.get(name, default)

    def param_bool(self, name: str, default: bool) -> bool:
        raw = self.params.get(name)
        if raw is None:
            return default
        return raw.strip().lower() in ("1", "true", "yes", "on")


@runtime_checkable
class Emitter(Protocol):
    """エミッタモジュールが満たす公開インターフェース(構造的型)。

    モジュールレベルで KEY / EXT を定義し、emit() を実装する。
    NEEDS_MUSICXML / NEEDS_AUDIO が True の場合、対応する入力が無いとき
    レジストリ側で ValueError(握りつぶさず正直に失敗)。
    """

    KEY: str
    EXT: str
    NEEDS_MUSICXML: bool
    NEEDS_AUDIO: bool

    def emit(self, ctx: EmitContext, out_path: Path) -> Path: ...
