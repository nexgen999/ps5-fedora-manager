#!/usr/bin/env bash
#@ id: web-nginx
#@ version: 1.0.0
#@ section: websrv
#@ icon: network-server-symbolic
#@ title: nginx
#@ title_fr: nginx
#@ desc: Lightweight web server and reverse proxy.
#@ desc_fr: Serveur web léger et reverse proxy.
#@ packages: nginx
#@ root: yes
set -euo pipefail

PKGS=(nginx)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de web-nginx…"
dnf install -y --skip-unavailable "${PKGS[@]}"
