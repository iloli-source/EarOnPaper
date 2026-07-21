"""楽器プロファイル（弦数・音域制約・チューニング）— TAB生成の探索空間定義層。

F-079 / Issue #90。NF-045「出力プロファイル層」の一部として、TAB生成の前段で
弦割当の候補空間そのものを固定する。研究(F-079-grok / F-079-codex)の合意点は明快:

    「TAB品質は音の正しさではなく、どの楽器プロファイルでどの弦へ割るかで決まる。」
    「instrument profile は表示設定ではなく hard constraints（探索空間の定義）である。」

このモジュールは各楽器の開放弦(低→高のMIDI)・最大フレット・和名を frozen dataclass で
保持し、音高列を「この楽器で演奏可能か」で分類する。tab.py の assign_frets と同一の
候補モデル ``pitch == open_midi[string] + fret`` (0 <= fret <= fret_max) に従うため、
プロファイルを差し替えるだけで既存の弦割当DPをそのまま別楽器へ適用できる。

研究が繰り返し挙げた失敗例と、その回避方針(本実装での対応):

- 弦数/音域プロファイル不一致（5弦原曲を4弦へ暗黙ダウンチューン、high C 無しで不能）
  → 弦数と音域を「情報」でなく「制約」として持つ。bass4 と bass5 を別プロファイルに
    分離し、暗黙の弦数変換をしない。fit_to_profile は音域外を黙って丸めず
    out_of_range に理由付きで分類して返す（F-079-codex「不可能音を黙って丸めない」）。

- 低域境界の欠落（標準6弦 E2=40 前提のパイプラインが 7弦B1・5弦ベースB0 を落とす）
  → 各プロファイルに実際の最低開放弦MIDIを持たせ、lowest_open_midi で明示。
    テストで guitar7 の低B1(35)・bass5 の低B0(23) が in_range になることを検証する。

- 弦順反転（低→高 と 高→低 の取り違えで図は正しそうに見えて別楽器）
  → strings は必ず「低→高（各弦の開放MIDIが昇順）」で保持し、構築時に検証する。
    tab.py の TUNING_GUITAR=(40,45,50,55,59,64) と同じ並び。

- 調弦を変えずに標準フレットで近似する妥協（最悪のTABを生む）
  → Drop D / baritone を独立プロファイルとして持ち、標準の使い回しを強制しない。

- 多重写像で音は合うが弾けない（同一音高が複数の(string,fret)へ写る）
  → fit_to_profile は演奏可能性(=候補が1つ以上あるか)のみ判定し、最終的な弦割当
    (span/ポジション連続などの soft cost 最適化)は tab.py の DP へ委譲する。責務分離。

原理的限界(notes): 本モジュールは「音域内か」までしか保証しない。同時発音数が弦数を
超える和音や、物理的な運指スパン制約は assign_frets 側の責務であり、ここでは扱わない。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from earpipe.contracts import QuantizedNote

# 半音数（オクターブ）。マジックナンバー回避。
_SEMITONES_PER_OCTAVE = 12


@dataclass(frozen=True)
class InstrumentProfile:
    """1つの撥弦楽器の演奏可能空間を定義する不変プロファイル。

    Attributes:
        name: プロファイル識別子（英小文字・PROFILES のキー。例 "guitar6"）。
        strings: 各弦の開放弦MIDI番号を「低→高」で並べたタプル。
            必ず開放MIDIが昇順（strings[i] <= strings[i+1]）であること。
            例: 6弦標準EADGBE = (40, 45, 50, 55, 59, 64)。
        fret_max: 最大フレット番号（0=開放。この値まで押弦可能）。
        name_ja: 表示用の日本語名（例 "ギター6弦(標準EADGBE)"）。
    """

    name: str
    strings: tuple[int, ...]
    fret_max: int
    name_ja: str

    def __post_init__(self) -> None:
        """構築時にプロファイルの整合性を検証する（不正なプロファイルを早期に弾く）。"""
        if not self.strings:
            raise ValueError(f"strings が空です: {self.name}")
        if self.fret_max < 0:
            raise ValueError(f"fret_max は0以上である必要があります: {self.fret_max}")
        # 弦順反転の失敗（研究3.8/左手図の逆順）を構造的に防ぐ: 低→高の昇順を強制。
        if any(a > b for a, b in zip(self.strings, self.strings[1:])):
            raise ValueError(
                f"strings は低→高（開放MIDI昇順）で指定してください: {self.strings}"
            )

    @property
    def string_count(self) -> int:
        """弦数。"""
        return len(self.strings)

    @property
    def lowest_open_midi(self) -> int:
        """最低開放弦のMIDI（演奏可能音域の下限）。"""
        return self.strings[0]

    @property
    def highest_midi(self) -> int:
        """演奏可能音域の上限MIDI（最高弦の最大フレット）。"""
        return self.strings[-1] + self.fret_max

    def candidates(self, midi: int) -> list[tuple[int, int]]:
        """音高 midi を弾ける (string_index, fret) 候補を全列挙する。

        tab.py._candidates と同一モデル（pitch == open_midi + fret,
        0 <= fret <= fret_max）。string_index は 0=最低弦。

        Args:
            midi: 対象のMIDI番号。

        Returns:
            演奏可能な (string_index, fret) のリスト。演奏不能なら空リスト。
        """
        out: list[tuple[int, int]] = []
        for si, open_midi in enumerate(self.strings):
            fret = midi - open_midi
            if 0 <= fret <= self.fret_max:
                out.append((si, fret))
        return out

    def is_playable(self, midi: int) -> bool:
        """音高 midi がこの楽器で（オクターブ移動なしに）演奏可能か。"""
        return bool(self.candidates(midi))

    def octave_folds_to_range(self, midi: int) -> int:
        """音域内に収めるのに必要なオクターブ移動数を返す（+上げ/-下げ、0=不要）。

        音域外の音を「暗黙にダウンチューン/丸め」せず、必要な移動量を数値で正直に返す
        （F-079-codex: octave-shift は提案として明示する）。実際に音を動かすのは
        呼び出し側の判断に委ねる（本メソッドは移動量の算出のみ）。
        """
        lo, hi = self.lowest_open_midi, self.highest_midi
        if midi < lo:
            return (lo - midi + (_SEMITONES_PER_OCTAVE - 1)) // _SEMITONES_PER_OCTAVE
        if midi > hi:
            return -((midi - hi + (_SEMITONES_PER_OCTAVE - 1)) // _SEMITONES_PER_OCTAVE)
        return 0


# 標準チューニング（すべて低→高のMIDI番号）。
# guitar6 は tab.py.TUNING_GUITAR と一致（40,45,50,55,59,64）。
PROFILES: dict[str, InstrumentProfile] = {
    "guitar6": InstrumentProfile(
        name="guitar6",
        strings=(40, 45, 50, 55, 59, 64),  # E2 A2 D3 G3 B3 E4
        fret_max=19,
        name_ja="ギター6弦(標準EADGBE)",
    ),
    "guitar7": InstrumentProfile(
        name="guitar7",
        strings=(35, 40, 45, 50, 55, 59, 64),  # B1 E2 A2 D3 G3 B3 E4
        fret_max=19,
        name_ja="ギター7弦(標準B-EADGBE)",
    ),
    "guitar_dropd": InstrumentProfile(
        name="guitar_dropd",
        strings=(38, 45, 50, 55, 59, 64),  # D2 A2 D3 G3 B3 E4
        fret_max=19,
        name_ja="ギター6弦(ドロップD)",
    ),
    "bass4": InstrumentProfile(
        name="bass4",
        strings=(28, 33, 38, 43),  # E1 A1 D2 G2
        fret_max=24,
        name_ja="ベース4弦(標準EADG)",
    ),
    "bass5": InstrumentProfile(
        name="bass5",
        strings=(23, 28, 33, 38, 43),  # B0 E1 A1 D2 G2
        fret_max=24,
        name_ja="ベース5弦(標準B-EADG)",
    ),
    "baritone": InstrumentProfile(
        name="baritone",
        strings=(35, 40, 45, 50, 54, 59),  # B1 E2 A2 D3 F#3 B3 (B standard)
        fret_max=19,
        name_ja="バリトンギター(Bスタンダード)",
    ),
}

# guitar6 を tab.py と同一定義に保つための自己検証（不変条件のドキュメント兼テスト保険）。
assert PROFILES["guitar6"].strings == (40, 45, 50, 55, 59, 64)


@dataclass(frozen=True)
class FitResult:
    """fit_to_profile の結果。採用可能音と音域外音を理由付きで分離して保持する。

    音域外を黙って丸めない（研究の一致した推奨）。out_of_range には
    octave_shift_suggested を添え、UI/後段が「オクターブ移動」「弦数拡張の提案」
    「破棄」のどれを選ぶかを判断できるようにする。

    Attributes:
        profile: 適用したプロファイル。
        in_range: この楽器でそのまま演奏可能な音符（QuantizedNote のまま保持）。
        out_of_range: 音域外の音符と、収めるのに必要なオクターブ移動数の対。
            (note, octave_shift_suggested)。octave_shift_suggested は
            +で上げ/-で下げ（必ず非ゼロ）。
    """

    profile: InstrumentProfile
    in_range: tuple[QuantizedNote, ...]
    out_of_range: tuple[tuple[QuantizedNote, int], ...]

    @property
    def n_in_range(self) -> int:
        """演奏可能音の数。"""
        return len(self.in_range)

    @property
    def n_out_of_range(self) -> int:
        """音域外音の数。"""
        return len(self.out_of_range)


def get_profile(name: str) -> InstrumentProfile:
    """名前でプロファイルを取得する。未知名は利用可能名を添えて弾く。

    Args:
        name: PROFILES のキー。

    Returns:
        対応する InstrumentProfile。

    Raises:
        KeyError: 未知のプロファイル名（システム境界での入力検証）。
    """
    try:
        return PROFILES[name]
    except KeyError as exc:
        available = ", ".join(sorted(PROFILES))
        raise KeyError(
            f"未知のプロファイル '{name}'。利用可能: {available}"
        ) from exc


def fit_to_profile(
    notes: Sequence[QuantizedNote],
    profile: InstrumentProfile,
) -> FitResult:
    """音高列をプロファイルに照らし「演奏可能」「音域外」に分類する。

    音域外の音は破棄も丸めもせず、収めるのに必要なオクターブ移動数を添えて
    out_of_range に返す（呼び出し側が octave-shift / 弦数拡張 / 破棄を選べる）。
    実際の弦・フレット割当（ポジション連続・運指スパン最適化）は行わない。
    それは tab.py.assign_frets（DP）の責務であり、本関数は探索空間への適合判定のみ担う。

    Args:
        notes: 分類対象の量子化音符列。
        profile: 適用する楽器プロファイル。

    Returns:
        FitResult（in_range / out_of_range を保持）。
    """
    in_range: list[QuantizedNote] = []
    out_of_range: list[tuple[QuantizedNote, int]] = []
    for note in notes:
        if profile.is_playable(note.midi):
            in_range.append(note)
        else:
            shift = profile.octave_folds_to_range(note.midi)
            out_of_range.append((note, shift))
    return FitResult(
        profile=profile,
        in_range=tuple(in_range),
        out_of_range=tuple(out_of_range),
    )
