"""Bureau inconnu : aucun réglage d'apparence, mais le reste fonctionne."""
from __future__ import annotations

from .base import Environment


class Generic(Environment):
    def __init__(self) -> None:
        super().__init__(
            id="generic",
            name="Bureau générique",
            terminal=("x-terminal-emulator",),
            file_manager=("xdg-open",),
            settings_cli="",
        )
