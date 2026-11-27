#!/usr/bin/env python3
"""Couverture des paquets de langue par rapport à l'anglais.

Usage :
    python3 beta/tools/lang_status.py                 # tableau
    python3 beta/tools/lang_status.py --allow-missing # ne pas échouer
    python3 beta/tools/lang_status.py --missing fr    # clés absentes d'une langue

Ajouter une langue : copier `langs/en.json` en `langs/xx.json`, traduire, puis
relancer ce script jusqu'à 100 %.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ps5m import i18n  # noqa: E402


def main(argv: list[str]) -> int:
    if "--missing" in argv:
        index = argv.index("--missing")
        code = argv[index + 1] if len(argv) > index + 1 else "fr"
        done, total, missing = i18n.coverage(code)
        print(f"{code} : {done}/{total}")
        for key in missing:
            print("  -", key)
        return 0 if done == total else 1

    incomplete = False
    for code in i18n.codes():
        done, total, missing = i18n.coverage(code)
        if total == 0:
            print(f"{code:>3}  illisible")
            incomplete = True
            continue
        percent = 100 * done // total
        state = "ok" if done == total else f"{len(missing)} clé(s) manquante(s)"
        print(f"{code:>3}  {percent:>3}%  {done}/{total}  {state}")
        incomplete = incomplete or done != total

    if incomplete and "--allow-missing" not in argv:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
