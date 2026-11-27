"""Environnements de bureau pris en charge.

Ajouter un bureau = un module dans ce dossier + une entrée dans `detect.py`.
Chaque environnement décrit uniquement ce qui diffère : terminal, gestionnaire
de fichiers, commandes de thème et d'accentuation, environnement de session.
"""
from __future__ import annotations

from .base import Environment
from .detect import current, detect, registry, select

__all__ = ["Environment", "detect", "current", "registry", "select"]
