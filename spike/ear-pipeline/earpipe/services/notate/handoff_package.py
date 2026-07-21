"""F-093 人手仕上げ作業パッケージ出力(Issue #103)。

自動採譜の結果を外部(プロ)採譜者に引き継ぐための一式を、1ディレクトリ
(+ zip)にまとめて書き出す。中身は「下書き MusicXML」「信頼度サマリ(低信頼
音のリスト)」「区間音源(あれば)」「人間向け README」「由来(provenance)」から成る。

build_handoff_package(musicxml_path, notes, out_dir, audio_path=None) -> Path
を提供する。戻り値はまとめた .zip のパス(zip 化に失敗する環境では
パッケージ・ディレクトリのパスへフォールバックし、黙って壊れない)。

先行研究(F-093-grok.md / F-093-codex.md)から反映した堅牢化:
  - **単一 XML を納品物にしない**(codex 結論2/5, grok 5.2)。draft.musicxml だけ
    でなく confidence.csv / regions.json / manifest.json / README を multi-layer で
    同梱する。MusicXML はラウンドトリップ保存形式ではない(Library of Congress:
    "round-trip import/export should not be expected")。
  - **「下書き/仮説」であることを明示**(codex 1章末, grok 5.2-1)。ファイル名を
    draft.* にし、README/manifest に final でない旨を書く。
  - **信頼度を p(correct) と呼ばない**(codex 結論3/2章)。列名は confidence では
    なく model_uncertainty_signal 系の意味であることを README に明記し、低信頼を
    「間違い」ではなく「未確定=要人手確認」として扱う。赤一色で塗らない(grok 5.3)。
  - **非ハイライト部分にも未検査の誤りが残ると明示**(codex 3章 Vertanen 反省)。
    低信頼リストに載らない音も抜き取り検査を促す注記を README に入れる。
  - **区間音源は pre-roll/post-roll を付けて切る**(codex 4章, grok 5.1-4)。小節
    ぴったりで切るとアタック・タイ・ペダル文脈が消え「採譜が間違って見える」ため、
    低信頼音の onset 前後にマージンを付けて切り出す。切り出し秒(time origin)を
    regions.json に記録し、clip と note の時刻対応を失わない。
  - **著作権/ライセンス境界をマニフェストに書く**(grok 2.4 W, 5.4)。入力音源の
    権利は利用者が保持する旨を manifest/README に明記する。

原理的限界・重依存の非採用(notes にも記載):
  - torch/Demucs 等の重い分離や専用 AMT モデルはこの環境で使わない(禁止依存)。
    区間音源は「元音源から低信頼区間を切り出す」だけで、stem 分離はしない。
    分離アーティファクトを confidence に混ぜない(codex 4章末)。
  - confidence は QuantizedNote が持つ単一スカラーをそのまま使う。研究が推奨する
    軸分解(pitch/onset/offset/voice/tuplet/alignment)は上流が単一値しか持たない
    ため未対応で、README に「単一スカラーの未校正信号」と正直に明記する。
  - audio_path 未指定/読み込み失敗時は区間音源を省略し、その旨を manifest に残す
    (音がなくても下書き+信頼度サマリは必ず渡せる)。
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from earpipe.contracts import QuantizedNote

# 低信頼と見なす confidence のしきい値(未満を「要人手確認」に載せる)。
# 研究(codex 3章)の反省を踏まえ「間違い」ではなく「未確定」の意味で使う。
_LOW_CONF_THRESHOLD = 0.5

# 区間音源を切り出す際の前後マージン(秒)。アタック・先行装飾・タイ・ペダル
# 残響の文脈を残すため(codex 4章 pre-roll/post-roll)。
_PRE_ROLL_SEC = 0.30
_POST_ROLL_SEC = 0.30

# 区間音源を切り出す最大本数(タイムアウト/肥大化を避ける運用上限。grok 2.1 F/G)。
_MAX_SEGMENTS = 24

# パッケージ内のファイル名(すべて「下書き」であることが分かる名前)。
_DRAFT_XML_NAME = "draft.musicxml"
_CONFIDENCE_CSV_NAME = "confidence_low_notes.csv"
_REGIONS_JSON_NAME = "regions.json"
_MANIFEST_NAME = "manifest.json"
_README_NAME = "README_for_transcriber.txt"
_SEGMENTS_DIR = "audio_segments"

_XML_SUFFIXES = (".musicxml", ".xml")

# CSV のヘッダ。confidence を p(correct) と誤称しないため列名に signal を含める。
_CSV_HEADER = (
    "index,start_beats,dur_beats,midi,onset_sec,offset_sec,"
    "uncertainty_signal,segment_file\n"
)

_README_TEXT = """\
外部採譜者向け 人手仕上げ作業パッケージ(採譜 / Pitchsieve F-093)
================================================================

