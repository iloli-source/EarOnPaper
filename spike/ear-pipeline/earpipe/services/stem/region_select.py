"""stemサービス: 区間選択採譜のための区間切り出し(F-007・Issue #105)。

曲全体ではなく「ユーザーが指定した区間だけ」を採譜する機能の最下層。
指定 [start_sec, end_sec) を元波形から切り出し、境界に微小フェード
(edge fade)をかけてプチノイズ(クリック/ポップ)を回避する。

なぜフェードが要るか(研究の反映):
    任意位置で波形を「ハサミで切る」と、切り口で振幅が不連続になり
    STFT 上の端点不連続(spectral leakage)や、再生時の可聴クリックを
    生む(F-007-codex §2-1「STFT の端 padding 差 / spectral leakage」、
    F-007-grok BP5「アタックを切らない」・失敗タイプ3「境界でノートが
    切れる/二重化」)。切り口だけを線形ランプで 0 に収束させることで、
    区間端のアーティファクトを抑える。フェード長は既定 5ms と極短にして
    実音(アタック・ノート頭)を潰さないようにする。

責務の境界(重要):
    本関数の責務は「範囲検証 + 物理的な切り出し + 境界フェード」に限定する。
    研究が推奨する「推論範囲 ≠ 返却範囲(context を余分に読んで採譜し返却時
    だけ crop する)」設計(F-007-codex §4-1)や、区間をまたぐノートの分類
    (inside / started_before / ends_after)は上位(pipeline 配線側・採譜
    エンジン)の責務であり、ここでは行わない(YAGNI)。

原理的限界(正直な明記):
    - フェードは「切り口のクリック」を消すだけで、区間の頭で既に鳴っていた
      持続音のアタック欠落(F-007-grok 失敗タイプ14, F-007-codex §2-3)や、
      末尾での note-off/decay 欠落(同 §2-4)は解決しない。それらは
      「区間を物理的に切ってから採譜する」限り原理的に残る劣化であり、
      context 付き推論でしか本質的には緩和できない。
    - 純Python + numpy のみで実装(重依存なし)。フィルタ等は使わない。
"""

from __future__ import annotations

import numpy as np

# フェード長の既定値(秒)。5ms はクリック除去には十分短く、実音を潰さない。
_DEFAULT_EDGE_FADE_SEC = 0.005


def crop_region(
    y: np.ndarray,
    sr: int,
    start_sec: float,
    end_sec: float,
    edge_fade_sec: float = _DEFAULT_EDGE_FADE_SEC,
) -> np.ndarray:
    """波形 y から [start_sec, end_sec) を切り出し境界に微小フェードをかける。

    切り出しはサンプルindexを唯一の真実とし、start = round(start_sec*sr)、
    end = round(end_sec*sr) で丸める(往復変換ずれを避ける)。切り出した区間の
    先頭 fade_len サンプルを 0→1 の線形ランプ、末尾 fade_len サンプルを 1→0 の
    線形ランプで乗算し、切り口のクリック/ポップを抑える。

    入力 y は変更しない(常に新しい配列を返す。immutable 方針)。

    Args:
        y: モノラル波形(1次元 float 配列を想定)。
        sr: サンプルレート(Hz、正の整数)。
        start_sec: 区間開始秒(0 以上)。
        end_sec: 区間終了秒(start_sec より大)。
        edge_fade_sec: 境界フェード長(秒、0 以上)。既定 5ms。
            区間長の半分を超える場合は区間長の半分にクリップし、先頭と末尾の
            フェードが重ならないようにする。

    Returns:
        切り出し済みの新しい 1 次元 float 配列(境界フェード適用済み)。

    Raises:
        ValueError: 入力が 1 次元でない、sr が非正、edge_fade_sec が負、
            start_sec が負、end_sec <= start_sec、区間が波形範囲外(空区間に
            なる)の場合。範囲は境界で fail-fast する(信頼できない入力を
            黙って通さない)。
    """
    # --- 入力検証(システム境界での fail-fast) ---
    if y.ndim != 1:
        raise ValueError(f"y は1次元配列である必要があります(ndim={y.ndim})")
    if sr <= 0:
        raise ValueError(f"sr は正である必要があります(sr={sr})")
    if edge_fade_sec < 0:
        raise ValueError(
            f"edge_fade_sec は0以上である必要があります(edge_fade_sec={edge_fade_sec})"
        )
    if start_sec < 0:
        raise ValueError(f"start_sec は0以上である必要があります(start_sec={start_sec})")
    if not end_sec > start_sec:
        raise ValueError(
            f"end_sec は start_sec より大きい必要があります"
            f"(start_sec={start_sec}, end_sec={end_sec})"
        )

    n = int(y.shape[0])
    start = int(round(start_sec * sr))
    end = int(round(end_sec * sr))

    # 丸めやオーバーフローで区間が波形外/空になるのを防ぐ
    start = max(0, start)
    end = min(n, end)
    if end <= start:
        raise ValueError(
            f"区間が波形範囲外か空です(start={start}, end={end}, len={n})。"
            f"start_sec/end_sec が波形長({n / sr:.3f}秒)に収まるか確認してください"
        )

    # 元配列を変更しないようコピーして切り出す(ビューではなく独立配列)
    region = np.array(y[start:end], dtype=float, copy=True)
    region_len = region.shape[0]

    # フェード長をサンプルに換算し、区間長の半分を超えないようクリップする
    fade_len = int(round(edge_fade_sec * sr))
    fade_len = max(0, min(fade_len, region_len // 2))
    if fade_len == 0:
        return region

    # 0→1 / 1→0 の線形ランプ(endpoint=False で 0 を必ず含み 1 まで届かせない
    # ことで、切り口の振幅を確実に 0 側へ収束させる)
    ramp = np.linspace(0.0, 1.0, fade_len, endpoint=False, dtype=float)
    region[:fade_len] *= ramp
    region[region_len - fade_len :] *= ramp[::-1]
    return region
