"""生成AI楽曲向け採譜プリセット(F-092 / Issue #99)。

Suno / Udio / MusicGen / Stable Audio 等の生成AI音源は、一聴すると
「分離が良く・ノイズが少なく・音圧が安定」でAMTしやすく見えるが、
採譜には逆に危険な特性を持つ(先行研究 F-092-grok / F-092-codex)。

本モジュールは純Python(numpy)のみで、**破壊的でない軽い前処理**
`genai_preprocess` と、その音源特性に合わせた**推奨パラメータ**
`GENAI_PRESET` を提供する。重い学習済みモデルや専用ステム分離器
(torch/demucs 系)は導入しない — 前処理は「採譜器を惑わすノイズ床と
オフセットを均す」程度に留め、倍音や抑揚を削る強い加工は一切しない。

先行研究から反映した失敗回避(pitfalls):
- クリーンミックスの罠: 過度なマスタリングEQ/コンプは倍音とベロシティ
  手がかりを消すため行わない(grok BP2 / codex §2)。
- ニューラルコーデック由来の高域アーティファクトが hi-hat / シェイカー /
  弦ノイズとして誤採譜される(codex §4)。→ ごく軽い高域デエンファシス
  (1次シェルフ)で「立ちすぎた高域倍音」だけをわずかに寝かせる。破壊は
  しない(shelf_gain は 1.0 に近い既定)。
- DCオフセット/微小直流成分は onset 検出を汚す。→ 平均除去。
- 過剰量子化は「破壊的編集」になりやすい(codex §3)。→ プリセットは
  16分ハード量子化を既定にしつつ、`quantize_strength` と
  `scale_lock` を明示し、呼び出し側が段階選択できる値として渡す。
- 表現(bend/portamento)は note-only 既定(grok F6 / codex §3)。
- ドラム/非音高FXは本プリセットの対象外(tonal tracks only, grok F8)。
- Audio→MIDI は不可逆な復元問題であり 100% 再現は約束しない
  (grok F1/F2)。プリセットは「編集用の下書きMIDI」に最適化する。
"""

from dataclasses import dataclass

import numpy as np

# --- 前処理パラメータ(いずれも「軽い・非破壊」を厳守) ---
# DCオフセット除去は平均減算のみ。ハイパスは倍音の低次を削りうるため使わない。
_HIGH_SHELF_GAIN = 0.88   # 高域シェルフの利得(<1.0でわずかに減衰)。0.8〜0.95が安全域。
# 1未満だが 0 には決してしない — 完全カットは倍音(音高手がかり)を壊す。
_HIGH_SHELF_COEF = 0.55   # 1次シェルフの平滑係数(0<coef<1)。大きいほど高域寄りに作用。
_PEAK_TARGET = 0.97       # ピーク正規化の目標振幅(クリップ回避のヘッドルーム込み)。
# 正規化は「利得のみ」= 相対ダイナミクスを保存する(コンプではない)。
_MIN_PEAK = 1e-6          # これ未満のピーク(無音相当)は正規化しない(ゼロ割回避)。


@dataclass(frozen=True)
class GenaiPreset:
    """生成AI楽曲向けの推奨採譜パラメータ(不変)。

    各値は既存サービスの引数名に対応する推奨値であり、本プリセットは
    パラメータを「提示」するだけで既存パイプラインを書き換えない。

    - detect_min_conf: `ear.mono.detect_events(min_conf=...)` へ。クリーンな
      合成音は倍音が過度に整い phantom F0 / オクターブ誤りを出しやすい
      (codex §2-3)ため既定 0.5 より高くしてゴースト音を抑える。
    - detect_pitch_tol: `detect_events(pitch_tol=...)` へ。合成音のビブラート
      は浅く安定しているため既定より狭めてよい。
    - grid_per_beat: `rhythm.quantize.quantize_events(grid_per_beat=...)` へ。
      電子/ループ寄りの生成曲は 16分格子(=4)が既定。
    - quantize_strength: 量子化の吸着強度(0.0=無吸着 / 1.0=完全吸着)。
      生成曲はグリッド感が強いので 1.0 寄りだが、破壊回避のため <1.0 を
      推奨値とする(段階量子化: codex §3, grok BP3)。呼び出し側が対応する
      場合のみ利用する助言値。
    - scale_lock: 検出キーへの音階スナップを推奨するか。ゴーストノート削減に
      効く一方、ブルーノート/グライドを潰す危険があるため既定 True でも
      note-only と併用する前提(grok F6)。
    - pitch_bend: 表現(ベンド)を出力するか。note-only 既定 = False。
    - drums: 非音高パーカッションを採譜対象にするか(本プリセットは False)。
    """

    detect_min_conf: float
    detect_pitch_tol: float
    grid_per_beat: int
    quantize_strength: float
    scale_lock: bool
    pitch_bend: bool
    drums: bool
    notes: str


