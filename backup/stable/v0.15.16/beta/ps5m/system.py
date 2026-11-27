"""Lecture de l'état du système (paquets RPM, chemins), sans GTK."""
from __future__ import annotations

import glob
import os
import subprocess
from pathlib import Path


def rpm_present(packages: list[str] | tuple[str, ...]) -> dict[str, bool]:
    """Présence de paquets RPM, architecture comprise (un seul appel à rpm)."""
    specs = [p for p in dict.fromkeys(packages) if p]
    if not specs:
        return {}
    try:
        result = subprocess.run(
            ["rpm", "-q", "--qf", "%{NAME} %{ARCH}\n", *specs],
            capture_output=True,
            text=True,
            timeout=20,
        )
        output = result.stdout or ""
    except (OSError, subprocess.SubprocessError):
        output = ""
    found: set[str] = set()
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 2:
            found.add(parts[0])
            found.add(f"{parts[0]}.{parts[1]}")
    state: dict[str, bool] = {}
    for spec in specs:
        base, _, arch = spec.partition(".")
        state[spec] = f"{base}.{arch}" in found if arch else base in found
    return state


def expand_path(pattern: str) -> list[str]:
    """`~/x`, `$HOME/x` et `/home/*/x` → chemins réels existants."""
    expanded = os.path.expanduser(os.path.expandvars(pattern))
    return sorted(glob.glob(expanded))


def path_present(patterns: list[str] | tuple[str, ...]) -> dict[str, bool]:
    return {pattern: bool(expand_path(pattern)) for pattern in patterns}


def home() -> Path:
    return Path(os.path.expanduser("~"))
