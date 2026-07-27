"""記譜層: 推定コードを五線譜スコアの上部へコードネームとして合成する(#151)。

vocal-chord-format調査(docs/research/vocal-chord-format-*.md)で確定した標準形
「リードシート=五線メロディ＋五線上部コードネーム(＋歌詞)」の前半を実装する。
コードネームは記譜ソフト共通の慣行どおりメロディと独立したレイヤーとして扱い、
music21 の harmony.ChordSymbol(MusicXML harmony 要素→Verovio が五線上部に刻印)
で注入する。歌詞はスコープ外(別R&D)。

拍軸の整合(remap_spans): コードをフルミックス採譜から取る場合(--stem 併用)、
メロディ(ステム)採譜とはトリム秒・BPM・アンカー拍が異なる。両ランとも
単一テンポの線形格子なので、秒を共通軸に beats を線形変換して写像する。
テンポ推定が倍/半分で食い違うと写像も歪む(正直な限界・#136のbpm_source参照)。

スロット整理は chordchart._measure_slots を再利用(半小節単位・1小節最大2つ・
継続省略)。解釈不能なコード名は例外を握り潰さずスキップ数として報告する。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from earpipe.services.notate.chord import ChordSpan
from earpipe.services.notate.chordchart import _measure_slots

# (bpm, trimmed_leading_sec, anchored_lead_beats) — pipeline result と同じ並び
RunMeta = tuple[float, float, float]


def remap_spans(
    spans: Sequence[ChordSpan], src: RunMeta, dst: RunMeta
) -> list[ChordSpan]:
    """src ランの拍軸のコード区間を、秒を介して dst ランの拍軸へ線形写像する。"""
    src_bpm, src_trim, src_anchor = src
    dst_bpm, dst_trim, dst_anchor = dst

    def conv(beats: float) -> float:
        # anchor_to_zero は先頭音符が0拍になるよう start_beats から lead を引く。
        # つまり保存拍 b の格子上の位置は b + anchor(トリム起点の拍軸)。
        # 符号を誤ると両ランのlead差だけコードがずれる(レビュー指摘 #151)。
        sec = src_trim + (beats + src_anchor) * 60.0 / src_bpm
        return (sec - dst_trim) * dst_bpm / 60.0 - dst_anchor

    return [
        replace(cs, start_beats=conv(cs.start_beats), end_beats=conv(cs.end_beats))
        for cs in spans
    ]


def inject_chords(score, spans: Sequence[ChordSpan], beats: int) -> int:
    """スコアの各小節へコードネーム(harmony)を注入し、注入数を返す。

    メロディに存在する小節にのみ注入する(範囲外のコードはスキップ)。
    music21 が解釈できないコード名もスキップし、注入数に含めない。
    """
    from music21 import harmony
    from music21.stream import Measure

    measures = list(score.parts[0].getElementsByClass(Measure)) if score.parts else []
    if not measures or not spans:
        return 0

    n_measures = len(measures)
    slots = _measure_slots(spans, n_measures, beats)
    injected = 0
    for m, measure_slots in enumerate(slots):
        for beat_in, cs in measure_slots:
            figure = _m21_figure(cs.name)
            if not figure:
                continue
            try:
                sym = harmony.ChordSymbol(figure)
            except Exception:
                continue
            sym.writeAsChord = False
            # 五線上部に固定(リードシート慣行)。未指定だとVerovioの配置が
            # 上下混在し得る(実曲検証で発見・#151)
            sym.placement = "above"
            measures[m].insert(beat_in, sym)
            injected += 1
    return injected


def _m21_figure(name: str) -> str:
    """エンジンのコード名を music21 の figure 表記へ写す。

    music21 はルート/ベースのフラットを 'b' でなく '-' で表す(Bb→B-)。
    変換しないと ChordSymbol が ValueError となり、フラット系コードが
    全て黙ってスキップされる(実曲検証で発見・#151)。シャープ '#' はそのまま。
    """

    def conv_root(part: str) -> str:
        if len(part) >= 2 and part[0].isalpha() and part[1] == "b":
            return part[0] + "-" + part[2:]
        return part

    name = name.replace("N.C.", "").strip()
    if not name:
        return ""
    if "/" in name:
        root, bass = name.split("/", 1)
        return conv_root(root) + "/" + conv_root(bass)
    return conv_root(name)
