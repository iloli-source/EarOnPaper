"""受入テスト C7: 完全ローカル処理 — パイプライン実行中のネットワーク送信ゼロ (Issue #44)。

core-requirements-v3 C7 / NF-013(外部送信なしの既定) / ADR-003 の検証。
- 本体プロセス: socket をモンキーパッチし、接続試行があれば即失敗
- bp_worker サブプロセス: EARPIPE_FORBID_NET 環境変数でワーカー側にも同じガードを
  インストールし、poly 経路(別インタプリタ)まで含めて通信ゼロを検証する
"""

import socket
from pathlib import Path

import pytest
import soundfile as sf

from earpipe.pipeline import transcribe_file
from earpipe.services.ear.poly import bp_python_path
from tests.conftest import MELODY_DOTTED, SR, render_melody


@pytest.fixture()
def melody_wav(tmp_path: Path) -> Path:
    wav = tmp_path / "melody.wav"
    sf.write(wav, render_melody(MELODY_DOTTED, bpm=90), SR)
    return wav


@pytest.fixture()
def net_guard(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """本体プロセスのネットワークAPIを遮断し、試行を記録する。"""
    attempts: list[str] = []

    def _record_and_fail(name: str):
        def _fail(*args: object, **kwargs: object) -> None:
            attempts.append(name)
            raise AssertionError(f"ネットワーク接続が試行された: {name} args={args!r}")

        return _fail

    monkeypatch.setattr(socket.socket, "connect", _record_and_fail("socket.connect"))
    monkeypatch.setattr(socket, "create_connection", _record_and_fail("create_connection"))
    monkeypatch.setattr(socket, "getaddrinfo", _record_and_fail("getaddrinfo"))
    return attempts


@pytest.mark.integration
class TestC7NetworkZero:
    def test_mono_pipeline_no_network(
        self, melody_wav: Path, net_guard: list[str], tmp_path: Path
    ) -> None:
        """mono経路(採譜→MusicXML→MIDI)が一切の接続試行なしで完走する。"""
        result = transcribe_file(
            melody_wav,
            out_musicxml=tmp_path / "out.musicxml",
            out_midi=tmp_path / "out.mid",
        )
        assert result["n_notes"] > 0
        assert net_guard == [], f"接続試行を検出: {net_guard}"

    def test_field_mode_no_network(
        self, melody_wav: Path, net_guard: list[str], tmp_path: Path
    ) -> None:
        """フィールド録音モード(降噪・SNR分析込み)でも通信ゼロ。"""
        result = transcribe_file(
            melody_wav,
            out_musicxml=tmp_path / "out.musicxml",
            field_mode=True,
        )
        assert "field_report" in result
        assert net_guard == [], f"接続試行を検出: {net_guard}"

    def test_pdf_engraving_no_network(
        self, melody_wav: Path, net_guard: list[str], tmp_path: Path
    ) -> None:
        """PDF描画(Verovio)まで含めて通信ゼロ(ADR-004のオフライン要件)。"""
        result = transcribe_file(
            melody_wav,
            out_musicxml=tmp_path / "out.musicxml",
            out_pdf=tmp_path / "out.pdf",
        )
        assert (tmp_path / "out.pdf").stat().st_size > 0
        assert result["n_notes"] > 0
        assert net_guard == [], f"接続試行を検出: {net_guard}"

    @pytest.mark.skipif(
        bp_python_path() is None,
        reason="basic-pitch実行環境(tools/ai-ears/.venv312)が見つからない",
    )
    def test_poly_subprocess_no_network(
        self,
        melody_wav: Path,
        net_guard: list[str],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """poly経路: bp_workerサブプロセス側にもガードを入れ通信ゼロで完走する。

        EARPIPE_FORBID_NET はサブプロセスに環境変数として継承され、
        bp_worker が自プロセスの socket を遮断する(services/ear/bp_worker.py)。
        """
        monkeypatch.setenv("EARPIPE_FORBID_NET", "1")
        result = transcribe_file(
            melody_wav,
            out_musicxml=tmp_path / "out.musicxml",
            engine="poly",
        )
        # 接続試行があればbp_workerが非ゼロ終了しRuntimeErrorになるため、
        # ここに到達した時点でサブプロセス側も通信ゼロが立証される
        assert result["n_events"] >= 0
        assert net_guard == [], f"本体側で接続試行を検出: {net_guard}"
