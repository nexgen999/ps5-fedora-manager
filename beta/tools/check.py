#!/usr/bin/env python3
"""Contrôles de cohérence de la bêta (sans GTK, sans root).

Vérifie :
  1. chaque script d'addon a un en-tête valide, un identifiant unique et un fichier `.sh` ;
  2. ses `needs` pointent vers des greffons existants (aucune dépendance fantôme) ;
  3. `index.json` est à jour (version, empreinte) ;
  4. chaque script est syntaxiquement valide (`bash -n`) ;
  5. chaque langue couvre toutes les clés de l'anglais.

Usage : python3 beta/tools/check.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ps5m import catalog, i18n  # noqa: E402

def check_addons() -> list[str]:
    problems: list[str] = []
    try:
        addons = catalog.load_local()
    except catalog.CatalogError as exc:
        return [f"catalogue : {exc}"]

    seen: set[str] = set()
    for addon in addons.values():
        if addon.id in seen:
            problems.append(f"{addon.id} : identifiant en double")
        seen.add(addon.id)
        if not addon.version or addon.version == "0.0.0":
            problems.append(f"{addon.id} : version absente")
        for need in addon.needs:
            if need not in addons:
                problems.append(f"{addon.id} : dépendance inconnue « {need} »")
        if not addon.packages and not addon.check_paths and not addon.action:
            problems.append(f"{addon.id} : ni paquets, ni chemins, ni action")
        script = addon.path
        if script is None or not script.exists():
            problems.append(f"{addon.id} : script introuvable")
            continue
        if script.suffix != ".sh":
            problems.append(f"{addon.id} : le fichier doit être un .sh")
        if not script.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash"):
            problems.append(f"{addon.id} : shebang bash manquant")
        syntax = subprocess.run(
            ["bash", "-n", str(script)], capture_output=True, text=True
        )
        if syntax.returncode != 0:
            problems.append(f"{addon.id} : bash -n → {syntax.stderr.strip()}")
    return problems


def check_index() -> list[str]:
    path = catalog.ADDONS_DIR / catalog.INDEX_NAME
    try:
        on_disk = catalog.read_index(path)
    except catalog.CatalogError as exc:
        return [f"index.json : {exc}"]
    local = catalog.load_local()
    problems: list[str] = []
    for addon in local.values():
        current = on_disk.get(addon.id)
        if current is None:
            problems.append(f"{addon.id} absent de index.json")
            continue
        if catalog.version_key(current.version) != catalog.version_key(addon.version):
            problems.append(f"{addon.id} : index {current.version} ≠ script {addon.version}")
        if current.sha256 != addon.sha256:
            problems.append(f"{addon.id} : empreinte index.json différente du script")
    for extra in sorted(set(on_disk) - set(local)):
        problems.append(f"{extra} : dans index.json mais sans script")
    return problems


def check_langs() -> list[str]:
    problems: list[str] = []
    for code in i18n.codes():
        done, total, missing = i18n.coverage(code)
        if total == 0:
            problems.append(f"{code}.json illisible")
        elif missing:
            problems.append(f"{code}.json : {len(missing)} clé(s) manquante(s)")
    return problems


def check_imports() -> list[str]:
    """Importe les modules (GTK réel si présent, factice sinon)."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "import_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return []
    output = (result.stdout or "") + (result.stderr or "")
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    return ["imports : échec"] + [f"  {line}" for line in lines[-25:]]


def main() -> int:
    groups = {
        "greffons": check_addons(),
        "catalogue": check_index(),
        "langues": check_langs(),
        "imports": check_imports(),
    }
    failed = False
    for name, problems in groups.items():
        if problems:
            failed = True
            print(f"{name} : {len(problems)} problème(s)")
            for problem in problems:
                print("  -", problem)
        else:
            print(f"{name} : ok")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
