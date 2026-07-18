"""bp_worker のプロセス間契約テスト(レビューHIGH-1/MEDIUM-2対応)。

引数バリデーションは basic-pitch の import より前に走るため、
3.12 venv がなくても現行インタプリタで検証できる。
"""

import subprocess
import sys

import pytest
from earpipe.ear_poly import _WORKER, _validate_worker_json


class TestBpWorkerArgv:
    def test_no_args_exits_1_with_usage(self):
        proc = subprocess.run(
            [sys.executable, str(_WORKER)], capture_output=True, text=True, timeout=30
        )
        assert proc.returncode == 1
        assert "Usage" in proc.stderr

    def test_missing_file_exits_1(self, tmp_path):
        missing = tmp_path / "not_exist.wav"
        proc = subprocess.run(
            [sys.executable, str(_WORKER), str(missing)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 1
        assert "File not found" in proc.stderr


class TestValidateWorkerJson:
    def test_valid_list_passes(self):
        raw = [{"onset": 0.0, "offset": 0.5, "midi": 60, "confidence": 0.9}]
        assert _validate_worker_json(raw) == raw

    def test_empty_list_passes(self):
        assert _validate_worker_json([]) == []

    def test_non_list_raises(self):
        with pytest.raises(RuntimeError, match="unexpected JSON type"):
            _validate_worker_json({"onset": 0.0})

    def test_missing_key_raises(self):
        with pytest.raises(RuntimeError, match="契約"):
            _validate_worker_json([{"onset": 0.0, "offset": 0.5, "midi": 60}])

    def test_non_dict_element_raises(self):
        with pytest.raises(RuntimeError, match="契約"):
            _validate_worker_json([[0.0, 0.5, 60, 0.9]])
