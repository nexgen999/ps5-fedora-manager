#!/usr/bin/env python3
"""Génère un script de greffon à partir de quelques options.

Usage :
    python3 beta/tools/new_addon.py --id app-btop --section library \
        --packages "btop" --title-en "btop" --title-fr "btop" \
        --desc-en "Resource monitor." --desc-fr "Moniteur de ressources."

    # ou, pour un script qui n'installe pas de paquets RPM :
    python3 beta/tools/new_addon.py --id repo-x --section repos \
        --check-paths /etc/yum.repos.d/x.repo --body-file body.sh

Le fichier créé contient l'en-tête `#@` lu par `ps5m/catalog.py`, le mode
`--check` (0 = installé) et l'installation. Il reste ensuite à éditer à la main
si la commande doit sortir du schéma « dnf install ».
"""
from __future__ import annotations

import argparse
from pathlib import Path

ADDONS_DIR = Path(__file__).resolve().parent.parent / "addons"


def render(
    addon_id: str,
    section: str,
    title_en: str,
    title_fr: str,
    desc_en: str,
    desc_fr: str,
    version: str = "1.0.0",
    icon: str = "application-x-executable-symbolic",
    packages: str = "",
    check_paths: str = "",
    needs: str = "",
    root: str = "yes",
    body: str = "",
) -> str:
    """Texte complet d'un script de greffon."""
    header = [
        "#!/usr/bin/env bash",
        f"#@ id: {addon_id}",
        f"#@ version: {version}",
        f"#@ section: {section}",
        f"#@ icon: {icon}",
        f"#@ title: {title_en}",
        f"#@ title_fr: {title_fr}",
        f"#@ desc: {desc_en}",
        f"#@ desc_fr: {desc_fr}",
    ]
    if packages:
        header.append(f"#@ packages: {packages}")
    if check_paths:
        header.append(f"#@ check_paths: {check_paths}")
    if needs:
        header.append(f"#@ needs: {needs}")
    header.append(f"#@ root: {root}")

    if body:
        return "\n".join(header) + "\nset -euo pipefail\n\n" + body.strip() + "\n"

    pkgs = packages.split()
    pkg_list = " ".join(pkgs)
    return (
        "\n".join(header)
        + "\nset -euo pipefail\n\n"
        + f"PKGS=({pkg_list})\n\n"
        + 'if [ "${1:-}" = "--check" ]; then\n'
        + '    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0\n'
        + "    exit 1\n"
        + "fi\n\n"
        + f'echo "→ Installation de {addon_id}…"\n'
        + 'dnf install -y --skip-unavailable "${PKGS[@]}"\n'
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Crée un greffon versionné.")
    parser.add_argument("--id", required=True)
    parser.add_argument("--section", required=True)
    parser.add_argument("--title-en", required=True)
    parser.add_argument("--title-fr", required=True)
    parser.add_argument("--desc-en", required=True)
    parser.add_argument("--desc-fr", required=True)
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--icon", default="application-x-executable-symbolic")
    parser.add_argument("--packages", default="")
    parser.add_argument("--check-paths", default="")
    parser.add_argument("--needs", default="")
    parser.add_argument("--root", default="yes", choices=("yes", "no"))
    parser.add_argument("--body-file", default="")
    args = parser.parse_args()

    body = Path(args.body_file).read_text(encoding="utf-8") if args.body_file else ""
    target = ADDONS_DIR / f"{args.id}.sh"
    if target.exists():
        print(f"{target} existe déjà : édite le script et incrémente sa version.")
        return 1
    target.write_text(
        render(
            args.id,
            args.section,
            args.title_en,
            args.title_fr,
            args.desc_en,
            args.desc_fr,
            version=args.version,
            icon=args.icon,
            packages=args.packages,
            check_paths=args.check_paths,
            needs=args.needs,
            root=args.root,
            body=body,
        ),
        encoding="utf-8",
    )
    target.chmod(0o755)
    print(f"{target} créé. Puis : python3 beta/tools/build_catalog.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
