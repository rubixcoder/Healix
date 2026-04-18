import shutil
import subprocess
from pathlib import Path
from typing import Any


def _sanitize_suggested_fix(suggested_fix: str) -> str:
    text = suggested_fix.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text[3:-3].strip()

    if "```" in text:
        parts = text.split("```")
        candidate = ""
        for i, part in enumerate(parts):
            if i % 2 == 1 and ("def " in part or "class " in part):
                candidate = part.strip()
                break
        if candidate:
            text = candidate

    if "def " in text or "class " in text:
        return text

    return suggested_fix.strip()


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


def run_demo_tests(project_root: Path | str | None = None, suggested_fix: str | None = None) -> dict[str, Any]:
    """Run pytest on the demo_app folder and optionally apply a fix in a sandbox."""
    root = Path(project_root or Path.cwd())
    sandbox_root = root / "sandbox_run"
    demo_root = root / "demo_app"

    if sandbox_root.exists():
        shutil.rmtree(sandbox_root)

    shutil.copytree(demo_root, sandbox_root / "demo_app")

    if suggested_fix:
        fix_text = _sanitize_suggested_fix(suggested_fix)
        target_file = sandbox_root / "demo_app" / "logic.py"
        target_file.write_text(fix_text, encoding="utf-8")

    try:
        return _run_pytest(sandbox_root)
    finally:
        if sandbox_root.exists():
            shutil.rmtree(sandbox_root)
