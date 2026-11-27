#!/usr/bin/env bash
#@ id: deps-python-versions
#@ version: 1.0.0
#@ section: deps
#@ icon: dialog-information-symbolic
#@ title: Show Python versions
#@ title_fr: Afficher les versions de Python
#@ desc: python3, pip3 and venv versions.
#@ action: yes
#@ desc_fr: Versions de python3, pip3 et venv.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
python3 --version
pip3 --version 2>/dev/null || echo "pip3 absent"
