#!/usr/bin/env bash
#@ id: dev-python-gtk
#@ version: 1.0.0
#@ section: dev
#@ icon: text-x-python-symbolic
#@ title: Python + GTK4 / Libadwaita
#@ title_fr: Python + GTK4 / Libadwaita
#@ desc: Headers, introspection, gtk4/libadwaita dev packages and Blueprint.
#@ desc_fr: En-têtes, introspection, paquets de développement gtk4/libadwaita et Blueprint.
#@ packages: python3-devel python3-pip python3-virtualenv python3-pytest gobject-introspection-devel gtk4-devel libadwaita-devel libsecret-devel blueprint-compiler desktop-file-utils appstream gtk4-devel-tools devhelp
#@ root: yes
set -euo pipefail

PKGS=(python3-devel python3-pip python3-virtualenv python3-pytest gobject-introspection-devel gtk4-devel libadwaita-devel libsecret-devel blueprint-compiler desktop-file-utils appstream gtk4-devel-tools devhelp)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-python-gtk…"
dnf install -y --skip-unavailable "${PKGS[@]}"
