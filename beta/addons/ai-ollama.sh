#!/usr/bin/env bash
#@ id: ai-ollama
#@ version: 1.0.0
#@ section: aidev
#@ icon: applications-science-symbolic
#@ title: Ollama (local models)
#@ title_fr: Ollama (modèles locaux)
#@ desc: Run local language models with a single command.
#@ desc_fr: Exécute des modèles de langage locaux en une commande.
#@ check_paths: /usr/local/bin/ollama
#@ root: yes
set -euo pipefail

INSTALLER="https://ollama.com/install.sh"

if [ "${1:-}" = "--check" ]; then
    command -v ollama >/dev/null 2>&1
    exit $?
fi

echo "→ Installation d'Ollama (script officiel)…"
curl -fsSL "$INSTALLER" | sh
systemctl enable --now ollama 2>/dev/null || true
echo "→ Modèle conseillé : ollama pull llama3.2"
