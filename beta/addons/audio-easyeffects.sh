#!/usr/bin/env bash
#@ id: audio-easyeffects
#@ version: 1.0.0
#@ section: audio
#@ icon: audio-volume-high-symbolic
#@ title: Easy Effects
#@ title_fr: Easy Effects
#@ desc: Equalizer, noise reduction and Dolby Atmos effects over PipeWire.
#@ desc_fr: Égaliseur, réduction de bruit et effets Dolby Atmos via PipeWire.
#@ packages: easyeffects
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then
    rpm -q easyeffects >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation d'Easy Effects…"
dnf install -y easyeffects
