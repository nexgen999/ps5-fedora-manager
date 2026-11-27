#!/usr/bin/env bash
#@ id: deps-node-uninstall
#@ version: 1.0.0
#@ section: deps
#@ icon: user-trash-symbolic
#@ title: Uninstall Node.js
#@ title_fr: Désinstaller Node.js
#@ desc: Removes nodejs and npm.
#@ action: yes
#@ desc_fr: Supprime nodejs et npm.
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
dnf remove -y nodejs npm
