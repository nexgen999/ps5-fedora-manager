"""Pages de la bêta : une page = un module, enregistré ici.

Ajouter une page = créer `pages/xxx.py` avec `build(win) -> Gtk.Widget`
puis l'ajouter dans `STATIC` (page fixe) ou la brancher sur une section du
catalogue (`SECTION_PAGES`).
"""
from __future__ import annotations

from .about import build as build_about
from .addons import build_section as build_section
from .logs import build as build_logs

# Pages fixes de la barre latérale : (identifiant, clé de titre, constructeur).
STATIC = (
    ("logs", "nav.logs", build_logs),
    ("about", "nav.about", build_about),
)

__all__ = ["STATIC", "build_section", "build_logs", "build_about"]
