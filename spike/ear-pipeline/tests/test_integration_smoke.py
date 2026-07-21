"""統合スモーク: 実採譜フロー(CLI transcribe)が現在配線済みの出力を実生成するか。

root-cause-analysis.md の教訓「ユニット緑≠製品に反映済み」への対策(#111)。
ユニットテストは各モジュールを個別に検証するが、本テストは app が呼ぶのと同じ
`earpipe.pipeline.main(["transcribe", ...])` を通し、end-to-end で成果物が
生成・非空であることを確認する。新しい出力形式を pipeline/CLI へ結線(#109)したら、
本ファイルに1ケース追加して「実際に出せる」ことを固定する。

現在配線済みの出力: MusicXML / MIDI / 五線譜PDF / ギターTAB譜PDF。
"""

from earpipe import pipeline


def test_transcribe_generates_all_wired_outputs(simple_wav, tmp_path):
    # Arrange: app と同じ CLI 経路。mono エンジンで決定的に(basic-pitch不要)
    wav_path, _melody, _bpm = simple_wav
    out_xml = tmp_path / "out.musicxml"
    out_midi = tmp_path / "out.mid"
    out_pdf = tmp_path / "out.pdf"
    out_tab = tmp_path / "out_tab.pdf"

    # Act
    rc = pipeline.main(
        [
            "transcribe",
            str(wav_path),
            "-o",
            str(out_xml),
            "--midi",
            str(out_midi),
            "--pdf",
            str(out_pdf),
            "--tab",
            str(out_tab),
            "--engine",
            "mono",
        ]
    )

    # Assert: 終了コード0 かつ 4形式すべてが通常ファイルで非空
    assert rc == 0
    for path in (out_xml, out_midi, out_pdf, out_tab):
        assert path.is_file(), f"{path.name} が生成されていない"
        assert path.stat().st_size > 0, f"{path.name} が空"

    # MusicXML は最低限スコア構造を含む(空の殻でない)
    xml = out_xml.read_text(encoding="utf-8")
    assert "score-partwise" in xml or "score-timewise" in xml
    assert "<note" in xml


def test_transcribe_musicxml_only_default(simple_wav, tmp_path):
    """最小オプション(MusicXMLのみ)でも成功する。"""
    # Arrange
    wav_path, _melody, _bpm = simple_wav
    out_xml = tmp_path / "min.musicxml"

    # Act
    rc = pipeline.main(["transcribe", str(wav_path), "-o", str(out_xml), "--engine", "mono"])

    # Assert
    assert rc == 0
    assert out_xml.is_file() and out_xml.stat().st_size > 0


def test_transcribe_dispatch_formats_are_generated(simple_wav, tmp_path):
    """--format 経由の登録形式(#109 結線)が end-to-end で実生成される。

    「export 済みだが未配線」を防ぐため、CLI から各形式が実際に出せることを固定する。
    新形式を結線したら本ケースに key を追加すること。
    """
    # Arrange: lilypond は musicxml を要するため -o も渡す
    wav_path, _melody, _bpm = simple_wav
    out_xml = tmp_path / "o.musicxml"
    keys = ["jianpu", "leadsheet", "ust", "abc", "lilypond"]
    fmt_args = []
    for k in keys:
        fmt_args += ["--format", f"{k}={tmp_path / (k + '.out')}"]

    # Act
    rc = pipeline.main(
        ["transcribe", str(wav_path), "-o", str(out_xml), "--engine", "mono", *fmt_args]
    )

    # Assert: 全形式が通常ファイルで非空
    assert rc == 0
    for k in keys:
        out = tmp_path / f"{k}.out"
        assert out.is_file(), f"{k} が生成されていない"
        assert out.stat().st_size > 0, f"{k} が空"


def test_transcribe_analysis_outputs_are_generated(simple_wav, tmp_path):
    """--analysis 経由の解析注釈(#109 B-2a: 移動ド/度数/Nashville)が e2e で実生成される。

    「export 済みだが未配線」を防ぐため、CLI から各解析が実際に出せることを固定する。
    新しい解析を結線したら本ケースに key を追加すること。
    """
    # Arrange
    wav_path, _melody, _bpm = simple_wav
    out_xml = tmp_path / "a.musicxml"
    keys = ["movable_do", "roman", "nashville"]
    ana_args = []
    for k in keys:
        ana_args += ["--analysis", f"{k}={tmp_path / (k + '.txt')}"]

    # Act
    rc = pipeline.main(
        ["transcribe", str(wav_path), "-o", str(out_xml), "--engine", "mono", *ana_args]
    )

    # Assert: 全解析が通常ファイルで非空
    assert rc == 0
    for k in keys:
        out = tmp_path / f"{k}.txt"
        assert out.is_file(), f"{k} が生成されていない"
        assert out.stat().st_size > 0, f"{k} が空"
