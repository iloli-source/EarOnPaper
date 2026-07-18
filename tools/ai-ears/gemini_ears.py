#!/usr/bin/env python3
"""第二の耳 — Gemini音声入力モデルによる音楽的比較判定。

計算指標(ears.py)が測れない「音楽としての質」を、音声を直接聴けるGemini
(音声入力対応モデル)に判定させる。元音源と採譜結果の合成音を渡し、
構造化JSONで判定を受け取る。

使い方:
    .venv/bin/python gemini_ears.py --original song.wav --transcription result.mid
注意: 2026-07-19時点でAPIキーの無料枠クォータが枯渇(429)。
      クォータ回復後(日次リセット)に実行すること。429はキー有効の証左。
"""

import argparse
import base64
import json
import pathlib
import tempfile
import urllib.error
import urllib.request

MODELS = ["gemini-3-flash-preview", "gemini-2.5-flash"]

PROMPT = """あなたは経験豊富な採譜者(音源を楽譜に起こす専門家)です。
2つの音声を聴き比べてください。1つ目が元の音源、2つ目がAI採譜ツールの
出力を機械合成した音です。以下をJSONだけで回答してください:

{
  "melody_identity": <0-10, メロディが同じ曲として認識できる度合い>,
  "rhythm_naturalness": <0-10, リズム・タイミングの自然さ(元と比べて)>,
  "harmony_accuracy": <0-10, 和音・伴奏の一致度(該当なしなら null)>,
  "usable_as_draft": <true/false, 音楽家がこれを下書きとして直す価値があるか>,
  "estimated_fix_effort": <"light"|"moderate"|"heavy"|"rewrite", 使える譜面にする手直し量の見立て>,
  "main_problems": [<主な問題点を日本語で最大3つ>],
  "ear_or_notation": <"ear"|"notation"|"both"|"neither",
    問題の主因が「音の聴き取り(耳)」か「譜面化(記譜)」か>
}"""


def load_key() -> str:
    env = pathlib.Path.home() / ".gemini/.env"
    for line in env.read_text().splitlines():
        if "API_KEY" in line and "=" in line:
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("APIキーが ~/.gemini/.env に見つかりません")


def to_wav_bytes(path: str) -> bytes:
    """mp3等はffmpegでwav化してから読む。wavはそのまま。"""
    p = pathlib.Path(path)
    if p.suffix.lower() == ".wav":
        return p.read_bytes()
    import subprocess

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(p),
             "-ar", "22050", "-ac", "1", tmp.name],
            check=True,
        )
        return pathlib.Path(tmp.name).read_bytes()


def synth_transcription_wav(midi_path: str) -> bytes:
    """採譜MIDIを聴き比べ用の音にする(ears.pyの合成を利用)。"""
    import numpy as np
    import soundfile as sf

    import ears

    pm, _ = ears.load_midi(midi_path)
    audio = ears.synthesize_midi(pm)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        sf.write(tmp.name, audio.astype(np.float32), ears.SR)
        return pathlib.Path(tmp.name).read_bytes()


def judge(original: str, transcription: str) -> dict:
    key = load_key()
    parts = [
        {"text": PROMPT},
        {"text": "【1つ目: 元の音源】"},
        {"inline_data": {"mime_type": "audio/wav",
                         "data": base64.b64encode(to_wav_bytes(original)).decode()}},
        {"text": "【2つ目: AI採譜出力の合成音】"},
        {"inline_data": {"mime_type": "audio/wav",
                         "data": base64.b64encode(synth_transcription_wav(transcription)).decode()}},
    ]
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"response_mime_type": "application/json"}}

    last_error = None
    for model in MODELS:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent?key={key}")
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                data = json.load(resp)
            text = "".join(p.get("text", "")
                           for p in data["candidates"][0]["content"]["parts"])
            return {"model": model, "judgment": json.loads(text)}
        except urllib.error.HTTPError as e:
            last_error = f"{model}: HTTP {e.code}"
            if e.code == 429:
                continue  # 次のモデルへ(全滅ならクォータ枯渇として報告)
            raise
    raise SystemExit(
        f"全モデルでエラー({last_error})。429ならクォータ枯渇 — "
        "日次リセット(日本時間夕方頃)後に再実行してください。キー自体は有効です。")


def main():
    p = argparse.ArgumentParser(description="第二の耳 — Gemini音楽的判定")
    p.add_argument("--original", required=True)
    p.add_argument("--transcription", required=True)
    args = p.parse_args()
    result = judge(args.original, args.transcription)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
