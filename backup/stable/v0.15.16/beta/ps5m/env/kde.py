"""KDE Plasma : thème via KConfig, rechargement par D-Bus."""
from __future__ import annotations

from .base import Environment


class Kde(Environment):
    def __init__(self) -> None:
        super().__init__(
            id="kde",
            name="KDE Plasma",
            terminal=("konsole", "-e"),
            file_manager=("xdg-open",),
            settings_cli="kwriteconfig6",
        )

    def set_theme_commands(self, dark: bool) -> list[list[str]]:
        scheme = "BreezeDark" if dark else "BreezeLight"
        return [
            [
                "kwriteconfig6",
                "--file",
                "kdeglobals",
                "--group",
                "General",
                "--key",
                "ColorScheme",
                scheme,
            ],
            ["qdbus6", "org.kde.KWin", "/KWin", "reconfigure"],
        ]

    def set_accent_commands(self, accent: str) -> list[list[str]]:
        # Plasma n'a pas d'équivalent direct : on laisse le bureau gérer.
        return []
