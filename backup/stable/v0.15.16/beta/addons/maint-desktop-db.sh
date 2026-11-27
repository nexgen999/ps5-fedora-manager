#!/usr/bin/env bash
#@ id: maint-desktop-db
#@ version: 1.0.0
#@ section: maint
#@ icon: applications-other-symbolic
#@ title: Rebuild desktop database
#@ title_fr: Reconstruire la base des applications
#@ desc: update-desktop-database for system and user menus.
#@ action: yes
#@ desc_fr: update-desktop-database pour les menus système et utilisateur.
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
update-desktop-database /usr/share/applications 2>/dev/null || true
update-desktop-database "${HOME}/.local/share/applications" 2>/dev/null || true
echo "→ Base des applications reconstruite."
