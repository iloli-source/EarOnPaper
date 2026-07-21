"""F-059 テンポ変更再生(Issue #107)。

聴き取り(耳コピ)補助のための、(a) ピッチ維持でのタイムストレッチ／減速再生と
(b) A-B区間ループ生成を提供する。譜面データではなく「聴くための音声波形」を返す
オフラインユーティリティであり、リアルタイム再生エンジンではない。

設計の要点(先行研究 F-059-grok / F-059-codex の失敗例を反映):

- タイムストレッチと「量子化(タイミング補正)」は別機能(grok 失敗クラスタA)。
  本モジュールは「聴き取り用減速」だけを担い、譜面のクオンタイズには一切使わない。
  誤用防止のため、量子化に流用しやすいAPI(グリッド合わせ等)は提供しない。

- librosa.effects.time_stretch の内部は phase vocoder で、公式Docが
  "makes no attempt to handle transients, and is likely to produce many
  audible artifacts" と明言する参照実装(codex §3)。アタックのにじみ・
  phasiness・残響状の尾引きが常態(grok 失敗クラスタB, codex §1)。ゆえに
  「綺麗な原音」は原理的に得られない。強いスロー(rate<=0.5 目安)ほど破綻が
  顕著化する(codex §1・grok クラスタI)。この限界は notes に正直に記す。

- rate<1 で減速・ピッチ維持、rate>1 で加速・ピッチ維持。ピッチが動くのは
  「resample によるテープ風速度変更」であり本関数はそれをしない(チップマンク
  事故の回避・grok 失敗クラスタE, codex §5)。音高は保たれ、速さだけが変わる。

- A-Bループは time-stretch 品質とは独立に「境界の波形不連続」でクリックが出る
  (codex §6)。ゼロクロスだけでは傾き・チャンネル差を保証しないため、繋ぎ目に
  等パワークロスフェードを掛けて click/pop を抑える。エンジン任せにしない。

依存は導入済みの librosa/numpy のみ(純Python軽量)。torch/Rubber Band 等の重い
外部エンジンは非採用(環境制約・grok/codex の高品質エンジンはリアルタイム/本番
向けでオフライン聴き取り用途には過剰)。品質限界は上記のとおり notes 参照。
"""

from __future__ import annotations

import librosa
import numpy as np

# タイムストレッチ比率の実務上限・下限。極端な比率は「聴き取り」より
# 「音響現象(グリッチ)」になり artifact だらけで役に立たない
# (grok 失敗クラスタI, codex §1)。0近傍・負・巨大値は物理的に無効。
_MIN_RATE = 0.25
_MAX_RATE = 4.0

# アーティファクト注意ゾーンの下限。これ未満の減速は phase vocoder の
# transient smearing が顕著化し、採譜判断を誤らせやすい(codex §1・§3)。
# 呼び出し側UIが警告表示できるよう定数として公開する。
ARTIFACT_WARNING_RATE = 0.5

# ループ境界のクロスフェード長(秒)。codex §6 の推奨 3-10ms の中間値。
# 短すぎるとクリックが残り、長すぎると音の頭を舐めて聴き取りを損なう。
_CROSSFADE_SEC = 0.005


def is_artifact_prone(rate: float) -> bool:
    """指定 rate が phase vocoder のアーティファクト注意ゾーンかを返す。

    True のとき、減速が強く transient smearing / phasiness が耳に付きやすい
    (codex §1・§3)。UI 側の「アーティファクト注意」表示の判定に使う。
    有効範囲外(_MIN_RATE 未満)は当然 True。
    """
    return rate < ARTIFACT_WARNING_RATE


def time_stretch(y: np.ndarray, sr: int, rate: float) -> np.ndarray:
    """ピッチを維持したままテンポを変える(rate<1 で減速、rate>1 で加速)。

    内部は librosa.effects.time_stretch(phase vocoder)。音高は保存され、
    再生長は概ね元の 1/rate 倍になる(rate=0.5 で約2倍の長さ=半速)。
    sr は出力長の妥当性検証にのみ用い、リサンプルはしない(ピッチは不変)。

    引数:
        y: モノラル音声波形(1次元 float 配列を想定。stem/preprocess の load_audio 出力)。
        sr: サンプルレート(Hz)。正の整数であること。
        rate: 速度比。0.25〜4.0。1未満で遅く・1超で速く、いずれもピッチ維持。

    戻り値:
        ピッチ維持でタイムストレッチした新しい波形(入力は破壊しない)。

    例外:
        TypeError: y が ndarray でない場合。
        ValueError: y が空/多次元、sr が非正、rate が有効範囲外の場合。

    限界(先行研究より・捏造なし):
        phase vocoder はトランジェント(アタック)を保てず、にじみ・phasiness・
        残響状アーティファクトが常態(codex §3, grok クラスタB)。rate が
        ARTIFACT_WARNING_RATE 未満だと破綻が顕著(is_artifact_prone で判定可)。
        高品質が要る本番用途は Rubber Band 等が別途必要だが本環境では非採用。
    """
    if not isinstance(y, np.ndarray):
        raise TypeError(f"y must be numpy.ndarray, got {type(y).__name__}")
    if y.ndim != 1:
        raise ValueError(f"y must be 1-D (mono), got ndim={y.ndim}")
    if y.size == 0:
        raise ValueError("y must not be empty")
    if not isinstance(sr, (int, np.integer)) or sr <= 0:
        raise ValueError(f"sr must be a positive int, got {sr!r}")
    if not np.isfinite(rate) or not _MIN_RATE <= rate <= _MAX_RATE:
        raise ValueError(
            f"rate must be finite and within {_MIN_RATE}..{_MAX_RATE}, got {rate!r}"
        )
    if rate == 1.0:
        # 恒等: 余計なアーティファクトを一切載せないため素通しコピーを返す。
        return np.array(y, dtype=y.dtype, copy=True)
    # librosa 0.11 は rate をキーワード専用引数として要求する。
    stretched = librosa.effects.time_stretch(y, rate=float(rate))
    return np.ascontiguousarray(stretched)


