#!/usr/bin/env python3
"""Importe tous les modules de la bêta pour attraper les erreurs GTK.

Deux modes, automatiques :

- **GTK réel** : si `gi` est installé (cas de la PS5), les modules sont
  importés tels quels. Une classe Libadwaita qui n'existe pas dans la version
  installée, un `gi.require_version` oublié ou une faute de frappe dans un
  import font échouer le test.
- **sans affichage** : si `gi` est absent (machine de développement, CI), un
  `gi` factice est installé dans `sys.modules`. Il ne teste pas le rendu, mais
  il vérifie tout le reste : imports, noms au niveau module, classes dérivées
  de widgets, absence de dépendance circulaire.

Aucun serveur X/Wayland n'est nécessaire dans les deux cas.

    python3 beta/tools/import_check.py [-v]
"""
from __future__ import annotations

import importlib
import sys
import traceback
import types
from pathlib import Path

BETA = Path(__file__).resolve().parent.parent
TOOLS = BETA / "tools"


class _StubMeta(type):
    """Tout attribut de classe renvoie une nouvelle classe utilisable."""

    def __getattr__(cls, name: str):
        if name.startswith("__"):
            raise AttributeError(name)
        return _stub_class(name)

    def __call__(cls, *args, **kwargs):  # une classe factice s'instancie
        return super().__call__(*args, **kwargs)


class _StubBase(metaclass=_StubMeta):
    def __init__(self, *args, **kwargs) -> None:
        pass

    def __getattr__(self, name: str):
        if name.startswith("__"):
            raise AttributeError(name)
        return _stub_class(name)


def _stub_class(name: str):
    return _StubMeta(name, (_StubBase,), {})


def install_fake_gi() -> list[tuple[str, str]]:
    """Installe un `gi` minimal et renvoie les `require_version` demandés."""
    calls: list[tuple[str, str]] = []

    gi = types.ModuleType("gi")
    repository = types.ModuleType("gi.repository")

    def require_version(namespace: str, version: str) -> None:
        calls.append((namespace, version))

    def repository_getattr(name: str):
        return _stub_class(name)

    gi.require_version = require_version  # type: ignore[attr-defined]
    repository.__getattr__ = repository_getattr  # type: ignore[attr-defined]
    gi.repository = repository  # type: ignore[attr-defined]
    sys.modules["gi"] = gi
    sys.modules["gi.repository"] = repository
    return calls


def module_names() -> list[str]:
    names: list[str] = []
    for path in sorted((BETA / "ps5m").rglob("*.py")):
        relative = path.relative_to(BETA).with_suffix("")
        parts = list(relative.parts)
        if parts[-1] == "__init__":
            parts.pop()
        names.append(".".join(parts))
    return names


def main(argv: list[str]) -> int:
    verbose = "-v" in argv

    try:
        import gi  # noqa: F401

        real = True
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw  # noqa: F401
    except (ImportError, ValueError):
        real = False
        calls = install_fake_gi()
        gi = importlib.import_module("gi")
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw  # noqa: F401

    sys.path.insert(0, str(BETA))
    failures: list[tuple[str, str]] = []
    imported = 0
    for name in module_names():
        try:
            importlib.import_module(name)
            imported += 1
            if verbose:
                print(f"  ok  {name}")
        except Exception:  # noqa: BLE001 - on veut la trace complète
            failures.append((name, traceback.format_exc()))

    mode = "GTK réel" if real else "GTK factice (sans affichage)"
    print(f"imports : {imported}/{imported + len(failures)} modules · {mode}")

    # Les deux espaces de noms doivent avoir été demandés par l'application.
    wanted = {"Gtk": "4.0", "Adw": "1"}
    if not real:
        missing = [f"{ns} {ver}" for ns, ver in wanted.items()
                   if (ns, ver) not in calls]
        if missing:
            failures.append(("gi.require_version", f"non demandé : {missing}"))

    if Adw is None:  # pragma: no cover - garde-fou
        failures.append(("gi.repository", "Adw indisponible"))

    for name, trace in failures:
        print(f"\nÉCHEC {name}\n{trace}")
    if failures:
        print(f"\n{len(failures)} module(s) en échec")
        return 1
    print("imports : ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
