#!/usr/bin/env python3
"""AIの耳ハーネスの自己検証。

正解が分かっているテスト: 既知メロディのMIDIをsine合成した音源に対し、
(1) 同一MIDI → 高スコア
(2) 音高を数個ずらした改変MIDI → 低下
(3) リズムを崩した改変MIDI → 低下
(4) 無関係MIDI → 大幅低下
のスコア勾配が出ることを確認する。
"""

import copy
import json
import random
from pathlib import Path

import numpy as np
import pretty_midi
import soundfile as sf

import ears

OUT = Path(__file__).parent / "testdata"
OUT.mkdir(exist_ok=True)

# きらきら星 + 変化句 の16小節相当メロディ (BPM=100, 4/4)
MELODY = [  # (MIDIノート, 拍長)
    (60, 1), (60, 1), (67, 1), (67, 1), (69, 1), (69, 1), (67, 2),
    (65, 1), (65, 1), (64, 1), (64, 1), (62, 1), (62, 1), (60, 2),
    (67, 1), (67, 1), (65, 1), (65, 1), (64, 1), (64, 1), (62, 2),
    (67, 0.5), (69, 0.5), (67, 1), (65, 1), (64, 1), (62, 0.5), (60, 0.5), (62, 1), (60, 2),
]
BPM = 100


def build_midi(melody, bpm=BPM) -> pretty_midi.PrettyMIDI:
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    inst = pretty_midi.Instrument(program=0)
    beat = 60.0 / bpm
    t = 0.0
    for pitch, beats in melody:
        inst.notes.append(pretty_midi.Note(velocity=90, pitch=pitch,
                                           start=t, end=t + beats * beat * 0.95))
        t += beats * beat
    pm.instruments.append(inst)
    return pm


def render_sine(pm, path: Path):
    """MIDIをサイン波で音源化(ears側のsynthesizeとは独立の実装で交差検証)。"""
    sr = ears.SR
    end = pm.get_end_time() + 0.5
    audio = np.zeros(int(end * sr))
    for inst in pm.instruments:
        for n in inst.notes:
            f = 440.0 * 2 ** ((n.pitch - 69) / 12)
            i0, i1 = int(n.start * sr), int(n.end * sr)
            tt = np.arange(i1 - i0) / sr
            seg = 0.5 * np.sin(2 * np.pi * f * tt)
            env = np.minimum(1, np.minimum(np.arange(len(seg)) / (0.01 * sr),
                                           (len(seg) - np.arange(len(seg))) / (0.05 * sr)))
            audio[i0:i1] += seg * np.clip(env, 0, 1)
    peak = np.abs(audio).max()
    if peak > 0:
        audio /= peak
    sf.write(path, audio, sr)
    return path


def mutate_pitches(pm, n_mutations=8, seed=7):
    rng = random.Random(seed)
    pm2 = copy.deepcopy(pm)
    notes = pm2.instruments[0].notes
    for idx in rng.sample(range(len(notes)), min(n_mutations, len(notes))):
        notes[idx].pitch += rng.choice([-4, -3, 3, 4, 6])
    return pm2


def mutate_rhythm(pm, seed=11):
    # 注(レビューLOW-3): deepcopy後のNoteをin-place変更している。呼び出し元のpmは不変。
    # プロジェクトの不変原則の例外だがテスト生成スクリプトのため許容(明記して記録)。
    rng = random.Random(seed)
    pm2 = copy.deepcopy(pm)
    for n in pm2.instruments[0].notes:
        shift = rng.uniform(-0.28, 0.28)
        n.start = max(0.0, n.start + shift)
        n.end = max(n.start + 0.05, n.end + shift)
    return pm2


def unrelated_midi():
    rng = random.Random(3)
    melody = [(rng.randint(48, 84), rng.choice([0.25, 0.5, 1])) for _ in range(60)]
    return build_midi(melody, bpm=140)


class Args:
    def __init__(self, original, transcription):
        self.original = str(original)
        self.transcription = str(transcription)
        self.report = None


def run_case(name, audio_path, pm_variant):
    midi_path = OUT / f"{name}.mid"
    pm_variant.write(str(midi_path))
    result = ears.cmd_compare(Args(audio_path, midi_path))
    return {k: result[k]["score"] for k in ("chroma", "onset", "tempo", "health")} | {
        "overall": result["overall"]["score"]}


def main():
    pm = build_midi(MELODY)
    ref_midi = OUT / "reference.mid"
    pm.write(str(ref_midi))
    audio_path = render_sine(pm, OUT / "reference.wav")

    cases = {
        "same(同一MIDI)": pm,
        "pitch_mut(音高改変8箇所)": mutate_pitches(pm),
        "rhythm_mut(リズム崩し)": mutate_rhythm(pm),
        "unrelated(無関係MIDI)": unrelated_midi(),
    }
    results = {}
    for name, variant in cases.items():
        key = name.split("(")[0]
        results[name] = run_case(key, audio_path, variant)

    print("\n===== 感度検証サマリー =====")
    print(json.dumps(results, ensure_ascii=False, indent=2))

    same = results["same(同一MIDI)"]["overall"]
    pitch = results["pitch_mut(音高改変8箇所)"]["overall"]
    rhythm = results["rhythm_mut(リズム崩し)"]["overall"]
    unrel = results["unrelated(無関係MIDI)"]["overall"]

    checks = {
        "同一MIDIが最高スコア": same == max(same, pitch, rhythm, unrel),
        "同一 > 音高改変": same > pitch,
        "同一 > リズム崩し": same > rhythm,
        "改変 > 無関係 (音高)": pitch > unrel,
        "改変 > 無関係 (リズム)": rhythm > unrel,
        "同一が0.8以上": same >= 0.8,
        "無関係が0.6未満": unrel < 0.6,
    }
    print("\n===== 判定 =====")
    ok = True
    for k, v in checks.items():
        print(("PASS " if v else "FAIL ") + k)
        ok &= v
    return results, checks, ok


if __name__ == "__main__":
    results, checks, ok = main()
    raise SystemExit(0 if ok else 1)
