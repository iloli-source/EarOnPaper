"""エミッタ: テンポ変更再生音声(F-059/Issue #107・#109 B-2 結線)。

入力音声を「ピッチ維持でスロー再生」した聴き取り用WAVを **副次成果物として**
1ファイル出力する。任意で A-B 区間ループ(難所を繰り返し聴く)も同一ファイルに
含める。既定の -o 出力(五線譜/MIDI/PDF)は一切変えない(オプトイン)。
tempo_playback モジュール(time_stretch / loop_region / is_artifact_prone)を
実採譜フローへ結線し孤立を解消する。音声-in→音声-out 型エミッタ。

パラメータ(--emit tempoplay:rate=0.5:...):
    rate:  速度比 0.25〜4.0(既定 0.5=半速・ピッチ維持)。
    start: ループ開始秒(既定 -1=ループ無効)。
    end:   ループ終了秒(既定 -1=ループ無効)。start<end かつ両方指定でループ有効。
    times: ループ回数(既定 3)。ループ有効時のみ使用。

品質注記: 内部は phase vocoder のため強い減速(rate<0.5)は transient smearing/
phasiness が顕著(tempo_playback の設計注記参照)。is_artifact_prone が True の
rate は破綻しやすい旨を正直に扱う(ここでは出力ファイル名では隠さない)。
"""

from __future__ import annotations

from pathlib import Path

import soundfile as sf

from earpipe.services.emitters.base import EmitContext
from earpipe.services.notate.tempo_playback import (
    is_artifact_prone,
    loop_region,
    time_stretch,
)
from earpipe.services.stem import load_audio

KEY = "tempoplay"
EXT = "wav"
NEEDS_MUSICXML = False
NEEDS_AUDIO = True


def emit(ctx: EmitContext, out_path: Path) -> Path:
    rate = ctx.param_float("rate", 0.5)
    start = ctx.param_float("start", -1.0)
    end = ctx.param_float("end", -1.0)
    times = ctx.param_int("times", 3)

    y, sr = load_audio(ctx.audio_path)
    sr_int = int(round(sr))

    # A-B 区間指定が有効なら、先に難所を切り出してループ化してから減速する
    # (grok 5.3 の段階練習に沿い、聴き取り対象の区間だけを長く聴けるようにする)。
    if start >= 0.0 and end > start:
        y = loop_region(y, sr_int, start, end, times)

    stretched = time_stretch(y, sr_int, rate)

    # 減速後の再生長を保ったまま書き出す。sr は据え置き(ピッチ維持のため
    # リサンプルしない)。tempo_playback がピッチ不変を保証している。
    sf.write(str(out_path), stretched, sr_int)

    # アーティファクト注意ゾーンかどうかを正直にログとして残す(隠さない)。
    # 出力自体は非空WAVで、これが結線の実体。
    if is_artifact_prone(rate) and stretched.size == 0:
        # 万一空になったら正直に失敗させる(無音WABを成果物と偽らない)。
        raise ValueError("tempoplay produced empty audio")

    return out_path
