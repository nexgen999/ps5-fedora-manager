#!/usr/bin/env python3
"""Auto-test de la logique sans GTK : catalogue, langues, environnements.

Usage : python3 beta/tools/selftest.py
Sert de garde-fou avant de pousser : il n'installe rien et ne touche à rien.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ps5m import catalog, i18n, system  # noqa: E402
from ps5m.env import detect, select  # noqa: E402
from ps5m.journal import Journal  # noqa: E402

CHECKS = 0


def ok(condition: bool, label: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(label)
    print(f"  ok  {label}")


def test_catalog() -> None:
    addons = catalog.load_local()
    ok(len(addons) >= 40, f"{len(addons)} greffons lus")
    sections = {a.section for a in addons.values()}
    ok(len(sections) >= 14, f"{len(sections)} sections couvertes")
    ok(any(a.action for a in addons.values()), "greffons d'action reconnus")
    ok(all(a.version.count(".") == 2 for a in addons.values()),
       "versions au format x.y.z")
    codecs = addons["codecs-av"]
    ok(codecs.version == "1.0.1", f"version de codecs-av = {codecs.version}")
    ok(len(codecs.packages) == 11, f"codecs-av : {len(codecs.packages)} paquets")
    ok("gstreamer1-plugin-libav" in codecs.packages, "nom actuel du greffon libav")
    ok(codecs.needs == ("repo-rpmfusion",), "codecs-av dépend de repo-rpmfusion")
    ok(codecs.title("fr").startswith("Codecs"), "titre français de codecs-av")

    ok(catalog.version_key("1.10.0") > catalog.version_key("1.9.9"), "comparaison 1.10 > 1.9")
    ok(catalog.version_key("0.15.10") > catalog.version_key("0.15.9"), "comparaison 0.15.10")

    local = {"a": catalog.Addon(id="a", version="1.0.0")}
    remote = {
        "a": catalog.Addon(id="a", version="1.0.0"),
        "b": catalog.Addon(id="b", version="2.0.0"),
    }
    outdated, removed = catalog.pending(local, remote)
    ok([a.id for a in outdated] == ["b"], "seul le greffon modifié doit être téléchargé")
    ok(removed == [], "aucun greffon supprimé")

    ordered = [a.id for a in catalog.order(list(addons.values()))]
    ok(ordered.index("repo-rpmfusion") < ordered.index("codecs-av"), "dépendances avant dépendants")

    index = catalog.read_index(catalog.ADDONS_DIR / catalog.INDEX_NAME)
    ok(set(index) == set(addons), "index.json couvre tous les scripts")
    ok(index["ffmpeg-full"].sha256 == addons["ffmpeg-full"].sha256, "empreinte identique")


def test_langs() -> None:
    i18n.load("en")
    ok(i18n.tr("status.installed") == "Installed", "anglais chargé")
    i18n.load("fr")
    ok(i18n.tr("status.installed") == "Installé", "français chargé")
    ok(i18n.tr("status.partial", done=10, total=11) == "10/11", "placeholders formatés")
    ok(i18n.tr("cle.inexistante") == "cle.inexistante", "clé inconnue rendue telle quelle")
    for code in i18n.codes():
        done, total, missing = i18n.coverage(code)
        ok(done == total and not missing, f"{code} : {done}/{total} clés")
    ok(len(i18n.available()) == 6, "6 langues proposées")


def test_env() -> None:
    kde = select("kde")
    ok(kde.id == "kde", "sélection KDE")
    ok(len(kde.set_theme_commands(True)) == 2, "KDE : deux commandes de thème")
    ok(not kde.supports("accent"), "KDE : accent non pris en charge")

    gnome = select("gnome")
    ok(gnome.supports("accent"), "GNOME : accent pris en charge")
    ok("prefer-dark" in " ".join(gnome.set_theme_commands(True)[0]), "GNOME : thème sombre")

    os.environ["XDG_CURRENT_DESKTOP"] = "X-Cinnamon"
    ok(detect().id == "cinnamon", "détection Cinnamon")
    os.environ["XDG_CURRENT_DESKTOP"] = "KDE"
    ok(detect().id == "kde", "détection KDE")
    os.environ["XDG_CURRENT_DESKTOP"] = "i3"
    ok(detect().id == "generic", "bureau inconnu → générique")
    select("gnome")


def test_system_and_journal() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        marker = Path(tmp) / "dossier" / "fichier"
        marker.parent.mkdir()
        marker.write_text("x", encoding="utf-8")
        ok(system.path_present([str(marker)])[str(marker)], "chemin existant détecté")
        ok(not system.path_present([f"{tmp}/absent"])[f"{tmp}/absent"], "chemin absent détecté")
        ok(system.path_present([f"{tmp}/*/fichier"])[f"{tmp}/*/fichier"], "glob résolu")

        log = Path(tmp) / "manager.log"
        journal = Journal(log)
        journal.write("test")
        ok("test" in journal.text(), "journal écrit sur disque")
        ok("test" in Journal(log).text(), "journal relu au démarrage")


def main() -> int:
    for name, test in (
        ("catalogue", test_catalog),
        ("langues", test_langs),
        ("environnements", test_env),
        ("système + journal", test_system_and_journal),
    ):
        print(f"{name} :")
        test()
    print(f"\n{CHECKS} vérifications OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
