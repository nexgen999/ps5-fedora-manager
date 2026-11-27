#!/usr/bin/env bash
#@ id: feature-print-off
#@ version: 1.0.0
#@ section: features
#@ icon: printer-symbolic
#@ title: Disable printing
#@ title_fr: Couper l'impression
#@ desc: systemctl disable --now cups.
#@ action: yes
#@ desc_fr: systemctl disable --now cups.
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
systemctl disable --now cups
