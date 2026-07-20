"""記譜出力の検証層(F-052 / Issue #66): MusicXMLの妥当性を機械検査する。

出力口 score.py write_musicxml が生む MusicXML を対象に、music21で
パース可能か・パート/音符が存在するか・書き出し→再読込のラウンドトリップで
音符要素数が保存されるか・(スキーマがあれば)XSDに適合するかを検査する。

設計方針(先行リサーチ pitfalls を反映):
- パース失敗は例外を握り潰さず ``errors`` に型名+要旨を残して is_valid=False。
- note_count は「音符要素数」で固定する。和音(chord.Chord)は music21 の
  ``recurse().notes`` で1要素として数えられるため、pitch総数(和音を展開した数)
  ではなく要素数を採用する。ラウンドトリップ比較も同じ尺度で行う。
- ラウンドトリップは makeNotation デフォルト(True)で書き出す。makeNotation=False
  は小節の無いScoreで MusicXMLExportException を投げるため使わない。記譜補正で
  音符が増減しうるので、厳密一致を is_valid の必須条件にはせず、差分は
  errors に記録し roundtrip_ok で表現する。
- lxml のパース/検証は no_network=True・resolve_entities=False・load_dtd=False で
  行い、music21出力先頭の DOCTYPE(partwise.dtd への外部参照)によるネットワーク
  待ちや XXE を防ぐ。
- XSD検証は musicxml.xsd 冒頭の xs:import(xml.xsd / xlink.xsd)が到達不能な
  リモートURLを指すため、素のロードでは xml:lang 解決に失敗する。ローカル同名
  ファイルへ差し替える Resolver を登録して初めてロード/検証できる。スキーマが
  無い/ロード失敗時は warnings に未実行注記を残し、is_valid は構造検査結果で決める。

イミュータビリティ注記(pitfall 8): frozen dataclass でも list フィールドは
中身が可変。ValidationReport は構築時に errors/warnings を確定させ、以後は
mutate しない運用でイミュータブル性を担保する。
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import music21

# 小節整合の許容誤差(拍)。三連符などの端数を弾かないための緩衝。
_DURATION_TOLERANCE = 1.0 / 2048.0

# 同梱スキーマの場所(F-052リサーチで実在確認: musicxml.xsd + xml.xsd + xlink.xsd)。
_SCHEMA_DIR = Path(__file__).resolve().parents[3] / "tests" / "schemas" / "musicxml40"
_SCHEMA_MAIN = _SCHEMA_DIR / "musicxml.xsd"


@dataclass(frozen=True)
class ValidationReport:
    """MusicXML検証結果(F-052)。

    Attributes:
        is_valid: 総合判定。パース成功かつ構造検査(パート/音符存在)を満たすか。
            XSDが実行できた場合はXSD適合も条件に含める。
        errors: 致命的な問題(パース失敗・パート無し・ラウンドトリップ差分・
            XSD不適合など)。空なら致命的問題なし。
        warnings: 非致命的な注記(空譜面・小節整合の乖離・XSD未実行など)。
        note_count: 音符「要素」数(和音は1要素として数える。pitch総数ではない)。
        roundtrip_ok: 書き出し→再読込で音符要素数が保存されたか。

    Note:
        frozen だが errors/warnings は list のため中身は可変。構築時に確定させ
        以後 mutate しない前提で運用する(モジュールdocstring参照)。
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    note_count: int = 0
    roundtrip_ok: bool = False


def _build_resolver_class() -> type | None:
    """lxml が使えれば Resolver サブクラスを生成して返す(無ければ None)。"""
    try:
        from lxml import etree as ET
    except Exception:
        return None

    class _Resolver(ET.Resolver):  # type: ignore[misc]
        def resolve(self, url: str, pubid: str | None, context: object):  # noqa: D401
            """import 先URLを basename でローカルスキーマへ差し替える。"""
            base = os.path.basename(url)
            local = _SCHEMA_DIR / base
            if local.exists():
                return self.resolve_filename(str(local), context)
            return None

    return _Resolver


def _load_schema():
    """ローカルResolver経由で MusicXML XSD を構築する。

    Returns:
        (schema, parser) の組。lxml不在・スキーマ不在・ロード失敗時は None。
    """
    if not _SCHEMA_MAIN.exists():
        return None
    resolver_cls = _build_resolver_class()
    if resolver_cls is None:
        return None
    try:
        from lxml import etree as ET

        parser = ET.XMLParser(
            no_network=True, resolve_entities=False, load_dtd=False
        )
        parser.resolvers.add(resolver_cls())
        xsd_doc = ET.parse(str(_SCHEMA_MAIN), parser)
        schema = ET.XMLSchema(xsd_doc)
    except Exception:
        return None
    return schema, parser


def _count_note_elements(score: music21.stream.Score) -> int:
    """音符要素数を数える(和音は1要素。pitch総数ではない・pitfall 2)。"""
    return len(list(score.recurse().notes))


