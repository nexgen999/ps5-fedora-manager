#!/usr/bin/env bash
#@ id: ai-diagnostic
#@ version: 1.0.0
#@ section: aidev
#@ icon: utilities-system-monitor-symbolic
#@ title: AI diagnostics
#@ title_fr: Diagnostic IA
#@ desc: RAM, GPU and disk space for local models.
#@ action: yes
#@ desc_fr: RAM, GPU et espace disque pour les modèles locaux.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
free -h
echo
lspci 2>/dev/null | grep -Ei "vga|3d|display" || true
echo
df -h "${HOME}"
