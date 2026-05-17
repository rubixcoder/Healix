import ast
import difflib
from pathlib import Path
from typing import Any


def _sanitize_suggested_fix(suggested_fix: str) -> str:
    text = suggested_fix.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text[3:-3].strip()

    if "```" in text:
        parts = text.split("```")
        for i, part in enumerate(parts):
            if i % 2 == 1 and ("def " in part or "class " in part):
                return part.strip()
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

    block_lines: list[str] = []
    start_line = lines[start_idx]
    signature = start_line.strip()
    indent = len(start_line) - len(start_line.lstrip())
    decorator_idx = start_idx

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
        if current_indent <= indent and line.lstrip().startswith(("def ", "class ")):
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

    changes = [
        line
        for line in patch_diff.splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]
    return len(changes) <= max_changed_lines


def _syntax_check_python_file(path: Path) -> str | None:
    try:
        source = path.read_text(encoding="utf-8")
        ast.parse(source)
        return None
    except SyntaxError as exc:
        return str(exc)


def apply_patch_to_file(original_file: Path, suggested_fix: str) -> dict[str, Any]:
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
