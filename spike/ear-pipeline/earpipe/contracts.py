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


@dataclass(frozen=True)
class FieldReport:
    """フィールド録音の分析報告: 抽出しなかった成分も含めて正直に分類する(C8)。

    比率は入力エネルギーに対する概算(HPSS+スペクトル平坦度によるヒューリスティック)。
    """

    snr_db: float           # 推定SNR(dB)。大きいほどクリーン
    noise_profile: str      # "clean" / "noisy" / "very_noisy"
    harmonic_ratio: float   # 音程を持ちうる成分の比率
    percussive_ratio: float  # 打撃様(非音程)成分の比率
    noise_like_ratio: float  # ノイズ様成分の比率
