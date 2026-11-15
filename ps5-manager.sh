#!/bin/bash
# ==============================================================================
# PS5 Fedora Manager - Script Principal (Interface Graphique Zenity)
# ==============================================================================

# Vérification des dépendances graphiques
if ! command -v zenity &>/dev/null; then
    dnf install -y zenity
fi

# Définition des chemins
INSTALL_DIR="/opt/ps5-manager"
MODULES_DIR="$INSTALL_DIR/modules"
REPO_URL="https://github.com/nexgen999/ps5-fedora-manager.git"

# Fonction de mise à jour automatique
update_manager() {
    if [ -d "$INSTALL_DIR/.git" ]; then
        cd "$INSTALL_DIR" && git pull origin main
        chmod +x "$INSTALL_DIR"/*.sh "$MODULES_DIR"/*.sh 2>/dev/null || true
        cp -f "$INSTALL_DIR/ps5-manager.desktop" /usr/share/applications/ps5-manager.desktop 2>/dev/null || true
        update-desktop-database /usr/share/applications/ 2>/dev/null || true
        zenity --info --title="Mise à jour" --text="Le gestionnaire et les modules ont été mis à jour avec succès !" --width=350
    else
        mkdir -p "$INSTALL_DIR"
        git clone "$REPO_URL" "$INSTALL_DIR"
        zenity --info --title="Installation" --text="Dépôt cloné avec succès dans $INSTALL_DIR !" --width=350
    fi
}

# Infos système pour l'en-tête
OS_VER=$(grep -E '^PRETTY_NAME=' /etc/os-release | cut -d'"' -f2 | sed 's/ (.*//')
K_VER=$(uname -r | cut -d'-' -f1)

# Boucle principale du Menu Graphique (Style Tableau Zenity)
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

    # Si l'utilisateur clique sur Cancel ou ferme la fenêtre
    if [ $? -ne 0 ] || [ -z "$CHOICE" ]; then
        exit 0
    fi

    # Exécution de l'action choisie (dans un terminal propre si le sous-module utilise whiptail)
    case $CHOICE in
        1)
            SUB=$(zenity --list --title="Gestion du Manager" --text="Choisissez une action :" --width=450 --height=250 \
                --column="ID" --column="Action" \
                "1" "Vérifier et mettre à jour depuis GitHub" \
                "2" "Désinstaller complètement le Manager")
            [ "$SUB" = "1" ] && update_manager
            if [ "$SUB" = "2" ]; then
                rm -rf "$INSTALL_DIR" /usr/local/bin/ps5-manager /usr/share/applications/ps5-manager.desktop /usr/share/pixmaps/ps5-manager.png
                zenity --info --text="PS5 Fedora Manager a été désinstallé." --width=300
                exit 0
            fi
            ;;
        2) gnome-terminal --title="Configuration des Langues" -- bash "$MODULES_DIR/02-langues.sh" ;;
        3) gnome-terminal --title="Gestion des Dépôts" -- bash "$MODULES_DIR/03-depots.sh" ;;
        4) gnome-terminal --title="Gestion des Utilisateurs" -- bash "$MODULES_DIR/04-utilisateurs.sh" ;;
        5) gnome-terminal --title="Mises à jour Fedora" -- bash "$MODULES_DIR/05-maj-systeme.sh" ;;
        6) gnome-terminal --title="Maintenance Système" -- bash "$MODULES_DIR/06-maintenance.sh" ;;
        7) gnome-terminal --title="Alimentation PS5" -- bash "$MODULES_DIR/07-alimentation.sh" ;;
        8) gnome-terminal --title="PS5 Fan Manager" -- bash "$MODULES_DIR/08-fan-manager.sh" ;;
        9) gnome-terminal --title="PS5 Hardware Control" -- bash "$MODULES_DIR/09-hw-control.sh" ;;
        10) gnome-terminal --title="Mesa & Vulkan" -- bash "$MODULES_DIR/10-mesa-vulkan.sh" ;;
        11) gnome-terminal --title="Kernel PS5" -- bash "$MODULES_DIR/11-kernel.sh" ;;
        12) gnome-terminal --title="Logithèque PS5" -- bash "$MODULES_DIR/12-logiciels.sh" ;;
        13) gnome-terminal --title="Software Presets" -- bash "$MODULES_DIR/13-presets.sh" ;;
    esac
done
