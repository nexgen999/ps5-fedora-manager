#!/usr/bin/env bash
#@ id: ai-models
#@ version: 1.0.0
#@ section: aidev
#@ icon: applications-science-symbolic
#@ title: Models in memory
#@ title_fr: Modèles en mémoire
#@ desc: ollama ps: models currently loaded.
#@ action: yes
#@ desc_fr: ollama ps : modèles actuellement chargés.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
command -v ollama >/dev/null 2>&1 && ollama ps || echo "Ollama absent"
