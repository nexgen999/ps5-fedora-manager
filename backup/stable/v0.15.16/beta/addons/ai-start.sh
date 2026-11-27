#!/usr/bin/env bash
#@ id: ai-start
#@ version: 1.0.0
#@ section: aidev
#@ icon: media-playback-start-symbolic
#@ title: Start AI services
#@ title_fr: Démarrer les services IA
#@ desc: Starts Ollama and the Open WebUI container.
#@ action: yes
#@ desc_fr: Démarre Ollama et le conteneur Open WebUI.
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
systemctl start ollama 2>/dev/null || true
podman start open-webui 2>/dev/null || echo "→ Conteneur Open WebUI absent."
systemctl is-active ollama || true
