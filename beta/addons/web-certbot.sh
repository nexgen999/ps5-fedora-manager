#!/usr/bin/env bash
#@ id: web-certbot
#@ version: 1.0.0
#@ section: websrv
#@ icon: security-high-symbolic
#@ title: Certbot (HTTPS)
#@ title_fr: Certbot (HTTPS)
#@ desc: Let's Encrypt certificates for Apache and nginx.
#@ desc_fr: Certificats Let's Encrypt pour Apache et nginx.
#@ packages: certbot python3-certbot-apache python3-certbot-nginx
#@ root: yes
set -euo pipefail

PKGS=(certbot python3-certbot-apache python3-certbot-nginx)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de web-certbot…"
dnf install -y --skip-unavailable "${PKGS[@]}"
