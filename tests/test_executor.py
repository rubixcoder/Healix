import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.executor import run_demo_tests


def test_run_demo_tests_reports_failure(monkeypatch, tmp_path):
    demo_app = tmp_path / "demo_app"
    demo_app.mkdir()
    (demo_app / "logic.py").write_text("def get_item(items, index):\n    return items[index]\n")

    class CompletedProcess:
        def __init__(self, returncode, stdout, stderr):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command, cwd, capture_output, text):
        assert command == ["pytest", "demo_app/", "-q"]
        assert cwd == tmp_path / "sandbox_run"
        return CompletedProcess(1, "F", "1 failed")

    monkeypatch.setattr("subprocess.run", fake_run)
    result = run_demo_tests(tmp_path)

    assert result["status"] == "failed"
    assert result["return_code"] == 1
    assert result["stdout"] == "F"
    assert result["stderr"] == "1 failed"
    assert result["patch_diff"] == ""
    assert result["patch_target_file"] == "demo_app/logic.py"
    assert result["patch_applied"] is False


def test_run_demo_tests_applies_suggested_fix(monkeypatch, tmp_path):
    demo_app = tmp_path / "demo_app"
    demo_app.mkdir()
    logic_py = demo_app / "logic.py"
    logic_py.write_text("def get_item(items, index):\n    return items[index]\n")

    class CompletedProcess:
        def __init__(self, returncode, stdout, stderr):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command, cwd, capture_output, text):
        assert command == ["pytest", "demo_app/", "-q"]
        assert cwd == tmp_path / "sandbox_run"
        assert (tmp_path / "sandbox_run" / "demo_app" / "logic.py").exists()
        fixed_content = (tmp_path / "sandbox_run" / "demo_app" / "logic.py").read_text()
        assert "if index < 0 or index >= len(items):" in fixed_content or "return None" in fixed_content
        return CompletedProcess(0, "", "")

    monkeypatch.setattr("subprocess.run", fake_run)
    suggested_fix = "def get_item(items, index):\n    if index < 0 or index >= len(items):\n        return None\n    return items[index]\n"
    result = run_demo_tests(tmp_path, suggested_fix=suggested_fix)

    assert result["status"] == "passed"
    assert result["return_code"] == 0
    assert result["patch_diff"] != ""
    assert "+    if index < 0 or index >= len(items):" in result["patch_diff"]
    assert result["patch_target_file"] == "demo_app/logic.py"
    assert result["patch_applied"] is True


def test_run_demo_tests_uses_docker_when_requested(monkeypatch, tmp_path):
    demo_app = tmp_path / "demo_app"
    demo_app.mkdir()
    (demo_app / "logic.py").write_text("def get_item(items, index):\n    return items[index]\n")

    def fake_docker_run(root, image_name):
        assert root == tmp_path / "sandbox_run"
        assert image_name == "healix-sandbox:latest"
        patched_content = (tmp_path / "sandbox_run" / "demo_app" / "logic.py").read_text()
        assert "if index < 0 or index >= len(items):" in patched_content or "return None" in patched_content
        return {
            "status": "passed",
            "return_code": 0,
            "stdout": "",
            "stderr": "",
        }

    monkeypatch.setattr("agents.executor._run_pytest_docker", fake_docker_run)

    suggested_fix = "def get_item(items, index):\n    if index < 0 or index >= len(items):\n        return None\n    return items[index]\n"
    result = run_demo_tests(tmp_path, suggested_fix=suggested_fix, use_docker=True)

    assert result["status"] == "passed"
    assert result["return_code"] == 0
    assert result["patch_diff"] != ""
    assert result["patch_applied"] is True
    assert result["patch_target_file"] == "demo_app/logic.py"


def test_run_demo_tests_generates_minimal_patch(monkeypatch, tmp_path):
    demo_app = tmp_path / "demo_app"
    demo_app.mkdir()
    logic_py = demo_app / "logic.py"
    logic_py.write_text("def get_item(items, index):\n    return items[index]\n\n" \
                       "def other():\n    return True\n")

    class CompletedProcess:
        def __init__(self, returncode, stdout, stderr):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command, cwd, capture_output, text):
        assert command == ["pytest", "demo_app/", "-q"]
        assert cwd == tmp_path / "sandbox_run"
        patched = (tmp_path / "sandbox_run" / "demo_app" / "logic.py").read_text()
        assert "def get_item(items, index):" in patched
        assert "def other():" in patched
        return CompletedProcess(0, "", "")

    monkeypatch.setattr("subprocess.run", fake_run)
    suggested_fix = "def get_item(items, index):\n    if index < 0 or index >= len(items):\n        return None\n    return items[index]\n"
    result = run_demo_tests(tmp_path, suggested_fix=suggested_fix)

    assert result["patch_diff"] != ""
    assert "def get_item(items, index):" in result["patch_diff"]
    assert "-def other()" not in result["patch_diff"]
    assert "+def other()" not in result["patch_diff"]