これは「完成した楽譜」ではなく、自動採譜が出した**下書き(仮説)**の一式です。
そのまま清書せず、下記の弱点を前提に手直ししてください。

■ 同梱物
  - draft.musicxml            下書き MusicXML(記譜仮説。final ではありません)
  - confidence_low_notes.csv  自動採譜が確信を持てなかった音の一覧(要人手確認)
  - regions.json              低信頼区間と、切り出した区間音源との対応(時刻原点つき)
  - audio_segments/           低信頼音の前後を切り出した区間音源(元音源がある場合のみ)
  - manifest.json             由来・設定・権利・既知の弱点(機械可読)

■ 信頼度(confidence)の読み方 — ここが最重要
  - この値は「正しい確率(p_correct)」ではありません。モデルの**未校正の
    不確かさ信号**です。100% 相当でも誤り得ます。
  - 低信頼としてリストに載った音は「間違い」ではなく「**未確定=まず耳で確認**」の意味。
    赤く塗って一律に消さないでください。候補として区間音源と聴き比べてください。
  - **リストに載っていない音が正しいとは限りません。** ハイライトは注意を移すだけで、
    載らなかった誤りは見落とされやすいことが研究で繰り返し報告されています。
    低信頼リスト以外も必ず抜き取り検査してください。

■ MusicXML についての注意
  - MusicXML はソフト間の「交換」形式であって完全保存形式ではありません。
    タイ・連符・移調・声部・レイアウトは、開くソフト(MuseScore/Finale/Sibelius/
    Dorico)で崩れることがあります。開けた≠再現できた、です。
  - リズム(音価・拍節)は自動量子化由来のため、変拍子に見えても実は 4/4 等の
    ことがあります。区間音源で聴き直して拍子を確定してください。

■ 区間音源について
  - 低信頼音の onset 前後にマージン(pre-roll/post-roll)を付けて切り出しています。
    切り出し開始秒は regions.json の time_origin_sec に記録しています。
  - 元音源が無い/読めない場合、audio_segments は空です(manifest に理由を記載)。

■ 権利・ライセンス
  - 入力音源の著作権・利用権は**利用者が保持**する前提です。区間音源の再配布可否は
    利用者の権利に従ってください。本パッケージは権利処理を代行しません。
