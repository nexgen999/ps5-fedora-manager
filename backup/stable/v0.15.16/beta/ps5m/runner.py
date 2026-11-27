"""Exécution des scripts de greffons, en streaming, sans GTK."""
from __future__ import annotations

import os
import pty
import select
import shutil
import subprocess
from pathlib import Path
from typing import Callable

Emit = Callable[[str], None]


def run_script(
    script: Path, emit: Emit, args: tuple[str, ...] = (), root: bool = False
) -> int:
    """Lance `bash script.sh [args]` et renvoie le code de sortie.

    Même approche que l'application stable : un pseudo-terminal pour que dnf et
    les installateurs s'affichent ligne par ligne dans le journal. Un greffon
    `root: yes` passe par `pkexec` quand l'application n'est pas déjà root :
    polkit demande alors le mot de passe une seule fois, dans une boîte native.
    """
    command = ["bash", str(script), *args]
    if root and os.geteuid() != 0 and shutil.which("pkexec"):
        command = ["pkexec", *command]
    emit(f"commande : {' '.join(command)}")
    master, slave = pty.openpty()
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=slave,
        stderr=slave,
        close_fds=True,
        env=os.environ.copy(),
    )
    os.close(slave)
    pending = b""
    while True:
        ready, _, _ = select.select([master], [], [], 0.2)
        if ready:
            try:
                chunk = os.read(master, 4096)
            except OSError:
                break
            if not chunk:
                break
            pending += chunk
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                emit(line.decode("utf-8", errors="replace").rstrip())
        elif process.poll() is not None:
            break
    if pending:
        emit(pending.decode("utf-8", errors="replace").rstrip())
    os.close(master)
    return process.wait()


def check_script(script: Path) -> bool:
    """Exécute le script en mode `--check` (0 = installé)."""
    try:
        result = subprocess.run(
            ["bash", str(script), "--check"],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def run_command(command: list[str], timeout: float = 30.0) -> tuple[int, str]:
    """Exécute une commande courte et renvoie (code, sortie)."""
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)
    return result.returncode, (result.stdout or result.stderr or "").strip()
