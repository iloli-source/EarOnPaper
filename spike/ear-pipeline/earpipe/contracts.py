"""契約IF: サービス間で受け渡す型付き入出力スキーマ(ADR-001)。

全サービスはここで定義された不変(frozen)データ型のみを介して通信する。
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PitchEvent:
    """音程イベント: いつからいつまで、どの高さ(MIDIノート番号)が、どれくらい確かか。"""

    onset: float       # 開始秒
    offset: float      # 終了秒
    midi: int          # MIDIノート番号(60=中央のド)
    confidence: float  # 0-1


@dataclass(frozen=True)
class QuantizedNote:
    """量子化済み音符の二重表現(C3・Issue #38)。

    - 格子側: start_beats/dur_beats(四分音符=1.0 の拍単位)。譜面表示・MusicXML用
    - 実側: onset_sec/offset_sec(元イベントの実タイミング秒)。評価・rawエクスポート用

    背景: PD15曲実測で格子スナップが音符を正解タイミングから引き剥がすことを確認
    (results-pd.md)。格子は「楽譜にするため」の表現であり、データとしての
    実タイミングを破壊してはならない。旧4引数構築との互換のため実側は既定NaN。

    注意(レビュー#40 L1): NaN != NaN のため、実側が未設定(NaN)同士の
    インスタンスは他フィールドが同一でも == で等しくならない。同一性判定は
    (start_beats, midi) 等の格子側キーで行うこと(quantizeのdedupはこの方式)。
    """

    start_beats: float
    dur_beats: float
    midi: int
    confidence: float
    onset_sec: float = float("nan")
    offset_sec: float = float("nan")


@dataclass(frozen=True)
class FieldReport:
    """フィールド録音の分析報告: 抽出しなかった成分も含めて正直に分類する(C8)。

    比率は入力エネルギーに対する概算(HPSS+スペクトル平坦度によるヒューリスティック)。
    """

    snr_db: float           # 推定SNR(内部プロキシ値)。大きいほどクリーン
    noise_profile: Literal["clean", "noisy", "very_noisy"]  # レビュー#40 L2: 型で値域を固定
    harmonic_ratio: float   # 音程を持ちうる成分の比率
    percussive_ratio: float  # 打撃様(非音程)成分の比率
    noise_like_ratio: float  # ノイズ様成分の比率
