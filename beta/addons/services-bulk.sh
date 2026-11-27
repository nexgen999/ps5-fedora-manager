#!/usr/bin/env bash
#@ id: services-bulk
#@ version: 1.0.0
#@ section: services
#@ icon: system-run-symbolic
#@ title: Stop unnecessary daemons
#@ title_fr: Couper les daemons inutiles
#@ desc: Bluetooth, printing, Avahi and ModemManager.
#@ action: yes
#@ desc_fr: Bluetooth, impression, Avahi et ModemManager.
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
for unit in bluetooth.service cups.service avahi-daemon.service ModemManager.service; do
    if systemctl list-unit-files "$unit" >/dev/null 2>&1; then
        systemctl disable --now "$unit" 2>/dev/null || true
        echo "→ $unit coupé."
    fi
done
