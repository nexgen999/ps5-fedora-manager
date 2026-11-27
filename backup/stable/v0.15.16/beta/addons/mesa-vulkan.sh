#!/usr/bin/env bash
#@ id: mesa-vulkan
#@ version: 1.0.0
#@ section: mesa
#@ icon: video-display-symbolic
#@ title: Vulkan tools
#@ title_fr: Outils Vulkan
#@ desc: vulkaninfo, vulkan-tools and headers.
#@ desc_fr: vulkaninfo, vulkan-tools et en-têtes.
#@ packages: vulkan-tools vulkan-loader-devel
#@ root: yes
set -euo pipefail

PKGS=(vulkan-tools vulkan-loader-devel)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de mesa-vulkan…"
dnf install -y --skip-unavailable "${PKGS[@]}"
