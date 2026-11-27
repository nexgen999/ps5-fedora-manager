#!/usr/bin/env bash
#@ id: gaming-log
#@ version: 1.0.0
#@ section: gaming
#@ icon: text-x-generic-symbolic
#@ title: Show the launch log
#@ title_fr: Afficher le journal de lancement
#@ desc: Last lines of the Steam and gamescope logs.
#@ action: yes
#@ desc_fr: Dernières lignes des journaux Steam et gamescope.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
for f in "${HOME}/.steam/steam/logs/content_log.txt" "${HOME}/.local/share/gamescope/log"; do
    [ -r "$f" ] && { echo "== $f"; tail -n 20 "$f"; }
done
journalctl --user --no-pager --lines=20 2>/dev/null | tail -20 || true
