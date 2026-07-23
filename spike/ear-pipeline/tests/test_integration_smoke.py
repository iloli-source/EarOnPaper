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
    # gp5 は producer が拡張子を .gp5 に正規化するため別テストで検証(下記)。
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


def test_transcribe_emit_outputs_are_generated(simple_wav, tmp_path):
    """--emit 経由の汎用エミッタ(#109 B-2)が e2e で副次成果物を実生成する。

    孤立実装の結線を CLI から固定する。新エミッタを追加したら key を足すこと。
    既定の -o 出力は不変(オプトイン)であることも併せて確認。
    """
    # Arrange: validate は musicxml を要するため -o も渡す
    wav_path, _melody, _bpm = simple_wav
    out_xml = tmp_path / "e.musicxml"
    emit_validate = tmp_path / "report.txt"
    emit_simplify = tmp_path / "simple.musicxml"

    # Act
    rc = pipeline.main(
        [
            "transcribe", str(wav_path), "-o", str(out_xml), "--engine", "mono",
            "--emit", f"validate={emit_validate}",
            "--emit", f"simplify={emit_simplify}#level=0.6",
        ]
    )

    # Assert: 両エミッタが通常ファイルで非空
    assert rc == 0
    for out in (emit_validate, emit_simplify):
        assert out.is_file(), f"{out.name} が生成されていない"
        assert out.stat().st_size > 0, f"{out.name} が空"


def test_transcribe_emit_confview_with_leading_silence(simple_wav, tmp_path):
    """#126 再発防止: 先頭無音つき音源でも audio 必要エミッタ(confview)が成功する。

    先頭無音があるとトリムで一時wavが作られ in_path が差し替わるが、一時wavが
    エミッタ実行前に削除されると FileNotFoundError でエンジンが code 1 終了する
    (実MP3のユーザーテストで顕在化)。一時ファイルは全ディスパッチ完了まで生存すること。
    """
    import numpy as np
    import soundfile as sf

    # Arrange: 既存合成メロディの先頭に1秒の無音を付けてトリム経路を必ず通す
    wav_path, _melody, _bpm = simple_wav
    y, sr = sf.read(str(wav_path), dtype="float32")
    padded = tmp_path / "padded.wav"
    sf.write(str(padded), np.concatenate([np.zeros(sr, dtype=np.float32), y]), sr)
    out_xml = tmp_path / "c.musicxml"
    confview_out = tmp_path / "confview.pdf"

    # Act
    rc = pipeline.main(
        ["transcribe", str(padded), "-o", str(out_xml), "--engine", "mono",
         "--emit", f"confview={confview_out}"]
    )

    # Assert: 成功し解析ビューPDFが非空で生成される
    assert rc == 0
    assert confview_out.is_file(), "confview が生成されていない"
    assert confview_out.stat().st_size > 0, "confview が空"


def test_transcribe_gp5_format_is_generated(simple_wav, tmp_path):
    """#113 修正後: --format gp5 が e2e で非空の .gp5 を実生成する(クラッシュしない)。

    write_guitarpro は出力拡張子を .gp5 に正規化するため、要求パスではなく
    生成された .gp5 ファイルの存在・非空を確認する。
    """
    # Arrange
    wav_path, _melody, _bpm = simple_wav
    out_xml = tmp_path / "g.musicxml"
    gp5_out = tmp_path / "out.gp5"

    # Act
    rc = pipeline.main(
        ["transcribe", str(wav_path), "-o", str(out_xml), "--engine", "mono",
         "--format", f"gp5={gp5_out}"]
    )

    # Assert: .gp5 が通常ファイルで非空
    assert rc == 0
    assert gp5_out.is_file(), "gp5 が生成されていない"
    assert gp5_out.stat().st_size > 0, "gp5 が空"
