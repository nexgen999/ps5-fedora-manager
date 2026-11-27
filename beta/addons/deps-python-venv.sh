#!/usr/bin/env bash
#@ id: deps-python-venv
#@ version: 1.0.0
#@ section: deps
#@ icon: folder-new-symbolic
#@ title: Create a Python virtualenv
#@ title_fr: Créer un environnement Python
#@ desc: Creates ~/my_project with venv and shows the versions.
#@ action: yes
#@ desc_fr: Crée ~/my_project avec venv et affiche les versions.
#@ root: no
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
[ -d "${HOME}/my_project" ] || python3 -m venv "${HOME}/my_project"
"${HOME}/my_project/bin/python3" --version
"${HOME}/my_project/bin/pip3" --version
