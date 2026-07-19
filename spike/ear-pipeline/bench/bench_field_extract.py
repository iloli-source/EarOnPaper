"""C8 フィールド録音モード ベンチ(Issue #60): 選択抽出率・誤音符化率の実測。

PD曲(正解MIDI)を合成レンダリング → 雑音を段階SNRで混入 → フィールドモード
(analyze_field→denoise→detect_events→select_events)で採譜し、正解と突合して
2指標を測る。初回は「記録のみ」(閾値は封緘せず、実測をベースラインとして残す)。

指標:
  - 選択抽出率(selective extraction rate) = 正解メロディノートの recall。
    雑音下で「音程成分をどれだけ拾えたか」。
  - 誤音符化率(false-note rate) = 出力ノートのうち正解に対応しない割合(=1-precision)。
    雑音起因の余剰ノート(幽霊)の率。
  - 雑音のみ誤発火(noise-only spurious) = 正解を含まない純雑音区間を採譜したとき
    出た余剰ノート数を、その曲の正解ノート数で正規化した率。「拾えないものは
    拾えないと正直に言う」の実測(理想は0)。

フィールドモードは単音(pYIN)経路のため、正解は各時刻の最高音から構成した単声
メロディ線とし、その**メロディ線だけを単音合成**して雑音を混ぜる。伴奏つきPD曲を
そのまま合成すると、pretty_midiの合成音+pYINが低音/最強倍音に張り付いてメロディを
拾えず(実測: furusato/sakuraでクリーンでも抽出≒0)、雑音耐性でなく「多声混合からの
単音抽出の限界」を測ることになるため。単声化して測ることで、C8の狙い=「音程成分を
雑音からどれだけ選択抽出できるか」を正解と揃った条件で計測する。多声混合そのものの
劣化はF-108の poly タグ(オンデマンド分解)側の課題として分離する。

合成方針: 本ベンチはメロディ線を自前で単音合成する(synth_melody。conftestの
render_melodyと同系の倍音+アタック/リリース合成)。多声そのままの合成が必要な
比較は bench_pd.py の render() 側にあり(編集禁止)、本ベンチは単音経路の評価に
特化するため多声合成は使わない。実行時間対策で 3曲 × 雑音3種 × SNR3段階、各曲先頭15秒。

使い方: .venv/bin/python bench/bench_field_extract.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pretty_midi

from earpipe.services.ear import detect_events, select_events
from earpipe.services.stem import analyze_field, denoise

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "tools" / "ai-ears" / "testdata" / "pd-corpus"
OUT = Path(__file__).resolve().parent / "bench_out"
SR = 22050
CLIP_SEC = 15.0   # 先頭15秒に統一。3曲×9条件=27採譜×pYIN のため実行時間対策(結果に明記)
ONSET_TOL = 0.10  # 音高一致+開始±100ms でマッチ(bench_pd と同じ基準)

# 3曲を選定した理由: メロディが明瞭な民謡3曲。furusato/sakura/hamabe は
# 単声メロディ+薄い伴奏で、単音抽出器(pYIN)の抽出対象(メロディ線)が明確。
# 厚い和音曲(moonlight等)は単音経路の評価対象として不適のため除外した。
SONGS = [
    ("furusato", "民謡・単声メロディ"),
    ("sakura", "民謡・単声メロディ"),
    ("hamabe_no_uta", "民謡・薄い伴奏"),
]

# 雑音3種。実フィールド録音の主要な妨害を代表させる
NOISE_KINDS = ("white", "pink", "percussion")
SNR_LEVELS = (20.0, 10.0, 5.0)


# --- 正解メロディ(各時刻の最高音)の抽出 ---------------------------------


_MIN_MELODY_DUR = 0.12  # これ未満のメロディ音は合成・検出とも不安定なので除外


def melody_notes(mid_path: Path, sec: float) -> list[tuple[float, float, int]]:
    """正解MIDIから、重なりのない単声スカイライン(各時刻の最高音)を返す。

    伴奏つきPD曲の上声(メロディ)を単音列として取り出す。時間軸を走査し、常に
    「その時刻に鳴っている最高音」を採用して重なりを解消するため、返り値は
    monophonic(同時発音なし)を保証する。単音抽出器の評価に用いるための正解。
    返り値: [(onset, offset, midi)]。
    """
    pm = pretty_midi.PrettyMIDI(str(mid_path))
    notes = [
        (float(n.start), float(min(n.end, sec)), int(n.pitch))
        for inst in pm.instruments
        if not inst.is_drum
        for n in inst.notes
        if n.start < sec and n.end > n.start
    ]
    if not notes:
        return []
    # 全ノートの開始/終了を境界にした区間ごとに、鳴っている最高音を選ぶ
    bounds = sorted({t for o, e, _ in notes for t in (o, e)})
    segments: list[tuple[float, float, int]] = []
    for a, b in zip(bounds[:-1], bounds[1:], strict=False):
        if b - a < 1e-4:
            continue
        mid = (a + b) / 2
        sounding = [m for o, e, m in notes if o <= mid < e]
        if not sounding:
            continue
        top = max(sounding)
        # 直前区間と同音・連続なら連結
        if segments and segments[-1][2] == top and abs(segments[-1][1] - a) < 1e-4:
            po, _pe, pm_ = segments[-1]
            segments[-1] = (po, b, pm_)
        else:
            segments.append((a, b, top))
    return [
        (o, e, m) for o, e, m in segments if e - o >= _MIN_MELODY_DUR
    ]


def synth_melody(melody: list[tuple[float, float, int]], sr: int = SR) -> np.ndarray:
    """単声メロディ線を倍音つきsineで合成する(音間に短い無音を挟む)。

    conftest.render_melody と同系の合成(実楽器に寄せた倍音+アタック/リリース)。
    正解メロディと1対1で対応する音声を作り、雑音耐性を正解と揃えて測るため。
    """
    if not melody:
        return np.zeros(sr, dtype=np.float64)
    total = max(e for _o, e, _m in melody) + 0.5
    y = np.zeros(int(total * sr), dtype=np.float64)
    harmonics = (1.0, 0.5, 0.25)
    for onset, offset, midi in melody:
        f = 440.0 * 2 ** ((midi - 69) / 12)
        t0, t1 = onset, max(onset, offset - 0.03)  # 末尾に30ms無音
        n0, n1 = int(t0 * sr), int(t1 * sr)
        n = n1 - n0
        if n <= 0:
            continue
        t = np.arange(n) / sr
        seg = np.zeros(n)
        for k, h in enumerate(harmonics, start=1):
            seg += 0.4 * h * np.sin(2 * np.pi * f * k * t)
        env = np.ones(n)
        a = min(int(0.006 * sr), n // 4)
        r = min(int(0.03 * sr), n // 4)
        if a > 0:
            env[:a] = np.linspace(0, 1, a)
        if r > 0:
            env[-r:] = np.linspace(1, 0, r)
        y[n0:n1] += seg * env
    peak = float(np.max(np.abs(y)))
    if peak > 0.9:
        y *= 0.9 / peak
    return y


# --- 雑音生成・混合 -------------------------------------------------------


def _white(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.standard_normal(n)


def _pink(n: int, rng: np.random.Generator) -> np.ndarray:
    spec = np.fft.rfft(rng.standard_normal(n))
    freqs = np.fft.rfftfreq(n, d=1.0 / SR)
    scale = np.ones_like(freqs)
    scale[1:] = freqs[1:] ** (-0.5)
    scale[0] = 0.0
    y = np.fft.irfft(spec * scale, n=n)
    return y / (np.max(np.abs(y)) + 1e-12)


def _percussion(n: int, rng: np.random.Generator) -> np.ndarray:
    """等間隔の減衰ノイズバースト(足音・打撃の代表)。"""
    y = np.zeros(n)
    burst = int(0.05 * SR)
    env = np.exp(-np.linspace(0, 8, burst))
    step = int(0.5 * SR)
    pos = 0
    while pos + burst < n:
        y[pos : pos + burst] += rng.standard_normal(burst) * env
        pos += step
    return y


def _make_noise(kind: str, n: int, rng: np.random.Generator) -> np.ndarray:
    if kind == "white":
        return _white(n, rng)
    if kind == "pink":
        return _pink(n, rng)
    return _percussion(n, rng)


def _mix_at_snr(signal: np.ndarray, noise: np.ndarray, snr_db: float) -> np.ndarray:
    noise = noise[: len(signal)]
    if len(noise) < len(signal):
        noise = np.pad(noise, (0, len(signal) - len(noise)))
    p_sig = float(np.mean(signal**2)) + 1e-18
    p_noise = float(np.mean(noise**2)) + 1e-18
    scale = np.sqrt(p_sig / (p_noise * 10 ** (snr_db / 10)))
    mixed = signal + noise * scale
    return mixed / (np.max(np.abs(mixed)) + 1e-12) * 0.9


# --- 採譜(フィールドモード)と指標 --------------------------------------


def _field_transcribe(y: np.ndarray) -> list[tuple[int, float, float]]:
    """フィールドモード相当の採譜: 解析→降噪→検出→SNR適応選択。"""
    analysis = analyze_field(y, SR)
    events = detect_events(denoise(y, SR), SR)
    events = select_events(events, analysis.snr_db)
    return [(e.midi, e.onset, e.offset) for e in events]


def _recall_and_falserate(
    truth: list[tuple[float, float, int]],
    pred: list[tuple[int, float, float]],
) -> tuple[float, float, int, int]:
    """(選択抽出率=recall, 誤音符化率=1-precision, matched, n_pred) を返す。"""
    used: set[int] = set()
    matched = 0
    for pm, po, _ in pred:
        best, best_d = None, ONSET_TOL
        for i, (to, _te, tm) in enumerate(truth):
            if i in used or tm != pm:
                continue
            d = abs(po - to)
            if d <= best_d:
                best, best_d = i, d
        if best is not None:
            used.add(best)
            matched += 1
    recall = matched / len(truth) if truth else 0.0
    false_rate = (len(pred) - matched) / len(pred) if pred else 0.0
    return recall, false_rate, matched, len(pred)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rng = np.random.default_rng(60)  # Issue #60
    rows = []
    for slug, cat in SONGS:
        mid = CORPUS / f"{slug}.mid"
        if not mid.exists():
            rows.append({"slug": slug, "status": "GT missing"})
            print(f"{slug}: GT missing")
            continue
        try:
            truth = melody_notes(mid, CLIP_SEC)
            clean = synth_melody(truth)
            import soundfile as sf

            sf.write(OUT / f"field_{slug}_melody.wav", clean, SR)

            # 雑音のみ誤発火(正解ゼロの純雑音を採譜して余剰ノート数を測る)
            noise_only = {}
            for kind in NOISE_KINDS:
                pure = _make_noise(kind, len(clean), rng)
                pure = pure / (np.max(np.abs(pure)) + 1e-12) * 0.5
                spur = len(_field_transcribe(pure))
                noise_only[kind] = round(spur / len(truth), 3) if truth else 0.0

            for kind in NOISE_KINDS:
                for snr in SNR_LEVELS:
                    noise = _make_noise(kind, len(clean), rng)
                    mixed = _mix_at_snr(clean, noise, snr)
                    pred = _field_transcribe(mixed)
                    recall, false_rate, matched, n_pred = _recall_and_falserate(truth, pred)
                    rows.append(
                        {
                            "slug": slug,
                            "cat": cat,
                            "noise": kind,
                            "snr_db": snr,
                            "gt_melody": len(truth),
                            "n_pred": n_pred,
                            "matched": matched,
                            "extract_rate": round(recall, 3),
                            "false_note_rate": round(false_rate, 3),
                            "noise_only_spurious": noise_only[kind],
                            "status": "ok",
                        }
                    )
                    print(
                        f"{slug} {kind} SNR{snr:.0f}: extract={recall:.3f} "
                        f"false={false_rate:.3f} noise_only={noise_only[kind]:.3f}"
                    )
        except Exception as e:  # 1曲の失敗で全体を止めない(失敗は正直に記録)
            rows.append({"slug": slug, "status": f"FAIL {type(e).__name__}: {e}"})
            print(f"{slug}: FAIL {e}")

    (OUT / "results_field_extract.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1)
    )
    _print_markdown(rows)
    print("saved results_field_extract.json")


def _print_markdown(rows: list[dict]) -> None:
    ok = [r for r in rows if r.get("status") == "ok"]
    if not ok:
        print("no ok rows")
        return
    print(f"\n# フィールド抽出ベンチ (曲×雑音×SNR, 各先頭{CLIP_SEC:.0f}s)")
    print("| 曲 | 雑音 | SNR(dB) | 正解メロディ | 選択抽出率 | 誤音符化率 | 雑音のみ誤発火 |")
    print("|---|---|---|---|---|---|---|")
    for r in ok:
        print(
            f"| {r['slug']} | {r['noise']} | {r['snr_db']:.0f} | {r['gt_melody']} | "
            f"{r['extract_rate']:.3f} | {r['false_note_rate']:.3f} | "
            f"{r['noise_only_spurious']:.3f} |"
        )
    # SNR別の平均(全曲・全雑音)
    print("\n## SNR別平均(全曲×全雑音)")
    print("| SNR(dB) | 選択抽出率 平均 | 誤音符化率 平均 |")
    print("|---|---|---|")
    for snr in SNR_LEVELS:
        sub = [r for r in ok if r["snr_db"] == snr]
        if sub:
            er = sum(r["extract_rate"] for r in sub) / len(sub)
            fr = sum(r["false_note_rate"] for r in sub) / len(sub)
            print(f"| {snr:.0f} | {er:.3f} | {fr:.3f} |")


if __name__ == "__main__":
    main()
