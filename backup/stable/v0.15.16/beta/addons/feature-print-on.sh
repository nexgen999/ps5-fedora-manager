#!/usr/bin/env bash
#@ id: feature-print-on
#@ version: 1.0.0
#@ section: features
#@ icon: printer-symbolic
#@ title: Enable printing
#@ title_fr: Activer l'impression
#@ desc: systemctl enable --now cups.
#@ action: yes
#@ desc_fr: systemctl enable --now cups.
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
systemctl enable --now cups
systemctl --no-pager --lines=3 status cups || true
