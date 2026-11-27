#!/usr/bin/env bash
#@ id: mesa-radv
#@ version: 1.0.0
#@ section: mesa
#@ icon: video-display-symbolic
#@ title: Force the RADV Vulkan driver
#@ title_fr: Forcer le pilote Vulkan RADV
#@ desc: Writes AMD_VULKAN_ICD=RADV for the session (AMD GPUs).
#@ desc_fr: Écrit AMD_VULKAN_ICD=RADV pour la session (GPU AMD).
#@ check_paths: ~/.config/environment.d/50-radv.conf
#@ root: no
set -euo pipefail

TARGET="${HOME}/.config/environment.d/50-radv.conf"
mkdir -p "$(dirname "$TARGET")"
printf '%s\n' "AMD_VULKAN_ICD=RADV" > "$TARGET"
echo "→ $TARGET écrit (actif à la prochaine session)."
