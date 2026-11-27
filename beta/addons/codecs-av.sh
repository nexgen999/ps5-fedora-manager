#!/usr/bin/env bash
#@ id: codecs-av
#@ version: 1.0.1
#@ section: video
#@ icon: video-x-generic-symbolic
#@ title: Audio and video codecs
#@ title_fr: Codecs audio et vidéo
#@ desc: Full GStreamer plus RPM Fusion codecs (H.264, HEVC, AAC, MP3, Dolby…).
#@ desc_fr: GStreamer complet et codecs RPM Fusion (H.264, HEVC, AAC, MP3, Dolby…).
#@ packages: gstreamer1-plugins-good gstreamer1-plugins-bad-free gstreamer1-plugins-bad-free-extras gstreamer1-plugins-ugly gstreamer1-plugin-libav gstreamer1-plugins-bad-freeworld gstreamer1-plugin-openh264 libavcodec-freeworld lame x264-libs x265-libs
#@ needs: repo-rpmfusion
#@ root: yes
set -euo pipefail

PKGS=(
    gstreamer1-plugins-good
    gstreamer1-plugins-bad-free
    gstreamer1-plugins-bad-free-extras
    gstreamer1-plugins-ugly
    gstreamer1-plugin-libav          # nom actuel : « plugins » a disparu depuis Fedora 43
    gstreamer1-plugins-bad-freeworld
    gstreamer1-plugin-openh264
    libavcodec-freeworld
    lame
    x264-libs
    x265-libs
)

if [ "${1:-}" = "--check" ]; then
    missing=0
    for pkg in "${PKGS[@]}"; do
        rpm -q "$pkg" >/dev/null 2>&1 || { echo "manquant : $pkg"; missing=1; }
    done
    exit "$missing"
fi

echo "→ Installation des codecs audio et vidéo…"
dnf install -y --skip-unavailable "${PKGS[@]}"
