import ast
import difflib
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

DOCKER_IMAGE_NAME = "healix-sandbox:latest"
DOCKERFILE_NAME = "Dockerfile.sandbox"


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

    return text


def _extract_top_level_block(text: str) -> tuple[str, str] | None:
    lines = text.strip().splitlines()
    if not lines:
        return None

    start_idx = None
    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("def ") or stripped.startswith("class "):
            start_idx = idx
            break

    if start_idx is None:
        return None

    block_lines = []
    start_line = lines[start_idx]
    signature = start_line.strip()
    indent = len(start_line) - len(start_line.lstrip())
    decorator_idx = start_idx

    # Include any decorators that directly precede the block
    while decorator_idx > 0:
        prev_line = lines[decorator_idx - 1].strip()
        if prev_line.startswith("@"):
            decorator_idx -= 1
        else:
            break

    block_lines.extend(lines[decorator_idx:start_idx + 1])

    for line in lines[start_idx + 1:]:
        if line.strip() == "":
            block_lines.append(line)
            continue
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= indent and (line.lstrip().startswith("def ") or line.lstrip().startswith("class ")):
            break
        block_lines.append(line)

    return "\n".join(block_lines).rstrip() + "\n", signature


def _find_block_range(lines: list[str], signature: str) -> tuple[int, int] | None:
    prefix = signature.split("(")[0].strip()
    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(prefix) and stripped.endswith(":"):
            indent = len(line) - len(stripped)
            end_idx = idx + 1
            for j in range(idx + 1, len(lines)):
                if lines[j].strip() == "":
                    continue
                current_indent = len(lines[j]) - len(lines[j].lstrip())
                if current_indent <= indent and lines[j].lstrip().startswith(("def ", "class ")):
                    break
                end_idx = j + 1
            return idx, end_idx
    return None


def _apply_suggested_fix_to_file(original_file: Path, suggested_fix: str) -> dict[str, Any]:
    original_text = original_file.read_text(encoding="utf-8")
    sanitized = _sanitize_suggested_fix(suggested_fix)
    block_result = _extract_top_level_block(sanitized)

    if block_result is None:
        updated_text = sanitized
        replaced = False
    else:
        block_text, signature = block_result
        original_lines = original_text.splitlines()
        block_range = _find_block_range(original_lines, signature)
        if block_range:
            start, end = block_range
            updated_lines = original_lines[:start] + block_text.splitlines() + original_lines[end:]
            updated_text = "\n".join(updated_lines).rstrip() + "\n"
            replaced = True
        else:
            updated_text = sanitized
            replaced = False

    patch_diff = _generate_patch(original_text, updated_text, str(original_file), str(original_file))

    if not _validate_patch(patch_diff):
        return {
            "applied": False,
            "error": "Patch validation failed: patch is too broad or empty.",
            "patch_diff": patch_diff,
            "target_file": str(original_file),
        }

    original_file.write_text(updated_text, encoding="utf-8")

    if original_file.suffix == ".py":
        syntax_error = _syntax_check_python_file(original_file)
        if syntax_error is not None:
            return {
                "applied": False,
                "error": f"Syntax validation failed: {syntax_error}",
                "patch_diff": patch_diff,
                "target_file": str(original_file),
            }

    return {
        "applied": True,
        "patch_diff": patch_diff,
        "target_file": str(original_file),
        "replaced_block": replaced,
    }


def _generate_patch(original_text: str, updated_text: str, fromfile: str, tofile: str) -> str:
    original_lines = original_text.splitlines(keepends=True)
    updated_lines = updated_text.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines,
        updated_lines,
        fromfile=fromfile,
        tofile=tofile,
        lineterm="",
    )
    return "\n".join(diff)


def _validate_patch(patch_diff: str, max_changed_lines: int = 100) -> bool:
    if not patch_diff.strip():
        return False

    changes = [line for line in patch_diff.splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))]
    return len(changes) <= max_changed_lines


def _syntax_check_python_file(path: Path) -> str | None:
    try:
        source = path.read_text(encoding="utf-8")
        ast.parse(source)
        return None
    except SyntaxError as exc:
        return str(exc)


def _docker_image_exists(image_name: str) -> bool:
    completed = subprocess.run(
        ["docker", "image", "inspect", image_name],
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _build_docker_image(root: Path, image_name: str) -> dict[str, Any]:
    dockerfile_path = root / DOCKERFILE_NAME
    if not dockerfile_path.exists():
        return {
            "status": "failed",
            "return_code": 1,
            "stdout": "",
            "stderr": f"Dockerfile not found: {dockerfile_path}",
        }

    command = [
        "docker",
        "build",
        "-t",
        image_name,
        "-f",
        str(dockerfile_path),
        str(root),
    ]
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
    if not _docker_image_exists(image_name):
        build_result = _build_docker_image(root, image_name)
        if build_result["status"] != "passed":
            return {
                "status": "failed",
                "return_code": build_result["return_code"],
                "stdout": build_result["stdout"],
                "stderr": build_result["stderr"],
            }

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

        patch_result = _apply_suggested_fix_to_file(sandbox_target_file, suggested_fix)
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
