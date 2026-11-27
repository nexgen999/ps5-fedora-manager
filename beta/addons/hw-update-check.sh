#!/usr/bin/env bash
#@ id: hw-update-check
#@ version: 1.0.0
#@ section: hardware
#@ icon: software-update-available-symbolic
#@ title: Check for updates
#@ title_fr: Vérifier les mises à jour
#@ desc: Compares the installed Hardware Control GUI with GitHub.
#@ action: yes
#@ desc_fr: Compare l'interface Hardware Control installée avec GitHub.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
LOCAL=/opt/ps5-hwcon-gui/src
[ -d "$LOCAL/.git" ] || { echo "→ Interface non installée."; exit 0; }
REMOTE=$(git ls-remote https://github.com/NotHavocc/ps5-hwcon-gui HEAD | cut -f1)
CURRENT=$(git -C "$LOCAL" rev-parse HEAD)
if [ "$REMOTE" = "$CURRENT" ]; then
    echo "→ Déjà à jour ($CURRENT)."
else
    echo "→ Mise à jour disponible : $CURRENT → $REMOTE"
fi
