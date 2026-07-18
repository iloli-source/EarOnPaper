"""basic-pitch 推論ワーカー。

このスクリプトは basic-pitch が動く別インタプリタ(Python 3.12 venv)で実行される。
本体パッケージ(Python 3.14)からは subprocess 経由で呼ばれ、標準出力の JSON だけが契約。
ライセンス: basic-pitch はコード・モデルとも Apache-2.0 (Spotify)。

使い方: python bp_worker.py input.wav
出力: [{"onset": s, "offset": s, "midi": int, "confidence": 0-1}, ...]
"""

import contextlib
import json
import sys


def main() -> int:  # pragma: no cover (3.12側で実行されE2Eテストで検証)
    wav = sys.argv[1]
    real_stdout = sys.stdout
    # basic-pitch は stdout に進捗文字列を出すため、JSON契約を守るよう stderr へ隔離する
    sys.stdout = sys.stderr
    from pathlib import Path

    from basic_pitch import ICASSP_2022_MODEL_PATH
    from basic_pitch.inference import predict

    # モデル選択の経緯(2026-07-19検証):
    # - TF SavedModel: この環境のTF2.16(Keras3)と非互換でロード不能
    # - ONNX(nmp.onnx): ロードは通るが出力が壊れる(無音でnote事後確率mean0.60)→使用禁止
    # - TFLite(nmp.tflite): 健全(無音でnote max0.16→音符ゼロ)。これを使用する
    model = Path(str(ICASSP_2022_MODEL_PATH))
    tflite = model.parent / "nmp.tflite"
    if not tflite.exists():
        raise RuntimeError(f"nmp.tflite が見つかりません: {tflite}")
    model = tflite
    _, _, note_events = predict(str(wav), str(model))
    out = [
        {
            "onset": float(start),
            "offset": float(end),
            "midi": int(pitch),
            "confidence": float(amplitude),
        }
        for start, end, pitch, amplitude, _bends in note_events
    ]
    with contextlib.suppress(Exception):
        sys.stdout = real_stdout
    json.dump(out, real_stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
