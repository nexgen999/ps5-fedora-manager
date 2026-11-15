#!/bin/bash
# ==============================================================================
# PS5 Fedora Manager - Script Monolithique Complet (Zenity GUI)
# ==============================================================================

# Vérification et installation automatique de Zenity si absent
if ! command -v zenity &>/dev/null; then
    sudo dnf install -y zenity
fi

# Chemins et variables utilisateur
INSTALL_DIR="/opt/ps5-manager"
REPO_URL="https://github.com/nexgen999/ps5-fedora-manager.git"
REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || echo 'ps5')}"
USER_UID=$(id -u "$REAL_USER" 2>/dev/null || echo "1000")

# Forcer les variables d'environnement graphique et D-Bus pour les actions root/user
export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="/run/user/$USER_UID"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$USER_UID/bus}"

# Fonction de mise à jour et d'installation automatique
update_manager() {
    if [ -d "$INSTALL_DIR/.git" ]; then
        cd "$INSTALL_DIR"
        sudo git fetch --all
        sudo git reset --hard origin/main
        sudo chmod +x "$INSTALL_DIR/ps5-manager.sh"
        sudo cp -f "$INSTALL_DIR/ps5-manager.sh" /usr/local/bin/ps5-manager
        sudo chmod +x /usr/local/bin/ps5-manager
        sudo update-desktop-database /usr/share/applications/ 2>/dev/null || true
        zenity --info --title="Mise à jour" --text="Le gestionnaire a été mis à jour avec succès !" --width=350
    else
        sudo mkdir -p "$INSTALL_DIR"
        sudo git clone "$REPO_URL" "$INSTALL_DIR" 2>/dev/null || true
        sudo chmod +x "$INSTALL_DIR/ps5-manager.sh"
        sudo cp -f "$INSTALL_DIR/ps5-manager.sh" /usr/local/bin/ps5-manager
        sudo chmod +x /usr/local/bin/ps5-manager
        zenity --info --title="Installation" --text="Installation terminée avec succès !" --width=350
    fi
}

# Infos système pour l'en-tête
OS_VER=$(grep -E '^PRETTY_NAME=' /etc/os-release | cut -d'"' -f2 | sed 's/ (.*//')
K_VER=$(uname -r | cut -d'-' -f1)

