#!/usr/bin/env python3
"""Compare les options de la version stable (0.15.x) avec les greffons de la bêta.

Lecture **statique** de `ps5_manager.py` (AST, aucun import de GTK) :

- `SECTIONS` et `PAGE_BUILDERS` donnent la liste des sections et leur fonction ;
- dans chaque `build_page_*`, on relève les titres de groupes, les lignes
  (`win.row`, `_install_row`, `win.show_confirm`) et les paquets installés
  (`packages=[...]`, `dnf install …`) ;
- les titres `T("clé")` sont résolus avec la table `STRINGS` (français) ;
- les greffons bêta viennent de `addons/index.json`.

Sortie : `doc/fr/comparaison-0.15.11.md`, `doc/en/comparison-0.15.11.md`, et un
résumé sur la sortie standard. `--json` écrit la comparaison brute.

    python3 beta/tools/compare_stable.py [--json /tmp/comparaison.json]
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # racine du dépôt
BETA = Path(__file__).resolve().parent.parent
STABLE = ROOT / "ps5_manager.py"

# Section stable → sections bêta (fx éclaté en audio + vidéo, hw renommé).
SECTION_MAP = {
    "logs": ("logs",),
    "library": ("library",),
    "aidev": ("aidev",),
    "dev": ("dev",),
    "websrv": ("websrv",),
    "easy": ("easy",),
    "services": ("services",),
    "fx": ("audio", "video"),
    "deps": ("deps",),
    "gaming": ("gaming",),
    "features": ("features",),
    "update": ("update",),
    "lang": ("lang",),
    "repos": ("repos",),
    "users": ("users",),
    "fedora": ("fedora",),
    "maint": ("maint",),
    "power": ("power",),
    "fan": ("fan",),
    "hw": ("hardware",),
    "mesa": ("mesa",),
    "kernel": ("kernel",),
    "fix": ("fix",),
    "ui_lang": ("ui_lang",),
}

SKIP_ARGS = {"dnf", "install", "reinstall", "-y", "--skip-unavailable", "&&", "|"}


def literal(node: ast.AST):
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return None


def resolve(node: ast.AST | None, strings: dict[str, str]) -> str:
    """Texte français d'un argument (T("clé"), _L("fr", "en"), littéral)."""
    if node is None:
        return ""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Call):
        name = getattr(node.func, "id", getattr(node.func, "attr", ""))
        if name == "T" and node.args:
            key = literal(node.args[0])
            if isinstance(key, str):
                return strings.get(key, key)
        if name in ("_L", "L") and node.args:
            first = literal(node.args[0])
            if isinstance(first, str):
                return first
        if name in ("pref_group", "PreferencesGroup"):
            for keyword in node.keywords:
                if keyword.arg == "title":
                    return resolve(keyword.value, strings)
    if isinstance(node, ast.JoinedStr):
        return "<dynamique>"
    if isinstance(node, ast.BinOp):
        return "<dynamique>"
    return ""


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name) and func.value.id == "win":
                return func.attr
            return func.attr
    return ""


def target(node: ast.AST) -> str:
    """Pointeur d'une ligne : attribut du noeud passé à l'appel."""
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg in ("on_activate", "callback", "on_clicked", "handler"):
                return call_name(keyword.value)
    return ""


def packages_of(body: list[ast.AST]) -> list[str]:
    """Paquets installés par une page : `packages=[…]` et `dnf install …`."""
    found: list[str] = []

    for node in ast.walk(ast.Module(body=body, type_ignores=[])):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg == "packages":
                value = literal(keyword.value)
                if isinstance(value, (list, tuple)):
                    found += [str(item) for item in value if str(item).strip()]
        if call_name(node) in ("run_cmd_pty", "run_cmd", "run_command"):
            for arg in node.args:
                value = literal(arg)
                if isinstance(value, (list, tuple)):
                    items = [str(item) for item in value]
                    if "install" in items:
                        found += [
                            item for item in items
                            if item not in SKIP_ARGS and item.strip()
                        ]
    return list(dict.fromkeys(found))


