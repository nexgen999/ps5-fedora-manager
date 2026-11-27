"""GNOME : thème et accentuation via gsettings."""
from __future__ import annotations

from .base import Environment


class Gnome(Environment):
    def __init__(self) -> None:
        super().__init__(
            id="gnome",
            name="GNOME",
            terminal=("kgx", "--"),
            file_manager=("xdg-open",),
            settings_cli="gsettings",
        )

    def set_theme_commands(self, dark: bool) -> list[list[str]]:
        scheme = "prefer-dark" if dark else "prefer-light"
        return [["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", scheme]]

    def set_accent_commands(self, accent: str) -> list[list[str]]:
        return [["gsettings", "set", "org.gnome.desktop.interface", "accent-color", accent]]