"""


@dataclass(frozen=True)
class HandoffManifest:
    """パッケージの由来と設定(manifest.json の中身)。

    採譜者が「この下書きが何から・どう作られたか」を機械可読に辿れるようにする。
    信頼度は単一スカラーの未校正信号である旨を is_calibrated=False で明示する。
    """

    feature_id: str
    generated_at_utc: str
    is_draft: bool
    low_confidence_threshold: float
    total_notes: int
    low_confidence_notes: int
    audio_included: bool
    audio_note: str
    confidence_is_calibrated: bool
    rights_notice: str


def _validate_musicxml(musicxml_path: Path) -> bytes:
    """入力 MusicXML を読み、非圧縮 MusicXML らしさを最小検証して返す。

    Args:
        musicxml_path: 下書きとして同梱する非圧縮 MusicXML(.musicxml/.xml)。

    Returns:
        入力ファイルの生バイト列。

    Raises:
        FileNotFoundError: パスが存在しない/通常ファイルでない場合。
        ValueError: 拡張子が非対応、空、または内容が XML に見えない場合。
    """
    if not musicxml_path.is_file():
        raise FileNotFoundError(f"MusicXMLファイルが見つかりません: {musicxml_path}")
    if musicxml_path.suffix.lower() not in _XML_SUFFIXES:
        raise ValueError(
            f"非圧縮MusicXML(.musicxml/.xml)を指定してください: {musicxml_path.name}"
        )
    data = musicxml_path.read_bytes()
    if not data.strip():
        raise ValueError(f"MusicXMLファイルが空です: {musicxml_path}")
    head = data.lstrip()[:4]
    if head[:2] == b"PK":
        raise ValueError(
            "圧縮済み(.mxl)が渡されました。非圧縮MusicXMLを指定してください。"
        )
    if not head.startswith(b"<"):
        raise ValueError(f"MusicXMLとして解釈できません(XML宣言なし): {musicxml_path}")
    return data


def _select_low_confidence(
    notes: Sequence[QuantizedNote], threshold: float
) -> list[tuple[int, QuantizedNote]]:
    """低信頼な音を(元インデックス, 音)の組で抽出する。

    元の並び順のインデックスを保持し、採譜者が draft と突き合わせられるようにする。
    """
    return [
        (idx, note)
        for idx, note in enumerate(notes)
        if note.confidence < threshold
    ]


def _csv_field(value: float) -> str:
    """CSV 数値セルを安定表記にする(NaN は空欄=未設定を明示)。"""
    if value != value:  # NaN 判定(NaN != NaN)
        return ""
    return f"{value:.6g}"


def _load_audio_safe(audio_path: Path) -> tuple[object, int] | None:
    """音源を読み込む。読めない/依存が無い場合は None(区間音源をスキップ)。

    重依存を強制しないため、soundfile/librosa の失敗はすべて握って None を返す
    (音がなくても下書き+信頼度サマリは必ず渡せる)。
    """
    if not audio_path.is_file():
        return None
    try:
        import soundfile as sf  # 遅延import: 音源同梱時のみ依存させる
    except Exception:
        return None
    try:
        data, sr = sf.read(str(audio_path), always_2d=False)
    except Exception:
        return None
    if getattr(data, "size", 0) == 0 or sr <= 0:
        return None
    return data, int(sr)


def _write_segment(
    audio: object,
    sr: int,
    note: QuantizedNote,
    out_path: Path,
) -> float | None:
    """低信頼音の前後マージン付き区間を切り出して WAV 保存する。

    Args:
        audio: 読み込んだ波形(numpy 配列)。
        sr: サンプルレート。
        note: 切り出し対象の音。
        out_path: 出力する WAV パス。

    Returns:
        切り出し開始秒(time origin)。実タイミング(onset_sec)が未設定(NaN)で
        切り出せない場合は None。
    """
    onset = note.onset_sec
    offset = note.offset_sec
    if onset != onset:  # NaN: 実タイミング未設定なら区間音源にできない
        return None
    if offset != offset or offset <= onset:
        offset = onset + 0.5  # 実長不明時は最小長でフォールバック

    try:
        import numpy as np
        import soundfile as sf
    except Exception:
        return None

    arr = np.asarray(audio)
    total = arr.shape[0]
    start_sec = max(0.0, onset - _PRE_ROLL_SEC)
    end_sec = offset + _POST_ROLL_SEC
    start_idx = max(0, int(start_sec * sr))
    end_idx = min(total, int(end_sec * sr))
    if end_idx <= start_idx:
        return None
    try:
        sf.write(str(out_path), arr[start_idx:end_idx], sr)
    except Exception:
        return None
    return start_idx / sr


def _build_segments(
    low_conf: list[tuple[int, QuantizedNote]],
    audio: object,
    sr: int,
    segments_dir: Path,
) -> dict[int, tuple[str, float]]:
    """低信頼音ごとに区間音源を切り出し、{元index: (相対ファイル名, 開始秒)} を返す。

    _MAX_SEGMENTS 本を上限に、実タイミングを持つ音だけ切り出す。
    """
    segments_dir.mkdir(parents=True, exist_ok=True)
    result: dict[int, tuple[str, float]] = {}
    for idx, note in low_conf[:_MAX_SEGMENTS]:
        fname = f"seg_{idx:04d}.wav"
        origin = _write_segment(audio, sr, note, segments_dir / fname)
        if origin is not None:
            result[idx] = (f"{_SEGMENTS_DIR}/{fname}", origin)
    return result


def _write_confidence_csv(
    low_conf: list[tuple[int, QuantizedNote]],
    segments: dict[int, tuple[str, float]],
    out_path: Path,
) -> None:
    """低信頼音の一覧を CSV で書く(区間音源への参照付き)。"""
    lines = [_CSV_HEADER]
    for idx, note in low_conf:
        seg_file = segments.get(idx, ("", 0.0))[0]
        lines.append(
            f"{idx},{_csv_field(note.start_beats)},{_csv_field(note.dur_beats)},"
            f"{note.midi},{_csv_field(note.onset_sec)},{_csv_field(note.offset_sec)},"
            f"{_csv_field(note.confidence)},{seg_file}\n"
        )
    out_path.write_text("".join(lines), encoding="utf-8")


def _write_regions_json(
    low_conf: list[tuple[int, QuantizedNote]],
    segments: dict[int, tuple[str, float]],
    out_path: Path,
) -> None:
    """低信頼区間と区間音源の対応(時刻原点つき)を regions.json に書く。"""
    regions = []
    for idx, note in low_conf:
        seg = segments.get(idx)
        regions.append(
            {
                "note_index": idx,
                "midi": note.midi,
                "start_beats": _json_num(note.start_beats),
                "dur_beats": _json_num(note.dur_beats),
                "onset_sec": _json_num(note.onset_sec),
                "offset_sec": _json_num(note.offset_sec),
                "uncertainty_signal": _json_num(note.confidence),
                "segment_file": seg[0] if seg else None,
                "time_origin_sec": seg[1] if seg else None,
                "note": "uncertainty_signal は正しさの確率ではない。要人手確認。",
            }
        )
    payload = {
        "low_confidence_threshold": _LOW_CONF_THRESHOLD,
        "count": len(regions),
        "regions": regions,
    }
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _json_num(value: float) -> float | None:
    """JSON 化できない NaN を None(=未設定)に落とす。"""
    if value != value:  # NaN
        return None
    return value


def _write_manifest(manifest: HandoffManifest, out_path: Path) -> None:
    """manifest.json を書く。"""
    out_path.write_text(
        json.dumps(manifest.__dict__, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _zip_directory(pkg_dir: Path, zip_path: Path) -> bool:
    """パッケージ・ディレクトリを zip にまとめる。失敗時 False。"""
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(pkg_dir.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(pkg_dir))
    except OSError:
        return False
    return True


def build_handoff_package(
    musicxml_path: str | Path,
    notes: Sequence[QuantizedNote],
    out_dir: str | Path,
    audio_path: str | Path | None = None,
) -> Path:
    """外部採譜者向けの人手仕上げ作業パッケージを 1 ディレクトリ(+zip)にまとめる。

    区間音源(元音源があれば低信頼区間を切り出し)・下書き MusicXML・信頼度サマリ
    (低信頼音のリスト)・由来(manifest)・README を out_dir 配下の
    ``handoff_package/`` に配置し、``handoff_package.zip`` にまとめて返す。
    完全ローカル処理(外部送信なし)。研究の信頼度伝達の失敗例を反映し、
    低信頼は「間違い」でなく「要人手確認」として提示する。

    Args:
        musicxml_path: 下書きとして同梱する非圧縮 MusicXML(.musicxml/.xml)。
        notes: 量子化済み音符列(confidence を持つ)。低信頼抽出の元データ。
        out_dir: 出力先ディレクトリ。無ければ作成する。
        audio_path: 区間音源の元となる音源(任意)。無い/読めない場合は
            区間音源を省略し、その旨を manifest に記す。

    Returns:
        まとめた ``handoff_package.zip`` のパス。zip 化に失敗する環境では
        パッケージ・ディレクトリのパスを返す(黙って壊れない)。

    Raises:
        FileNotFoundError: 入力 MusicXML が存在しない場合。
        ValueError: 入力が非圧縮 MusicXML でない/空の場合。
    """
    src = Path(musicxml_path)
    xml_data = _validate_musicxml(src)

    out = Path(out_dir)
    pkg_dir = out / "handoff_package"
    pkg_dir.mkdir(parents=True, exist_ok=True)

    # 1) 下書き MusicXML を「draft」名で同梱(final でないと分かる名前)。
    (pkg_dir / _DRAFT_XML_NAME).write_bytes(xml_data)

    # 2) 低信頼音を抽出(元インデックス保持)。
    low_conf = _select_low_confidence(notes, _LOW_CONF_THRESHOLD)

    # 3) 区間音源(元音源があり読めれば低信頼区間を切り出す)。
    audio_included = False
    audio_note = "audio_path が未指定のため区間音源は省略しました。"
    segments: dict[int, tuple[str, float]] = {}
    if audio_path is not None:
        loaded = _load_audio_safe(Path(audio_path))
        if loaded is None:
            audio_note = (
                "audio_path を読み込めなかったため区間音源を省略しました"
                "(依存不足/破損/未対応形式)。"
            )
        else:
            audio, sr = loaded
            segments = _build_segments(
                low_conf, audio, sr, pkg_dir / _SEGMENTS_DIR
            )
            audio_included = bool(segments)
            if audio_included:
                audio_note = (
                    f"低信頼音 {len(segments)} 件について前後マージン付き区間音源を"
                    "切り出しました(time_origin_sec は regions.json 参照)。"
                )
            else:
                audio_note = (
                    "元音源は読めましたが、実タイミング(onset_sec)を持つ低信頼音が"
                    "なかったため区間音源はありません。"
                )

    # 4) 信頼度サマリ(CSV)と低信頼区間(JSON)。
    _write_confidence_csv(low_conf, segments, pkg_dir / _CONFIDENCE_CSV_NAME)
    _write_regions_json(low_conf, segments, pkg_dir / _REGIONS_JSON_NAME)

    # 5) README(研究の失敗例を人間向けに要約)。
    (pkg_dir / _README_NAME).write_text(_README_TEXT, encoding="utf-8")

    # 6) manifest(由来・設定・権利・弱点)。
    manifest = HandoffManifest(
        feature_id="F-093",
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        is_draft=True,
        low_confidence_threshold=_LOW_CONF_THRESHOLD,
        total_notes=len(notes),
        low_confidence_notes=len(low_conf),
        audio_included=audio_included,
        audio_note=audio_note,
        confidence_is_calibrated=False,
        rights_notice=(
            "入力音源の著作権・利用権は利用者が保持する前提。区間音源の再配布可否は"
            "利用者の権利に従うこと。本パッケージは権利処理を代行しない。"
        ),
    )
    _write_manifest(manifest, pkg_dir / _MANIFEST_NAME)

    # 7) zip にまとめる(失敗時はディレクトリを返す=黙って壊れない)。
    zip_path = out / "handoff_package.zip"
    if _zip_directory(pkg_dir, zip_path):
        return zip_path
    return pkg_dir
