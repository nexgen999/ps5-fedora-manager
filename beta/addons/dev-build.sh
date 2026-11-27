#!/usr/bin/env bash
#@ id: dev-build
#@ version: 1.0.0
#@ section: dev
#@ icon: applications-engineering-symbolic
#@ title: Build essentials
#@ title_fr: Socle de compilation
#@ desc: gcc, cmake, meson, ninja, autotools, rpmdevtools and rpmlint.
#@ desc_fr: gcc, cmake, meson, ninja, autotools, rpmdevtools et rpmlint.
#@ packages: gcc gcc-c++ make cmake meson ninja-build pkgconf-pkg-config autoconf automake libtool patch rpmdevtools rpmlint
#@ root: yes
set -euo pipefail

PKGS=(gcc gcc-c++ make cmake meson ninja-build pkgconf-pkg-config autoconf automake libtool patch rpmdevtools rpmlint)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-build…"
dnf install -y --skip-unavailable "${PKGS[@]}"
