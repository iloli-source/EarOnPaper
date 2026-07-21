"""drums エミッタのテスト(#109 B-2 結線検証)。

「非空レポートが出る」だけでは detect_drums が実際に打点を検出したか分からない
(メロディ音源では検出0でも通ってしまう=偽成功)。よって **打点のある合成打楽器音**
(短いノイズバースト列)を与え、実際に hit_count>=1 と kit ラベルが出ることを検証する。
AAA形式。
"""

from __future__ import annotations

import numpy as np
import soundfile as sf

from earpipe.services.emitters import drums as drums_emitter
from earpipe.services.emitters.base import EmitContext


def _percussive_wav(path, sr=22050, n_hits=6, gap_sec=0.4):
    """一定間隔の短いノイズバースト(=明確なトランジェント)を書き出す。"""
    total = int(sr * gap_sec * (n_hits + 1))
    y = np.zeros(total, dtype="float32")
    rng = np.random.default_rng(0)
    burst_len = int(sr * 0.04)  # 40ms
    for i in range(n_hits):
        start = int(sr * gap_sec * (i + 1))
        env = np.exp(-np.linspace(0, 8, burst_len)).astype("float32")  # 減衰打撃
        y[start:start + burst_len] += (rng.standard_normal(burst_len).astype("float32") * env * 0.6)
    sf.write(str(path), y, sr)
    return path


def test_drums_emitter_detects_real_onsets(tmp_path):
    # Arrange: 6発の打点がある合成打楽器音
    wav = _percussive_wav(tmp_path / "perc.wav")
    ctx = EmitContext(notes=[], bpm=120.0, title="drums", audio_path=wav)
    out_path = tmp_path / f"out.{drums_emitter.EXT}"

    # Act
    drums_emitter.emit(ctx, out_path)

    # Assert: 実際に打点が検出され、行としても出ている(検出0では通らない)
    lines = out_path.read_text(encoding="utf-8").splitlines()
    hit_count = int(next(l for l in lines if l.startswith("hit_count:")).split(":")[1])
    assert hit_count >= 1, f"打点が検出されていない(偽成功): \n{lines}"
    # kit_summary に少なくとも1種別の集計行がある
    summary_idx = lines.index("kit_summary:")
    assert lines[summary_idx + 1].strip().startswith("- ")
    # 実際の打点データ行(先頭が時刻の数字)が hit_count と一致する
    hits_idx = lines.index("hits (onset_sec / kit / confidence):")
    hit_rows = [l for l in lines[hits_idx + 1:] if l.strip() and l.lstrip()[0].isdigit()]
    assert len(hit_rows) == hit_count


def test_drums_emitter_declares_audio_contract():
    # Arrange / Act / Assert
    assert drums_emitter.KEY == "drums"
    assert drums_emitter.NEEDS_AUDIO is True
    assert drums_emitter.NEEDS_MUSICXML is False
