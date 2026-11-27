#!/usr/bin/env bash
#@ id: dev-debug
#@ version: 1.0.0
#@ section: dev
#@ icon: applications-engineering-symbolic
#@ title: Debug & profiling
#@ title_fr: Debug et profilage
#@ desc: gdb, lldb, valgrind, heaptrack and sysprof.
#@ desc_fr: gdb, lldb, valgrind, heaptrack et sysprof.
#@ packages: gdb lldb valgrind heaptrack sysprof
#@ root: yes
set -euo pipefail

PKGS=(gdb lldb valgrind heaptrack sysprof)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-debug…"
dnf install -y --skip-unavailable "${PKGS[@]}"