def _check_structure(
    score: music21.stream.Score, errors: list[str], warnings: list[str]
) -> None:
    """パート/音符の存在と小節整合を検査し、errors/warnings に追記する。"""
    parts = list(score.parts)
    if not parts:
        errors.append("パート無し: score.parts が空")
        return

    has_note = len(list(score.recurse().notes)) > 0
    has_rest = len(list(score.recurse().getElementsByClass(music21.note.Rest))) > 0
    if not has_note and not has_rest:
        warnings.append("空譜面: 音符も休符も存在しない")

    # 小節整合: barDuration と実音価合計の乖離は warning 止まり(makeNotationで
    # 概ね整合するが端数を許容する)。
    for part in parts:
        for measure in part.getElementsByClass(music21.stream.Measure):
            try:
                bar_len = float(measure.barDuration.quarterLength)
                actual = float(
                    sum(el.quarterLength for el in measure.notesAndRests)
                )
            except Exception:
                continue
            if actual > 0 and abs(bar_len - actual) > _DURATION_TOLERANCE:
                warnings.append(
                    f"小節整合の乖離: 小節長{bar_len:.4f} vs 実音価{actual:.4f}"
                )


def _check_roundtrip(
    score: music21.stream.Score,
    original_count: int,
    errors: list[str],
) -> bool:
    """書き出し→再読込で音符要素数が保存されるかを検査する。

    makeNotation デフォルト(True)で書き出す。tempfile は try/finally で確実に
    削除する(pitfall 5)。書き出し/再parseのいずれかで例外なら roundtrip_ok=False。
    """
    fd, tmp_path = tempfile.mkstemp(suffix=".musicxml")
    os.close(fd)
    try:
        score.write("musicxml", fp=tmp_path)
        reparsed = music21.converter.parse(tmp_path)
        new_count = _count_note_elements(reparsed)
    except Exception as exc:  # noqa: BLE001 - 型名を残して握り潰さない
        errors.append(
            f"ラウンドトリップ失敗: {type(exc).__name__}: {exc}"
        )
        return False
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if new_count != original_count:
        errors.append(
            f"ラウンドトリップで音符要素数が変化: {original_count}→{new_count}"
        )
        return False
    return True


def _check_xsd(path: Path, errors: list[str], warnings: list[str]) -> bool | None:
    """XSD検証を試みる。実行できたら True/False、実行不能なら None を返す。

    実行不能時は warnings に未実行注記を残し、is_valid は構造検査で決める。
    """
    loaded = _load_schema()
    if loaded is None:
        warnings.append("XSD未実行(構造検証にフォールバック): スキーマ利用不可")
        return None
    schema, parser = loaded
    try:
        from lxml import etree as ET

        doc = ET.parse(str(path), parser)
        ok = bool(schema.validate(doc))
    except Exception as exc:  # noqa: BLE001
        warnings.append(
            f"XSD未実行(構造検証にフォールバック): {type(exc).__name__}: {exc}"
        )
        return None
    if not ok:
        errors.append(f"XSD不適合: {schema.error_log}")
    return ok


def validate_musicxml(path: str | Path) -> ValidationReport:
    """MusicXMLファイルの妥当性を検査して ValidationReport を返す。

    検査順序:
        1. music21でparse(例外は捕捉し is_valid=False で即return)。
        2. 構造検査(パート/音符の存在・小節整合)。
        3. ラウンドトリップ(書き出し→再読込で音符要素数保存)。
        4. XSD検証(lxml+ローカルスキーマが使えるときのみ。無ければwarning)。

    Args:
        path: 検査対象の MusicXML ファイルパス。

    Returns:
        ValidationReport。例外は投げず、問題は errors/warnings に集約する。
    """
    target = Path(path)
    errors: list[str] = []
    warnings: list[str] = []

    # 1. parse段: 失敗したら以降の検査をスキップして即return。
    try:
        score = music21.converter.parse(str(target))
    except Exception as exc:  # noqa: BLE001 - 広く捕捉しつつ型名を残す
        errors.append(f"パース失敗: {type(exc).__name__}: {exc}")
        return ValidationReport(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            note_count=0,
            roundtrip_ok=False,
        )

    note_count = _count_note_elements(score)

    # 2. 構造検査。
    _check_structure(score, errors, warnings)

    # 3. ラウンドトリップ。
    roundtrip_ok = _check_roundtrip(score, note_count, errors)

    # 4. XSD検証(実行できたときのみ is_valid の条件に含める)。
    xsd_result = _check_xsd(target, errors, warnings)

    structure_ok = not any(e.startswith("パート無し") for e in errors)
    is_valid = structure_ok
    if xsd_result is not None:
        is_valid = is_valid and xsd_result

    return ValidationReport(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        note_count=note_count,
        roundtrip_ok=roundtrip_ok,
    )