GENAI_PRESET: dict = {
    "detect_min_conf": 0.6,     # 既定0.5より高め: phantom F0/オクターブ誤り抑制
    "detect_pitch_tol": 0.4,    # 既定0.5より狭め: 安定した合成ビブラート前提
    "grid_per_beat": 4,         # 16分格子(電子/ループ寄り生成曲の既定)
    "quantize_strength": 0.8,   # 段階量子化: 完全吸着(1.0)で演奏を殺さない
    "scale_lock": True,         # 検出キーへスナップ(ゴースト削減)。note-only併用前提
    "pitch_bend": False,        # note-only 既定(表現は別レーン。grok F6)
    "drums": False,             # tonal tracks only(非音高FXは対象外。grok F8)
    "preprocess": {
        "high_shelf_gain": _HIGH_SHELF_GAIN,
        "peak_target": _PEAK_TARGET,
    },
    "notes": (
        "生成AI音源向け下書きMIDIプリセット。Audio→MIDIは不可逆で100%再現は"
        "しない。前処理は非破壊(DC除去+軽い高域デエンファシス+利得正規化のみ)。"
        "ドラム/非音高FXは対象外。重い学習済みモデル・torch/demucsは未使用。"
    ),
}


def genai_preset() -> GenaiPreset:
    """`GENAI_PRESET` を型付き不変オブジェクトとして返す(型安全な参照用)。"""
    return GenaiPreset(
        detect_min_conf=float(GENAI_PRESET["detect_min_conf"]),
        detect_pitch_tol=float(GENAI_PRESET["detect_pitch_tol"]),
        grid_per_beat=int(GENAI_PRESET["grid_per_beat"]),
        quantize_strength=float(GENAI_PRESET["quantize_strength"]),
        scale_lock=bool(GENAI_PRESET["scale_lock"]),
        pitch_bend=bool(GENAI_PRESET["pitch_bend"]),
        drums=bool(GENAI_PRESET["drums"]),
        notes=str(GENAI_PRESET["notes"]),
    )


def _remove_dc_offset(y: np.ndarray) -> np.ndarray:
    """直流(DC)オフセットを平均減算で除去する(新配列を返す)。

    微小直流はスペクトルフラックス型 onset を汚す(codex §4)。平均を引く
    だけの線形操作で、音高情報には触れない。
    """
    return y - float(np.mean(y))


def _high_shelf_deemphasis(
    y: np.ndarray, gain: float, coef: float
) -> np.ndarray:
    """高域をごくわずかに寝かせる1次シェルフ(非破壊・新配列を返す)。

    生成AI音源の高域には checkerboard 由来の微小アーティファクトが乗り
    (codex §4 / arXiv:2506.19108)、hi-hat / シェイカー / 弦ノイズとして
    誤採譜されうる。ここでは「高域成分だけを gain(<1) 倍する」ごく弱い
    デエンファシスで、その立ちすぎた高域をわずかに抑える。

    実装は1次ローパスで低域成分 lp を作り、y = lp + gain*(y-lp) とする。
    gain=1.0 なら恒等(何もしない)。倍音を消さないよう gain は 0 にしない
    (呼び出し側が gain>=1 を渡した場合は恒等的に振る舞い、増幅はしない)。
    """
    if gain >= 1.0:
        return y.copy()
    lp = np.empty_like(y)
    if y.size == 0:
        return lp
    lp[0] = y[0]
    a = float(coef)
    for i in range(1, y.size):
        lp[i] = a * lp[i - 1] + (1.0 - a) * y[i]
    high = y - lp
    return lp + gain * high


def _peak_normalize(y: np.ndarray, target: float) -> np.ndarray:
    """ピーク振幅を target に合わせる利得のみの正規化(相対ダイナミクス保存)。

    コンプ/リミッターではなく単一利得の乗算なので、ベロシティ推定の手がかり
    (音量差)を潰さない(codex §2-4 の velocity 平坦化を避ける)。無音相当は
    触らない。
    """
    peak = float(np.max(np.abs(y))) if y.size else 0.0
    if peak < _MIN_PEAK:
        return y.copy()
    return y * (target / peak)


def genai_preprocess(y: np.ndarray, sr: int) -> np.ndarray:
    """生成AI音源向けの軽い非破壊前処理を施した新しい波形を返す。

    処理順:
      1. DCオフセット除去(平均減算)
      2. 軽い高域デエンファシス(高域アーティファクト抑制・1次シェルフ)
      3. ピーク正規化(利得のみ。相対ダイナミクス保存)

    いずれも倍音・音高・相対音量を壊さない範囲に限定する。入力長は保存し、
    入力配列は変更しない(immutable)。空入力・無音は安全に素通しする。

    Args:
        y: モノラル波形(1次元想定。多次元はモノラルへ畳む)。
        sr: サンプルレート(Hz)。現状の軽処理では係数計算に用いないが、
            将来の周波数依存処理のためインタフェースに残す。破壊防止のため
            正の有限値を要求する。

    Returns:
        前処理済みの新しい float64 波形(入力と同じ長さ)。

    Raises:
        ValueError: sr が正の有限値でない場合(境界検証・fail fast)。

    限界(正直な記録): 本前処理は「採譜器を惑わす高域アーティファクトと
    オフセット」を軽く均すだけで、レイヤーの過同期(個別 onset の潰れ)・
    非物理エンベロープ・phantom F0 といった生成AI固有の困難は解消しない
    (codex §2)。それらは検出/量子化側のパラメータ(GENAI_PRESET)と、
    最終的な人手修正で扱う設計。
    """
    if not np.isfinite(sr) or sr <= 0:
        raise ValueError(f"sr must be a positive finite number, got {sr}")

    x = np.asarray(y, dtype=np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if x.size == 0:
        return x.copy()

    x = _remove_dc_offset(x)
    x = _high_shelf_deemphasis(x, _HIGH_SHELF_GAIN, _HIGH_SHELF_COEF)
    x = _peak_normalize(x, _PEAK_TARGET)
    return x
