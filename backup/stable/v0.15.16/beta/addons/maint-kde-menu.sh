#!/usr/bin/env bash
#@ id: maint-kde-menu
#@ version: 1.0.0
#@ section: maint
#@ icon: view-refresh-symbolic
#@ title: Rebuild KDE menu cache
#@ title_fr: Reconstruire le cache du menu KDE
#@ desc: kbuildsycoca (KDE only, harmless elsewhere).
#@ action: yes
#@ desc_fr: kbuildsycoca (KDE uniquement, sans effet ailleurs).
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 --noincremental
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
    kbuildsycoca5 --noincremental
else
    echo "→ KDE n'est pas installé : rien à faire."
fi
