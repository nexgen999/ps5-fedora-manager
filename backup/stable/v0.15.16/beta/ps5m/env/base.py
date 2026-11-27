"""Contrat commun à tous les environnements de bureau."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence


@dataclass(frozen=True)
class Environment:
    """Ce qu'un bureau fournit et qui varie d'un environnement à l'autre.

    Les pages ne testent jamais le nom du bureau : elles appellent ces méthodes.
    Un bureau qui ne sait pas faire quelque chose renvoie une liste vide, et
    l'interface masque alors l'option correspondante (`supports()`).
    """

    id: str
    name: str
    terminal: tuple[str, ...] = ("x-terminal-emulator",)
    file_manager: tuple[str, ...] = ("xdg-open",)
    settings_cli: str = ""
    autostart_dir: str = "~/.config/autostart"
    extra_env: Mapping[str, str] = field(default_factory=dict)

    # ---- lancement ----
    def open_terminal(self, command: Sequence[str]) -> list[str]:
        """Commande pour ouvrir un terminal et y lancer `command`."""
        return [*self.terminal, *command]

    def open_path(self, path: str) -> list[str]:
        return [*self.file_manager, path]

    # ---- apparence ----
    def set_theme_commands(self, dark: bool) -> list[list[str]]:
        """Commandes pour passer en thème sombre/clair ; vide si non géré."""
        return []

    def set_accent_commands(self, accent: str) -> list[list[str]]:
        """Commandes pour changer la couleur d'accentuation ; vide sinon."""
        return []

    # ---- session ----
    def session_env(self) -> dict[str, str]:
        """Variables à transmettre aux commandes lancées dans la session."""
        return dict(self.extra_env)

    # ---- capacités ----
    def supports(self, feature: str) -> bool:
        return {
            "theme": bool(self.set_theme_commands(True)),
            "accent": bool(self.set_accent_commands("blue")),
            "terminal": bool(self.terminal),
        }.get(feature, False)

    def describe(self) -> dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "terminal": " ".join(self.terminal),
            "file_manager": " ".join(self.file_manager),
            "settings": self.settings_cli or "—",
        }
