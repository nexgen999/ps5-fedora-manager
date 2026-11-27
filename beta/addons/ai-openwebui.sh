#!/usr/bin/env bash
#@ id: ai-openwebui
#@ version: 1.0.0
#@ section: aidev
#@ icon: applications-internet-symbolic
#@ title: Open WebUI
#@ title_fr: Open WebUI
#@ desc: Web chat for local models, through a Podman container.
#@ action: yes
#@ packages: podman
#@ desc_fr: Chat web pour les modèles locaux, via un conteneur Podman.
#@ needs: ai-ollama
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then
    podman container exists open-webui >/dev/null 2>&1
    exit $?
fi
command -v podman >/dev/null 2>&1 || { echo "Podman absent"; exit 1; }
podman run -d --name open-webui -p 3000:8080 \
    --add-host=host.containers.internal:host-gateway \
    -v open-webui:/app/backend/data \
    ghcr.io/open-webui/open-webui:main
