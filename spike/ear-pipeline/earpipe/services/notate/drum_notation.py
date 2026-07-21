"""ドラム譜の記譜(F-036 / Issue #89): detect_drums 出力 → MusicXML。

detect_drums(ear/drums.py)が返す打点列(onset_sec, kit, confidence)を、
percussion clef(中立譜号) + unpitched note へ記譜し MusicXML 文字列を返す。
描画そのものは別モジュール(engrave.py の Verovio スタック)に委ねる。

先行研究(docs/research/upcoming/F-036-{grok,codex}.md)で洗い出された罠を
反映した設計:

1. **off-by-one(最大の地雷)**: MusicXML の `<midi-unpitched>` は 1-based
   (1..128)。GM percussion note(0-based, 例: Kick=36)をそのまま入れると
   全打楽器が半音1つ下の別楽器に化ける。変換は単一関数
   `gm_note_to_musicxml_unpitched()`(= n + 1)に閉じ込め、テストで固定する。
2. **kitPieceId を主キーにする**: display-step / MIDI note / notehead /
   voice のいずれも主キーにしない。kit ラベル(kick/snare/...)を第一級キーとし、
   そこから GM note・表示位置・notehead を一意に引く(_KIT_MAP)。
3. **notehead は装飾でなく音色選択**: hihat / cymbal は同じ譜線上でも
   `x`(hihat) / diamond(cymbal)で楽器を区別する(W3C tutorial 準拠)。
   正規化して潰すと音色が混線するため kit ごとに固定する。
4. **percussion clef は音高を持たない**: display-step/octave は「表示位置」で
   あり音色ではない。音色は `<midi-unpitched>` + `<instrument>` 側で持たせる。
5. **「標準ドラム譜」は絶対標準ではない**: 線位置・notehead 割当はソフト/出版で
   揺れる。ここでは W3C percussion tutorial の配置を素直な既定として採用する。

原理的限界(notes に正直に記録):
- 単一エクスポータで全記譜ソフト(MuseScore/Dorico/Finale/Sibelius)互換は
  取れない。GM を近似の共通土台として generic MusicXML を出すに留める。
- detect_drums の kit 粒度(kick/snare/hihat/tom/cymbal/unknown)は粗く、
  ride bell / side stick / rimshot / open-close HH 等は表現できない。
  未知/未対応の kit は unknown レーン(1本の中立線)へ倒し、誤った音色付けを避ける。
- MusicXML→DAW 経路では notehead/stem/voice 等の記譜情報が落ちる(SMF の限界)。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import music21
from music21 import clef, instrument, meter, stream, tempo
from music21.note import Rest, Unpitched

# --- 既定パラメータ ----------------------------------------------------------
_DEFAULT_TIME_SIGNATURE = "4/4"
_BEATS_PER_MEASURE = 4  # 4/4 固定(detect_drums はメーター情報を持たないため)
_MIN_BPM = 1.0
_MAX_BPM = 400.0  # 常識外の BPM をガード(入力検証)
_QUANTIZE_DENOM = 4  # 16分音符格子へ量子化(1拍 = 4 分割)
_MIN_QUARTER_LEN = Fraction(1, 4)  # 記譜する最小音価(16分)

# GM→MusicXML の off-by-one を吸収する単一の定数(研究の最重要ポイント)。
_MUSICXML_UNPITCHED_OFFSET = 1  # midi-unpitched(1-based) = gm_note(0-based) + 1


@dataclass(frozen=True)
class _KitPiece:
    """1つの kit 音色の記譜定義(kitPieceId を主キーとする第一級オブジェクト)。

    Attributes:
        gm_note: General MIDI percussion note(0-based, channel 10 前提)。
        display_step: 譜面上の表示位置(A-G)。音高ではなく座標(percussion clef)。
        display_octave: 表示位置のオクターブ。
        notehead: 符頭形状(音色選択。None=通常符頭)。hihat=x / cymbal=diamond。
        instrument_cls: music21 の楽器クラス(part-list の楽器名解決に使う)。
        label: 凡例・可読ラベル(日本語不要のため英語の kit 名をそのまま使う)。
    """

    gm_note: int
    display_step: str
    display_octave: int
    notehead: str | None
    instrument_cls: type[music21.instrument.Instrument]
    label: str


# kit ラベル → 記譜定義。W3C percussion tutorial の配置を素直な既定とする。
# display 位置は「treble clef 上の見た目位置」であり音高ではない点に注意。
# gm_note は 0-based の GM 値(midi-unpitched への +1 は export 時に一括変換)。
_KIT_MAP: dict[str, _KitPiece] = {
    # kick: 最下部スペース(F4)相当、通常符頭。GM 36 Bass Drum 1。
    "kick": _KitPiece(36, "F", 4, None, instrument.BassDrum, "Bass Drum"),
    # snare: 第3スペース(C5)、通常符頭。GM 38 Acoustic Snare。
    "snare": _KitPiece(38, "C", 5, None, instrument.SnareDrum, "Snare"),
    # hihat: 上部(G5)、x 符頭で cymbal と区別。GM 42 Closed Hi-Hat
    #  (研究注記: music21 HiHatCymbal の既定 44 は pedal HH。ここでは closed を採る)。
    "hihat": _KitPiece(42, "G", 5, "x", instrument.HiHatCymbal, "Hi-Hat"),
    # tom: 中央線(A4)相当、通常符頭。GM 45 Low Tom を代表として採用。
    "tom": _KitPiece(45, "A", 4, None, instrument.TomTom, "Tom"),
    # cymbal: 上部(A5)、diamond 符頭で hihat と区別。GM 49 Crash Cymbal 1。
    "cymbal": _KitPiece(49, "A", 5, "diamond", instrument.Cymbals, "Crash Cymbal"),
}

# 未知/未対応 kit を倒す先。中立の1線(B4)・通常符頭・GM値なし(音色付けしない)。
_UNKNOWN_PIECE = _KitPiece(-1, "B", 4, None, instrument.Percussion, "Unknown")

_VALID_KITS = frozenset(_KIT_MAP) | {"unknown"}


def gm_note_to_musicxml_unpitched(gm_note: int) -> int:
    """GM percussion note(0-based)→ MusicXML `<midi-unpitched>`(1-based)。

    研究で最大の地雷とされる off-by-one をここ1箇所に閉じ込める。
    MusicXML 仕様は 1..128 の 1-based、GM は 0..127 の 0-based。
    例: Kick GM 36 → 37 / Snare 38 → 39 / Closed HH 42 → 43 / Crash 49 → 50。

    Args:
        gm_note: General MIDI の打楽器ノート番号(0..127)。

    Returns:
        MusicXML `<midi-unpitched>` に入れる 1-based 値(1..128)。

    Raises:
        ValueError: gm_note が 0..127 の範囲外のとき。
    """
    if not 0 <= gm_note <= 127:
        raise ValueError(f"GM note は 0..127 の範囲: {gm_note}")
    return gm_note + _MUSICXML_UNPITCHED_OFFSET


def _validate_inputs(drum_hits: list[dict], bpm: float) -> None:
    """入力(打点列・BPM)を境界で検証する(不正データを早期に弾く)。"""
    if not isinstance(drum_hits, list):
        raise TypeError(f"drum_hits は list: {type(drum_hits).__name__}")
    if not _MIN_BPM <= float(bpm) <= _MAX_BPM:
        raise ValueError(f"bpm は {_MIN_BPM}..{_MAX_BPM} の範囲: {bpm}")
    for i, hit in enumerate(drum_hits):
        if not isinstance(hit, dict):
            raise TypeError(f"drum_hits[{i}] は dict: {type(hit).__name__}")
        if "onset_sec" not in hit or "kit" not in hit:
            raise ValueError(f"drum_hits[{i}] に onset_sec/kit が無い: {hit}")
        onset = hit["onset_sec"]
        if not isinstance(onset, (int, float)) or onset < 0:
            raise ValueError(f"drum_hits[{i}].onset_sec が不正: {onset}")


def _piece_for(kit: str) -> _KitPiece:
    """kit ラベルから記譜定義を引く(未知は unknown レーンへ倒す)。"""
    return _KIT_MAP.get(kit, _UNKNOWN_PIECE)


def _quantize_beat(onset_sec: float, sec_per_beat: float) -> Fraction:
    """打点(秒)を拍位置へ変換し 16分格子へ量子化した拍数(Fraction)を返す。"""
    raw_beats = onset_sec / sec_per_beat
    steps = round(raw_beats * _QUANTIZE_DENOM)
    return Fraction(steps, _QUANTIZE_DENOM)


def _build_unpitched(piece: _KitPiece, quarter_len: Fraction) -> Unpitched:
    """記譜定義から music21 の Unpitched 音符を1つ生成する(不変生成)。"""
    note = Unpitched(displayName=f"{piece.display_step}{piece.display_octave}")
    if piece.notehead is not None:
        note.notehead = piece.notehead
    note.storedInstrument = piece.instrument_cls()
    note.quarterLength = float(quarter_len)
    return note


def _build_part(drum_hits: list[dict], bpm: float) -> stream.Part:
    """打点列から percussion clef の Part を組み立てる。

    量子化した拍位置に各打点を offset 配置し、休符で埋めるのは music21 の
    makeNotation に委ねる(重なりは同一 offset の別音として素直に置く)。
    """
    sec_per_beat = 60.0 / bpm
    part = stream.Part()
    part.partName = "Drums"
    part.insert(0, instrument.Percussion())
    part.insert(0, clef.PercussionClef())
    part.insert(0, meter.TimeSignature(_DEFAULT_TIME_SIGNATURE))
    part.insert(0, tempo.MetronomeMark(number=float(bpm)))

    # 打点を拍位置昇順に整列(元の onset 順に依存しない安定化)。
    ordered = sorted(drum_hits, key=lambda h: float(h["onset_sec"]))
    for hit in ordered:
        beat = _quantize_beat(float(hit["onset_sec"]), sec_per_beat)
        piece = _piece_for(str(hit["kit"]))
        note = _build_unpitched(piece, _MIN_QUARTER_LEN)
        part.insert(float(beat), note)

    # 空(打点ゼロ)でも妥当なスコアにするため、1小節の全休符を最低限置く。
    if not ordered:
        part.insert(0.0, Rest(quarterLength=float(_BEATS_PER_MEASURE)))

    part.makeNotation(inPlace=True)
    return part


# --- MusicXML 後処理: <midi-unpitched> の注入 --------------------------------
# music21 v10 の exporter は note レベルの <unpitched> に <midi-unpitched> を
# 出力しない(音色→MIDI マップが欠落する)。研究の最重要事項である 1-based の
# midi-unpitched を、display-step/octave をキーに1パスで注入して補う。
_NOTE_BLOCK_RE = re.compile(r"<note\b.*?</note>", re.DOTALL)
_DISPLAY_STEP_RE = re.compile(r"<display-step>\s*([A-G])\s*</display-step>")
_DISPLAY_OCTAVE_RE = re.compile(r"<display-octave>\s*(-?\d+)\s*</display-octave>")

# display 位置(step, octave)→ GM note(0-based)の逆引き。_KIT_MAP から生成。
_DISPLAY_TO_GM: dict[tuple[str, int], int] = {
    (p.display_step, p.display_octave): p.gm_note
    for p in _KIT_MAP.values()
    if p.gm_note >= 0
}


def _inject_midi_unpitched(xml: str) -> str:
    """各 unpitched note に 1-based の `<midi-unpitched>` を注入する。

    display-step/octave から GM note を逆引きし、off-by-one を単一関数
    (gm_note_to_musicxml_unpitched)で解決した値を `</unpitched>` 直後に挿入する。
    未知位置の note は音色付けせず素通しする(誤った音色を付けない)。
    """

    def _fix_note(m: re.Match[str]) -> str:
        block = m.group(0)
        if "<midi-unpitched>" in block or "<unpitched>" not in block:
            return block
        step_m = _DISPLAY_STEP_RE.search(block)
        oct_m = _DISPLAY_OCTAVE_RE.search(block)
        if not step_m or not oct_m:
            return block
        key = (step_m.group(1), int(oct_m.group(1)))
        gm = _DISPLAY_TO_GM.get(key)
        if gm is None:
            return block
        midi_unpitched = gm_note_to_musicxml_unpitched(gm)
        tag = f"<midi-unpitched>{midi_unpitched}</midi-unpitched>"
        # music21 は <instrument> を持つ <unpitched> を出さないため、
        # <unpitched>...</unpitched> の内側末尾へ midi-unpitched を差し込む。
        return block.replace(
            "</unpitched>", f"  {tag}\n        </unpitched>", 1
        )

    return _NOTE_BLOCK_RE.sub(_fix_note, xml)


def drums_to_musicxml(
    drum_hits: list[dict],
    bpm: float,
    out_path: str | Path | None = None,
) -> str | Path:
    """detect_drums 出力をドラム譜(MusicXML)へ記譜する(F-036)。

    処理:
      1. 入力(打点列・BPM)を境界で検証する。
      2. kit ラベルを主キーに percussion clef の Part を組み立てる
         (display 位置・notehead・楽器は _KIT_MAP から一意に引く)。
      3. music21 で MusicXML 文字列を生成する。
      4. 1-based の `<midi-unpitched>` を1パスで注入し off-by-one を解決する。
      5. out_path 指定時はファイルへ書き出しそのパスを、未指定時は MusicXML
         文字列そのものを返す。

    Args:
        drum_hits: detect_drums の戻り値。各 dict は少なくとも
            "onset_sec"(float, 秒)と "kit"(str)を持つ。"confidence" は任意
            (記譜には使わない)。空リストも受け付ける(1小節の休符譜になる)。
        bpm: テンポ(拍/分)。1..400 の範囲を要求する。
        out_path: 書き出し先。None なら MusicXML 文字列を返す。

    Returns:
        out_path が None のとき MusicXML 文字列(str)、
        指定時は書き出したパス(Path)。

    Raises:
        TypeError / ValueError: 入力スキーマ・値域が不正なとき。

    限界(正直な記録):
    - generic MusicXML(GM 近似)であり、単一出力で全記譜ソフト互換は取れない。
    - detect_drums の kit 粒度は粗く、open/close HH・ride bell・rimshot 等は
      表現できない。未対応 kit は unknown レーン(中立線)へ倒す。
    - 拍は 4/4・16分格子に量子化する。detect_drums は拍子/小節情報を持たないため。
    """
    _validate_inputs(drum_hits, bpm)

    part = _build_part(drum_hits, bpm)
    score = stream.Score()
    score.insert(0, part)

    exporter = music21.musicxml.m21ToXml.GeneralObjectExporter(score)
    raw_xml = exporter.parse().decode("utf-8")
    xml = _inject_midi_unpitched(raw_xml)

    if out_path is None:
        return xml

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(xml, encoding="utf-8")
    return out
