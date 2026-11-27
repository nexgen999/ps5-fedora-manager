#!/usr/bin/env bash
#@ id: maint-old-kernels
#@ version: 1.0.0
#@ section: maint
#@ icon: drive-harddisk-symbolic
#@ title: Remove old kernels
#@ title_fr: Supprimer les anciens noyaux
#@ desc: Keeps the running kernel and the newest one.
#@ action: yes
#@ desc_fr: Conserve le noyau courant et le plus récent.
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
OLD=$(dnf repoquery --installonly --latest-limit=-1 -q 2>/dev/null || true)
if [ -z "$OLD" ]; then
    echo "→ Aucun ancien noyau à supprimer."
    exit 0
fi
echo "→ Suppression : $OLD"
# shellcheck disable=SC2086
dnf remove -y $OLD