def collect(builder: ast.FunctionDef, strings: dict[str, str]) -> dict:
    groups: list[str] = []
    options: list[dict[str, str]] = []
    for node in sorted(ast.walk(builder), key=lambda n: getattr(n, "lineno", 0)):
        if not isinstance(node, ast.Call):
            continue
        name = call_name(node)
        if name in ("pref_group", "PreferencesGroup"):
            title = resolve(node, strings)
            if title:
                groups.append(title)
        elif name in ("row", "_install_row"):
            if len(node.args) < 2:
                continue
            label = resolve(node.args[1], strings) if name == "_install_row" else resolve(node.args[0], strings)
            subtitle_node = node.args[2] if name == "_install_row" and len(node.args) > 2 else (
                node.args[1] if name == "row" and len(node.args) > 1 else None
            )
            options.append({
                "label": label or "<sans titre>",
                "subtitle": resolve(subtitle_node, strings) if subtitle_node else "",
                "action": target(node),
            })
        elif name == "show_confirm" and node.args:
            label = resolve(node.args[0], strings)
            if label:
                options.append({"label": label, "subtitle": "", "action": "show_confirm"})
    # Dédupliquer par libellé en gardant l'ordre
    seen: set[str] = set()
    unique = []
    for option in options:
        if option["label"] in seen or not option["label"]:
            continue
        seen.add(option["label"])
        unique.append(option)
    return {"groups": list(dict.fromkeys(groups)), "options": unique,
            "packages": packages_of(builder.body)}


def read_catalogs(tree: ast.Module) -> dict[str, list[dict]]:
    """Catalogues `DEV_CATALOG`, `WEB_CATALOG`… écrits avec `_dev_entry(...)`."""
    catalogs: dict[str, list[dict]] = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        elif isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        else:
            continue
        if not isinstance(value, (ast.Tuple, ast.List)):
            continue
        names = [t.id for t in targets if isinstance(t, ast.Name)]
        if not names or not names[0].endswith("_CATALOG"):
            continue
        entries: list[dict] = []
        for element in value.elts:
            if not isinstance(element, ast.Call):
                continue
            args = [literal(arg) for arg in element.args]
            if len(args) < 3:
                continue
            packages: list[str] = []
            for keyword in element.keywords:
                if keyword.arg == "packages":
                    value = literal(keyword.value)
                    if isinstance(value, (list, tuple)):
                        packages = [str(v) for v in value]
            entries.append({
                "label": str(args[2]),
                "subtitle": str(args[4]) if len(args) > 4 and isinstance(args[4], str) else "",
                "packages": packages,
            })
        catalogs[names[0]] = entries
    return catalogs


def stable_pages() -> dict[str, dict]:
    tree = ast.parse(STABLE.read_text(encoding="utf-8"))
    catalogs = read_catalogs(tree)
    strings: dict[str, str] = {}
    builders: dict[str, str] = {}

    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "STRINGS" for t in node.targets
        ):
            value = literal(node.value)
            if isinstance(value, dict):
                # STRINGS = {"fr": {...}, "en": {...}}
                french = value.get("fr")
                table = french if isinstance(french, dict) else value
                strings = {str(k): str(v) for k, v in table.items()}
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "PAGE_BUILDERS" for t in node.targets
        ):
            # Les valeurs sont des noms de fonctions : literal_eval ne suffit pas.
            if isinstance(node.value, ast.Dict):
                for key_node, value_node in zip(node.value.keys, node.value.values):
                    key = literal(key_node)
                    name = (
                        value_node.id
                        if isinstance(value_node, ast.Name)
                        else getattr(value_node, "attr", "")
                    )
                    if isinstance(key, str) and name:
                        builders[key] = name

    functions = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    pages: dict[str, dict] = {}
    for section, function_name in builders.items():
        builder = functions.get(function_name)
        if builder is None:
            pages[section] = {"groups": [], "options": [], "packages": [],
                             "error": f"{function_name} introuvable"}
            continue
        page = collect(builder, strings)
        page["packages"] = list(page["packages"])
        for name, entries in catalogs.items():
            if not any(
                isinstance(call, ast.Call)
                and call_name(call) == "_build_catalog_page"
                and any(isinstance(arg, ast.Name) and arg.id == name for arg in call.args)
                for call in ast.walk(builder)
            ):
                continue
            for entry in entries:
                page["options"].append(
                    {"label": entry["label"], "subtitle": entry["subtitle"],
                     "action": "_build_catalog_page"}
                )
                page["packages"] += [p for p in entry["packages"] if p not in page["packages"]]
        pages[section] = page
    return pages


def beta_addons() -> dict[str, list[dict]]:
    data = json.loads((BETA / "addons" / "index.json").read_text(encoding="utf-8"))
    by_section: dict[str, list[dict]] = {}
    for addon in data.get("addons", []):
        by_section.setdefault(addon["section"], []).append(addon)
    for items in by_section.values():
        items.sort(key=lambda a: a["id"])
    return by_section


def base_name(package: str) -> str:
    return package.split(".")[0]


