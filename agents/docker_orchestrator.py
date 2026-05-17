import subprocess
from pathlib import Path
from typing import Any

from agents.config import DOCKERFILE_NAME


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
