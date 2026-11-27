#!/usr/bin/env bash
#@ id: hw-check
#@ version: 1.0.0
#@ section: hardware
#@ icon: computer-symbolic
#@ title: Check PS5 hardware
#@ title_fr: Vérifier le matériel PS5
#@ desc: Lists hwmon entries and PS5 sysfs nodes.
#@ action: yes
#@ desc_fr: Liste les entrées hwmon et les nœuds sysfs PS5.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
for hw in /sys/class/hwmon/hwmon*; do
    [ -r "$hw/name" ] && echo "hwmon : $(cat "$hw/name")"
done
ls /sys/devices/platform/ 2>/dev/null | grep -i ps5 || echo "→ Aucun nœud PS5 visible."
lspci -nn 2>/dev/null | grep -Ei "sony|ps5|amd" || true
