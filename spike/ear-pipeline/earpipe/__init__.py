"""earpipe — 採譜エンジン（二層構造: 耳=楽器非依存 / 記譜=出力プロファイル）。

公開APIは遅延importする。従来は ``import earpipe.services.rhythm`` のような下位機能の
利用でも、トップレベル ``earpipe.__init__`` が music21/描画層まで即時importしていた。
そのため、音声・リズムだけを使う環境やテストが任意の記譜依存不足で起動不能になっていた。
"""

from importlib import import_module

_EXPORTS = {
    "PitchEvent": ("earpipe.ear", "PitchEvent"),
    "detect_events": ("earpipe.ear", "detect_events"),
    "QuantizedNote": ("earpipe.quantize", "QuantizedNote"),
    "estimate_tempo": ("earpipe.quantize", "estimate_tempo"),
    "quantize_events": ("earpipe.quantize", "quantize_events"),
    "to_score": ("earpipe.notate", "to_score"),
    "write_musicxml": ("earpipe.notate", "write_musicxml"),
    "write_midi": ("earpipe.notate", "write_midi"),
    "transcribe_file": ("earpipe.pipeline", "transcribe_file"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = target
    value = getattr(import_module(module_name), attribute)
    globals()[name] = value
    return value
