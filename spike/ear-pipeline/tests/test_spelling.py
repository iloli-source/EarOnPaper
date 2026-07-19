"""C4 調整合ピッチスペリング（Issue #36）のユニットテスト。

調既知の合成メロディで「調推定 → 調文脈に整合する異名同音の綴り」を検証する。
限界(明記): 全体1調のみ(転調・区間調は将来課題)、半音階の綴りは調号方向の単純規則。
"""

import music21
import pytest

from earpipe.contracts import QuantizedNote
from earpipe.services.notate import to_score
from earpipe.services.notate.spelling import estimate_key, spell_midi


def _mel(midis, dur=1.0, last_dur=2.0):
    notes = []
    t = 0.0
    for i, m in enumerate(midis):
        d = last_dur if i == len(midis) - 1 else dur
        notes.append(QuantizedNote(start_beats=t, dur_beats=d, midi=m, confidence=0.9))
        t += d
    return notes


# 調が明確な合成メロディ(音階を上行し主音で終止)
G_DUR = _mel([67, 69, 71, 72, 74, 76, 78, 79, 74, 71, 67])          # G major: F#=78
DES_DUR = _mel([61, 63, 65, 66, 68, 70, 72, 73, 68, 65, 61])        # Db major: Db=61, Gb=66
A_MOLL = _mel([69, 72, 76, 74, 71, 69, 72, 69])                     # A minor(自然): 派生音なし


class TestEstimateKey:
    def test_g_major_estimated(self):
        key = estimate_key(G_DUR)
        assert key.sharps == 1

    def test_des_major_estimated(self):
        key = estimate_key(DES_DUR)
        assert key.sharps == -5

    def test_a_minor_estimated_no_accidentals(self):
        key = estimate_key(A_MOLL)
        assert key.sharps == 0

    def test_empty_defaults_to_c(self):
        key = estimate_key([])
        assert key.sharps == 0


class TestSpellMidi:
    def test_sharp_key_spells_sharp(self):
        key = music21.key.Key("G")
        assert spell_midi(66, key).name == "F#"

    def test_flat_key_spells_flat(self):
        key = music21.key.Key("D-")
        assert spell_midi(61, key).name == "D-"
        assert spell_midi(66, key).name == "G-"

    def test_diatonic_notes_unchanged(self):
        key = music21.key.Key("C")
        for midi, name in [(60, "C"), (62, "D"), (64, "E"), (65, "F"), (67, "G")]:
            assert spell_midi(midi, key).name == name

    @pytest.mark.parametrize("midi", range(60, 73))
    def test_no_double_accidentals_any_key(self, midi):
        for tonic in ["C", "G", "D-", "F#", "E-"]:
            p = spell_midi(midi, music21.key.Key(tonic))
            assert p.midi == midi  # 綴り変更で音高は不変
            assert abs(p.alter) <= 1  # ダブルシャープ/フラット禁止


class TestScoreIntegration:
    def test_key_signature_inserted(self):
        score = to_score(G_DUR, bpm=100)
        ks = score.recurse().getElementsByClass(music21.key.KeySignature).first()
        assert ks is not None and ks.sharps == 1

    def test_spelling_in_score_follows_key(self):
        score = to_score(DES_DUR, bpm=100)
        names = {n.pitch.name for n in score.recurse().notes if n.isNote}
        assert "D-" in names and "C#" not in names
        assert "G-" in names and "F#" not in names

    def test_musicxml_has_key_fifths(self, tmp_path):
        from earpipe.services.notate import write_musicxml

        out = tmp_path / "g.musicxml"
        write_musicxml(to_score(G_DUR, bpm=100), out)
        xml = out.read_text(encoding="utf-8")
        assert "<fifths>1</fifths>" in xml
        reparsed = music21.converter.parse(str(out))
        assert len(list(reparsed.recurse().notes)) > 0


class TestReview40MidiPreservation:
    """レビュー#40 M2: spell_midiは全音高・代表調でMIDI音高を必ず保存する
    (assert撤去後の明示フォールバックの検証)。"""

    @pytest.mark.parametrize("key_name,mode", [
        ("C", "major"), ("G", "major"), ("D-", "major"),
        ("a", "minor"), ("e", "minor"), ("b-", "minor"),
    ])
    def test_spell_preserves_midi_for_all_semitones(self, key_name, mode):
        key = music21.key.Key(key_name, mode)
        for midi in range(48, 84):
            assert spell_midi(midi, key).midi == midi
