#!/usr/bin/env bash
#@ id: web-openssh
#@ version: 1.0.0
#@ section: websrv
#@ icon: network-server-symbolic
#@ title: OpenSSH server
#@ title_fr: Serveur OpenSSH
#@ desc: Remote shell, started and enabled after install.
#@ action: yes
#@ packages: openssh-server
#@ desc_fr: Shell distant, démarré et activé après l'installation.
#@ root: yes
set -euo pipefail

PKGS=(openssh-server)
if [ "${1:-}" = "--check" ]; then
    rpm -q openssh-server >/dev/null 2>&1 && systemctl is-enabled sshd >/dev/null 2>&1
    exit $?
fi
dnf install -y --skip-unavailable "${PKGS[@]}"
systemctl enable --now sshd
