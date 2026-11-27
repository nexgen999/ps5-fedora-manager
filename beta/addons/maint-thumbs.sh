#!/usr/bin/env bash
#@ id: maint-thumbs
#@ version: 1.0.0
#@ section: maint
#@ icon: image-x-generic-symbolic
#@ title: Clear thumbnail cache
#@ title_fr: Vider le cache des vignettes
#@ desc: Removes the per-user thumbnail cache.
#@ action: yes
#@ desc_fr: Supprime le cache de vignettes de l'utilisateur.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
rm -rf "${HOME}/.cache/thumbnails/"*
echo "→ Cache des vignettes vidé."
