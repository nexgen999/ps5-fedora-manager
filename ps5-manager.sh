#!/bin/bash
# ==============================================================================
# PS5 Fedora Manager - Script Principal (TUI)
# Auteur : nexgen999
# Description : Tableau de bord modulaire pour PS5 Linux
# ==============================================================================

# Sécurité : Exécution en root obligatoire pour la gestion système
if [ "$EUID" -ne 0 ]; then
  if command -v whiptail &>/dev/null; then
    whiptail --title "Erreur de privilèges" --msgbox "Ce gestionnaire doit être exécuté en tant que root (sudo ps5-manager)." 10 50
  else
    echo "Erreur : Ce gestionnaire doit être exécuté en tant que root."
  fi
  exit 1
fi

# Définition des chemins
INSTALL_DIR="/opt/ps5-manager"
MODULES_DIR="$INSTALL_DIR/modules"
REPO_URL="https://github.com/nexgen999/ps5-fedora-manager.git"

# Fonction de mise à jour automatique du manager et des modules
update_manager() {
    if ! command -v git &>/dev/null; then
        apt-get install -y git || dnf install -y git
    fi

    if [ -d "$INSTALL_DIR/.git" ]; then
        cd "$INSTALL_DIR" && git pull origin main
        whiptail --title "Mise à jour" --msgbox "Le gestionnaire et les modules ont été mis à jour avec succès !" 10 50
    else
        mkdir -p "$INSTALL_DIR"
        git clone "$REPO_URL" "$INSTALL_DIR"
        whiptail --title "Installation" --msgbox "Dépôt cloné avec succès dans $INSTALL_DIR !" 10 50
    fi
}

# Vérification initiale si le dossier des modules existe
if [ ! -d "$MODULES_DIR" ]; then
    update_manager
fi

# Boucle principale du Menu TUI
while true; do
    CHOICE=$(whiptail --title "PS5 Fedora Manager (v1.0)" \
    --menu "Sélectionnez une catégorie ou une action :" 22 76 13 \
    "1"  "Mises à jour & Désinstallation du Manager" \
    "2"  "Configuration des langues (Clavier + Système)" \
    "3"  "Gestion des dépôts (RPM Fusion, Flatpak...)" \
    "4"  "Gestion des utilisateurs & compte Root" \
    "5"  "Mises à jour globales Fedora (Système & Apps)" \
    "6"  "Maintenance & Nettoyage des caches" \
    "7"  "Management de l'alimentation (Veille)" \
    "8"  "PS5 Fan Manager (Ventilation & Boost)" \
    "9"  "PS5 Hardware Control (GUI & Sysfs)" \
    "10" "Mise à jour Mesa / Vulkan & RADV" \
    "11" "Mise à jour du Kernel PS5" \
    "12" "Logiciels recommandés (Steam, Heroic, Decky...)" \
    "13" "Installation de Software Presets (Gaming, Dev...)" \
    "0"  "Quitter" 3>&1 1>&2 2>&3)

    EXIT_STATUS=$?
    if [ $EXIT_STATUS != 0 ]; then
        clear
        exit 0
    fi

    case $CHOICE in
        1)
            # Option 1 : Géré en interne ou via un sous-module
            SUB=$(whiptail --title "Gestion du Manager" --menu "Choisissez une action :" 12 50 2 \
            "1" "Vérifier et mettre à jour le Manager" \
            "2" "Désinstaller le Manager de la machine" 3>&1 1>&2 2>&3)
            [ "$SUB" = "1" ] && update_manager
            [ "$SUB" = "2" ] && { rm -rf "$INSTALL_DIR" /usr/local/bin/ps5-manager; whiptail --msgbox "Manager désinstallé." 8 40; exit 0; }
            ;;
        2) [ -f "$MODULES_DIR/02-langues.sh" ] && bash "$MODULES_DIR/02-langues.sh" || whiptail --msgbox "Module introuvable !" 8 40 ;;
        3) [ -f "$MODULES_DIR/03-depots.sh" ] && bash "$MODULES_DIR/03-depots.sh" || whiptail --msgbox "Module introuvable !" 8 40 ;;
        4) [ -f "$MODULES_DIR/04-utilisateurs.sh" ] && bash "$MODULES_DIR/04-utilisateurs.sh" || whiptail --msgbox "Module introuvable !" 8 40 ;;
        5) [ -f "$MODULES_DIR/05-maj-systeme.sh" ] && bash "$MODULES_DIR/05-maj-systeme.sh" || whiptail --msgbox "Module introuvable !" 8 40 ;;
        6) [ -f "$MODULES_DIR/06-maintenance.sh" ] && bash "$MODULES_DIR/06-maintenance.sh" || whiptail --msgbox "Module introuvable !" 8 40 ;;
        7) [ -f "$MODULES_DIR/07-alimentation.sh" ] && bash "$MODULES_DIR/07-alimentation.sh" || whiptail --msgbox "Module introuvable !" 8 40 ;;
        8) [ -f "$MODULES_DIR/08-fan-manager.sh" ] && bash "$MODULES_DIR/08-fan-manager.sh" || whiptail --msgbox "Module introuvable !" 8 40 ;;
        9) [ -f "$MODULES_DIR/09-hw-control.sh" ] && bash "$MODULES_DIR/09-hw-control.sh" || whiptail --msgbox "Module introuvable !" 8 40 ;;
        10) [ -f "$MODULES_DIR/10-mesa-vulkan.sh" ] && bash "$MODULES_DIR/10-mesa-vulkan.sh" || whiptail --msgbox "Module introuvable !" 8 40 ;;
        11) [ -f "$MODULES_DIR/11-kernel.sh" ] && bash "$MODULES_DIR/11-kernel.sh" || whiptail --msgbox "Module introuvable !" 8 40 ;;
        12) [ -f "$MODULES_DIR/12-logiciels.sh" ] && bash "$MODULES_DIR/12-logiciels.sh" || whiptail --msgbox "Module introuvable !" 8 40 ;;
        13) [ -f "$MODULES_DIR/13-presets.sh" ] && bash "$MODULES_DIR/13-presets.sh" || whiptail --msgbox "Module introuvable !" 8 40 ;;
        0)
            clear
            exit 0
            ;;
    esac
done
