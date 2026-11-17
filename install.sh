#!/bin/bash
set -euo pipefail

# Dépendances complètes pour l'interface GTK4 / Libadwaita / PyGObject sur Fedora 45
sudo dnf install -y \
    python3 python3-gobject gtk4 libadwaita gobject-introspection \
    polkit glib2 curl git desktop-file-utils util-linux
sudo dnf install -y xhost || true

INSTALL_DIR="/opt/ps5-manager"
POLKIT_POLICY="/usr/share/polkit-1/actions/io.github.nexgen999.ps5-manager.policy"

sudo mkdir -p "$INSTALL_DIR" /etc/ps5-manager /var/log/ps5-manager
sudo chown root:root "$INSTALL_DIR" /etc/ps5-manager /var/log/ps5-manager
sudo chmod 0755 "$INSTALL_DIR" /etc/ps5-manager /var/log/ps5-manager

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    sudo install -o root -g root -m 0755 "$SCRIPT_DIR/ps5_manager.py" "$INSTALL_DIR/ps5_manager.py"
    [ -f "$SCRIPT_DIR/ps5-manager.desktop" ] && sudo install -o root -g root -m 0644 "$SCRIPT_DIR/ps5-manager.desktop" "$INSTALL_DIR/ps5-manager.desktop"
    [ -f "$SCRIPT_DIR/icon.png" ] && sudo install -o root -g root -m 0644 "$SCRIPT_DIR/icon.png" "$INSTALL_DIR/icon.png"
    [ -f "$SCRIPT_DIR/install.sh" ] && sudo install -o root -g root -m 0755 "$SCRIPT_DIR/install.sh" "$INSTALL_DIR/install.sh"
else
    sudo chown root:root "$INSTALL_DIR/ps5_manager.py"
    sudo chmod 0755 "$INSTALL_DIR/ps5_manager.py"
fi

sudo install -o root -g root -m 0755 "$INSTALL_DIR/ps5_manager.py" /usr/local/bin/ps5-manager

# Purge les restes de l'ancienne installation (interface bash/zenity et GUI PyGObject)
sudo rm -f /usr/local/bin/ps5-manager-gui /usr/local/bin/ps5-manager-gui.py \
    "$INSTALL_DIR/ps5-manager.sh" "$INSTALL_DIR/ps5-manager.sh.next" \
    "$INSTALL_DIR/ps5-manager-gui.py"

if [ -f "$SCRIPT_DIR/ps5-manager.desktop" ]; then
    sudo install -o root -g root -m 0644 "$SCRIPT_DIR/ps5-manager.desktop" /usr/share/applications/ps5-manager.desktop
    sudo update-desktop-database /usr/share/applications/ >/dev/null 2>&1 || true
fi

if [ -f "$SCRIPT_DIR/icon.png" ]; then
    sudo install -o root -g root -m 0644 "$SCRIPT_DIR/icon.png" /usr/share/pixmaps/ps5-manager.png
fi

# Règle Polkit permettant à pkexec de préserver l'affichage graphique (allow_gui=true)
sudo tee "$POLKIT_POLICY" >/dev/null <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
<policyconfig>
  <action id="io.github.nexgen999.ps5-manager.pkexec">
    <description>Run PS5 Fedora Manager as root</description>
    <description xml:lang="fr">Exécuter PS5 Fedora Manager en tant que root</description>
    <message>Authentication is required to run PS5 Fedora Manager</message>
    <message xml:lang="fr">Une authentification est requise pour exécuter PS5 Fedora Manager</message>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin_keep</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">/usr/local/bin/ps5-manager</annotate>
    <annotate key="org.freedesktop.policykit.exec.allow_gui">true</annotate>
  </action>
</policyconfig>
EOF
sudo chown root:root "$POLKIT_POLICY"
sudo chmod 0644 "$POLKIT_POLICY"

# Contextes SELinux sur Fedora 45
if command -v restorecon >/dev/null 2>&1; then
    sudo restorecon -RF \
        "$INSTALL_DIR" \
        /usr/local/bin/ps5-manager \
        /usr/share/applications/ps5-manager.desktop \
        "$POLKIT_POLICY" \
        /etc/ps5-manager \
        /var/log/ps5-manager >/dev/null 2>&1 || true
fi

VERSION="$(sed -n 's/^APP_VERSION = "\(.*\)"/\1/p' "$INSTALL_DIR/ps5_manager.py" | head -1)"
echo "PS5 Fedora Manager ${VERSION:-?} (GTK4 / Libadwaita) installé avec les droits et dépendances. Lancez : ps5-manager"
echo "Fichier installé : $(readlink -f /usr/local/bin/ps5-manager)"
