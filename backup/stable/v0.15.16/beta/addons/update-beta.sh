#!/usr/bin/env bash
#@ id: update-beta
#@ version: 1.0.0
#@ section: update
#@ icon: software-update-available-symbolic
#@ title: Update the manager itself
#@ title_fr: Mettre à jour le manager
#@ desc: git pull in the repository that contains this beta folder.
#@ desc_fr: git pull dans le dépôt qui contient ce dossier beta.
#@ action: yes
#@ root: no
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if [ "${1:-}" = "--check" ]; then
    exit 1
fi

command -v git >/dev/null 2>&1 || { echo "git absent"; exit 1; }
echo "→ Mise à jour de $ROOT…"
git -C "$ROOT" pull --ff-only
