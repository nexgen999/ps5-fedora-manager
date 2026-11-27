"""Budgie : thème GTK et icônes via gsettings, accent non exposé."""
from __future__ import annotations

from .base import Environment


class Budgie(Environment):
    def __init__(self) -> None:
        super().__init__(
            id="budgie",
            name="Budgie",
            terminal=("gnome-terminal", "--"),
            file_manager=("xdg-open",),
            settings_cli="gsettings",
        )

    def set_theme_commands(self, dark: bool) -> list[list[str]]:
        theme = "Adwaita-dark" if dark else "Adwaita"
        return [
            ["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", theme],
            ["gsettings", "set", "org.gnome.desktop.interface", "color-scheme",
             "prefer-dark" if dark else "prefer-light"],
        ]

    def set_accent_commands(self, accent: str) -> list[list[str]]:
        return []
