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

    # 3) 同時発音の異常な密度(1秒窓での平均同時ノート数)
    density_penalty = 0.0
    if len(notes) > 1:
        total = max(ends.max() - starts.min(), 1e-6)
        density = len(notes) / total
        if density > 25:
            issues.append(f"音符密度が異常({density:.0f}個/秒) — 幽霊音符の疑い")
            # 指摘だけでなく減点にも反映する(テストで発見したバグの修正 2026-07-19:
            # 旧実装は密度を指摘に載せるのみでスコアに反映せず、密なゴミ出力が高得点になり得た)
            density_penalty = min(0.6, 0.4 + (density - 25) / 100)
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

WEIGHTS = {"chroma": 0.4, "onset": 0.3, "tempo": 0.1, "health": 0.2}


def overall(results: dict) -> dict:
    usable = {k: w for k, w in WEIGHTS.items() if results[k]["score"] is not None}
    wsum = sum(usable.values())
    total = sum(results[k]["score"] * w for k, w in usable.items()) / wsum
    excluded = [k for k in WEIGHTS if k not in usable]
    if total >= 0.80:
        verdict = "高一致 — 手直しは軽い可能性(人の耳での確認を推奨)"
    elif total >= 0.60:
        verdict = "部分一致 — それなりの手直しが必要な水準"
    else:
        verdict = "低一致 — 大幅な手直しか作り直しが必要な水準"
    return {"score": round(float(total), 4), "verdict": verdict,
            "weights": WEIGHTS, "excluded_metrics": excluded}


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
             "tempo": "テンポ整合", "health": "譜面健全性"}
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
    pc.add_argument("--report", help="Markdownレポートの出力先")
    pc.set_defaults(func=cmd_compare)

    pi = sub.add_parser("inspect", help="譜面健全性のみ検査(音源不要)")
    pi.add_argument("--transcription", required=True, help="採譜結果(MIDI)")
    pi.set_defaults(func=cmd_inspect)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
