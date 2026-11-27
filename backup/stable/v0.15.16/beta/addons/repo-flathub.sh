#!/usr/bin/env bash
#@ id: repo-flathub
#@ version: 1.0.0
#@ section: repos
#@ icon: software-store-symbolic
#@ title: Flathub
#@ title_fr: Flathub
#@ desc: Adds the Flathub remote for Flatpak applications.
#@ desc_fr: Ajoute le dépôt Flathub pour les applications Flatpak.
#@ check_paths: /var/lib/flatpak/repo
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then
    command -v flatpak >/dev/null 2>&1 || exit 1
    flatpak remotes --system --columns=name 2>/dev/null | grep -qx flathub
    exit $?
fi

command -v flatpak >/dev/null 2>&1 || dnf install -y flatpak
flatpak remote-add --system --if-not-exists flathub \
    https://dl.flathub.org/repo/flathub.flatpakrepo
echo "→ Flathub ajouté."
