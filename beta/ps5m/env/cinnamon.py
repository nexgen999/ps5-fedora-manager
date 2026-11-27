"""Cinnamon : thème GTK via gsettings, terminal gnome-terminal."""
from __future__ import annotations

from .base import Environment


class Cinnamon(Environment):
    def __init__(self) -> None:
        super().__init__(
            id="cinnamon",
            name="Cinnamon",
            terminal=("gnome-terminal", "--"),
            file_manager=("xdg-open",),
            settings_cli="gsettings",
        )

    def set_theme_commands(self, dark: bool) -> list[list[str]]:
        theme = "Adwaita-dark" if dark else "Adwaita"
        return [
            ["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", theme],
            ["gsettings", "set", "org.cinnamon.desktop.interface", "gtk-theme", theme],
        ]

    def set_accent_commands(self, accent: str) -> list[list[str]]:
        return []
