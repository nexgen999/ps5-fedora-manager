"""Détection du bureau courant, sans GTK ni dépendance externe."""
from __future__ import annotations

import os

from .base import Environment
from .budgie import Budgie
from .cinnamon import Cinnamon
from .generic import Generic
from .gnome import Gnome
from .kde import Kde

# Jetons reconnus dans XDG_CURRENT_DESKTOP / DESKTOP_SESSION (minuscules).
_TOKENS: dict[str, type[Environment]] = {
    "gnome": Gnome,
    "ubuntu": Gnome,
    "kde": Kde,
    "plasma": Kde,
    "cinnamon": Cinnamon,
    "budgie": Budgie,
}

FACTORIES = {
    "gnome": Gnome,
    "kde": Kde,
    "cinnamon": Cinnamon,
    "budgie": Budgie,
    "generic": Generic,
}

_current: Environment | None = None


def registry() -> dict[str, str]:
    """Identifiant → nom lisible, pour l'écran À propos."""
    return {key: factory().name for key, factory in FACTORIES.items()}


def detect() -> Environment:
    """Bureau courant d'après l'environnement de session."""
    raw = " ".join(
        filter(
            None,
            (
                os.environ.get("XDG_CURRENT_DESKTOP", ""),
                os.environ.get("DESKTOP_SESSION", ""),
                os.environ.get("GDMSESSION", ""),
            ),
        )
    ).lower()
    for token, factory in _TOKENS.items():
        if token in raw:
            return factory()
    return Generic()


def current() -> Environment:
    global _current
    if _current is None:
        _current = detect()
    return _current


def select(env_id: str) -> Environment:
    """Force un environnement (utile pour tester une autre configuration)."""
    global _current
    factory = FACTORIES.get(env_id, Generic)
    _current = factory()
    return _current
