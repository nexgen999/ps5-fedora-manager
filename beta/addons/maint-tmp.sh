#!/usr/bin/env bash
#@ id: maint-tmp
#@ version: 1.0.0
#@ section: maint
#@ icon: folder-temp-symbolic
#@ title: Clean temporary files
#@ title_fr: Nettoyer les fichiers temporaires
#@ desc: Runs systemd-tmpfiles --clean (files older than 10 days).
#@ action: yes
#@ desc_fr: Lance systemd-tmpfiles --clean (fichiers de plus de 10 jours).
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
systemd-tmpfiles --clean
