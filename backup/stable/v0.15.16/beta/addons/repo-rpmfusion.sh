#!/usr/bin/env bash
#@ id: repo-rpmfusion
#@ version: 1.0.0
#@ section: repos
#@ icon: network-server-symbolic
#@ title: RPM Fusion (free + nonfree)
#@ title_fr: RPM Fusion (free + nonfree)
#@ desc: Adds the RPM Fusion free and nonfree repositories.
#@ desc_fr: Ajoute les dépôts RPM Fusion free et nonfree.
#@ packages: rpmfusion-free-release rpmfusion-nonfree-release
#@ root: yes
set -euo pipefail

PKGS=(rpmfusion-free-release rpmfusion-nonfree-release)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation des dépôts RPM Fusion…"
if dnf install -y "${PKGS[@]}"; then
    exit 0
fi
echo "Paquets absents des dépôts Fedora, installation directe :"
dnf install -y \
    "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm" \
    "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm"
