#!/usr/bin/env bash
#@ id: gaming-uninstall
#@ version: 1.0.0
#@ section: gaming
#@ icon: user-trash-symbolic
#@ title: Uninstall gaming tools
#@ title_fr: Désinstaller les outils de jeu
#@ desc: Removes Gamescope, GameMode and MangoHud (keeps Steam).
#@ action: yes
#@ desc_fr: Supprime Gamescope, GameMode et MangoHud (conserve Steam).
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
for pkg in gamescope gamemode mangohud; do
    rpm -q "$pkg" >/dev/null 2>&1 && dnf remove -y "$pkg" || true
done
