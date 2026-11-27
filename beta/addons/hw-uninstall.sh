#!/usr/bin/env bash
#@ id: hw-uninstall
#@ version: 1.0.0
#@ section: hardware
#@ icon: user-trash-symbolic
#@ title: Uninstall Hardware Control
#@ title_fr: Désinstaller Hardware Control
#@ desc: Removes the GUI and its systemd units (keeps Python).
#@ action: yes
#@ desc_fr: Supprime l'interface et ses unités systemd (conserve Python).
#@ root: yes
set -euo pipefail

if [ "${1:-}" = "--check" ]; then exit 1; fi
systemctl disable --now ps5hwcon.service 2>/dev/null || true
rm -rf /opt/ps5-hwcon-gui
rm -f /etc/systemd/system/ps5hwcon.service /usr/share/applications/ps5-hwcon.desktop
systemctl daemon-reload
echo "→ Interface Hardware Control supprimée."
