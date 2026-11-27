#!/usr/bin/env bash
#@ id: feature-print
#@ version: 1.0.0
#@ section: features
#@ icon: printer-symbolic
#@ title: Printing (CUPS)
#@ title_fr: Impression (CUPS)
#@ desc: CUPS server, filters and the printer setup tool.
#@ desc_fr: Serveur CUPS, filtres et outil de configuration d'imprimante.
#@ packages: cups cups-filters system-config-printer
#@ root: yes
set -euo pipefail

PKGS=(cups cups-filters system-config-printer)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de feature-print…"
dnf install -y --skip-unavailable "${PKGS[@]}"
