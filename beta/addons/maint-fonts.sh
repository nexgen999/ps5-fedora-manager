#!/usr/bin/env bash
#@ id: maint-fonts
#@ version: 1.0.0
#@ section: maint
#@ icon: font-x-generic-symbolic
#@ title: Rebuild font cache
#@ title_fr: Reconstruire le cache des polices
#@ desc: fc-cache -f for system and user fonts.
#@ action: yes
#@ desc_fr: fc-cache -f pour les polices système et utilisateur.
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
fc-cache -f
