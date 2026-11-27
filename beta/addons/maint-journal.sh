#!/usr/bin/env bash
#@ id: maint-journal
#@ version: 1.0.0
#@ section: maint
#@ icon: text-x-generic-symbolic
#@ title: Shrink the system journal
#@ title_fr: Réduire le journal système
#@ desc: Keeps the last 100 MB of systemd journal.
#@ action: yes
#@ desc_fr: Conserve les 100 derniers Mo du journal systemd.
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
journalctl --vacuum-size=100M
