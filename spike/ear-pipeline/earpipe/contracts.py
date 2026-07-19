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


# F-108: フィールド録音モードの音事件分類タグ(要件v2.7の6種)。
# pitched_stable/pitched_transient は音符化対象、
# noisy/inharmonic は音符化せず音響オブジェクトとして保持、
# speech は声(採譜対象外)、poly は和音(オンデマンド分解)。
SoundClass = Literal[
    "pitched_stable",     # 安定した音程(持続音・単音の主対象)
    "pitched_transient",  # 音程はあるが極短(撥弦アタック等)
    "noisy",              # 広帯域雑音(雨・ヒス。音符化しない)
    "speech",             # 声・発話(採譜対象外)
    "poly",               # 多声(和音。オンデマンドで分解)
    "inharmonic",         # 非調波(金属打・ノック。音符化しない)
]

# 音符化を許す分類タグ。noisy/inharmonic/speech は音響オブジェクトとして保持し
# 五線化しない(F-108受入条件(1): 「拾えないものは拾えないと正直に言う」)。
NOTABLE_CLASSES: frozenset[str] = frozenset({"pitched_stable", "pitched_transient", "poly"})


@dataclass(frozen=True)
class SoundEvent:
    """音事件の分類結果(F-108・C8)。

    音程を持つ成分だけを選択的に音符化するための前段判定。
    分類はHPSS+スペクトル平坦度+調波性ヒューリスティックであり、
    speech の識別は「有声だが調波ピークが不安定」という粗い代理であって
    ASR相当ではない(限界はclassify_segmentのdocstringに明記)。
    """

    label: SoundClass
    confidence: float       # 0-1: 分類の確からしさ(最有力クラスのスコア)
    is_notable: bool        # 音符化を許すか(label in NOTABLE_CLASSES)
