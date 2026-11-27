#!/usr/bin/env bash
#@ id: kernel-ps5
#@ version: 1.0.0
#@ section: kernel
#@ icon: drive-harddisk-symbolic
#@ title: PS5 kernel patches
#@ title_fr: Correctifs noyau PS5
#@ desc: ps5-linux patch set and tools repositories (sources only, no kernel build).
#@ desc_fr: Jeu de correctifs ps5-linux et dépôts d'outils (sources seules, pas de compilation).
#@ check_paths: /usr/src/ps5-linux
#@ root: yes
set -euo pipefail

TARGET=/usr/src/ps5-linux
PATCHES="https://github.com/ps5-linux/ps5-linux-patches.git"

if [ "${1:-}" = "--check" ]; then
    [ -d "$TARGET/.git" ]
    exit $?
fi

dnf install -y --skip-unavailable git
mkdir -p /usr/src
if [ -d "$TARGET/.git" ]; then
    git -C "$TARGET" pull --ff-only
else
    git clone --depth 1 "$PATCHES" "$TARGET"
fi
echo "→ Sources dans $TARGET (compilation volontairement laissée manuelle)."
