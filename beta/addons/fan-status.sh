#!/usr/bin/env bash
#@ id: fan-status
#@ version: 1.0.0
#@ section: fan
#@ icon: weather-windy-symbolic
#@ title: Fan and temperature status
#@ title_fr: État du ventilateur et des températures
#@ desc: ps5fan.service state and hwmon temperatures.
#@ action: yes
#@ desc_fr: État de ps5fan.service et températures hwmon.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
systemctl is-active ps5fan.service 2>/dev/null || echo "ps5fan.service inactif"
for hw in /sys/class/hwmon/hwmon*; do
    [ -r "$hw/name" ] || continue
    echo "$(cat "$hw/name") :"
    for t in "$hw"/temp*_input; do
        [ -r "$t" ] || continue
        echo "  $(basename "$t") = $(( $(cat "$t") / 1000 )) °C"
    done
done
