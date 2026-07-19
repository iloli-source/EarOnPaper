"""契約IF: サービス間で受け渡す型付き入出力スキーマ(ADR-001)。

全サービスはここで定義された不変(frozen)データ型のみを介して通信する。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PitchEvent:
    """音程イベント: いつからいつまで、どの高さ(MIDIノート番号)が、どれくらい確かか。"""

    onset: float       # 開始秒
    offset: float      # 終了秒
    midi: int          # MIDIノート番号(60=中央のド)
    confidence: float  # 0-1


@dataclass(frozen=True)
class QuantizedNote:
    """拍格子に量子化された音符。start/dur は四分音符=1.0 の拍単位。"""

    start_beats: float
    dur_beats: float
    midi: int
    confidence: float
