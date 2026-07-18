"""AIの耳ハーネスのテスト共通fixture。

並行エージェントが testdata/ を使用中のため、テストは一切 testdata/ に触れず、
pytest の一時ディレクトリに自前の合成fixtureを生成して使う。
"""

import sys
from pathlib import Path

import pytest

# ears.py / synth_test.py は tools/ai-ears/ 直下にある
HARNESS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS_DIR))

import ears  # noqa: E402
import synth_test  # noqa: E402


class CompareArgs:
    """ears.cmd_compare に渡す最小の引数オブジェクト。"""

    def __init__(self, original, transcription, report=None):
        self.original = str(original)
        self.transcription = str(transcription)
        self.report = str(report) if report else None


@pytest.fixture(scope="session")
def workdir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("ai-ears-fixtures")


@pytest.fixture(scope="session")
def reference_pm():
    """正解が既知の基準メロディ(きらきら星+変化句, BPM100)。"""
    return synth_test.build_midi(synth_test.MELODY)


@pytest.fixture(scope="session")
def reference_audio(workdir, reference_pm) -> Path:
    """基準メロディをears非依存のサイン波実装で音源化(交差検証)。"""
    return synth_test.render_sine(reference_pm, workdir / "reference.wav")


@pytest.fixture(scope="session")
def reference_midi(workdir, reference_pm) -> Path:
    path = workdir / "reference.mid"
    reference_pm.write(str(path))
    return path


@pytest.fixture(scope="session")
def sensitivity_scores(workdir, reference_pm, reference_audio):
    """感度検証4ケースのスコアを一括計算(セッション1回、重い処理の共有)。"""
    cases = {
        "same": reference_pm,
        "pitch_mut": synth_test.mutate_pitches(reference_pm),
        "rhythm_mut": synth_test.mutate_rhythm(reference_pm),
        "unrelated": synth_test.unrelated_midi(),
    }
    results = {}
    for name, pm in cases.items():
        midi_path = workdir / f"{name}.mid"
        pm.write(str(midi_path))
        result = ears.cmd_compare(CompareArgs(reference_audio, midi_path))
        results[name] = {
            k: result[k]["score"] for k in ("chroma", "onset", "tempo", "health")
        } | {"overall": result["overall"]["score"]}
    return results
