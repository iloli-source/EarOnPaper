"""basic-pitch 推論ワーカー。

このスクリプトは basic-pitch が動く別インタプリタ(Python 3.12 venv)で実行される。
本体パッケージ(Python 3.14)からは subprocess 経由で呼ばれ、標準出力の JSON だけが契約。
ライセンス: basic-pitch はコード・モデルとも Apache-2.0 (Spotify)。

使い方: python bp_worker.py input.wav [onset_threshold frame_threshold]
  閾値は省略時 basic-pitch 既定(0.5 / 0.3)。低くすると弱音を拾う(#32 取りこぼし救済)。
出力: [{"onset": s, "offset": s, "midi": int, "confidence": 0-1}, ...]
"""

import json
import os
import sys
from pathlib import Path


def _install_net_guard() -> None:
    """受入C7(通信ゼロ): EARPIPE_FORBID_NET 設定時にネットワークを遮断する。

    推論経路が外部接続を試みた瞬間に失敗させることで、subprocess側まで含めた
    「完全ローカル動作」をテスト可能にする(Issue #44)。
    """
    import socket

    def _no_net(*_a: object, **_k: object) -> None:
        raise RuntimeError("EARPIPE_FORBID_NET: bp_worker内でネットワーク接続が試行された")

    socket.socket.connect = _no_net  # type: ignore[method-assign]
    socket.create_connection = _no_net  # type: ignore[assignment]
    socket.getaddrinfo = _no_net  # type: ignore[assignment]


def main() -> int:  # pragma: no cover (3.12側で実行されE2E/エラー系テストで検証)
    if os.environ.get("EARPIPE_FORBID_NET"):
        _install_net_guard()
    # 引数バリデーションは重い import より前に行う(レビューHIGH-1)
    if len(sys.argv) < 2:
        print(
            "Usage: bp_worker.py <input.wav> [onset_threshold frame_threshold]",
            file=sys.stderr,
        )
        return 1
    wav = sys.argv[1]
    if not Path(wav).exists():
        print(f"File not found: {wav}", file=sys.stderr)
        return 1
    try:
        onset_th = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
        frame_th = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
    except ValueError:
        print("thresholds must be numbers", file=sys.stderr)
        return 1
    if not (0.0 < onset_th <= 1.0 and 0.0 < frame_th <= 1.0):
        print("thresholds must be in (0, 1]", file=sys.stderr)
        return 1

    real_stdout = sys.stdout
    # basic-pitch は stdout に進捗文字列を出すため、JSON契約を守るよう stderr へ隔離する。
    # 復元は try/finally で保証する(レビューMEDIUM-1: suppressによる握りつぶしを廃止)
    sys.stdout = sys.stderr
    try:
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
        _, _, note_events = predict(
            str(wav),
            str(tflite),
            onset_threshold=onset_th,
            frame_threshold=frame_th,
        )
    finally:
        sys.stdout = real_stdout

    out = [
        {
            "onset": float(start),
            "offset": float(end),
            "midi": int(pitch),
            "confidence": float(amplitude),
        }
        for start, end, pitch, amplitude, _bends in note_events
    ]
    json.dump(out, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
