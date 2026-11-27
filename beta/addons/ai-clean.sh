#!/usr/bin/env bash
#@ id: ai-clean
#@ version: 1.0.0
#@ section: aidev
#@ icon: user-trash-symbolic
#@ title: Clean Podman images
#@ title_fr: Nettoyer les images Podman
#@ desc: podman image prune -f.
#@ action: yes
#@ desc_fr: podman image prune -f.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
podman image prune -f
