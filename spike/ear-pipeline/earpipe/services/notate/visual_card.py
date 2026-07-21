"""共有用ビジュアルカード(F-109 / Issue #93): 波形+抽出音符の重畳PNG生成。

SNS共有向けの固定比率(1200x630=1.91:1 OGP/Twitter Card準拠)の静止画を端末内で生成する。
背景に音声波形(ダウンサンプルしたピーク包絡)、前景に抽出音符(時間×音高の帯)を重ねる。
描画は自前SVG → cairosvg → PNG(engrave.py / tab.py と同じ描画スタック・完全ローカル)。

先行研究(F-109-grok.md / F-109-codex.md)の失敗例を反映した設計:

- 波形が音符を覆う(codex 2.1 / grok A2,D2): 波形は低不透明度の背景帯に閉じ込め、
  高さをカード高の一定割合に制限する。音符は縁取り付きの前景バーで主役にする。
- ピーク正規化で曲ごとに見た目が揃わない(codex 1.2): 最大値ではなく高パーセンタイルで
  表示ゲインを決め、極小音・クリップ音源でも破綻させない。
- 全音域表示で半音差が潰れる(codex 2.1): 検出音の音域に合わせてピッチ窓を自動ズームする。
- 波形上の細字が読めない/豆腐化(codex 2.2 / grok): テキストは背景チップ+縁取り、
  CJK対応フォントスタックを明示注入する。
- 色だけで情報を伝えない(codex 2.2 WCAG): 信頼度はバー高さ+不透明度+縁取りで併用表現する。
- ミュート視聴で意味が伝わらない(grok 5.2, checklist#1): タイトルと現在の代表音を焼き込む。
- 誤検出を「公式っぽく」見せて炎上(grok 5.4, checklist#2): 「AI推定・要校正」バッジを常時表示する。

原理的限界(正直):
- これは共有用の「見せるための簡約」であり、採譜そのものの正しさを保証しない。
- offsetは曖昧(codex 2.4)なので音価を厳密表示せず、バーは相対的な長さの目安に留める。
- 静止画のみを生成する(短尺動画/複数アスペクト比の再レイアウトは本モジュール範囲外)。
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from earpipe.contracts import QuantizedNote

# ---- カード寸法(SNS共有向け固定比率: 1.91:1 = X summary_large_image / OGP) ----
CARD_W = 1200
CARD_H = 630
_MARGIN = 56
_TITLE_H = 92          # 上部タイトル帯の高さ
_BADGE_H = 40          # 「AI推定」バッジ帯
_PLOT_TOP = _MARGIN + _TITLE_H
_PLOT_BOTTOM = CARD_H - _MARGIN - _BADGE_H
_PLOT_H = _PLOT_BOTTOM - _PLOT_TOP
_PLOT_LEFT = _MARGIN
_PLOT_RIGHT = CARD_W - _MARGIN
_PLOT_W = _PLOT_RIGHT - _PLOT_LEFT

# ---- 波形描画 ----
_WAVE_PEAKS = 480               # 横方向のピーク本数(ダウンサンプル解像度)
_WAVE_HEIGHT_FRAC = 0.28        # 波形が占める縦割合の上限(音符帯を侵食させない)
_WAVE_GAIN_PERCENTILE = 99.0    # ゲイン基準(最大値ではなく高パーセンタイル)
_WAVE_OPACITY = 0.30            # 背景扱い(前景音符より低コントラスト)

# ---- 音符描画 ----
_MIN_PITCH_SPAN = 12            # ピッチ窓の最小半音数(狭すぎると1音が巨大化する)
_PITCH_PAD = 2                  # 検出音域の上下に足す余白半音
_NOTE_MIN_H = 6.0               # バー最小高(小画面・再圧縮で消えないよう確保)
_NOTE_MIN_W = 4.0               # バー最小幅
_NOTE_MIN_CONF_OPACITY = 0.35   # 低信頼度でも完全に消さない下限不透明度

# ---- 色(彩度だけに頼らず縁取り・明度差で意味を出す) ----
_BG = "#0f1420"
_PLOT_BG = "#161d2e"
_WAVE_FILL = "#4a6fa5"
_NOTE_FILL = "#ffcf5c"
_NOTE_STROKE = "#3a2c00"
_GRID = "#243049"
_TEXT = "#f2f5fb"
_SUBTEXT = "#9fb0cc"
_BADGE_BG = "#c04a4a"

_CJK_FONT_STACK = (
    "Hiragino Sans, Hiragino Kaku Gothic ProN, Noto Sans CJK JP, "
    "Noto Sans JP, sans-serif"
)

_PITCH_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


@dataclass(frozen=True)
class CardLayout:
    """カードの描画メタ情報(テスト・検証用の要約)。

    - pitch_lo/pitch_hi: 自動ズームで採用したピッチ窓(MIDI半音, 両端含む)
    - notes_drawn: 実際に前景バーとして描いた音符数
    - duration_sec: 時間軸の総尺(秒)
    - wave_peaks: 波形として描いたピーク本数
    """

    pitch_lo: int
    pitch_hi: int
    notes_drawn: int
    duration_sec: float
    wave_peaks: int


def _esc(s: str) -> str:
    """SVGテキスト用の最小限のエスケープ。"""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _pitch_name(midi: int) -> str:
    """MIDIノート番号を音名+オクターブへ(例: 60 -> C4)。"""
    octave = midi // 12 - 1
    return f"{_PITCH_NAMES[midi % 12]}{octave}"


def downsample_peaks(y: np.ndarray, n_peaks: int = _WAVE_PEAKS) -> np.ndarray:
    """波形をn_peaks本のピーク包絡(各区間の最大絶対振幅)へダウンサンプルする。

    ステレオはモノラル合成する(codex 1.3: SNSカードでは左右合成の包絡で十分)。
    高パーセンタイルでゲインを決めるため、極小音源やクリップ音源でも0..1に収める。
    無音・空入力では長さn_peaksのゼロ配列を返す(描画側が平坦線を引ける)。

    Args:
        y: 音声波形。1次元(mono)または2次元(ch, samples)/(samples, ch)。
        n_peaks: 出力するピーク本数。

    Returns:
        shape (n_peaks,) の float32 配列。値域は[0, 1]。
    """
    if n_peaks < 1:
        raise ValueError("n_peaks は1以上が必要")

    arr = np.asarray(y, dtype=np.float64)
    if arr.ndim == 2:
        # (ch, samples) / (samples, ch) いずれでもチャンネル軸を平均してモノ化。
        ch_axis = 0 if arr.shape[0] < arr.shape[1] else 1
        arr = arr.mean(axis=ch_axis)
    arr = np.abs(arr.ravel())

    if arr.size == 0:
        return np.zeros(n_peaks, dtype=np.float32)

    # 各ピーク区間の最大絶対振幅を取る(padして均等分割)。
    pad = (-arr.size) % n_peaks
    if pad:
        arr = np.concatenate([arr, np.zeros(pad, dtype=arr.dtype)])
    peaks = arr.reshape(n_peaks, -1).max(axis=1)

    # ゲイン基準: 最大値ではなく高パーセンタイル(codex 1.2)。
    gain_ref = float(np.percentile(peaks, _WAVE_GAIN_PERCENTILE))
    if gain_ref <= 1e-9:
        gain_ref = float(peaks.max()) if peaks.max() > 0 else 1.0
    out = np.clip(peaks / gain_ref, 0.0, 1.0)
    return out.astype(np.float32)


def _pitch_window(notes: Sequence[QuantizedNote]) -> tuple[int, int]:
    """検出音域に合わせたピッチ窓(lo, hi)を決める(自動ズーム)。

    音符が無い/1音のみでも最小スパンを確保し、上下に余白を足す。
    """
    if not notes:
        base = 60  # 中央ド周辺を既定窓にする
        half = _MIN_PITCH_SPAN // 2
        return base - half, base + half

    midis = [n.midi for n in notes]
    lo, hi = min(midis), max(midis)
    lo -= _PITCH_PAD
    hi += _PITCH_PAD
    span = hi - lo
    if span < _MIN_PITCH_SPAN:
        grow = _MIN_PITCH_SPAN - span
        lo -= grow // 2
        hi += grow - grow // 2
    # MIDI有効域[0, 127]へクランプ(極端値でも破綻させない)。
    lo = max(0, lo)
    hi = min(127, hi)
    if hi <= lo:
        hi = lo + _MIN_PITCH_SPAN
    return lo, hi


def _note_time(n: QuantizedNote, bpm: float) -> tuple[float, float]:
    """音符の(開始秒, 終了秒)を求める。実側の秒があれば優先、無ければ拍から換算。

    QuantizedNoteのonset_sec/offset_secは既定NaN(旧4引数互換)。NaNなら
    start_beats/dur_beatsとbpmで秒換算する。offsetは曖昧なため最低長を確保する。
    """
    sec_per_beat = 60.0 / bpm if bpm > 0 else 0.5
    on = n.onset_sec
    off = n.offset_sec
    if math.isnan(on):
        on = n.start_beats * sec_per_beat
    if math.isnan(off) or off <= on:
        off = on + max(n.dur_beats, 0.0) * sec_per_beat
    # 最低長(codex 2.4: offsetは曖昧。極短でもバーが見えるよう下駄を履かせる)。
    if off <= on:
        off = on + 0.05
    return float(on), float(off)


def _total_duration(y: np.ndarray, sr: int, notes: Sequence[QuantizedNote],
                    bpm: float) -> float:
    """時間軸の総尺(秒)。音声長と最終音符終了の大きい方を採用する。"""
    audio_dur = 0.0
    arr = np.asarray(y)
    n_samples = arr.shape[-1] if arr.ndim else arr.size
    if sr > 0 and n_samples > 0:
        audio_dur = n_samples / sr
    note_dur = 0.0
    for n in notes:
        _, off = _note_time(n, bpm)
        note_dur = max(note_dur, off)
    dur = max(audio_dur, note_dur)
    return dur if dur > 0 else 1.0


def _build_svg(peaks: np.ndarray, notes: Sequence[QuantizedNote], bpm: float,
               duration: float, pitch_lo: int, pitch_hi: int,
               title: str | None) -> tuple[str, int]:
    """カード全体のSVG文字列を組み立てる。(svg, 描いた音符数)。"""
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" '
        f'height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}" '
        f'font-family="{_CJK_FONT_STACK}">',
        f'<rect width="{CARD_W}" height="{CARD_H}" fill="{_BG}"/>',
        f'<rect x="{_PLOT_LEFT}" y="{_PLOT_TOP}" width="{_PLOT_W}" '
        f'height="{_PLOT_H}" fill="{_PLOT_BG}" rx="12"/>',
    ]

    # --- ピッチグリッド(オクターブ線+音名。薄い破線=背景階層) ---
    span = pitch_hi - pitch_lo
    for midi in range(pitch_lo, pitch_hi + 1):
        if midi % 12 != 0:  # オクターブ(C)のみ線を引き団子を避ける
            continue
        frac = (midi - pitch_lo) / span
        gy = _PLOT_BOTTOM - frac * _PLOT_H
        parts.append(
            f'<line x1="{_PLOT_LEFT}" y1="{gy:.1f}" x2="{_PLOT_RIGHT}" '
            f'y2="{gy:.1f}" stroke="{_GRID}" stroke-width="1" '
            f'stroke-dasharray="4 6"/>'
        )
        parts.append(
            f'<text x="{_PLOT_LEFT + 6}" y="{gy - 4:.1f}" font-size="18" '
            f'fill="{_SUBTEXT}">{_pitch_name(midi)}</text>'
        )

    # --- 背景波形(低不透明度・高さ制限。中央線対称の包絡) ---
    wave_mid = _PLOT_BOTTOM - _PLOT_H * 0.5
    wave_amp = _PLOT_H * _WAVE_HEIGHT_FRAC * 0.5
    n = len(peaks)
    if n > 0:
        step = _PLOT_W / n
        bar_w = max(1.0, step * 0.8)
        wave_bars: list[str] = []
        for i, p in enumerate(peaks):
            h = max(1.0, float(p) * wave_amp)
            x = _PLOT_LEFT + i * step
            wave_bars.append(
                f'<rect x="{x:.1f}" y="{wave_mid - h:.1f}" '
                f'width="{bar_w:.1f}" height="{2 * h:.1f}"/>'
            )
        parts.append(
            f'<g fill="{_WAVE_FILL}" fill-opacity="{_WAVE_OPACITY}">'
            + "".join(wave_bars)
            + "</g>"
        )

    # --- 前景音符(縁取り付きバー。信頼度=高さ+不透明度で併用表現) ---
    drawn = 0
    top_conf: tuple[float, int] | None = None  # (conf, midi) 代表音の抽出
    note_rects: list[str] = []
    lane_h = _PLOT_H / (span + 1)
    for note in notes:
        if not (pitch_lo <= note.midi <= pitch_hi):
            continue
        on, off = _note_time(note, bpm)
        x0 = _PLOT_LEFT + (on / duration) * _PLOT_W
        x1 = _PLOT_LEFT + (off / duration) * _PLOT_W
        w = max(_NOTE_MIN_W, x1 - x0)
        # 信頼度でバー高を変える(高いほど太い)。色覚に依存しない冗長表現。
        conf = min(max(note.confidence, 0.0), 1.0)
        h = max(_NOTE_MIN_H, lane_h * (0.55 + 0.45 * conf))
        frac = (note.midi - pitch_lo) / span
        cy = _PLOT_BOTTOM - frac * _PLOT_H
        opacity = _NOTE_MIN_CONF_OPACITY + (1.0 - _NOTE_MIN_CONF_OPACITY) * conf
        note_rects.append(
            f'<rect x="{x0:.1f}" y="{cy - h / 2:.1f}" width="{w:.1f}" '
            f'height="{h:.1f}" rx="3" fill="{_NOTE_FILL}" '
            f'fill-opacity="{opacity:.2f}" stroke="{_NOTE_STROKE}" '
            f'stroke-width="1.2"/>'
        )
        drawn += 1
        if top_conf is None or conf > top_conf[0]:
            top_conf = (conf, note.midi)
    parts.extend(note_rects)

    # --- タイトル帯(ミュート視聴で意味が伝わるように) ---
    ttl = _esc(title) if title else "採譜プレビュー"
    parts.append(
        f'<text x="{_MARGIN}" y="{_MARGIN + 46}" font-size="42" '
        f'font-weight="bold" fill="{_TEXT}">{ttl}</text>'
    )
    rep = ""
    if top_conf is not None:
        rep = f"主要音 {_pitch_name(top_conf[1])}  |  "
    sub = f"{rep}BPM {int(round(bpm))}  |  {duration:.1f}s  |  {drawn}音"
    parts.append(
        f'<text x="{_MARGIN}" y="{_MARGIN + 78}" font-size="22" '
        f'fill="{_SUBTEXT}">{_esc(sub)}</text>'
    )

    # --- 「AI推定・要校正」バッジ(誤検出を公式に見せない・grok 5.4) ---
    badge_y = CARD_H - _MARGIN - _BADGE_H + 4
    badge_w = 280
    parts.append(
        f'<rect x="{_MARGIN}" y="{badge_y}" width="{badge_w}" '
        f'height="{_BADGE_H - 8}" rx="8" fill="{_BADGE_BG}"/>'
    )
    parts.append(
        f'<text x="{_MARGIN + badge_w / 2}" y="{badge_y + 22}" '
        f'font-size="18" font-weight="bold" text-anchor="middle" '
        f'fill="{_TEXT}">AI推定 / 要校正</text>'
    )
    parts.append(
        f'<text x="{_PLOT_RIGHT}" y="{badge_y + 22}" font-size="18" '
        f'text-anchor="end" fill="{_SUBTEXT}">Pitchsieve</text>'
    )

    parts.append("</svg>")
    return "".join(parts), drawn


def render_visual_card(
    y: np.ndarray,
    sr: int,
    notes: Sequence[QuantizedNote],
    out_path: str | Path,
    title: str | None = None,
    bpm: float = 120.0,
) -> Path:
    """波形+抽出音符を重畳したSNS共有用ビジュアルカードPNGを生成する。

    背景に音声波形(ダウンサンプルしたピーク包絡)、前景に抽出音符(時間×音高の帯)を
    重ねた固定比率(1200x630)のPNGを端末内で生成する(自前SVG → cairosvg → PNG)。
    完全ローカル処理(外部送信なし)。空音声・無音・空音符列でも妥当なPNGを生成する。

    Args:
        y: 音声波形(1次元mono または2次元ステレオ)。float想定だが型は問わない。
        sr: サンプルレート(Hz)。<=0や空音声のときは音符終端から総尺を決める。
        notes: 抽出済み音符(QuantizedNote列)。ピッチ窓は検出音域に自動ズームする。
        out_path: 出力PNGパス(str/Path)。拡張子は.pngへ正規化する。
        title: カード上部に焼き込むタイトル(省略時は既定文言)。
        bpm: 拍→秒換算に使うテンポ。onset_secがNaNの音符に適用する。

    Returns:
        書き出したPNGファイルの Path(常に存在する)。

    Raises:
        ValueError: bpm が負のとき(0は既定sec/beatへフォールバック)。
    """
    import cairosvg

    if bpm < 0:
        raise ValueError("bpm は0以上が必要")

    peaks = downsample_peaks(np.asarray(y))
    duration = _total_duration(np.asarray(y), sr, notes, bpm)
    pitch_lo, pitch_hi = _pitch_window(notes)
    svg, _ = _build_svg(peaks, notes, bpm, duration, pitch_lo, pitch_hi, title)

    out_path = Path(out_path)
    if out_path.suffix.lower() != ".png":
        out_path = out_path.with_suffix(".png")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    png_bytes = cairosvg.svg2png(
        bytestring=svg.encode("utf-8"), output_width=CARD_W, output_height=CARD_H
    )
    with open(out_path, "wb") as f:
        f.write(png_bytes)
    return out_path


def card_layout(
    y: np.ndarray,
    sr: int,
    notes: Sequence[QuantizedNote],
    bpm: float = 120.0,
) -> CardLayout:
    """描画せずにカードのレイアウト要約(CardLayout)だけを計算する(検証用)。

    render_visual_card と同じピッチ窓・総尺・描画対象音符数を返すので、
    PNGを開かずにレイアウトの妥当性(音域・音数・尺)をテストできる。
    """
    arr = np.asarray(y)
    peaks = downsample_peaks(arr)
    duration = _total_duration(arr, sr, notes, bpm)
    pitch_lo, pitch_hi = _pitch_window(notes)
    drawn = sum(1 for n in notes if pitch_lo <= n.midi <= pitch_hi)
    return CardLayout(
        pitch_lo=pitch_lo,
        pitch_hi=pitch_hi,
        notes_drawn=drawn,
        duration_sec=duration,
        wave_peaks=len(peaks),
    )
