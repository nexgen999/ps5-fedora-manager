#!/usr/bin/env bash
#@ id: fix-dnf
#@ version: 1.0.0
#@ section: fix
#@ icon: emblem-system-symbolic
#@ title: Rebuild the dnf cache
#@ title_fr: Reconstruire le cache dnf
#@ desc: Fixes "cannot download repomd.xml" and stale metadata errors.
#@ desc_fr: Corrige « cannot download repomd.xml » et les métadonnées obsolètes.
#@ action: yes
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then
    exit 1
fi

echo "→ Nettoyage puis reconstruction du cache dnf…"
dnf clean all
dnf makecache
