#!/usr/bin/env bash
#@ id: fix-steam
#@ version: 1.0.0
#@ section: fix
#@ icon: applications-games-symbolic
#@ title: Repair Steam
#@ title_fr: Réparer Steam
#@ desc: Clears shader cache and appcache, then relaunches Steam.
#@ action: yes
#@ desc_fr: Vide le cache de shaders et l'appcache, puis relance Steam.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
pkill -f steam 2>/dev/null || true
rm -rf "${HOME}/.steam/steam/appcache" \
       "${HOME}/.steam/steam/steamapps/shadercache" \
       "${HOME}/.steam/steam/logs"/* 2>/dev/null || true
mkdir -p "${HOME}/.steam/steam/steamapps/shadercache"
echo "→ Caches Steam vidés ; relance Steam pour reconstruire."