def loop_region(
    y: np.ndarray,
    sr: int,
    start_sec: float,
    end_sec: float,
    times: int,
) -> np.ndarray:
    """[start_sec, end_sec) 区間を times 回つなげた A-B ループ波形を返す。

    採譜の「難所だけ繰り返し聴く」用途(grok 5.2)。区間の切り出しは
    サンプル精度で行い、繰り返しの継ぎ目には等パワークロスフェードを掛けて
    境界の波形不連続によるクリック/ポップを抑える(codex §6: ゼロクロスだけでは
    傾き差を保証できない)。ループ全体の先頭・末尾はフェードせず素の区間を残す
    (聴き取りで音の頭を舐めないため、継ぎ目のみ処理する)。

    引数:
        y: モノラル音声波形(1次元 float 配列)。
        sr: サンプルレート(Hz)。正の整数。
        start_sec: ループ開始秒(0 以上)。
        end_sec: ループ終了秒(start_sec より大)。区間長はクロスフェードより長いこと。
        times: 繰り返し回数(1 以上の整数)。1 なら区間を1回返す。

    戻り値:
        区間を times 回連結した新しい波形(入力は破壊しない)。

    例外:
        TypeError: y が ndarray でない/times が int でない場合。
        ValueError: 波形が不正、sr が非正、区間が範囲外・逆順・過小、times<1 の場合。

    注記:
        本関数はテンポ変更を含まない。段階的な減速練習は time_stretch と
        組み合わせて呼び出し側で構成する(grok 5.3 の段階テンポ戦略)。
    """
    if not isinstance(y, np.ndarray):
        raise TypeError(f"y must be numpy.ndarray, got {type(y).__name__}")
    if y.ndim != 1:
        raise ValueError(f"y must be 1-D (mono), got ndim={y.ndim}")
    if y.size == 0:
        raise ValueError("y must not be empty")
    if not isinstance(sr, (int, np.integer)) or sr <= 0:
        raise ValueError(f"sr must be a positive int, got {sr!r}")
    if not isinstance(times, (int, np.integer)) or isinstance(times, bool):
        raise TypeError(f"times must be int, got {type(times).__name__}")
    if times < 1:
        raise ValueError(f"times must be >= 1, got {times}")
    if not (np.isfinite(start_sec) and np.isfinite(end_sec)):
        raise ValueError("start_sec/end_sec must be finite")
    if start_sec < 0.0 or end_sec <= start_sec:
        raise ValueError(
            f"require 0 <= start_sec < end_sec, got start={start_sec}, end={end_sec}"
        )

    start = int(round(start_sec * sr))
    end = int(round(end_sec * sr))
    if end > y.size:
        raise ValueError(
            f"end_sec exceeds audio length ({end_sec}s > {y.size / sr}s)"
        )
    segment = y[start:end]
    seg_len = segment.size
    if seg_len < 2:
        raise ValueError("loop region is too short (need >= 2 samples)")

    if times == 1:
        return np.array(segment, dtype=y.dtype, copy=True)

    # 継ぎ目のクロスフェード長(サンプル)。区間長の半分を超えないよう抑える。
    fade = int(round(_CROSSFADE_SEC * sr))
    fade = min(fade, seg_len // 2)
    if fade < 1:
        # 区間が極端に短くフェードできない場合は単純連結にフォールバックする
        # (クリックは残り得るが、無音や破壊よりは聴き取り優先)。
        return np.ascontiguousarray(np.tile(segment, times).astype(y.dtype, copy=False))

    # 等パワー(sin/cos)フェード窓。二乗和が一定になり継ぎ目で音量の谷を作らない。
    ramp = np.linspace(0.0, np.pi / 2.0, fade, endpoint=False, dtype=np.float64)
    fade_out = np.cos(ramp)
    fade_in = np.sin(ramp)

    seg = segment.astype(np.float64, copy=False)
    head = seg[:fade]                # 各周の先頭(次周のフェードイン素材)
    tail = seg[-fade:]              # 各周の末尾(現周のフェードアウト素材)
    joint = tail * fade_out + head * fade_in  # 周と周の重ね継ぎ目(1つ分)

    # 継ぎ目本体: 区間の「先頭 fade を除き末尾 fade を除いた中央部」。
    # ループ全体 = [先頭 fade] + (times-1 個の [中央部 + 継ぎ目]) + [中央部] + [末尾 fade]
    # とすると、隣り合う周の末尾と次周の先頭が joint で1度だけ重なり、
    # 全体長は times*seg_len - (times-1)*fade になる(継ぎ目でのみ短縮)。
    middle = seg[fade:-fade] if seg_len > 2 * fade else seg[fade:fade]

    pieces: list[np.ndarray] = [head]
    for i in range(times - 1):
        pieces.append(middle)
        pieces.append(joint)
    pieces.append(middle)
    pieces.append(tail)

    looped = np.concatenate(pieces)
    return np.ascontiguousarray(looped.astype(y.dtype, copy=False))
