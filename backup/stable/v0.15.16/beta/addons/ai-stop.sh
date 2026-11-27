#!/usr/bin/env bash
#@ id: ai-stop
#@ version: 1.0.0
#@ section: aidev
#@ icon: media-playback-stop-symbolic
#@ title: Stop AI services
#@ title_fr: Arrêter les services IA
#@ desc: Stops Open WebUI and Ollama to free memory.
#@ action: yes
#@ desc_fr: Arrête Open WebUI et Ollama pour libérer la mémoire.
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
podman stop open-webui 2>/dev/null || true
systemctl stop ollama 2>/dev/null || true
free -h | head -2
