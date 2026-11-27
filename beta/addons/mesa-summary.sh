#!/usr/bin/env bash
#@ id: mesa-summary
#@ version: 1.0.0
#@ section: mesa
#@ icon: dialog-information-symbolic
#@ title: Graphics summary
#@ title_fr: Résumé graphique
#@ desc: vulkaninfo and glxinfo summary.
#@ action: yes
#@ desc_fr: Résumé vulkaninfo et glxinfo.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
command -v vulkaninfo >/dev/null 2>&1 && vulkaninfo --summary
command -v glxinfo >/dev/null 2>&1 && glxinfo -B
