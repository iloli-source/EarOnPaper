"""体験テスト一括実行: usertest/input/ の全音源を採譜し、聴き比べ素材一式を作る。

各曲について MusicXML / MIDI / 五線譜PDF / JSONサマリー / 採譜再生音wav を生成し、
viewer.html が読む manifest.js を書き出す。完全ローカル処理（外部送信なし）。

使い方:
    .venv/bin/python usertest/run_usertest.py            # 未処理の曲だけ処理
    .venv/bin/python usertest/run_usertest.py --force    # 全曲やり直し

ファイル名が field_ で始まる音源は --field-mode を自動付与する。
poly（basic-pitch）が失敗した曲は mono にフォールバックし、その旨を記録する。
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

USERTEST = Path(__file__).resolve().parent
SPIKE = USERTEST.parent
VENV_PY = SPIKE / ".venv" / "bin" / "python"
BP_PYTHON = SPIKE.parent.parent / "tools" / "ai-ears" / ".venv312" / "bin" / "python"

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".aiff", ".aif", ".ogg"}
RENDER_SR = 22050

# 既知曲のラベル（台帳は曲IDで管理。ローカル表示用の短い説明のみ）
KNOWN_LABELS = {
    "u1": "U1 ピアノ曲（スタジオ品質・中庸テンポ）",
    "u2": "U2 弾き語り（ボーカル＋アコースティックギター）",
    "u4": "U4 バンド（ドラム・ベース・ギター・ボーカル）",
}


def transcribe(in_path: Path, engine: str, title: str = "") -> tuple[dict, float]:
    """パイプラインをサブプロセス実行し、(サマリーdict, 処理秒)を返す。失敗時は例外。"""
    name = in_path.stem
    out_xml = USERTEST / "output" / f"{name}.musicxml"
    out_mid = USERTEST / "output" / f"{name}.mid"
    out_pdf = USERTEST / "output" / f"{name}.pdf"
    out_tab = USERTEST / "output" / f"{name}_tab.pdf"
    out_tab_plain = USERTEST / "output" / f"{name}_tab_plain.pdf"
    cmd = [
        str(VENV_PY), "-m", "earpipe.pipeline", "transcribe", str(in_path),
        "-o", str(out_xml), "--midi", str(out_mid), "--pdf", str(out_pdf),
        "--tab", str(out_tab), "--tab-plain", str(out_tab_plain),
        "--engine", engine,
    ]
    if engine == "poly":
        cmd += ["--sensitivity", "auto"]
    if name.startswith("field_"):
        cmd += ["--field-mode"]
    if title:
        cmd += ["--title", title]
    env = {**os.environ, "EARPIPE_BP_PYTHON": str(BP_PYTHON)}
    t0 = time.time()
    proc = subprocess.run(
        cmd, cwd=SPIKE, env=env, capture_output=True, text=True, timeout=1800
    )
    elapsed = time.time() - t0
    if proc.returncode != 0:
        raise RuntimeError(f"{engine} failed (exit {proc.returncode}):\n{proc.stderr[-2000:]}")
    summary = json.loads(proc.stdout)
    return summary, elapsed


def _write_status(song: str, stage: str, pct: int) -> None:
    """viewer.htmlがポーリングする進行状況をstatus.jsに書き出す。"""
    payload = {"song": song, "stage": stage, "pct": pct, "ts": int(time.time() * 1000)}
    (USERTEST / "status.js").write_text(
        "window.USERTEST_STATUS = " + json.dumps(payload, ensure_ascii=False) + ";\n"
    )


def _compute_peaks(audio_path: Path, n_buckets: int = 800) -> list[float]:
    """波形描画用の振幅ピーク列を計算する（file://ではWebAudioデコード不可のため事前計算）。"""
    import librosa
    import numpy as np

    y, _sr = librosa.load(str(audio_path), sr=8000, mono=True)
    if y.size == 0:
        return []
    bucket = max(1, len(y) // n_buckets)
    trimmed = y[: (len(y) // bucket) * bucket]
    peaks = np.abs(trimmed).reshape(-1, bucket).max(axis=1)
    peak_max = float(peaks.max()) or 1.0
    return [round(float(p) / peak_max, 3) for p in peaks[:n_buckets]]


def render_midi(mid_path: Path, wav_path: Path) -> None:
    """MIDI→再生音wav（pretty_midi内蔵シンセ。G0'の聴き比べペアと同方式）。"""
    import numpy as np
    import pretty_midi
    import soundfile as sf

    pm = pretty_midi.PrettyMIDI(str(mid_path))
    audio = pm.synthesize(fs=RENDER_SR)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0:
        audio = audio / peak * 0.9
    sf.write(str(wav_path), audio, RENDER_SR)


def process_song(in_path: Path, index: int, force: bool) -> dict:
    name = in_path.stem
    title = f"Song {index + 1}"
    meta_path = USERTEST / "output" / f"{name}.json"
    render_path = USERTEST / "renders" / f"{name}_pitchsieve.wav"
    if meta_path.exists() and render_path.exists() and not force:
        print(f"[skip] {name}（処理済み。やり直しは --force）")
        return json.loads(meta_path.read_text())

    print(f"[run ] {title}: poly採譜を開始...")
    _write_status(title, "耳で音を拾っています（採譜中）", 10)
    fallback_note = None
    try:
        summary, elapsed = transcribe(in_path, engine="poly", title=title)
    except (RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired) as e:
        fallback_note = f"polyが失敗したためmonoで再実行: {e}"
        print(f"[warn] {title}: {fallback_note}")
        summary, elapsed = transcribe(in_path, engine="mono", title=title)

    print(f"[run ] {title}: 再生音を合成...")
    _write_status(title, "採譜結果の再生音を合成しています", 55)
    render_midi(USERTEST / "output" / f"{name}.mid", render_path)

    # PDFのOCR検証 + ページ画像生成（五線譜・TAB両方）
    _write_status(title, "楽譜を検証しています", 75)
    pdf_path = USERTEST / "output" / f"{name}.pdf"
    tab_pdf_path = USERTEST / "output" / f"{name}_tab.pdf"
    _verify_pdf(pdf_path, title)
    _verify_pdf(tab_pdf_path, title)
    if summary.get("tab"):
        _verify_tab_pdf(tab_pdf_path, summary["tab"])
    _write_status(title, "楽譜ページを画像化しています", 85)
    tab_plain_pdf_path = USERTEST / "output" / f"{name}_tab_plain.pdf"
    pages = _pdf_to_pages(pdf_path, name)
    tab_pages = _pdf_to_pages(tab_pdf_path, f"{name}_tab") if tab_pdf_path.exists() else []
    tab_plain_pages = _pdf_to_pages(tab_plain_pdf_path, f"{name}_tab_plain") if tab_plain_pdf_path.exists() else []
    _write_status(title, "波形を準備しています", 95)
    peaks_original = _compute_peaks(in_path)
    peaks_render = _compute_peaks(render_path)

    meta = {
        "id": name,
        "label": title,
        "original": f"input/{in_path.name}",
        "render": f"renders/{render_path.name}",
        "pdf": f"output/{name}.pdf",
        "pages": pages,
        "tab_pdf": f"output/{name}_tab.pdf" if tab_pdf_path.exists() else None,
        "tab_pages": tab_pages,
        "tab_plain_pages": tab_plain_pages,
        "n_octave_shifted": (summary.get("tab") or {}).get("n_octave_shifted"),
        "n_tab_dropped": (summary.get("tab") or {}).get("n_dropped"),
        "n_tab_overlaps": (summary.get("tab") or {}).get("n_overlaps"),
        "n_chords": (summary.get("tab") or {}).get("n_chords"),
        "peaks_original": peaks_original,
        "peaks_render": peaks_render,
        "musicxml": f"output/{name}.musicxml",
        "midi": f"output/{name}.mid",
        "engine": summary.get("engine"),
        "trimmed_leading_sec": summary.get("trimmed_leading_sec"),
        "anchored_lead_beats": summary.get("anchored_lead_beats"),
        "bpm": summary.get("bpm"),
        "n_notes": summary.get("n_notes"),
        "n_events": summary.get("n_events"),
        "tempo_map": summary.get("tempo_map"),
        "adaptive": summary.get("adaptive"),
        "field_report": summary.get("field_report"),
        "processing_sec": round(elapsed, 1),
        "fallback_note": fallback_note,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"[done] {title}: {meta['n_notes']}音符 / BPM{meta['bpm']} / {elapsed:.0f}秒")
    return meta


def _pdf_to_pages(pdf_path: Path, name: str) -> list[str]:
    """PDFを全ページPNG変換してoutput/pages/に保存し、相対パスのリストを返す。"""
    import fitz
    pages_dir = USERTEST / "output" / "pages"
    pages_dir.mkdir(exist_ok=True)
    doc = fitz.open(str(pdf_path))
    paths = []
    for i, page in enumerate(doc):
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        out = pages_dir / f"{name}_p{i + 1:02d}.png"
        pix.save(str(out))
        paths.append(f"output/pages/{out.name}")
    print(f"[pdf ] {len(paths)}ページをPNG変換")
    return paths


def _verify_tab_pdf(pdf_path: Path, tab_summary: dict) -> None:
    """TAB PDFをOCRして、フレット数字が消えず判読可能かを実データで確認する。"""
    import re

    import pypdf

    try:
        reader = pypdf.PdfReader(str(pdf_path))
        text = " ".join(p.extract_text() or "" for p in reader.pages)
    except Exception as e:
        print(f"[warn] TAB検証スキップ（{e}）")
        return

    digit_tokens = re.findall(r"\d{1,2}", text)
    placed = tab_summary.get("n_notes_placed", 0)
    overlaps = tab_summary.get("n_overlaps", 0)
    # データ整合性: 抽出数字がTAB音符数を大きく下回っていたら数字が欠落している
    if placed and len(digit_tokens) < placed * 0.9:
        print(f"[warn] TAB-OCR: 数字が欠落の疑い（抽出{len(digit_tokens)} < 配置{placed}）")
    else:
        print(f"[tab ] OCR整合OK（抽出数字{len(digit_tokens)} / 配置音符{placed}）")
    # 可読性: 重なりが多いと視覚的に読めない
    if overlaps:
        ratio = overlaps / placed * 100 if placed else 0
        print(f"[warn] TAB可読性: 数字の重なり {overlaps}箇所（配置の{ratio:.0f}%）"
              f" — 音数が多すぎてギターTABとして読みにくい")


def _verify_pdf(pdf_path: Path, expected_title: str) -> None:
    """PDFをテキスト抽出して文字化けがないか確認する。"""
    try:
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path))
        text = " ".join(
            page.extract_text() or "" for page in reader.pages[:3]
        )
        issues = []
        # タイトルが含まれているか
        if expected_title and expected_title not in text:
            issues.append(f"タイトル「{expected_title}」がPDF内に見当たりません")
        # 文字化けの典型パターン（制御文字・代替文字の多出）
        mojibake_chars = sum(1 for c in text if ord(c) in range(0xFFFD, 0xFFFE + 1) or ord(c) < 0x20 and c not in "\n\r\t")
        if mojibake_chars > 5:
            issues.append(f"文字化けの可能性（異常文字 {mojibake_chars}個）")
        if issues:
            print(f"[warn] PDF検証: {' / '.join(issues)}")
            print(f"       抽出テキスト先頭: {text[:120]!r}")
        else:
            print(f"[pdf ] OCR検証OK（抽出: {text[:60].strip()!r}…）")
    except Exception as e:
        print(f"[warn] PDF検証スキップ（{e}）")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true", help="処理済みの曲もやり直す")
    args = ap.parse_args()

    inputs = sorted(
        p for p in (USERTEST / "input").iterdir() if p.suffix.lower() in AUDIO_EXTS
    )
    if not inputs:
        print("input/ に音源がありません", file=sys.stderr)
        return 1

    songs = [process_song(p, i, args.force) for i, p in enumerate(inputs)]

    manifest = USERTEST / "manifest.js"
    manifest.write_text(
        "window.MANIFEST = " + json.dumps({"songs": songs}, ensure_ascii=False, indent=2) + ";\n"
    )
    _write_status("", "完了", 100)
    print(f"\nmanifest.js 更新（{len(songs)}曲）。viewer.html を開いて聴き比べできます。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
