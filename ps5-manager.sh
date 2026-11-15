#!/bin/bash
# ==============================================================================
# PS5 Fedora Manager - Script Principal (Interface Graphique Zenity)
# ==============================================================================

# Vérification et installation automatique de Zenity si absent
if ! command -v zenity &>/dev/null; then
    sudo dnf install -y zenity
fi

# Définition des chemins et de l'utilisateur réel pour le bus graphique
INSTALL_DIR="/opt/ps5-manager"
MODULES_DIR="$INSTALL_DIR/modules"
REPO_URL="https://github.com/nexgen999/ps5-fedora-manager.git"

REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || echo 'ps5')}"
USER_UID=$(id -u "$REAL_USER" 2>/dev/null || echo "1000")

# Forcer les variables d'environnement graphique et D-Bus
export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="/run/user/$USER_UID"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$USER_UID/bus}"

# Fonction de mise à jour forcée (écrase proprement l'ancien sans conflit Git)
update_manager() {
    if [ -d "$INSTALL_DIR/.git" ]; then
        cd "$INSTALL_DIR"
        sudo git fetch --all
        sudo git reset --hard origin/main
        sudo chmod +x "$INSTALL_DIR"/*.sh "$MODULES_DIR"/*.sh 2>/dev/null || true
        sudo cp -f "$INSTALL_DIR/ps5-manager.desktop" /usr/share/applications/ps5-manager.desktop 2>/dev/null || true
        sudo update-desktop-database /usr/share/applications/ 2>/dev/null || true
        zenity --info --title="Mise à jour" --text="Le gestionnaire a été mis à jour avec succès !" --width=350
    else
        sudo mkdir -p "$INSTALL_DIR"
        sudo git clone "$REPO_URL" "$INSTALL_DIR"
        sudo chmod +x "$INSTALL_DIR"/*.sh "$MODULES_DIR"/*.sh 2>/dev/null || true
        zenity --info --title="Installation" --text="Dépôt cloné avec succès !" --width=350
    fi
}

# Infos système pour l'en-tête
OS_VER=$(grep -E '^PRETTY_NAME=' /etc/os-release | cut -d'"' -f2 | sed 's/ (.*//')
K_VER=$(uname -r | cut -d'-' -f1)

# Boucle principale du Menu Graphique (Zenity)
while true; do
    CHOICE=$(zenity --list \
        --title="PS5 Linux Universal Manager (nexgen999)" \
        --text="<span size='x-large' weight='bold'>PS5 Linux Universal Manager (nexgen999)</span>\n\nSystème : $OS_VER | Noyau : $K_VER\nChoisissez une action :" \
        --width=820 \
        --height=520 \
        --column="Option" --column="Action" --column="Description" \
        "1"  "Mise à jour Manager"   "Vérifier les mises à jour GitHub ou désinstaller le manager" \
        "2"  "Langue & Clavier"      "Configurer la langue du système, le clavier et la session" \
        "3"  "Gestion des Dépôts"    "Gérer RPM Fusion, Flatpak (Flathub) et dépôts personnalisés" \
        "4"  "Utilisateurs & Root"   "Ajouter, éditer ou supprimer des comptes et mots de passe" \
        "5"  "Mises à jour Fedora"   "Mettre à jour le système DNF, Flatpak et les langpacks" \
        "6"  "Maintenance & Clean"   "Nettoyer les caches DNF, journaux système et fichiers temp" \
        "7"  "Alimentation (Veille)" "Activer ou désactiver la mise en veille écran et système" \
        "8"  "PS5 Fan Manager"       "Contrôler la ventilation, le mode Boost et ps5_control" \
        "9"  "PS5 Hardware Control"  "Installer ou gérer l'interface graphique matériel (GUI)" \
        "10" "Mesa / Vulkan & RADV"  "Mettre à jour les pilotes graphiques AMD et vérifier RADV" \
        "11" "Noyau PS5 (Kernel)"    "Télécharger et sélectionner le kernel Linux PS5 par défaut" \
        "12" "Logithèque PS5"        "Installer/gérer Steam, Heroic, ProtonUp-Qt, Decky, Brave..." \
        "13" "Software Presets"      "Déployer un pack complet : Gaming, Bureautique ou Dev")

    [ $? -ne 0 ] || [ -z "$CHOICE" ] && exit 0

    # Transmission propre et sécurisée de l'environnement graphique aux sous-modules
    RUN_MOD="sudo -u $REAL_USER env DISPLAY=$DISPLAY XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS bash"

    case $CHOICE in
        1)
            SUB=$(zenity --list --title="Gestion du Manager" --text="Choisissez une action :" --width=450 --height=250 \
                --column="ID" --column="Action" \
                "1" "Forcer la mise à jour depuis GitHub" \
                "2" "Désinstaller complètement le Manager")
            [ "$SUB" = "1" ] && update_manager
            if [ "$SUB" = "2" ]; then
                sudo rm -rf "$INSTALL_DIR" /usr/local/bin/ps5-manager /usr/share/applications/ps5-manager.desktop /usr/share/pixmaps/ps5-manager.png
                zenity --info --text="PS5 Fedora Manager a été désinstallé." --width=300
                exit 0
            fi
            ;;
        2) $RUN_MOD "$MODULES_DIR/02-langues.sh" ;;
        3) $RUN_MOD "$MODULES_DIR/03-depots.sh" ;;
        4) $RUN_MOD "$MODULES_DIR/04-utilisateurs.sh" ;;
        5) $RUN_MOD "$MODULES_DIR/05-maj-systeme.sh" ;;
        6) $RUN_MOD "$MODULES_DIR/06-maintenance.sh" ;;
        7) $RUN_MOD "$MODULES_DIR/07-alimentation.sh" ;;
        8) $RUN_MOD "$MODULES_DIR/08-fan-manager.sh" ;;
        9) $RUN_MOD "$MODULES_DIR/09-hw-control.sh" ;;
        10) $RUN_MOD "$MODULES_DIR/10-mesa-vulkan.sh" ;;
        11) $RUN_MOD "$MODULES_DIR/11-kernel.sh" ;;
        12) $RUN_MOD "$MODULES_DIR/12-logiciels.sh" ;;
        13) $RUN_MOD "$MODULES_DIR/13-presets.sh" ;;
    esac
done
