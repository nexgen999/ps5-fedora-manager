#!/usr/bin/env python3
"""Régénère `addons/index.json` depuis les en-têtes `#@` des scripts.

Usage :
    python3 beta/tools/build_catalog.py            # écrit le catalogue
    python3 beta/tools/build_catalog.py --check    # échoue si le catalogue est périmé

`--check` est prévu pour être lancé avant un commit (ou en CI) : il garantit que
l'index publié correspond bien aux scripts, donc que l'application téléchargera
la bonne version.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ps5m import catalog  # noqa: E402


def main(argv: list[str]) -> int:
    check = "--check" in argv
    directory = catalog.ADDONS_DIR
    expected = catalog.build_index(directory)
    path = directory / catalog.INDEX_NAME

    if check:
        try:
            on_disk = catalog.read_index(path)
        except catalog.CatalogError as exc:
            print(f"catalogue illisible : {exc}")
            return 1
        problems: list[str] = []
        for addon in expected["addons"]:
            current = on_disk.get(addon["id"])
            if current is None:
                problems.append(f"{addon['id']} absent de index.json")
            elif catalog.version_key(current.version) != catalog.version_key(
                addon["version"]
            ):
                problems.append(
                    f"{addon['id']} : index {current.version} ≠ script {addon['version']}"
                )
            elif current.sha256 and current.sha256 != addon["sha256"]:
                problems.append(f"{addon['id']} : empreinte différente")
        for stale in sorted(set(on_disk) - {a["id"] for a in expected["addons"]}):
            problems.append(f"{stale} : script supprimé mais encore dans index.json")
        if problems:
            print("index.json périmé :")
            for problem in problems:
                print("  -", problem)
            print("relance : python3 beta/tools/build_catalog.py")
            return 1
        print(f"index.json à jour ({len(on_disk)} greffons).")
        return 0

    written = catalog.write_index(directory)
    print(f"{written.relative_to(directory.parent.parent)} : {len(expected['addons'])} greffons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
