#!/usr/bin/env bash
#@ id: ai-logs
#@ version: 1.0.0
#@ section: aidev
#@ icon: text-x-generic-symbolic
#@ title: Open WebUI logs
#@ title_fr: Journaux Open WebUI
#@ desc: podman logs --tail 30 open-webui.
#@ action: yes
#@ desc_fr: podman logs --tail 30 open-webui.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
podman logs --tail 30 open-webui 2>&1 || echo "→ Conteneur absent."
