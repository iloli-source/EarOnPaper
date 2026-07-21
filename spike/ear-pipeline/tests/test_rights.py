"""採譜物の権利ガイダンス(F-073)のテスト。

配布/販売前の著作権注意を CLI から表示できること、採譜結果 JSON に短い注意が
添えられることを固定する。法的助言ではない旨(免責)も含むことを確認する。
"""

import json

from earpipe import pipeline
from earpipe.services.rights import rights_notice, rights_summary


def test_rights_notice_covers_key_points():
    # Arrange / Act
    text = rights_notice()
    # Assert: 配布/私的複製/パブリックドメイン/免責 の要点を含む
    for kw in ["著作権", "私的複製", "配布", "パブリックドメイン", "法的助言ではありません"]:
        assert kw in text, f"権利ガイダンスに『{kw}』が無い"


def test_rights_summary_is_short_nonempty():
    # Arrange / Act
    s = rights_summary()
    # Assert
    assert s.strip()
    assert "著作権" in s


def test_rights_subcommand_prints_notice(capsys):
    # Arrange / Act
    rc = pipeline.main(["rights"])
    # Assert
    assert rc == 0
    out = capsys.readouterr().out
    assert "採譜物の権利" in out
    assert "法的助言ではありません" in out


def test_transcribe_summary_includes_rights(simple_wav, tmp_path, capsys):
    """transcribe の標準出力 JSON に権利注意(rights)キーが含まれる。"""
    # Arrange
    wav_path, _melody, _bpm = simple_wav
    out_xml = tmp_path / "r.musicxml"

    # Act
    rc = pipeline.main(["transcribe", str(wav_path), "-o", str(out_xml), "--engine", "mono"])

    # Assert: 標準出力 JSON に rights キーがあり著作権注意を含む
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "rights" in payload
    assert "著作権" in payload["rights"]
