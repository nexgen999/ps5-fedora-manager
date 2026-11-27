#!/usr/bin/env bash
#@ id: dev-rust
#@ version: 1.0.0
#@ section: dev
#@ icon: text-x-script-symbolic
#@ title: Rust / Cargo
#@ title_fr: Rust / Cargo
#@ desc: Compiler, package manager, formatter and linter.
#@ desc_fr: Compilateur, gestionnaire de paquets, formateur et linter.
#@ packages: rust cargo rustfmt clippy
#@ root: yes
set -euo pipefail

PKGS=(rust cargo rustfmt clippy)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-rust…"
dnf install -y --skip-unavailable "${PKGS[@]}"
