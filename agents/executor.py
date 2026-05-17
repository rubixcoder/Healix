import shutil
import subprocess
from pathlib import Path
from typing import Any

from agents.config import DOCKER_IMAGE_NAME
from agents.docker_orchestrator import _build_docker_image, _docker_image_exists
from agents.patch_manager import apply_patch_to_file


def _run_pytest(root: Path) -> dict[str, Any]:
    command = ["pytest", "demo_app/", "-q"]
    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
    )
    return {
        "status": "passed" if completed.returncode == 0 else "failed",
        "return_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _run_pytest_docker(root: Path, image_name: str) -> dict[str, Any]:
    project_root = root
    if project_root.name == "sandbox_run":
        project_root = project_root.parent

    if not _docker_image_exists(image_name):
        build_result = _build_docker_image(project_root, image_name)
        if build_result["status"] != "passed":
            return build_result

    command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{str(root)}:/workspace:rw",
        "-w",
        "/workspace",
        image_name,
        "pytest",
        "demo_app/",
        "-q",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )
    return {
        "status": "passed" if completed.returncode == 0 else "failed",
        "return_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def run_demo_tests(project_root: Path | str | None = None, suggested_fix: str | None = None, target_file: str | None = None, use_docker: bool = False) -> dict[str, Any]:
    """Run pytest on the demo_app folder and optionally apply a fix in a sandbox."""
    root = Path(project_root or Path.cwd())
    sandbox_root = root / "sandbox_run"
    demo_root = root / "demo_app"

    if sandbox_root.exists():
        shutil.rmtree(sandbox_root)

    shutil.copytree(demo_root, sandbox_root / "demo_app")

    patch_diff = ""
    patch_target_file = target_file or "demo_app/logic.py"
    patch_applied = False

    sandbox_target_file = sandbox_root / patch_target_file
    if suggested_fix:
        if not sandbox_target_file.exists():
            return {
                "status": "failed",
                "return_code": 1,
                "stdout": "",
                "stderr": f"Target file not found in sandbox: {patch_target_file}",
                "patch_diff": "",
                "patch_target_file": patch_target_file,
                "patch_applied": False,
            }

        patch_result = apply_patch_to_file(sandbox_target_file, suggested_fix)
        patch_diff = patch_result.get("patch_diff", "")
        raw_target = patch_result.get("target_file", patch_target_file)
        try:
            patch_target_file = str(Path(raw_target).relative_to(sandbox_root))
        except Exception:
            patch_target_file = raw_target
        patch_applied = patch_result.get("applied", False)

        if not patch_applied:
            return {
                "status": "failed",
                "return_code": 1,
                "stdout": "",
                "stderr": patch_result.get("error", "Patch application failed."),
                "patch_diff": patch_diff,
                "patch_target_file": patch_target_file,
                "patch_applied": False,
            }

    try:
        if use_docker:
            pytest_result = _run_pytest_docker(sandbox_root, DOCKER_IMAGE_NAME)
        else:
            pytest_result = _run_pytest(sandbox_root)

        pytest_result.update({
            "patch_diff": patch_diff,
            "patch_target_file": patch_target_file,
            "patch_applied": patch_applied,
        })
        return pytest_result
    finally:
        if sandbox_root.exists():
            shutil.rmtree(sandbox_root)
