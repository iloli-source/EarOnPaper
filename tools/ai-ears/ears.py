#!/usr/bin/env python3
"""AIの耳 — 採譜結果の自動評価ハーネス。

元音源と採譜結果(MIDI)を比較し、音楽家の耳の代わりに数値で品質を測る。
使い方:
    .venv/bin/python ears.py compare --original song.wav --transcription result.mid --report report.md
    .venv/bin/python ears.py inspect --transcription result.mid   # 譜面健全性のみ(音源不要)
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

SR = 22050
CHROMA_HOP = 512
ONSET_TOLERANCE = 0.10  # 秒。音の出だし一致とみなす許容窓


# ---------------------------------------------------------------- 音声・MIDI読み込み

def load_audio(path: str):
    import librosa

    y, sr = librosa.load(path, sr=SR, mono=True)
    if len(y) == 0:
        raise ValueError(f"音声が空です: {path}")
    return y, sr


def load_midi(path: str):
    import pretty_midi

    pm = pretty_midi.PrettyMIDI(path)
    notes = [n for inst in pm.instruments if not inst.is_drum for n in inst.notes]
    if not notes:
        raise ValueError(f"MIDIに音符がありません: {path}")
    return pm, notes


def synthesize_midi(pm) -> np.ndarray:
    """採譜MIDIを音に戻す(サイン波合成、外部依存なし)。"""
    audio = pm.synthesize(fs=SR)
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak
    return audio


# ---------------------------------------------------------------- 指標1: 音高一致度

def chroma_similarity(y_orig: np.ndarray, y_synth: np.ndarray) -> dict:
    """クロマグラム(12音クラスの強度分布)をDTWで整列して類似度を測る。

    「メロディ・和音の音の高さの並びがどれだけ一致しているか」の指標。
    1.0=完全一致相当 / 0.0=無関係。
    """
    import librosa

    c1 = librosa.feature.chroma_cqt(y=y_orig, sr=SR, hop_length=CHROMA_HOP)
    c2 = librosa.feature.chroma_cqt(y=y_synth, sr=SR, hop_length=CHROMA_HOP)
    # 正規化(列ごと)
    c1 = librosa.util.normalize(c1, axis=0)
    c2 = librosa.util.normalize(c2, axis=0)
    D, wp = librosa.sequence.dtw(X=c1, Y=c2, metric="cosine")
    # 経路上の平均コサイン距離 → 類似度へ。
    # 注(レビューLOW-1): D[-1,-1]は累積コストで、len(wp)割りは「平均ステップコスト」の近似。
    # 短い/ノイズ音声では1.0を超えうるためclipで[0,1]に制限している。
    # 「1.0=完全一致」の解釈は距離が[0,1]に収まる場合のみ厳密に成立する。
    path_cost = D[-1, -1] / len(wp)
    similarity = float(np.clip(1.0 - path_cost, 0.0, 1.0))
    return {
        "score": round(similarity, 4),
        "explanation": (
            "音の高さの並び(ドレミの流れ)が元音源とどれだけ一致するか。"
            "1.0に近いほど一致。0.85以上=ほぼ同じ曲に聴こえる水準、"
            "0.6-0.85=部分的に一致、0.6未満=別物の可能性。"
        ),
    }


# ---------------------------------------------------------------- 指標2: 音の出だし一致

def onset_match(y_orig: np.ndarray, notes) -> dict:
    """元音源の「音の出だし」(オンセット)と採譜の音符開始時刻の突合。F値近似。"""
    import librosa

    onset_times = librosa.onset.onset_detect(y=y_orig, sr=SR, units="time")
    note_starts = np.array(sorted({round(n.start, 3) for n in notes}))
    if len(onset_times) == 0 or len(note_starts) == 0:
        return {"score": 0.0, "precision": 0.0, "recall": 0.0,
                "explanation": "音の出だしが検出できませんでした。"}

    def matched(a: np.ndarray, b: np.ndarray) -> int:
        used = np.zeros(len(b), dtype=bool)
        count = 0
        for t in a:
            idx = np.argmin(np.abs(b - t))
            if not used[idx] and abs(b[idx] - t) <= ONSET_TOLERANCE:
                used[idx] = True
                count += 1
        return count

    hit_recall = matched(onset_times, note_starts)      # 元音源の出だしが採譜に拾われた数
    hit_prec = matched(note_starts, onset_times)        # 採譜の音符が実音に対応する数
    recall = hit_recall / len(onset_times)
    precision = hit_prec / len(note_starts)
    f1 = 0.0 if (precision + recall) == 0 else 2 * precision * recall / (precision + recall)
    return {
        "score": round(float(f1), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "explanation": (
            "音の出だしのタイミング(±0.1秒)がどれだけ対応しているか。"
            "precision=採譜側の音符のうち実在の音に対応する割合(低いと幽霊音符が多い)、"
            "recall=実際の音のうち採譜に拾われた割合(低いと取りこぼしが多い)。"
        ),
    }


# ---------------------------------------------------------------- 指標3: テンポ・拍整合

def tempo_consistency(y_orig: np.ndarray, pm) -> dict:
    """元音源のテンポ推定と採譜のテンポ設定の整合。倍/半テンポは許容して比較。

    推定はonset強度の自己相関ベース(feature.tempo)を第一とし、beat_trackを予備に使う。
    どちらも推定不能な場合はscore=Noneを返し、総合スコアから除外する(0点で罰しない)。
    """
    import librosa

    env = librosa.onset.onset_strength(y=y_orig, sr=SR)
    tempo_audio = float(np.atleast_1d(librosa.feature.tempo(onset_envelope=env, sr=SR))[0])
    if tempo_audio <= 0:
        bt, _ = librosa.beat.beat_track(y=y_orig, sr=SR)
        tempo_audio = float(np.atleast_1d(bt)[0])
    tempi = pm.get_tempo_changes()[1]
    tempo_midi = float(np.median(tempi)) if len(tempi) else 120.0

    if tempo_audio <= 0 or tempo_midi <= 0:
        return {
            "score": None,
            "tempo_audio_bpm": round(tempo_audio, 1),
            "tempo_midi_bpm": round(tempo_midi, 1),
            "explanation": "元音源のテンポが推定できなかったため、この指標は評価不能(総合から除外)。",
        }
    candidates = [tempo_midi, tempo_midi * 2, tempo_midi / 2]
    ratio_err = min(abs(c - tempo_audio) / tempo_audio for c in candidates)
    score = float(np.clip(1.0 - ratio_err, 0.0, 1.0))
    return {
        "score": round(score, 4),
        "tempo_audio_bpm": round(tempo_audio, 1),
        "tempo_midi_bpm": round(tempo_midi, 1),
        "explanation": (
            "曲の速さ(テンポ)の推定が元音源と合っているか。倍速/半分の解釈は許容。"
            "低いと採譜のリズム格子全体がずれている可能性。"
        ),
    }


# ---------------------------------------------------------------- 指標5: 音域一致(オクターブ検出)

def register_match(y_orig: np.ndarray, notes) -> dict:
    """元音源の基音音域と採譜の音域の一致(オクターブ誤り検出)。指標v2.1。

    chroma系はオクターブ不変のため、オクターブを間違えた採譜でも高得点になる。
    v2(音価加重中央値の比較)は全音+12は検出できたが、部分オクターブ誤り
    (40%上げ/交互/長anchor挿入)は中央値が動かず素通しした(func-r2-output P0)。
    v2.1はノート単位のオクターブ整合分布で検出する:
      各音符の時間窓内の元音源f0のうち、音名(chroma)が一致するフレームとの
      オクターブ差 k を求め、k≠0 の音符の比率(外れ率)でペナルティを課す。
      音名一致フィルタにより多声の和声音は評価対象外となり誤罰を避ける。
      実音楽のオクターブ重ね(15%まで)は許容フロアとして正常扱い。
    大域中央値の比較も維持し、スコアは min(大域, 分布) の保守側を採る。
    """
    import librosa

    if not notes:
        return {"score": None, "explanation": "採譜に音符がないため評価不能(総合から除外)。"}
    f0, voiced_flag, _ = librosa.pyin(
        y_orig, fmin=27.5, fmax=4186.0, sr=SR, frame_length=2048
    )
    if f0 is None:
        return {"score": None, "explanation": "元音源の基音が推定できないため評価不能(総合から除外)。"}
    times = librosa.times_like(f0, sr=SR)
    voiced_mask = voiced_flag & np.isfinite(f0)
    voiced = f0[voiced_mask]
    if voiced.size < 10:
        return {"score": None, "explanation": "元音源の基音が推定できないため評価不能(総合から除外)。"}
    f0_midi = librosa.hz_to_midi(f0)
    orig_midi = float(np.median(librosa.hz_to_midi(voiced)))

    # --- 大域(v2互換): 音価加重中央値のずれ
    durations = np.array([max(n.end - n.start, 1e-3) for n in notes])
    pitches = np.array([n.pitch for n in notes], dtype=float)
    order = np.argsort(pitches)
    cum = np.cumsum(durations[order])
    est_midi = float(pitches[order][np.searchsorted(cum, cum[-1] / 2.0)])
    offset = est_midi - orig_midi
    dead, full = 6.0, 12.0
    score_global = float(np.clip(1.0 - max(0.0, abs(offset) - dead) / (full - dead), 0.0, 1.0))

    # --- 分布(v2.1): ノート単位のオクターブ整合
    CHROMA_TOL = 1.5   # 音名一致とみなす円距離(半音)
    MIN_FRAMES = 3     # 評価に必要な一致フレーム数
    FLOOR, SLOPE = 0.15, 0.35  # 外れ率15%まで正常(オクターブ重ね許容)、50%で0点
    outliers = 0
    evaluable = 0
    for n in notes:
        sel = voiced_mask & (times >= n.start) & (times <= n.end)
        if not np.any(sel):
            continue
        fm = f0_midi[sel]
        diff = np.asarray(n.pitch, dtype=float) - fm
        circ = np.abs((diff + 6.0) % 12.0 - 6.0)  # 音名(mod12)の円距離
        match = fm[circ <= CHROMA_TOL]
        if match.size < MIN_FRAMES:
            continue
        k = int(np.round(float(np.median(np.asarray(n.pitch, dtype=float) - match)) / 12.0))
        evaluable += 1
        if k != 0:
            outliers += 1
    if evaluable >= 5:
        outlier_ratio = outliers / evaluable
        score_partial = float(np.clip(1.0 - max(0.0, outlier_ratio - FLOOR) / SLOPE, 0.0, 1.0))
        score = min(score_global, score_partial)
        ratio_out = round(outlier_ratio, 3)
    else:
        # 評価可能ノートが少なすぎる場合は大域のみ(限界を明示)
        score = score_global
        ratio_out = None

    return {
        "score": round(score, 4),
        "offset_semitones": round(offset, 1),
        "octave_outlier_ratio": ratio_out,
        "evaluable_notes": evaluable,
        "explanation": (
            "音の高さの『絶対的な高さ(オクターブ)』が元音源と合っているか。"
            "音名一致(chroma)はオクターブ違いを見抜けないため、この指標で補完する。"
            "v2.1: 全体のずれに加え、音符単位のオクターブ外れ率(部分的な誤り)も検出する。"
            "外れ率15%までは実音楽のオクターブ重ねとして許容。"
        ),
    }


# ---------------------------------------------------------------- 指標4: 譜面健全性(音源不要)

def score_health(pm, notes) -> dict:
    """譜面としての内部健全性。音源がなくても検査できる項目。"""
    issues = []
    starts = np.array([n.start for n in notes])
    ends = np.array([n.end for n in notes])
    pitches = np.array([n.pitch for n in notes])
    durations = ends - starts

    # 1) 極端に短い音符(64分音符相当以下)の比率
    tempi = pm.get_tempo_changes()[1]
    bpm = float(np.median(tempi)) if len(tempi) else 120.0
    sixtyfourth = (60.0 / bpm) / 16.0
    too_short = float(np.mean(durations < sixtyfourth))
    if too_short > 0.15:
        issues.append(f"極端に短い音符(64分相当未満)が{too_short:.0%} — リズムが砕けている兆候")

    # 2) 音域の妥当性 (A0=21 〜 C8=108 の外)
    out_of_range = float(np.mean((pitches < 21) | (pitches > 108)))
    if out_of_range > 0:
        issues.append(f"楽器の音域外の音符が{out_of_range:.0%}")

    # 3) 音符密度(1秒あたりの音符数)。ハード閾値の崖は攻撃可能
    #    (旧25個/秒の崖: 20個/秒に整えた幽霊大群が素通りした — func-r1-fable-output P0)。
    #    12個/秒から連続的にペナルティを増やす(高速な実音楽でも概ね10個/秒未満)。
    density_penalty = 0.0
    if len(notes) > 1:
        total = max(ends.max() - starts.min(), 1e-6)
        density = len(notes) / total
        density_penalty = float(np.clip((density - 12.0) / 25.0, 0.0, 0.6))
        if density_penalty > 0.05:
            issues.append(f"音符密度が異常({density:.0f}個/秒) — 幽霊音符の疑い")
    # 4) 長い無音への音符配置は compare 側でしか判定できないため対象外(README参照)

    penalty = min(1.0, too_short * 2 + out_of_range * 3 + density_penalty
                  + (0.3 if len(issues) >= 3 else 0.0))
    score = float(np.clip(1.0 - penalty, 0.0, 1.0))
    return {
        "score": round(score, 4),
        "note_count": int(len(notes)),
        "issues": issues,
        "explanation": (
            "譜面として成立しているかの内部検査。音の高さが合っていても、"
            "細かすぎる音符・音域外・幽霊音符が多いと「直すのが大変な譜面」になる。"
        ),
    }


# ---------------------------------------------------------------- 総合

# 指標v2 (2026-07-19, Issue #48): register(オクターブ検出)を追加し重みを再配分。
# 指標v2.1 (2026-07-19, Issue #52): registerをノート単位オクターブ整合分布に是正し、
#   致命的欠陥フラグ(register/health≤0.3)でverdictの誤標識(高一致)を解消。
# v1: {chroma 0.4, onset 0.3, tempo 0.1, health 0.2}
# 較正変更のため、v1の数字との直接比較は不可(README「指標バージョン」参照)。
# 較正メモ: health/registerは「欠陥の不在」を測る指標で類似度を測らないため
# (無関係な曲でも1.0になり得る)、判別力のあるchroma/onsetの重みを主に保つ。
WEIGHTS = {"chroma": 0.35, "onset": 0.35, "tempo": 0.05, "health": 0.125, "register": 0.125}
# 正解MIDIあり運用: 楽譜レベルのリズム指標 score_rhythm を総合に組み込む(重み最大)。
WEIGHTS_WITH_REF = {
    "chroma": 0.2, "onset": 0.2, "tempo": 0.05,
    "health": 0.1, "register": 0.1, "score_rhythm": 0.35,
}


def overall(results: dict) -> dict:
    weights = WEIGHTS_WITH_REF if "score_rhythm" in results else WEIGHTS
    usable = {k: w for k, w in weights.items()
              if results.get(k, {}).get("score") is not None}
    wsum = sum(usable.values())
    total = sum(results[k]["score"] * w for k, w in usable.items()) / wsum
    excluded = [k for k in weights if k not in usable]
    # 致命的欠陥フラグ: 個別指標が重大水準で発火している場合、総合点が高くても
    # 「高一致」と標識しない(v2.1: 部分オクターブ誤りの誤標識解消 func-r2-output P1)。
    critical = []
    reg = results.get("register", {})
    if reg.get("score") is not None and reg["score"] <= 0.3:
        critical.append("オクターブ不整合")
    hl = results.get("health", {})
    if hl.get("score") is not None and hl["score"] <= 0.3:
        critical.append("譜面健全性")
    if total >= 0.80 and not critical:
        verdict = "高一致 — 手直しは軽い可能性(人の耳での確認を推奨)"
    elif critical and total >= 0.60:
        # 総合が中〜高なのに致命的欠陥指標が発火 → 高めのスコアで欠陥を隠さない
        verdict = (f"要確認({'・'.join(critical)}) — 総合{total:.2f}だが致命的欠陥指標が発火。"
                   "通常の一致判定は保留")
    elif total >= 0.60:
        verdict = "部分一致 — それなりの手直しが必要な水準"
    else:
        verdict = "低一致 — 大幅な手直しか作り直しが必要な水準"
    return {"score": round(float(total), 4), "verdict": verdict,
            "critical_flags": critical,
            "weights": weights, "excluded_metrics": excluded}


# ---------------------------------------------------------------- レポート

def make_report(result: dict, original: str, transcription: str) -> str:
    lines = [
        "# AIの耳 評価レポート",
        "",
        f"- 元音源: `{original}`",
        f"- 採譜結果: `{transcription}`",
        f"- 総合スコア: **{result['overall']['score']}** — {result['overall']['verdict']}",
        "",
        "| 指標 | スコア | 意味 |",
        "|---|---|---|",
    ]
    label = {"chroma": "音高一致度", "onset": "音の出だし一致",
             "tempo": "テンポ整合", "health": "譜面健全性",
             "register": "音域一致(オクターブ)", "score_rhythm": "楽譜レベルリズム(正解あり)"}
    for key, name in label.items():
        if key in result:
            r = result[key]
            lines.append(f"| {name} | {r['score']} | {r['explanation']} |")
    health = result.get("health", {})
    if health.get("issues"):
        lines += ["", "## 譜面健全性の指摘", ""]
        lines += [f"- {i}" for i in health["issues"]]
    lines += [
        "",
        "> 注意: このスコアは事前スクリーニングであり、音楽家の耳の代替ではない。",
        "> 「使える譜面か」の最終判定は人間のレビューで行う。",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI

def cmd_compare(args):
    y_orig, _ = load_audio(args.original)
    pm, notes = load_midi(args.transcription)
    y_synth = synthesize_midi(pm)

    result = {
        "chroma": chroma_similarity(y_orig, y_synth),
        "onset": onset_match(y_orig, notes),
        "tempo": tempo_consistency(y_orig, pm),
        "health": score_health(pm, notes),
        "register": register_match(y_orig, notes),
    }
    reference = getattr(args, "reference", None)
    if reference:
        from score_metrics import score_rhythm

        gt_pm, _ = load_midi(str(reference))
        sr_result = score_rhythm(gt_pm, pm)
        result["score_rhythm"] = {
            "score": round(float(sr_result["total"]), 4),
            **{k: v for k, v in sr_result.items() if k != "total"},
            "explanation": (
                "正解楽譜との拍単位の一致(楽譜レベルのリズム品質)。"
                "正解MIDIがある運用でのみ算出され、総合スコアに最大重みで組み込まれる。"
            ),
        }
    result["overall"] = overall(result)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.report:
        Path(args.report).write_text(make_report(result, args.original, args.transcription))
        print(f"\nレポート保存: {args.report}", file=sys.stderr)
    return result


def cmd_inspect(args):
    pm, notes = load_midi(args.transcription)
    result = {"health": score_health(pm, notes)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    p = argparse.ArgumentParser(description="AIの耳 — 採譜結果の自動評価")
    sub = p.add_subparsers(dest="command", required=True)

    pc = sub.add_parser("compare", help="元音源と採譜MIDIを比較")
    pc.add_argument("--original", required=True, help="元音源(wav/mp3等)")
    pc.add_argument("--transcription", required=True, help="採譜結果(MIDI)")
    pc.add_argument("--reference", help="正解MIDI(あればscore_rhythmを総合に組み込む)")
    pc.add_argument("--report", help="Markdownレポートの出力先")
    pc.set_defaults(func=cmd_compare)

    pi = sub.add_parser("inspect", help="譜面健全性のみ検査(音源不要)")
    pi.add_argument("--transcription", required=True, help="採譜結果(MIDI)")
    pi.set_defaults(func=cmd_inspect)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
