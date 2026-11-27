#!/usr/bin/env bash
#@ id: maint-disk
#@ version: 1.0.0
#@ section: maint
#@ icon: drive-harddisk-symbolic
#@ title: Disk usage report
#@ title_fr: Rapport d'utilisation du disque
#@ desc: df -h and the ten largest folders in your home.
#@ action: yes
#@ desc_fr: df -h et les dix plus gros dossiers du dossier personnel.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
df -h
echo
du -xh --max-depth=2 "${HOME}" 2>/dev/null | sort -rh | head -10