def compare() -> dict:
    pages = stable_pages()
    beta = beta_addons()
    everywhere = {p for items in beta.values() for a in items for p in a.get("packages", [])}
    everywhere_bases = {base_name(p) for p in everywhere}
    rows = []
    for section, page in pages.items():
        beta_sections = SECTION_MAP.get(section, (section,))
        addons = [a for sec in beta_sections for a in beta.get(sec, [])]
        beta_packages = {p for a in addons for p in a.get("packages", [])}
        missing = [
            p for p in page["packages"]
            if p not in everywhere and base_name(p) not in everywhere_bases
        ]
        rows.append({
            "section": section,
            "beta_sections": list(beta_sections),
            "groups": page["groups"],
            "options": page["options"],
            "packages": page["packages"],
            "addons": addons,
            "missing_packages": missing,
        })
    return {"stable_version": _stable_version(), "sections": rows}


def _stable_version() -> str:
    for line in (ROOT / "version.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            return line.strip()
    return "0.15.x"


def render(data: dict, lang: str) -> str:
    fr = lang == "fr"
    lines = [
        f"# {'Comparaison 0.15.11 → bêta' if fr else 'Comparison 0.15.11 → beta'}",
        "",
        ("Généré par `tools/compare_stable.py` à partir de `ps5_manager.py` et de "
         "`addons/index.json`. Il liste, section par section, les options de la "
         "version stable et les greffons disponibles dans la bêta."
         if fr else
         "Generated by `tools/compare_stable.py` from `ps5_manager.py` and "
         "`addons/index.json`. It lists, section by section, the stable options "
         "and the addons available in the beta."),
        "",
        ("| Section | Options stable | Greffons bêta | Paquets stable non couverts |"
         if fr else
         "| Section | Stable options | Beta addons | Uncovered stable packages |"),
        "|---|---|---|---|",
    ]
    for row in data["sections"]:
        lines.append(
            f"| `{row['section']}` | {len(row['options'])} | {len(row['addons'])} | "
            f"{len(row['missing_packages'])} |"
        )

    for row in data["sections"]:
        title = " / ".join(row["beta_sections"])
        lines += ["", f"## `{row['section']}` → {title}", ""]
        if row["groups"]:
            lines.append(("Groupes : " if fr else "Groups: ") + " · ".join(row["groups"]))
            lines.append("")
        lines.append("| Option 0.15.11 | Action |" if fr else "| 0.15.11 option | Action |")
        lines.append("|---|---|")
        for option in row["options"]:
            label = option["label"].replace("|", "\\|")
            action = option["action"] or "—"
            lines.append(f"| {label} | `{action}` |")
        lines.append("")
        if row["addons"]:
            lines.append("| Greffon bêta | Version | Paquets |" if fr
                         else "| Beta addon | Version | Packages |")
            lines.append("|---|---|---|")
            for addon in row["addons"]:
                name = addon.get("title_fr" if fr else "title", addon["id"])
                packages = ", ".join(f"`{p}`" for p in addon.get("packages", [])) or "—"
                lines.append(f"| **{name}** (`{addon['id']}`) | {addon['version']} | {packages} |")
        lines.append("")
        if row["missing_packages"]:
            lines.append(
                ("Paquets de la stable sans équivalent dans les greffons : "
                 if fr else "Stable packages with no addon equivalent: ")
                + ", ".join(f"`{p}`" for p in row["missing_packages"])
            )
        else:
            lines.append("Tous les paquets de la stable sont couverts." if fr
                         else "Every stable package is covered.")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    data = compare()
    for lang in ("fr", "en"):
        target = BETA / "doc" / lang / f"comparaison-{data['stable_version']}.md" if lang == "fr" else \
            BETA / "doc" / lang / f"comparison-{data['stable_version']}.md"
        target.write_text(render(data, lang), encoding="utf-8")
        print(f"{target.relative_to(BETA)} écrit")
    if "--json" in argv:
        index = argv.index("--json")
        out = Path(argv[index + 1]) if len(argv) > index + 1 else BETA / "comparaison.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{out} écrit")

    print(f"\nstable {data['stable_version']} : "
          f"{sum(len(r['options']) for r in data['sections'])} options lues, "
          f"{sum(len(r['addons']) for r in data['sections'])} greffons bêta, "
          f"{sum(len(r['missing_packages']) for r in data['sections'])} paquets non couverts")
    for row in data["sections"]:
        if row["missing_packages"]:
            print(f"  {row['section']:<9} manquants : {', '.join(row['missing_packages'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
