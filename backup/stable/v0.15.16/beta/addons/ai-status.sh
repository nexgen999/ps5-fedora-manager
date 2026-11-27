#!/usr/bin/env bash
#@ id: ai-status
#@ version: 1.0.0
#@ section: aidev
#@ icon: dialog-information-symbolic
#@ title: AI containers status
#@ title_fr: État des conteneurs IA
#@ desc: podman ps -a and ollama list.
#@ action: yes
#@ desc_fr: podman ps -a et ollama list.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
podman ps -a 2>/dev/null || echo "Podman absent"
echo
command -v ollama >/dev/null 2>&1 && ollama list || echo "Ollama absent"
