"""Pages de la bêta : une page = un module, enregistré ici.

- Une section qui n'a que des greffons utilise `addons.build_section`.
- Une section qui demande une vraie interface (services, langues, comptes…)
  fournit un module dédié, déclaré dans `SECTIONS`.
"""
from __future__ import annotations

from .about import build as build_about
from .addons import build_section
from .easy import build as build_easy
from .fedora import build as build_fedora
from .logs import build as build_logs
from .services import build as build_services
from .ui_lang import build as build_ui_lang
from .users import build as build_users

# Pages fixes : (identifiant, clé de titre, constructeur).
STATIC = (
    ("logs", "nav.logs", build_logs),
    ("about", "nav.about", build_about),
)

# Sections avec une page dédiée, dans l'ordre de la barre latérale.
SECTIONS = (
    ("easy", build_easy),
    ("services", build_services),
    ("ui_lang", build_ui_lang),
    ("users", build_users),
    ("fedora", build_fedora),
)

# Ordre global de la barre latérale (les sections sans greffon ni page dédiée
# sont simplement ignorées).
ORDER = (
    "easy", "library", "aidev", "dev", "websrv", "deps", "repos", "gaming",
    "audio", "video", "hardware", "mesa", "kernel", "power", "fan", "maint",
    "update", "lang", "features", "fix", "services", "ui_lang", "users",
    "fedora",
)

__all__ = ["STATIC", "SECTIONS", "ORDER", "build_section"]
