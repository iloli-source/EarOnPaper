"""F-103 出力先ソフト別エクスポートプロファイル(Issue #100)のユニットテスト。

先行研究(docs/research/upcoming/F-103-grok.md)の失敗例を回帰で固定する:
- F1 1:1変換幻想: generic は無改変・音符内容は不変
- F2 レイアウト喪失: Dorico 向けは絶対座標/手動改行/ページレイアウトを落とす
- F5 プレイヤー誤認: 空 part-name を補完する
- F9 Guitar Pro: 五線浄書装飾(ornaments)を落とし、歌詞/タイは保持する
- 堅牢性: 壊れXML/不明target/DOCTYPE喪失を安全に扱う
"""

import xml.etree.ElementTree as ET

import pytest

from earpipe.services.notate.output_profiles import (
    VALID_TARGETS,
    adjust_musicxml_for,
)

# 音符・座標属性・手動改行・空 part-name・装飾を含む最小 MusicXML。
# music21 の実出力構造(score-partwise 4.0・DOCTYPE 付き)を模す。
_SAMPLE_XML = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="4.0">
  <defaults>
    <scaling>
      <millimeters>7</millimeters>
      <tenths>40</tenths>
    </scaling>
    <page-layout>
      <page-height>1200</page-height>
    </page-layout>
    <system-layout>
      <system-margins><left-margin>0</left-margin></system-margins>
    </system-layout>
  </defaults>
  <part-list>
    <score-part id="P1">
      <part-name />
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <print new-system="yes" new-page="no" />
      <attributes>
        <divisions>2</divisions>
      </attributes>
      <note default-x="30" default-y="-15" relative-x="5">
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>quarter</type>
        <notations>
          <ornaments>
            <trill-mark />
          </ornaments>
          <tied type="start" />
        </notations>
        <lyric number="1">
          <syllabic>begin</syllabic>
          <text>la</text>
          <extend />
        </lyric>
      </note>
      <note default-x="60">
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>
"""


# DOCTYPE を持たない最小 MusicXML(DOCTYPE 再付与の捏造防止テスト用)。
_XML_NO_DOCTYPE = (
    "<score-partwise version='4.0'><part-list>"
    "<score-part id='P1'><part-name/></score-part></part-list>"
    "<part id='P1'><measure number='1'><note default-x='1'>"
    "<pitch><step>C</step><octave>4</octave></pitch>"
    "<duration>1</duration></note></measure></part></score-partwise>"
)


class TestNormalizationAndSafety:
    def test_generic_returns_input_unchanged(self):
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "generic")

        # Assert
        assert out == _SAMPLE_XML

    def test_unknown_target_falls_back_to_generic(self):
        # 不明 target は generic 扱い(grok: 不明はgeneric)→ 無改変
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "finale")

        # Assert
        assert out == _SAMPLE_XML

    def test_empty_target_falls_back_to_generic(self):
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "")

        # Assert
        assert out == _SAMPLE_XML

    def test_malformed_xml_returned_unchanged(self):
        # 壊れXMLは例外を握り潰さず無改変で返す(出力口を止めない)
        # Arrange
        broken = "<score-partwise><part><measure></part>"

        # Act
        out = adjust_musicxml_for(broken, "dorico")

        # Assert
        assert out == broken

    def test_empty_string_returned_unchanged(self):
        # Arrange / Act / Assert
        assert adjust_musicxml_for("", "dorico") == ""

    def test_case_insensitive_target(self):
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "DORICO")

        # Assert: 大文字でも Dorico プロファイルが効く(座標が消える)
        assert "default-x" not in out

    def test_valid_targets_are_exposed(self):
        # Arrange / Act / Assert
        assert set(VALID_TARGETS) == {
            "musescore",
            "dorico",
            "sibelius",
            "guitarpro",
            "generic",
        }


class TestNoteContentPreserved:
    @pytest.mark.parametrize("target", VALID_TARGETS)
    def test_note_count_is_never_changed(self, target):
        # F1: いかなる target でも音符本体は削らない(音楽内容は不変)
        # Arrange
        original = len(list(ET.fromstring(_SAMPLE_XML).iter("note")))

        # Act
        out = adjust_musicxml_for(_SAMPLE_XML, target)

        # Assert
        assert len(list(ET.fromstring(out).iter("note"))) == original

    @pytest.mark.parametrize("target", VALID_TARGETS)
    def test_output_is_parseable(self, target):
        # 調整後も必ず妥当な XML であること
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, target)

        # Assert: 例外なくパースできる
        ET.fromstring(out)

    @pytest.mark.parametrize("target", VALID_TARGETS)
    def test_pitches_preserved(self, target):
        # Arrange
        def steps(xml):
            return [p.findtext("step") for p in ET.fromstring(xml).iter("pitch")]

        # Act
        out = adjust_musicxml_for(_SAMPLE_XML, target)

        # Assert
        assert steps(out) == ["C", "E"]


class TestDoricoProfile:
    def test_strips_absolute_position_attrs(self):
        # F2: Dorico は絶対座標を捨てて再浄書。残すと壊れた整形になる
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "dorico")

        # Assert
        assert "default-x" not in out
        assert "default-y" not in out
        assert "relative-x" not in out

    def test_removes_manual_system_break(self):
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "dorico")
        root = ET.fromstring(out)

        # Assert: new-system/new-page 属性を持つ <print> は消える
        prints = list(root.iter("print"))
        assert all("new-system" not in p.attrib for p in prints)
        assert all("new-page" not in p.attrib for p in prints)

    def test_removes_page_and_system_layout_defaults(self):
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "dorico")
        defaults = ET.fromstring(out).find("defaults")

        # Assert: page/system-layout は消え、scaling は残る
        assert defaults.find("page-layout") is None
        assert defaults.find("system-layout") is None
        assert defaults.find("scaling") is not None

    def test_fills_empty_part_name(self):
        # F5: 空 part-name はプレイヤー誤認の温床。既定名を補う
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "dorico")
        name = ET.fromstring(out).find("part-list/score-part/part-name")

        # Assert
        assert name is not None
        assert name.text and name.text.strip()


class TestSibeliusProfile:
    def test_keeps_layout(self):
        # Sibelius は余白/レイアウト import が価値を持つため保持する
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "sibelius")

        # Assert: 座標もページレイアウトも保持
        assert "default-x" in out
        assert ET.fromstring(out).find("defaults/page-layout") is not None

    def test_fills_empty_part_name(self):
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "sibelius")
        name = ET.fromstring(out).find("part-list/score-part/part-name")

        # Assert
        assert name.text and name.text.strip()


class TestMusescoreProfile:
    def test_minimal_intervention_keeps_layout(self):
        # MuseScore は寛容。part-name 補完のみで座標は触らない
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "musescore")

        # Assert
        assert "default-x" in out
        name = ET.fromstring(out).find("part-list/score-part/part-name")
        assert name.text and name.text.strip()


class TestGuitarproProfile:
    def test_removes_ornaments(self):
        # F9/F4: GP は五線装飾を読み飛ばす。事前に落として往復を減らす
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "guitarpro")
        root = ET.fromstring(out)

        # Assert: ornaments は消える
        assert not list(root.iter("ornaments"))

    def test_preserves_lyrics_and_ties(self):
        # 歌詞の伸ばし(extend)欠落で歌詞がずれる事例(grok F9)。歌詞/タイは保持
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "guitarpro")
        root = ET.fromstring(out)

        # Assert
        assert list(root.iter("lyric"))
        assert list(root.iter("extend"))
        assert list(root.iter("tied"))  # notations/tied は残る

    def test_strips_positions(self):
        # タブ譜では絶対座標は無意味なので落とす
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "guitarpro")

        # Assert
        assert "default-x" not in out


class TestSerialization:
    def test_doctype_is_reattached(self):
        # ET は DOCTYPE を落とすため、元にあれば再付与する
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "dorico")

        # Assert
        assert "<!DOCTYPE score-partwise" in out

    def test_xml_declaration_present(self):
        # Arrange / Act
        out = adjust_musicxml_for(_SAMPLE_XML, "dorico")

        # Assert
        assert out.lstrip().startswith("<?xml")

    def test_no_doctype_when_source_lacks_one(self):
        # 元に DOCTYPE が無ければ捏造しない
        # Arrange / Act
        out = adjust_musicxml_for(_XML_NO_DOCTYPE, "dorico")

        # Assert
        assert "<!DOCTYPE" not in out


class TestRealMusic21Output:
    """music21 の実出力に対して壊さず動くことを確認する(統合寄り)。"""

    def test_adjusts_real_score_without_losing_notes(self):
        # Arrange
        music21 = pytest.importorskip("music21")
        from earpipe.contracts import QuantizedNote
        from earpipe.services.notate.score import to_score

        notes = [
            QuantizedNote(0.0, 1.0, 60, 0.9),
            QuantizedNote(1.0, 1.0, 64, 0.9),
            QuantizedNote(2.0, 1.0, 55, 0.9),
        ]
        score = to_score(notes, 120.0, "テスト曲")
        exporter = music21.musicxml.m21ToXml.GeneralObjectExporter(score)
        xml_bytes = exporter.parse()
        xml = xml_bytes.decode("utf-8")
        original_notes = len(list(ET.fromstring(xml).iter("note")))

        # Act
        out = adjust_musicxml_for(xml, "dorico")

        # Assert: パースでき、音符数が保存され、座標が落ちる
        root = ET.fromstring(out)
        assert len(list(root.iter("note"))) == original_notes
        assert "default-x" not in out
