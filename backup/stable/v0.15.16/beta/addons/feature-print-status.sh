#!/usr/bin/env bash
#@ id: feature-print-status
#@ version: 1.0.0
#@ section: features
#@ icon: dialog-information-symbolic
#@ title: Printing status
#@ title_fr: État de l'impression
#@ desc: cups.socket, cups.service and lpstat.
#@ action: yes
#@ desc_fr: cups.socket, cups.service et lpstat.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
systemctl is-active cups.socket cups.service 2>/dev/null || true
lpstat -t 2>/dev/null || echo "→ Aucune imprimante configurée."
