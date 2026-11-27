#!/usr/bin/env python3
"""Génère la référence des greffons (doc/fr/addons.md et doc/en/addons.md).

La documentation des greffons est dérivée de `addons/index.json` : elle ne peut
pas décrire autre chose que ce qui est réellement livré. Relancer ce script
après chaque modification d'un script ou du catalogue :

    python3 beta/tools/docs.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "doc"

TEXT = {
    "fr": {
        "title": "Référence des greffons",
        "intro": (
            "Chaque option de l'application est un script `.sh` autonome dans "
            "`beta/addons/`. Ce tableau est **généré** depuis `addons/index.json` "
            "par `tools/docs.py` : il reflète exactement ce qui est livré."
        ),
        "columns": ("Greffon", "Version", "Paquets", "État"),
        "state": "paquets RPM et/ou chemins",
        "action": "action (aucun état)",
        "fields": (
            "## En-tête d'un script\n\n"
            "```bash\n"
            "#!/usr/bin/env bash\n"
            "#@ id: codecs-av            # identifiant unique = nom du fichier\n"
            "#@ version: 1.0.1           # comparée par le catalogue (x.y.z)\n"
            "#@ section: video           # section de la barre latérale\n"
            "#@ icon: video-x-generic-symbolic\n"
            "#@ title: Video codecs      # titre anglais\n"
            "#@ title_fr: Codecs vidéo   # titre français\n"
            "#@ desc: ...                # description anglaise\n"
            "#@ desc_fr: ...             # description française\n"
            "#@ packages: a b c          # état : rpm -q\n"
            "#@ check_paths: /x /y/*     # état : chemins/globs\n"
            "#@ needs: repo-rpmfusion    # greffons installés avant\n"
            "#@ action: yes              # action pure : pas de pastille\n"
            "#@ root: yes                # exécuté via pkexec\n"
            "```\n\n"
            "Contrat : `--check` renvoie 0 si l'option est déjà installée. "
            "Sans paquets, sans chemins et sans `action`, `tools/check.py` refuse "
            "le greffon."
        ),
        "sections": {
            "easy": "Installation facile", "library": "Logithèque",
            "aidev": "IA & développeur", "dev": "Développement",
            "websrv": "Serveur web", "deps": "Dépendances",
            "repos": "Dépôts", "gaming": "Gaming", "audio": "Audio",
            "video": "Vidéo", "hardware": "Matériel", "mesa": "Graphismes",
            "kernel": "Noyau", "power": "Alimentation", "fan": "Ventilateur",
            "maint": "Maintenance", "update": "Mises à jour", "lang": "Langues",
            "features": "Fonctionnalités", "fix": "Réparation",
        },
    },
    "en": {
        "title": "Addon reference",
        "intro": (
            "Every option is a self-contained `.sh` script in `beta/addons/`. "
            "This table is **generated** from `addons/index.json` by "
            "`tools/docs.py`: it always matches what ships."
        ),
        "columns": ("Addon", "Version", "Packages", "State"),
        "state": "RPM packages and/or paths",
        "action": "action (no state)",
        "fields": (
            "## Script header\n\n"
            "```bash\n"
            "#!/usr/bin/env bash\n"
            "#@ id: codecs-av            # unique id = file name\n"
            "#@ version: 1.0.1           # compared by the catalog (x.y.z)\n"
            "#@ section: video           # sidebar section\n"
            "#@ icon: video-x-generic-symbolic\n"
            "#@ title: Video codecs      # English title\n"
            "#@ title_fr: Codecs vidéo   # French title\n"
            "#@ desc: ...                # English description\n"
            "#@ desc_fr: ...             # French description\n"
            "#@ packages: a b c          # state: rpm -q\n"
            "#@ check_paths: /x /y/*     # state: paths/globs\n"
            "#@ needs: repo-rpmfusion    # installed first\n"
            "#@ action: yes              # pure action: no badge\n"
            "#@ root: yes                # run through pkexec\n"
            "```\n\n"
            "Contract: `--check` exits 0 when the option is already installed. "
            "Without packages, paths or `action`, `tools/check.py` rejects it."
        ),
        "sections": {
            "easy": "Easy setup", "library": "Applications",
            "aidev": "AI & developer", "dev": "Development",
            "websrv": "Web server", "deps": "Dependencies",
            "repos": "Repositories", "gaming": "Gaming", "audio": "Audio",
            "video": "Video", "hardware": "Hardware", "mesa": "Graphics",
            "kernel": "Kernel", "power": "Power", "fan": "Fan",
            "maint": "Maintenance", "update": "Updates", "lang": "Languages",
            "features": "Features", "fix": "Repair",
        },
    },
}


def render(lang: str) -> str:
    data = json.loads((ROOT / "addons" / "index.json").read_text(encoding="utf-8"))
    text = TEXT[lang]
    raw = data.get("addons", {})
    addons = list(raw.values()) if isinstance(raw, dict) else list(raw)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for addon in addons:
        grouped[addon["section"]].append(addon)

    lines = [f"# {text['title']}", "", text["intro"], ""]
    for section in sorted(grouped, key=lambda s: text["sections"].get(s, s)):
        lines.append(f"## {text['sections'].get(section, section)}")
        lines.append("")
        lines.append("| " + " | ".join(text["columns"]) + " |")
        lines.append("|" + "|".join(["---"] * len(text["columns"])) + "|")
        for addon in sorted(grouped[section], key=lambda a: a["id"]):
            packages = ", ".join(f"`{p}`" for p in addon.get("packages", [])) or "—"
            state = text["action"] if addon.get("action") else text["state"]
            title = addon.get("title_fr" if lang == "fr" else "title", addon["id"])
            lines.append(
                f"| **{title}** (`{addon['id']}`) | {addon['version']} | {packages} | {state} |"
            )
        lines.append("")
    lines += ["", text["fields"], ""]
    lines.append(f"_{len(addons)} addons, {len(grouped)} sections._")
    return "\n".join(lines) + "\n"


def main() -> int:
    for lang in ("fr", "en"):
        target = DOC / lang / "addons.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(lang), encoding="utf-8")
        print(f"{target.relative_to(ROOT)} écrit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
