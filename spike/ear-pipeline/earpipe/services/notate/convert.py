"""F-037 記譜形式の相互変換ファサード(Issue #85)。

五線(QuantizedNote列)を起点に、簡譜(jianpu)テキスト・ギターTABフレット割当へ
一方向変換し、TABフレット割当から五線(QuantizedNote列)へ再構築する薄い変換層。

本モジュールは新規ロジックを持たず、既存の実装層(jianpu.to_jianpu /
tab.assign_frets)へ委譲するファサードである。tab_to_staff のみ TabNote から
MIDI を復元する逆写像を担う(これは既存層に無い純粋な情報復元であり、
チューニング開放弦MIDI + フレット + オクターブ移動から一意に音高が定まる)。

可逆性の保証範囲(先行研究 F-037-grok.md の段階的可逆性を反映):
- 五線 → 簡譜(staff_to_jianpu): **不可逆**。簡譜は主音相対の階名(do=1)であり、
  絶対音高・調号方向・弦フレット・多声レイアウトを保持しない。復路は「再記譜」で
  あって往復復元ではない(研究 3.1 表: 简谱は string/fret/絶対音高が ×)。
  よって jianpu → staff の関数は本モジュールでは提供しない。
- 五線 ⇄ TAB(staff_to_tab_frets / tab_to_staff): **音高・リズムのみ半可逆**。
  往路 staff→tab では (a) 同時7音以上の切り捨て、(b) 音域外のオクターブ移動
  (octave_shift)、(c) どのポジションにも載らない音のドロップ が起こりうる
  (tab.assign_frets の仕様・F-076制約)。復路 tab→staff は octave_shift を
  打ち消して元の音高を復元するが、ドロップされた音は戻らない(情報欠落)。
  さらに tab→staff→tab を再度回しても、同一音高に複数の弦フレット解があるため
  弦・フレット選択は一致する保証がない(研究 3.1「同一音高に複数の弦フレット解」)。

先行研究から反映した堅牢化(pitfalls対策):
- 黙って壊れない: ドロップ等の情報欠落は呼び出し側が件数を検知できるよう、
  変換は入力・出力の対応を破壊しない(研究 9-5「何が落ちたかのレポート」)。
  本ファサードは委譲先の戻り値をそのまま返し、件数の齟齬を隠さない。
- pitch-first 交換で TAB 属性が落ちる問題(研究 1.3): tab_to_staff は
  QuantizedNote(音高・リズムのみ)へ写すため弦・フレット情報は意図的に捨てる。
  これは「五線は音高の真実、TABは運指の真実」という非対称を明示するための割り切り。
- 空入力・縮退入力で例外を出さない(全関数が空列に対し空列/空文字を返す)。
"""

from __future__ import annotations

from collections.abc import Sequence

from earpipe.contracts import QuantizedNote
from earpipe.services.notate.jianpu import to_jianpu
from earpipe.services.notate.tab import TUNING_GUITAR, TabNote, assign_frets


def staff_to_jianpu(notes: Sequence[QuantizedNote], key_tonic_pc: int) -> str:
    """五線(QuantizedNote列)を簡譜(数字譜)テキスト近似の1行に変換する。

    実装は jianpu.to_jianpu に委譲する薄いファサード。主音のピッチクラスを
    唯一の真実として各音を音度 1-7 へ写す。

    Args:
        notes: 量子化済み音符列。空列なら "" を返す。
        key_tonic_pc: 主音のピッチクラス(0-11)。委譲先で % 12 に正規化される。

    Returns:
        簡譜トークンを半角空白で連結した1行文字列。入力が空なら空文字列。

    Notes:
        **不可逆**。簡譜は主音相対の階名であり、絶対音高・調号方向・弦フレット・
        多声レイアウトを保持しない。逆変換(簡譜→五線)は往復復元にならないため
        本モジュールでは提供しない(モジュール docstring の可逆性保証範囲を参照)。
    """
    # to_jianpu は list を期待するため list 化する(Sequence を安全に受ける)。
    return to_jianpu(list(notes), key_tonic_pc)


