#!/usr/bin/env bash
#@ id: fan-restart
#@ version: 1.0.0
#@ section: fan
#@ icon: view-refresh-symbolic
#@ title: Restart the fan service
#@ title_fr: Relancer le service du ventilateur
#@ desc: systemctl restart ps5fan.service.
#@ action: yes
#@ desc_fr: systemctl restart ps5fan.service.
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
systemctl restart ps5fan.service
systemctl --no-pager --lines=5 status ps5fan.service || true
