#!/usr/bin/env bash
#@ id: dev-diagnostic
#@ version: 1.0.0
#@ section: dev
#@ icon: utilities-system-monitor-symbolic
#@ title: System diagnostics
#@ title_fr: Diagnostic système
#@ desc: lsof, strace, sysstat, perf, ncdu, duf and hyperfine.
#@ desc_fr: lsof, strace, sysstat, perf, ncdu, duf et hyperfine.
#@ packages: lsof strace ltrace sysstat perf ncdu duf hyperfine
#@ root: yes
set -euo pipefail

PKGS=(lsof strace ltrace sysstat perf ncdu duf hyperfine)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-diagnostic…"
dnf install -y --skip-unavailable "${PKGS[@]}"
