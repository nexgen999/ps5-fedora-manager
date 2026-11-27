#!/usr/bin/env bash
#@ id: update-uninstall
#@ version: 1.0.0
#@ section: update
#@ icon: user-trash-symbolic
#@ title: Uninstall the manager
#@ title_fr: Désinstaller le manager
#@ desc: Removes /opt/ps5-manager and its launcher (stable install).
#@ action: yes
#@ desc_fr: Supprime /opt/ps5-manager et son lanceur (installation stable).
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
rm -rf /opt/ps5-manager
rm -f /usr/local/bin/ps5-manager /usr/share/applications/ps5-manager.desktop
echo "→ Manager désinstallé (le dépôt cloné n'est pas supprimé)."
