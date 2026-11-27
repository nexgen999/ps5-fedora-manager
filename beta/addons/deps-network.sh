#!/usr/bin/env bash
#@ id: deps-network
#@ version: 1.0.0
#@ section: deps
#@ icon: network-transmit-receive-symbolic
#@ title: Network tools
#@ title_fr: Outils réseau
#@ desc: curl, wget, rsync and ssh client.
#@ desc_fr: curl, wget, rsync et client ssh.
#@ packages: curl wget rsync openssh-clients
#@ root: yes
set -euo pipefail

PKGS=(curl wget rsync openssh-clients)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de deps-network…"
dnf install -y --skip-unavailable "${PKGS[@]}"
