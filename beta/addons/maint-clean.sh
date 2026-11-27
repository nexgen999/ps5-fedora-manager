#!/usr/bin/env bash
#@ id: maint-clean
#@ version: 1.0.0
#@ section: maint
#@ icon: user-trash-symbolic
#@ title: Clean the package cache
#@ title_fr: Nettoyer le cache des paquets
#@ desc: Removes cached packages and unused dependencies.
#@ desc_fr: Supprime les paquets en cache et les dépendances inutilisées.
#@ action: yes
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then
    exit 1   # action : toujours proposée
fi

echo "→ Nettoyage du cache dnf et des dépendances inutilisées…"
dnf clean all
dnf autoremove -y
