#!/usr/bin/env bash
#@ id: maint-flatpak
#@ version: 1.0.0
#@ section: maint
#@ icon: software-store-symbolic
#@ title: Update Flatpak apps
#@ title_fr: Mettre à jour les applications Flatpak
#@ desc: Updates Flatpak runtimes and removes unused ones.
#@ desc_fr: Met à jour les runtimes Flatpak et supprime les inutilisés.
#@ action: yes
#@ needs: repo-flathub
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then
    exit 1   # action : toujours proposée
fi

command -v flatpak >/dev/null 2>&1 || { echo "Flatpak absent"; exit 1; }
echo "→ Mise à jour des applications Flatpak…"
flatpak update -y --noninteractive
flatpak uninstall --unused -y
