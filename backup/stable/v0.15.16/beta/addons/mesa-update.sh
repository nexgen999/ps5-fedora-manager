#!/usr/bin/env bash
#@ id: mesa-update
#@ version: 1.0.0
#@ section: mesa
#@ icon: software-update-available-symbolic
#@ title: Update Mesa
#@ title_fr: Mettre à jour Mesa
#@ desc: dnf upgrade for mesa and Vulkan packages.
#@ action: yes
#@ desc_fr: dnf upgrade pour mesa et les paquets Vulkan.
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
dnf upgrade -y mesa-dri-drivers mesa-libGL mesa-vulkan-drivers
