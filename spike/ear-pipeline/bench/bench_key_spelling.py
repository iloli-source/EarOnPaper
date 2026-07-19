"""C4受入計測: 主調正解率と臨時記号の綴り一致率をPD15曲で判定する(Issue #58)。

受入条件(C4):
  (a) キー推定の主調正解率 ≥ 80%
  (b) 臨時記号の綴り一致率 ≥ 90%

前提: basic-pitch(採譜)は既に走っており、量子化MIDIが bench_out/*_spike.mid に
キャッシュされている。本ベンチはそのキャッシュのみを読むため basic-pitch venv 不要。
無ければ bench_pd.py で先に生成する(このベンチは生成しない)。

------------------------------------------------------------------------------
正解(truth)の作り方 — 手順と限界を正直に記録する
------------------------------------------------------------------------------
主調の正解:
  第一候補として正解MIDIの key_signature イベント
  (pretty_midi.key_signature_changes)を使う。PD15曲は全曲がこのイベントを
  持つことを確認済みなので、全曲このイベントを一次ソースとする。
  加えて、各曲について music21 の analyze('key') を「クリーンな正解MIDIの
  ノート列」に適用した結果と突合し、両者が一致することを併記する(相互検証)。
  ユーザー提供2曲はファイル名に調が入っている:
    Turkish_March_K331_C-Am … C-dur / a-moll 系(調号0=key_number 0/21 と整合)
    Romanze_Castellana_G-Em … G-dur / e-moll 系(調号1#=key_number 7/16 と整合)
  これらもファイル名の調域と key_signature が一致することを突合に用いる。

主調正解の判定:
  主調=「主音(pitch class)+旋法(major/minor)」の一致を厳密な正解とする。
  平行調(相対長短調。例 C-dur↔a-moll)は同じ調号だが主音・旋法が異なるため
  「不正解」として扱う(粉飾しない)。参考として、調号(sharps)の一致率も併記する
  (綴り・記譜に効くのは主に調号であるため、実務的な意味を持つ副指標)。

綴り一致率の正解(代理):
  正解MusicXMLは存在しない。そこで代理として
  「正解MIDIのノートを、正解調のもとで綴った結果」を参照綴りとする(spell_midi)。
  自社側は「自社が実際に出力する綴り」= spike_mid の各ノートを
  spelling.py で【推定調】のもとに綴った結果とする。参照は【正解調】、自社は
  【推定調】で綴るため、キー推定が外れれば綴りも外れる — この非対称が本指標の肝で、
  参照・自社を同一調で綴って自明に100%になる水増しを避けている。
  MIDIノート番号でマッチしたノート同士の綴り(F#かG♭か等)を比較する。
  ★真の版面綴りではなく「正解調のもとでの標準綴り」を真とみなす代理指標である。
  参照側が臨時記号を持つノート(alter != 0)に対象を限定して分母を数える
  (ナチュラル同士の自明一致で率が水増しされるのを避けるため)。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import music21
import pretty_midi

from bench.bench_pd import CLIP_SEC, SONGS
from earpipe.contracts import QuantizedNote
from earpipe.services.notate.spelling import estimate_key, spell_midi

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "tools" / "ai-ears" / "testdata" / "pd-corpus"
OUT = CORPUS / "bench_out"

KEY_ACCURACY_TARGET = 0.80
SPELLING_MATCH_TARGET = 0.90
_BEATS_PER_SEC = 2.0  # 秒→拍の便宜換算(estimate_keyは相対音価のみ使うため係数は無害)


def _truth_key_from_midi(gt_path: Path) -> music21.key.Key | None:
    """正解MIDIの key_signature イベントから正解調を得る(無ければ None)。"""
    pm = pretty_midi.PrettyMIDI(str(gt_path))
    changes = pm.key_signature_changes
    if not changes:
        return None
    name = pretty_midi.key_number_to_key_name(changes[0].key_number)  # 'C Major'/'D minor'
    tonic, mode = name.split()
    return music21.key.Key(tonic.replace("b", "-"), mode.lower())


def _music21_key_from_midi(gt_path: Path) -> music21.key.Key:
    """クリーンな正解MIDIに music21 analyze('key') を適用した相互検証用の調。

    注意: music21 analyze はMIDIから相対長短調を弁別できず、実測でユーザー提供2曲・
    promenade で調号ごと誤る(A major/E major/F major を返す)。よって本値は
    「調号(sharps)が一致するか」の弱い相互検証にのみ使い、主調正解の一次ソースは
    key_signature イベント、ユーザー提供2曲はファイル名の調域を優先突合とする。
    """
    return music21.converter.parse(str(gt_path)).analyze("key")


# ユーザー提供2曲はファイル名に調が埋め込まれている(調号の一次突合に使う)。
_FILENAME_KEY_SHARPS = {
    "user-samples/Turkish_March_K331_C-Am": 0,  # C-dur / a-moll = 調号0
    "user-samples/Romanze_Castellana_G-Em": 1,  # G-dur / e-moll = 調号1#
}


def _clip_notes(pm: pretty_midi.PrettyMIDI, sec: float) -> list[tuple[float, float, int]]:
    """先頭sec秒の非ドラムノート(start, dur, midi)を返す(bench_pdのCLIP方針に合わせる)。"""
    notes = []
    for inst in pm.instruments:
        if inst.is_drum:
            continue
        for n in inst.notes:
            if n.start < sec:
                notes.append((n.start, min(n.end, sec) - n.start, int(n.pitch)))
    return sorted(notes)


def _to_qnotes(clipped: list[tuple[float, float, int]]) -> list[QuantizedNote]:
    return [
        QuantizedNote(
            start_beats=s * _BEATS_PER_SEC,
            dur_beats=max(d * _BEATS_PER_SEC, 0.25),
            midi=m,
            confidence=0.9,
        )
        for s, d, m in clipped
    ]


def _key_label(key: music21.key.Key) -> str:
    return f"{key.tonic.name} {key.mode}"


def _spelling_match(
    ref_notes: list[tuple[float, float, int]],
    pred_notes: list[tuple[float, float, int]],
    truth_key: music21.key.Key,
    est_key: music21.key.Key,
) -> tuple[int, int]:
    """臨時記号ノートに限定した綴り一致(matched, total)を返す。

    参照側=正解MIDIノートを【正解調】で綴る。自社側=spike_midノートを自社が実際に
    出力する綴り=【推定調】で綴る(spell_midi)。MIDI番号でマッチしたノート同士の
    綴りを比較し、参照側が臨時記号(alter!=0)のものだけを分母に数える。
    推定調が外れれば綴りも外れるため、自明な100%にはならない。
    """
    ref_by_midi: dict[int, str] = {}
    for _s, _d, m in ref_notes:
        ref_by_midi.setdefault(m, spell_midi(m, truth_key).name)
    pred_by_midi: dict[int, str] = {}
    for _s, _d, m in pred_notes:
        pred_by_midi.setdefault(m, spell_midi(m, est_key).name)

    matched = total = 0
    for midi, ref_name in ref_by_midi.items():
        ref_pitch = music21.pitch.Pitch(ref_name)
        if ref_pitch.alter == 0:
            continue  # 臨時記号を持たない音は自明一致になるため対象外
        if midi not in pred_by_midi:
            continue  # 自社出力に現れなかった音は綴り比較の対象にしない
        total += 1
        if pred_by_midi[midi] == ref_name:
            matched += 1
    return matched, total


def main() -> int:
    rows = []
    for rel, slug, cat in SONGS:
        gt_path = CORPUS / f"{rel}.mid"
        spike_path = OUT / f"{slug}_spike.mid"
        if not gt_path.exists():
            rows.append({"slug": slug, "cat": cat, "status": "GT missing"})
            continue
        if not spike_path.exists():
            rows.append({"slug": slug, "cat": cat, "status": "spike cache missing"})
            continue

        truth_key = _truth_key_from_midi(gt_path)
        source = "key_signature"
        if truth_key is None:
            truth_key = _music21_key_from_midi(gt_path)
            source = "music21_analyze"
        m21_key = _music21_key_from_midi(gt_path)
        # 相互検証は「主音のピッチクラス(平行調も許容)」で見る。music21 analyze は
        # (1)相対長短調で主音を誤る (2)異名同音で調号符号を反転する(Db↔C#)ため、
        # sharps数値の一致で判定すると健全な正解まで✗になる。ピッチクラス+平行調なら
        # 異名同音・長短取り違えを吸収し、真に食い違う曲(promenade)だけを✗にできる。
        truth_pcs = {truth_key.tonic.pitchClass, truth_key.relative.tonic.pitchClass}
        m21_pcs = {m21_key.tonic.pitchClass, m21_key.relative.tonic.pitchClass}
        confirmations = [bool(truth_pcs & m21_pcs)]
        if rel in _FILENAME_KEY_SHARPS:
            confirmations.append(truth_key.sharps == _FILENAME_KEY_SHARPS[rel])
        truth_confirmed = all(confirmations)

        gt_clipped = _clip_notes(pretty_midi.PrettyMIDI(str(gt_path)), CLIP_SEC)
        pred_clipped = _clip_notes(pretty_midi.PrettyMIDI(str(spike_path)), CLIP_SEC)
        est_key = estimate_key(_to_qnotes(pred_clipped))

        tonic_ok = truth_key.tonic.pitchClass == est_key.tonic.pitchClass
        key_ok = tonic_ok and truth_key.mode == est_key.mode
        sharps_ok = truth_key.sharps == est_key.sharps

        matched, total = _spelling_match(gt_clipped, pred_clipped, truth_key, est_key)
        rate = (matched / total) if total else None

        rows.append({
            "slug": slug,
            "cat": cat,
            "status": "ok",
            "truth_key": _key_label(truth_key),
            "truth_source": source,
            "truth_confirmed_by_music21": truth_confirmed,
            "est_key": _key_label(est_key),
            "key_correct": key_ok,
            "sharps_correct": sharps_ok,
            "spelling_matched": matched,
            "spelling_total": total,
            "spelling_rate": round(rate, 4) if rate is not None else None,
        })

    ok = [r for r in rows if r["status"] == "ok"]
    key_rate = sum(r["key_correct"] for r in ok) / len(ok) if ok else 0.0
    sharps_rate = sum(r["sharps_correct"] for r in ok) / len(ok) if ok else 0.0
    sp_matched = sum(r["spelling_matched"] for r in ok)
    sp_total = sum(r["spelling_total"] for r in ok)
    sp_rate = (sp_matched / sp_total) if sp_total else 0.0

    key_pass = key_rate >= KEY_ACCURACY_TARGET
    sp_pass = sp_rate >= SPELLING_MATCH_TARGET

    print(f"# C4 キー/綴り計測 (n={len(ok)}/{len(rows)})\n")
    print("| 曲 | 分類 | 正解調(出典/調号相互検証) | 推定調 | 主調 | 調号 | 綴り一致(合致/対象) |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        if r["status"] != "ok":
            print(f"| {r['slug']} | {r['cat']} | {r['status']} | | | | |")
            continue
        conf = "✓" if r["truth_confirmed_by_music21"] else "✗"
        src = f"{r['truth_source']}/{conf}"
        key_mark = "○" if r["key_correct"] else "×"
        sharp_mark = "○" if r["sharps_correct"] else "×"
        if r["spelling_total"]:
            sp = f"{r['spelling_rate']:.1%} ({r['spelling_matched']}/{r['spelling_total']})"
        else:
            sp = "対象0"
        print(
            f"| {r['slug']} | {r['cat']} | {r['truth_key']} ({src}) | {r['est_key']} "
            f"| {key_mark} | {sharp_mark} | {sp} |"
        )

    print()
    print(f"主調正解率(主音+旋法): {key_rate:.1%}  "
          f"[目標≥{KEY_ACCURACY_TARGET:.0%}] {'PASS' if key_pass else 'FAIL'}")
    print(f"  参考・調号(sharps)一致率: {sharps_rate:.1%}")
    print(f"綴り一致率(臨時記号ノート): {sp_rate:.1%} ({sp_matched}/{sp_total})  "
          f"[目標≥{SPELLING_MATCH_TARGET:.0%}] {'PASS' if sp_pass else 'FAIL'}")

    result = {
        "n_ok": len(ok),
        "n_total": len(rows),
        "key_accuracy": round(key_rate, 4),
        "key_accuracy_target": KEY_ACCURACY_TARGET,
        "key_accuracy_pass": key_pass,
        "sharps_accuracy": round(sharps_rate, 4),
        "spelling_rate": round(sp_rate, 4),
        "spelling_matched": sp_matched,
        "spelling_total": sp_total,
        "spelling_target": SPELLING_MATCH_TARGET,
        "spelling_pass": sp_pass,
        "rows": rows,
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "results_key_spelling.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1)
    )
    print("\nsaved results_key_spelling.json")
    return 0 if (key_pass and sp_pass) else 1


if __name__ == "__main__":
    sys.exit(main())