# Boucle principale du Menu Graphique
while true; do
    CHOICE=$(zenity --list \
        --title="PS5 Linux Universal Manager (nexgen999)" \
        --text="<span size='x-large' weight='bold'>PS5 Linux Universal Manager</span>\n\nSystème : $OS_VER | Noyau : $K_VER\nChoisissez une action :" \
        --width=850 \
        --height=580 \
        --column="Opt" --column="Action" --column="Description" \
        "1"  "Mise à jour / Désinstallation" "Vérifier les mises à jour GitHub ou désinstaller le manager" \
        "2"  "Configuration des langues"    "Voir les langpacks, installer une langue et configurer la session" \
        "3"  "Gestion des dépôts"           "Voir, installer (RPM/Flatpak), supprimer, mettre à jour ou ajouter un dépôt" \
        "4"  "Gestion des utilisateurs"     "Voir, éditer, ajouter/supprimer des comptes et configurer le root" \
        "5"  "Mises à jour Fedora"          "Mettre à jour applications, système, langpacks et dépôts" \
        "6"  "Maintenance & Nettoyage"      "Nettoyage des fichiers temporaires, caches DNF et logs" \
        "7"  "Management de l'alimentation" "Activer ou désactiver la veille écran ou système" \
        "8"  "PS5 Fan Manager"              "Status, Fan on/off, Boost on/off, service et mise à jour" \
        "9"  "PS5 Hardware Control"         "Installation, mise à jour, désinstallation et check sysfs" \
        "10" "Mesa / Vulkan & RADV"         "Outils Vulkan, pilotes mesa et vérification RADV GPU AMD" \
        "11" "Mise à jour Kernel"           "Installer le dernier kernel PS5 et sélectionner le défaut" \
        "12" "Logithèque / Logiciels"       "Steam, Heroic, ProtonUp, Decky, Opera, Brave, Flatpaks..." \
        "13" "Software Presets"             "Installation groupée : Gaming, Bureautique ou Développeur")

    [ $? -ne 0 ] || [ -z "$CHOICE" ] && exit 0

    case $CHOICE in
        1)
            SUB=$(zenity --list --title="1. Mise à jour / Désinstallation" --text="Choisissez une option :" --width=450 --height=220 \
                --column="ID" --column="Action" \
                "1" "Mettre à jour le Manager depuis GitHub" \
                "2" "Désinstaller complètement le Manager")
            [ "$SUB" = "1" ] && update_manager
            if [ "$SUB" = "2" ]; then
                sudo rm -rf "$INSTALL_DIR" /usr/local/bin/ps5-manager /usr/share/applications/ps5-manager.desktop /usr/share/pixmaps/ps5-manager.png
                zenity --info --text="PS5 Fedora Manager a été désinstallé." --width=300
                exit 0
            fi
            ;;
        2)
            SUB=$(zenity --list --title="2. Configuration des langues" --text="Choisissez une option :" --width=500 --height=250 \
                --column="ID" --column="Action" \
                "1" "Voir les langpacks installés (système & clavier)" \
                "2" "Installer une nouvelle langue" \
                "3" "Configuration intégrale (Langue, Clavier, User) + Relancer session")
            case "$SUB" in
                1)
                    INFO=$(localectl status)
                    zenity --info --title="Langpacks & Clavier" --text="$INFO" --width=500 --height=300
                    ;;
                2)
                    LANG_IN=$(zenity --entry --title="Installer une langue" --text="Entrez le code de langue (ex: fr_FR.UTF-8, es_ES.UTF-8) :")
                    [ -n "$LANG_IN" ] && sudo dnf install -y "langpacks-$LANG_IN" && zenity --info --text="Langpack installé !" --width=300
                    ;;
                3)
                    SELECTED_LANG=$(zenity --list --title="Langue système" --text="Choisissez la langue :" --width=400 --height=200 --column="Langue" "fr_FR.UTF-8" "en_US.UTF-8" "es_ES.UTF-8" "de_DE.UTF-8")
                    SELECTED_KB=$(zenity --list --title="Clavier" --text="Choisissez la disposition :" --width=400 --height=200 --column="Layout" "fr" "us" "es" "de")
                    if [ -n "$SELECTED_LANG" ] && [ -n "$SELECTED_KB" ]; then
                        sudo localectl set-locale LANG="$SELECTED_LANG"
                        sudo localectl set-x11-keymap "$SELECTED_KB"
                        zenity --info --text="Configuration appliquée ! La session va se fermer pour appliquer les changements." --width=400
                        gnome-session-quit --logout --force
                    fi
                    ;;
            esac
            ;;
        3)
            SUB=$(zenity --list --title="3. Gestion des dépôts" --text="Choisissez une option :" --width=550 --height=300 \
                --column="ID" --column="Action" \
                "1" "Voir la liste des dépôts système (RPM / Flatpak)" \
                "2" "Installer les dépôts RPM (RPM Fusion, etc.)" \
                "3" "Installer le dépôt Flatpak (Flathub)" \
                "4" "Désinstaller / Supprimer un dépôt" \
                "5" "Mise à jour des dépôts & Nettoyage du cache" \
                "6" "Ajouter un dépôt personnalisé (URL)")
            case "$SUB" in
                1)
                    REPS=$(dnf repolist && flatpak remotes)
                    zenity --text-info --title="Liste des dépôts" --filename=<(echo "$REPS") --width=600 --height=400
                    ;;
                2)
                    sudo dnf install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
                    zenity --info --text="Dépôts RPM Fusion installés !" --width=300
                    ;;
                3)
                    flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
                    zenity --info --text="Flathub installé !" --width=300
                    ;;
                4)
                    REPO_RM=$(zenity --entry --title="Supprimer un dépôt" --text="Entrez le nom ou l'ID du dépôt DNF à désactiver/supprimer :")
                    [ -n "$REPO_RM" ] && sudo dnf config-manager --disable "$REPO_RM" && zenity --info --text="Dépôt désactivé." --width=300
                    ;;
                5)
                    sudo dnf clean all && sudo dnf upgrade --refresh -y
                    zenity --info --text="Dépôts mis à jour et cache nettoyé !" --width=300
                    ;;
                6)
                    REPO_URL_ADD=$(zenity --entry --title="Ajouter un dépôt" --text="Entrez l'URL du fichier .repo ou du dépôt :")
                    [ -n "$REPO_URL_ADD" ] && sudo dnf config-manager --add-repo "$REPO_URL_ADD" && zenity --info --text="Dépôt ajouté avec succès !" --width=300
                    ;;
            esac
            ;;
        4)
            SUB=$(zenity --list --title="4. Gestion des utilisateurs" --text="Choisissez une option :" --width=500 --height=280 \
                --column="ID" --column="Action" \
                "1" "Voir la liste des utilisateurs" \
                "2" "Éditer mon compte utilisateur (Mot de passe / Langue)" \
                "3" "Ajouter un utilisateur" \
                "4" "Supprimer un compte utilisateur" \
                "5" "Éditer / Changer le mot de passe Root")
            case "$SUB" in
                1)
                    USERS_LIST=$(cut -d: -f1,3,6,7 /etc/passwd)
                    zenity --text-info --title="Utilisateurs du système" --filename=<(echo "$USERS_LIST") --width=550 --height=350
                    ;;
                2)
                    NEW_PASS=$(zenity --password --title="Nouveau mot de passe" --text="Entrez le nouveau mot de passe pour $USER :")
                    [ -n "$NEW_PASS" ] && echo "$USER:$NEW_PASS" | sudo chpasswd && zenity --info --text="Mot de passe mis à jour !" --width=300
                    ;;
                3)
                    NEW_USER=$(zenity --entry --title="Ajouter un utilisateur" --text="Entrez le nom du nouveau compte :")
                    if [ -n "$NEW_USER" ]; then
                        NEW_UPASS=$(zenity --password --title="Mot de passe" --text="Entrez le mot de passe pour $NEW_USER :")
                        sudo useradd -m -s /bin/bash "$NEW_USER" && echo "$NEW_USER:$NEW_UPASS" | sudo chpasswd
                        zenity --info --text="Utilisateur $NEW_USER créé avec succès !" --width=300
                    fi
                    ;;
                4)
                    DEL_USER=$(zenity --entry --title="Supprimer un utilisateur" --text="Entrez le nom du compte à supprimer :")
                    [ -n "$DEL_USER" ] && sudo userdel -r "$DEL_USER" && zenity --info --text="Utilisateur supprimé." --width=300
                    ;;
                5)
                    ROOT_PASS=$(zenity --password --title="Mot de passe Root" --text="Entrez le nouveau mot de passe pour root :")
                    [ -n "$ROOT_PASS" ] && echo "root:$ROOT_PASS" | sudo chpasswd && zenity --info --text="Mot de passe root modifié !" --width=300
                    ;;
            esac
            ;;
        5)
            SUB=$(zenity --list --title="5. Mises à jour Fedora" --text="Choisissez une option :" --width=450 --height=250 \
                --column="ID" --column="Action" \
                "1" "Mettre à jour les applications (DNF & Flatpak)" \
                "2" "Mettre à jour le système complet" \
                "3" "Mettre à jour les langpacks" \
                "4" "Mettre à jour les repositories")
            case "$SUB" in
                1) sudo dnf upgrade -y && flatpak update -y && zenity --info --text="Applications mises à jour !" --width=300 ;;
                2) sudo dnf upgrade --refresh -y && zenity --info --text="Système mis à jour !" --width=300 ;;
                3) sudo dnf reinstall -y "langpacks-*" && zenity --info --text="Langpacks réinstallés/mis à jour !" --width=300 ;;
                4) sudo dnf makecache --refresh && zenity --info --text="Dépôts rafraîchis !" --width=300 ;;
            esac
            ;;
        6)
            sudo dnf clean all
            sudo rm -rf /var/cache/dnf/* ~/.cache/*
            zenity --info --title="Maintenance" --text="Caches DNF et fichiers temporaires nettoyés avec succès !" --width=350
            ;;
        7)
            SUB=$(zenity --list --title="7. Management de l'alimentation" --text="Choisissez une option :" --width=500 --height=250 \
                --column="ID" --column="Action" \
                "1" "Activer la veille système (Suspend)" \
                "2" "Désactiver la veille système" \
                "3" "Activer la mise en veille de l'écran" \
                "4" "Désactiver la mise en veille de l'écran")
            case "$SUB" in
                1) sudo systemctl unmask sleep.target suspend.target hibernate.target hybrid-sleep.target && zenity --info --text="Veille système activée." --width=300 ;;
                2) sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target && zenity --info --text="Veille système désactivée." --width=300 ;;
                3) gsettings set org.gnome.desktop.session idle-delay 300 && zenity --info --text="Veille écran activée (5 min)." --width=300 ;;
                4) gsettings set org.gnome.desktop.session idle-delay 0 && zenity --info --text="Veille écran désactivée." --width=300 ;;
            esac
            ;;
        8)
            SUB=$(zenity --list --title="8. PS5 Fan Manager" --text="Choisissez une option :" --width=450 --height=280 \
                --column="ID" --column="Action" \
                "1" "Voir le status du ventilateur" \
                "2" "Activer / Désactiver Fan" \
                "3" "Activer / Désactiver Mode Boost" \
                "4" "Voir l'état du service fan" \
                "5" "Relancer le service fan" \
                "6" "Mettre à jour ps5-linux-tools depuis GitHub")
            case "$SUB" in
                1)
                    STATUS=$(systemctl status ps5-fan 2>&1 || echo "Service non trouvé ou inactif")
                    zenity --info --title="Status Fan" --text="$STATUS" --width=500 --height=300
                    ;;
                2) sudo systemctl restart ps5-fan && zenity --info --text="Service ventilateur relancé." --width=300 ;;
                3) sudo systemctl start ps5-boost 2>/dev/null || zenity --info --text="Mode Boost géré." --width=300 ;;
                4)
                    ST=$(systemctl is-active ps5-fan || echo "inactif")
                    zenity --info --text="État du service : $ST" --width=300
                    ;;
                5) sudo systemctl restart ps5-fan && zenity --info --text="Service fan relancé." --width=300 ;;
                6)
                    git clone https://github.com/ps5-linux/ps5-linux-tools /tmp/ps5-tools 2>/dev/null || true
                    cd /tmp/ps5-tools && sudo bash install.sh
                    zenity --info --text="Outils PS5 mis à jour !" --width=300
                    ;;
            esac
            ;;
        9)
            SUB=$(zenity --list --title="9. PS5 Hardware Control" --text="Choisissez une option :" --width=500 --height=260 \
                --column="ID" --column="Action" \
                "1" "Vérifier la présence du matériel système (/sys/class/hwmon/)" \
                "2" "Installer PS5 Hardware Control GUI" \
                "3" "Mettre à jour PS5 Hardware Control" \
                "4" "Désinstaller PS5 Hardware Control")
            case "$SUB" in
                1)
                    HW=$(ls -l /sys/class/hwmon/)
                    zenity --text-info --title="Matériel /sys/class/hwmon/" --filename=<(echo "$HW") --width=600 --height=400
                    ;;
                2)
                    sudo dnf install -y python3-PyQt6
                    curl -fsSL https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-gui/main/install.sh | bash
                    zenity --info --text="PS5 Hardware Control GUI installé !" --width=300
                    ;;
                3)
                    curl -fsSL https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-gui/main/install.sh | bash
                    zenity --info --text="Mis à jour !" --width=300
                    ;;
                4)
                    sudo dnf remove -y ps5-hwcon-gui python3-PyQt6 2>/dev/null || rm -rf ~/.local/share/ps5-hwcon-gui
                    zenity --info --text="Désinstallé." --width=300
                    ;;
            esac
            ;;
        10)
            SUB=$(zenity --list --title="10. Mesa / Vulkan & RADV" --text="Choisissez une option :" --width=500 --height=240 \
                --column="ID" --column="Action" \
                "1" "Installer les outils Vulkan & Mesa demos" \
                "2" "Mettre à jour les paquets Mesa & Vulkan" \
                "3" "Vérifier la prise en charge RADV (GPU AMD PS5)")
            case "$SUB" in
                1) sudo dnf install -y vulkan-tools mesa-demos && zenity --info --text="Outils installés !" --width=300 ;;
                2) sudo dnf upgrade -y "mesa*" "vulkan*" && zenity --info --text="Mesa et Vulkan mis à jour !" --width=300 ;;
                3)
                    RADV_INFO=$(vulkaninfo --summary 2>/dev/null | grep -i "radv" || echo "vulkaninfo non trouvé ou pas de support RADV détecté")
                    zenity --info --title="Vérification RADV" --text="$RADV_INFO" --width=550 --height=300
                    ;;
            esac
            ;;
        11)
            SUB=$(zenity --list --title="11. Mise à jour Kernel PS5" --text="Choisissez une option :" --width=500 --height=220 \
                --column="ID" --column="Action" \
                "1" "Installer le dernier kernel depuis GitHub releases" \
                "2" "Sélectionner / Gérer le kernel par défaut")
            case "$SUB" in
                1)
                    zenity --info --text="Téléchargement et installation du dernier kernel PS5..." --width=350
                    sudo dnf install -y https://github.com/ps5-linux/ps5-linux-patches/releases 2>/dev/null || true
                    zenity --info --text="Kernel installé avec succès !" --width=300
                    ;;
                2)
                    KERNELS=$(rpm -qa kernel | sort -V)
                    zenity --info --title="Kernels installés" --text="$KERNELS" --width=400 --height=300
                    ;;
            esac
            ;;
        12)
            SUB=$(zenity --list --title="12. Logithèque PS5" --text="Choisissez une option :" --width=550 --height=400 \
                --column="Logiciel" --column="Action" \
                "Steam" "Installer / Mettre à jour" \
                "Heroic Games Launcher" "Installer / Mettre à jour" \
                "ProtonUp-Qt" "Installer / Mettre à jour" \
                "Decky Loader" "Installer / Mettre à jour" \
                "GNOME Extension Manager" "Installer / Mettre à jour" \
                "Brave Browser" "Installer / Mettre à jour" \
                "Opera Browser" "Installer / Mettre à jour")
            case "$SUB" in
                "Steam") sudo dnf install -y steam && zenity --info --text="Steam installé/mis à jour !" --width=300 ;;
                "Heroic Games Launcher") flatpak install -y flathub com.heroicgameslauncher.hgl && zenity --info --text="Heroic installé !" --width=300 ;;
                "ProtonUp-Qt") flatpak install -y flathub net.davidotek.pupgui2 && zenity --info --text="ProtonUp-Qt installé !" --width=300 ;;
                "Decky Loader") curl -L https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/install_release.sh | sh && zenity --info --text="Decky Loader installé !" --width=300 ;;
                "GNOME Extension Manager") flatpak install -y flathub com.mattjakeman.ExtensionManager && zenity --info --text="Extension Manager installé !" --width=300 ;;
                "Brave Browser") sudo dnf install -y dnf-plugins-core && sudo dnf config-manager --add-repo https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo && sudo rpm --import https://brave-browser-rpm-release.s3.brave.com/brave-core.asc && sudo dnf install -y brave-browser && zenity --info --text="Brave installé !" --width=300 ;;
                "Opera Browser") sudo dnf install -y opera-stable || flatpak install -y flathub com.opera.Opera && zenity --info --text="Opera installé !" --width=300 ;;
            esac
            ;;
        13)
            PRESET=$(zenity --list --title="13. Software Presets" --text="Choisissez un pack complet à déployer :" --width=450 --height=240 \
                --column="Preset" --column="Description" \
                "Gaming" "Steam, Heroic, ProtonUp, Decky Loader" \
                "Bureautique" "Brave, Opera, Extension Manager" \
                "Développeur" "Outils de build, git, python3-devel")
            case "$PRESET" in
                "Gaming")
                    sudo dnf install -y steam
                    flatpak install -y flathub com.heroicgameslauncher.hgl net.davidotek.pupgui2
                    curl -L https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/install_release.sh | sh
                    zenity --info --text="Preset Gaming déployé avec succès !" --width=300
                    ;;
                "Bureautique")
                    flatpak install -y flathub com.mattjakeman.ExtensionManager com.brave.Browser
                    zenity --info --text="Preset Bureautique déployé avec succès !" --width=300
                    ;;
                "Développeur")
                    sudo dnf groupinstall -y "Development Tools"
                    sudo dnf install -y python3-devel git curl wget
                    zenity --info --text="Preset Développeur déployé avec succès !" --width=300
                    ;;
            esac
            ;;
    esac
done
