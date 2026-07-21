"""F-103 出力先ソフト別エクスポートプロファイル(Issue #100)。

生成済み MusicXML 文字列を、取り込み先ソフト(MuseScore / Dorico / Sibelius /
Guitar Pro / generic)のインポート方言に合わせて**軽微に**調整する。
中心関数は :func:`adjust_musicxml_for` で、``target`` に応じた最小限の
除去/属性補完を施した MusicXML 文字列を返す。

設計方針(先行研究 docs/research/upcoming/F-103-grok.md の失敗例を反映):

- **1:1変換幻想を約束しない(grok F1)**: 本モジュールは「論理内容の移植」を
  助けるだけで、出版レイアウトの完全再現は保証しない。行うのは各ソフトの
  取り込みで壊れやすい/無視される要素の除去と、欠落しがちな属性の補完のみ。

- **レイアウトは捨てられる前提(grok F2 / Michael Good)**: Dorico など浄書系は
  ページ相対フォーマット(``default-x``/``default-y``・手動改行 ``<print>``)を
  取り込み時に破棄して再浄書する。これらを残すと「壊れた整形」として前景化する
  ため、Dorico 向けでは絶対座標系を落とす。Sibelius 向けは逆に余白・リハーサル
  マーク・マルチレスト系を保持する(Avid の import 改善が示す通り価値がある)。

- **要素サポートの穴を事前に削る(grok F4 / @viusmusic)**: 取り込み先が拒否/
  誤読する要素(Guitar Pro での五線浄書向け装飾など)は書出し前に削り、
  「取り込んでから手で消す」往復を減らす。削った内容は本モジュールでは
  DOM から除去し、呼び出し側が把握できるよう関数は「何を触ったか」を
  返さない代わりに、除去対象を保守的に限定する(過剰除去で音符を壊さない)。

- **用語・記譜方言の正規化(grok F8)**: オクターブ記号 8vb などソフト差のある
  語彙は generic では触らず、ターゲットが明示的に非対応なときのみ調整する。

- **Guitar Pro はタブ/演奏情報モデル(grok F9)**: 五線の美しさより演奏情報。
  歌詞の伸ばし(extension ``__``)欠落で歌詞がずれる事例があるため、GP 向けでは
  歌詞の syllabic/extend を保守的に保持しつつ、GP が読み飛ばす純浄書装飾を落とす。

- **不明target は generic**: 未知の target 名は generic として扱い、破壊しない。

堅牢性(pitfalls: 壊れXML/名前空間/DOCTYPE喪失):

- MusicXML partwise/timewise は既定で無名前空間。stdlib ``xml.etree`` で
  パースできる。パースに失敗する壊れXMLは**例外を握り潰さず**入力を無改変で
  返す(呼び出し側の出力口を止めない・データを捏造しない)。

- ``xml.etree`` は DOCTYPE 宣言を保持しないため、music21 出力先頭の
  ``<!DOCTYPE score-partwise ...>`` が消える。取り込み側が DOCTYPE を要求する
  ケースに配慮し、元文字列から DOCTYPE 行を抽出して再付与する。

- ネットワーク待ち/XXE 回避のため外部エンティティは解決しない(stdlib の
  既定パーサは DTD を読みに行かない)。
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

# 公開する妥当な target 集合。未知 target は generic に丸める。
VALID_TARGETS: tuple[str, ...] = (
    "musescore",
    "dorico",
    "sibelius",
    "guitarpro",
    "generic",
)
_DEFAULT_TARGET = "generic"

# レイアウト絶対座標属性(Dorico が取り込み時に捨てて再浄書する・grok F2)。
_LAYOUT_POSITION_ATTRS: tuple[str, ...] = (
    "default-x",
    "default-y",
    "relative-x",
    "relative-y",
)

# DOCTYPE 行を元文字列から拾うための正規表現(stdlib ET が落とすため再付与用)。
_DOCTYPE_RE = re.compile(r"<!DOCTYPE[^>]*>", re.IGNORECASE)
# XML 宣言を拾う(再付与時の重複を避けるため)。
_XML_DECL_RE = re.compile(r"^\s*<\?xml[^>]*\?>", re.IGNORECASE)


def _normalize_target(target: str) -> str:
    """target を正規化する。未知/空/非文字列は generic に丸める(grok: 不明はgeneric)。"""
    if not isinstance(target, str):
        return _DEFAULT_TARGET
    key = target.strip().lower()
    return key if key in VALID_TARGETS else _DEFAULT_TARGET


def _extract_doctype(xml: str) -> str | None:
    """元文字列から DOCTYPE 宣言を1つ抽出する(無ければ None)。"""
    match = _DOCTYPE_RE.search(xml)
    return match.group(0) if match else None


def _strip_layout_positions(root: ET.Element) -> None:
    """全要素から絶対座標レイアウト属性を除去する(Dorico 再浄書前提・grok F2)。

    ``default-x``/``default-y`` 等は浄書系が取り込み時に破棄し、残ると
    「壊れた整形」として前景化する。属性のみ落とし、要素・音符は保持する。
    """
    for el in root.iter():
        for attr in _LAYOUT_POSITION_ATTRS:
            if attr in el.attrib:
                del el.attrib[attr]


def _remove_manual_breaks(root: ET.Element) -> None:
    """手動改行/改ページ ``<print new-system>``/``<print new-page>`` を除去する。

    Dorico はページ相対フォーマットを取り込まず自前レイアウトを組む(grok F2・
    Michael Good)。改行/改ページ指示だけを落とし、``<print>`` が他の子(measure
    numbering 等)を持つ場合は属性のみ外して要素は残す(過剰除去を避ける)。
    """
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag != "print":
                continue
            child.attrib.pop("new-system", None)
            child.attrib.pop("new-page", None)
            # 属性も子も無くなった空の <print> は取り除く。
            if not child.attrib and len(child) == 0:
                parent.remove(child)


def _remove_page_layout_defaults(root: ET.Element) -> None:
    """``<defaults>`` 内のページ/システムレイアウトを除去する(Dorico 再浄書)。

    ``page-layout``/``system-layout``/``staff-layout`` は浄書系が捨てるため
    残す意味が薄い。``scaling``(音符サイズ基準)は保持する — 除去すると
    取り込み側で極端な倍率になる事例があるため。
    """
    defaults = root.find("defaults")
    if defaults is None:
        return
    for tag in ("page-layout", "system-layout", "staff-layout"):
        for el in defaults.findall(tag):
            defaults.remove(el)


def _ensure_part_names(root: ET.Element) -> None:
    """空の ``<part-name>`` に既定名を補完する(プレイヤー誤認の緩和・grok F5)。

    Sibelius→Dorico 等で part-name が空だとプレイヤー種別を誤認しやすい
    (ensemble→solo 等)。music21 の既定出力は ``<part-name />`` が空になり得る
    ため、空名の score-part に安全な既定名 "Instrument N" を補う。既存名は尊重する。
    """
    part_list = root.find("part-list")
    if part_list is None:
        return
    index = 0
    for score_part in part_list.findall("score-part"):
        index += 1
        name_el = score_part.find("part-name")
        if name_el is None:
            name_el = ET.SubElement(score_part, "part-name")
        if name_el.text is None or not name_el.text.strip():
            name_el.text = f"Instrument {index}"


def _remove_ornaments(root: ET.Element) -> None:
    """五線浄書向けの装飾 ``<ornaments>`` を除去する(Guitar Pro 向け・grok F4/F9)。

    Guitar Pro はタブ/演奏情報モデルで、五線の装飾記号(トリル・ターン等)を
    読み飛ばす/誤読する。取り込んでから手で消す往復(@viusmusic)を減らすため、
    ``notations`` 配下の ``ornaments`` のみを保守的に落とす。音符本体・タイ・
    スラー・歌詞は保持する(演奏に効く情報は壊さない)。
    """
    for notations in root.iter("notations"):
        for orn in notations.findall("ornaments"):
            notations.remove(orn)
    # 子の無くなった空 <notations> は取り除く(Guitar Pro の空要素警告を避ける)。
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag == "notations" and len(child) == 0 and not child.attrib:
                parent.remove(child)


def _apply_profile(root: ET.Element, target: str) -> None:
    """target 別の調整を DOM(root)に適用する(破壊的・in-place)。

    generic は無改変(素の MusicXML を尊重)。各プロファイルは軽微な調整に留め、
    音符/ピッチ/音価などの音楽内容には触れない。
    """
    if target == "generic":
        return

    if target == "dorico":
        # Dorico は絶対座標・手動改行・ページレイアウトを捨てて再浄書する。
        _strip_layout_positions(root)
        _remove_manual_breaks(root)
        _remove_page_layout_defaults(root)
        _ensure_part_names(root)
        return

    if target == "sibelius":
        # Sibelius は余白/リハーサル/マルチレストの import が改善済み。
        # レイアウトは保持し(価値がある)、プレイヤー誤認だけ緩和する。
        _ensure_part_names(root)
        return

    if target == "musescore":
        # MuseScore は比較的寛容。part-name 補完のみの最小介入に留める。
        _ensure_part_names(root)
        return

    if target == "guitarpro":
        # Guitar Pro はタブ/演奏情報モデル。五線浄書装飾を落とし、絶対座標も外す
        # (タブ譜では位置情報は無意味)。歌詞・タイ・スラーは保持する。
        _remove_ornaments(root)
        _strip_layout_positions(root)
        _ensure_part_names(root)
        return


def _serialize(root: ET.Element, source_xml: str) -> str:
    """DOM を MusicXML 文字列へ直列化する(XML宣言・DOCTYPE を保全)。

    stdlib ET は XML宣言と DOCTYPE を保持しないため、元文字列にあった DOCTYPE を
    再付与し、XML宣言(``xml_declaration=True``)を明示的に出す。
    """
    body = ET.tostring(root, encoding="unicode")
    doctype = _extract_doctype(source_xml)
    header = '<?xml version="1.0" encoding="utf-8"?>'
    if doctype:
        return f"{header}\n{doctype}\n{body}"
    return f"{header}\n{body}"


def adjust_musicxml_for(xml: str, target: str) -> str:
    """MusicXML 文字列を取り込み先ソフトの方言に合わせて軽微に調整して返す。

    Args:
        xml: 調整対象の MusicXML 文字列(score-partwise/timewise)。
        target: 取り込み先。``{"musescore", "dorico", "sibelius", "guitarpro",
            "generic"}`` のいずれか。未知/空/非文字列は ``generic`` に丸める。

    Returns:
        調整後の MusicXML 文字列。``generic``、または パース不能な壊れXMLの場合は
        入力を無改変で返す(出力口を止めない・データを捏造しない)。

    Note:
        本関数は「論理内容の移植」を助ける軽微な調整のみを行い、出版レイアウトの
        1:1 再現は保証しない(grok F1)。音符/ピッチ/音価には触れない。
    """
    target = _normalize_target(target)

    # generic は素の MusicXML を尊重(無改変・早期return)。
    if target == "generic":
        return xml

    if not isinstance(xml, str) or not xml.strip():
        # 空/非文字列は調整しようがないのでそのまま返す(捏造しない)。
        return xml

    # 壊れXMLは例外を握り潰さず、無改変で返す(呼び出し側の出力口を止めない)。
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return xml

    _apply_profile(root, target)
    return _serialize(root, xml)
