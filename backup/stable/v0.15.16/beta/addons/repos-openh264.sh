#!/usr/bin/env bash
#@ id: repos-openh264
#@ version: 1.0.0
#@ section: repos
#@ icon: folder-download-symbolic
#@ title: Enable OpenH264 repository
#@ title_fr: Activer le dépôt OpenH264
#@ desc: Cisco OpenH264 for WebRTC encoding.
#@ desc_fr: OpenH264 de Cisco pour l'encodage WebRTC.
#@ check_paths: /etc/yum.repos.d/fedora-cisco-openh264.repo
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then
    grep -q "enabled=1" /etc/yum.repos.d/fedora-cisco-openh264.repo 2>/dev/null
    exit $?
fi
dnf config-manager setopt fedora-cisco-openh264.enabled=1 \
    || dnf config-manager --set-enabled fedora-cisco-openh264
