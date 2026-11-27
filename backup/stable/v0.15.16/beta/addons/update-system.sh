#!/usr/bin/env bash
#@ id: update-system
#@ version: 1.0.0
#@ section: update
#@ icon: software-update-available-symbolic
#@ title: Update Fedora and all packages
#@ title_fr: Mettre à jour Fedora et tous les paquets
#@ desc: dnf upgrade --refresh, then reports whether a reboot is needed.
#@ desc_fr: dnf upgrade --refresh, puis indique si un redémarrage est nécessaire.
#@ action: yes
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then
    exit 1
fi

echo "→ Mise à jour complète du système…"
dnf upgrade --refresh -y
if dnf needs-restarting -r >/dev/null 2>&1; then
    echo "→ Aucun redémarrage nécessaire."
else
    echo "→ Redémarrage recommandé (noyau ou services mis à jour)."
fi
