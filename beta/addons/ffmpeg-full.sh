#!/usr/bin/env bash
#@ id: ffmpeg-full
#@ version: 1.0.0
#@ section: video
#@ icon: applications-multimedia-symbolic
#@ title: FFmpeg (full codecs)
#@ title_fr: FFmpeg (codecs complets)
#@ desc: ffmpeg and libavcodec-freeworld for every format.
#@ desc_fr: ffmpeg et libavcodec-freeworld pour tous les formats.
#@ packages: ffmpeg libavcodec-freeworld
#@ needs: repo-rpmfusion
#@ root: yes
set -euo pipefail

PKGS=(ffmpeg libavcodec-freeworld)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de FFmpeg complet…"
dnf install -y --skip-unavailable "${PKGS[@]}"
ffmpeg -version 2>/dev/null | head -1 || true