def staff_to_tab_frets(
    notes: Sequence[QuantizedNote],
    tuning: Sequence[int] = TUNING_GUITAR,
) -> list[TabNote]:
    """五線(QuantizedNote列)をギターTABの弦・フレット割当(TabNote列)に変換する。

    実装は tab.assign_frets に委譲する。手の移動最小化DPで弦・フレットを決める。

    Args:
        notes: 量子化済み音符列。空列なら空リストを返す。
        tuning: 開放弦MIDIの並び(低音弦→高音弦)。既定は標準6弦 EADGBE。
            **現状の割当エンジン(assign_frets)は標準6弦チューニング固定**であり、
            非標準チューニングは受理するが割当は標準6弦として計算される(限界)。
            将来 assign_frets が tuning を引数化した際にこの引数を委譲する。

    Returns:
        TabNote(弦index・フレット・オクターブ移動量)のリスト。

    Notes:
        **半可逆(音高・リズムのみ)**。同時7音以上の切り捨て・音域外のオクターブ移動・
        載らない音のドロップが起こりうる(F-076制約)。ドロップ件数は
        len(notes) と戻り値長の差から検知できる(黙って壊れない設計)。
    """
    # tuning は将来の割当エンジン差し替え用の予約引数。現行 assign_frets は
    # 標準6弦固定のため、非標準 tuning が渡された場合でも標準6弦で割り当てる。
    # ここで握りつぶさず、呼び出し側が把握できるよう戻り値はそのまま返す。
    del tuning  # 現行エンジンは未使用(将来委譲予定)。lint 明示のため明記。
    return assign_frets(notes)


def tab_to_staff(
    frets: Sequence[TabNote],
    tuning: Sequence[int] = TUNING_GUITAR,
) -> list[QuantizedNote]:
    """ギターTAB(TabNote列)を五線(QuantizedNote列)へ再構築する。

    各 TabNote の音高を「開放弦MIDI + フレット」で復元し、往路で加えられた
    オクターブ移動(octave_shift)を打ち消して元の音高へ戻す。弦・フレットという
    運指情報は五線には存在しないため意図的に捨てる。

    音高復元式: midi = tuning[string_index] + fret - 12 * octave_shift
    (octave_shift は往路で「音域に収めるため上げた/下げた」量。+上げ/-下げなので、
     逆変換では同じ量だけ戻すために減算する。)

    Args:
        frets: TabNote列。空列なら空リストを返す。
        tuning: 開放弦MIDIの並び。TabNote.string_index はこの並びの添字を指す。
            既定は標準6弦 EADGBE(assign_frets が用いるチューニングと一致)。

    Returns:
        QuantizedNote(音高・拍タイミングのみ)のリスト。confidence は TabNote から
        引き継ぐ。実側 onset/offset は情報が無いため既定 NaN のまま。

    Raises:
        IndexError: string_index が tuning の範囲外のとき(不正な入力を黙って
            破棄せず表面化させる。研究 1.7「黙って壊れる」を避ける)。

    Notes:
        **音高・リズムのみ復元**。tab→staff→tab を再度回しても弦・フレット選択が
        一致する保証はない(同一音高に複数の弦フレット解があるため)。復元後の
        音高はスペリング(異名同音)を持たない生の MIDI であり、綴りは別途
        spelling.spell_midi 等で調文脈から与える必要がある。
    """
    tuning_list = list(tuning)
    out: list[QuantizedNote] = []
    for t in frets:
        # 範囲外 string_index は黙って捨てず IndexError を表面化させる。
        open_midi = tuning_list[t.string_index]
        midi = open_midi + t.fret - 12 * t.octave_shift
        out.append(
            QuantizedNote(
                start_beats=t.start_beats,
                dur_beats=t.dur_beats,
                midi=midi,
                confidence=t.confidence,
            )
        )
    return out
