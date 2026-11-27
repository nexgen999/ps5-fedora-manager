#!/usr/bin/env bash
#@ id: mesa-freeworld
#@ version: 1.0.0
#@ section: mesa
#@ icon: video-display-symbolic
#@ title: Mesa freeworld (VA-API)
#@ title_fr: Mesa freeworld (VA-API)
#@ desc: Hardware video decoding for AMD and Intel GPUs.
#@ desc_fr: Décodage vidéo matériel pour GPU AMD et Intel.
#@ packages: mesa-va-drivers-freeworld mesa-vdpau-drivers-freeworld
#@ needs: repo-rpmfusion
#@ root: yes
set -euo pipefail

PKGS=(mesa-va-drivers-freeworld mesa-vdpau-drivers-freeworld)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de mesa-freeworld…"
dnf install -y --skip-unavailable "${PKGS[@]}"
