#!/usr/bin/env bash
#@ id: repos-refresh
#@ version: 1.0.0
#@ section: repos
#@ icon: view-refresh-symbolic
#@ title: Refresh repository metadata
#@ title_fr: Rafraîchir les métadonnées des dépôts
#@ desc: dnf clean expire-cache && dnf makecache.
#@ action: yes
#@ desc_fr: dnf clean expire-cache && dnf makecache.
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
dnf clean expire-cache
dnf makecache
