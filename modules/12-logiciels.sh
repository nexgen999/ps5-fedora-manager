#!/bin/bash
# ==============================================================================
# Module 12 : Gestion unitaire des logiciels recommandés - Zenity
# ==============================================================================

REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || echo 'ps5')}"

while true; do
    SOFTWARE=$(zenity --list \
        --title="Logiciels Recommandés" \
        --text="Sélectionnez un logiciel à gérer :" \
        --width=650 --height=420 \
        --column="ID" --column="Logiciel & Description" \
        "1" "Steam (DNF - Installer / MAJ / Désinstaller)" \
        "2" "Heroic Games Launcher (Flatpak)" \
        "3" "ProtonUp-Qt (Flatpak)" \
        "4" "Decky Loader (Script officiel)" \
        "5" "Etcher / BalenaEtcher (Dépôt RPM GitHub)" \
        "6" "Opera / Brave (Navigateurs Web)" \
        "7" "Bazaar (Gestionnaire de mods/jeux)" \
        "8" "Gnome Extension Manager (Flatpak)" \
        "0" "Retour au menu principal")

    [ $? -ne 0 ] || [ "$SOFTWARE" = "0" ] || [ -z "$SOFTWARE" ] && break

    case "$SOFTWARE" in
        1)
            ACTION_S=$(zenity --list --title="Steam" --text="Choisissez une action :" --width=400 --height=250 \
                --column="Action" \
                "Installer" \
                "Mettre à jour" \
                "Désinstaller")
            
            if [ "$ACTION_S" = "Installer" ]; then
                sudo dnf install -y steam && zenity --info --text="Steam installé avec succès !" --width=300
            elif [ "$ACTION_S" = "Mettre à jour" ]; then
                sudo dnf upgrade -y steam && zenity --info --text="Steam mis à jour !" --width=300
            elif [ "$ACTION_S" = "Désinstaller" ]; then
                sudo dnf remove -y steam && zenity --info --text="Steam désinstallé." --width=300
            fi
            ;;
        2)
            {
                echo "50"; echo "# Installation de Heroic Games Launcher..."; flatpak install -y flathub com.heroicgameslauncher.hgl
                echo "100"; echo "# Terminé !"; sleep 1
            } | zenity --progress --title="Heroic Launcher" --text="Installation..." --percentage=0 --auto-close --width=450
            zenity --info --title="Succès" --text="Heroic Games Launcher installé." --width=300
            ;;
        3)
            {
                echo "50"; echo "# Installation de ProtonUp-Qt..."; flatpak install -y flathub net.davidotek.pupgui2
                echo "100"; echo "# Terminé !"; sleep 1
            } | zenity --progress --title="ProtonUp-Qt" --text="Installation..." --percentage=0 --auto-close --width=450
            zenity --info --title="Succès" --text="ProtonUp-Qt installé." --width=300
            ;;
        4)
            {
                echo "30"; echo "# Téléchargement et installation de Decky Loader..."; curl -L https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/install_release.sh | sh
                echo "100"; echo "# Terminé !"; sleep 1
            } | zenity --progress --title="Decky Loader" --text="Installation..." --percentage=0 --auto-close --width=450
            zenity --info --title="Succès" --text="Decky Loader installé." --width=300
            ;;
        5)
            {
                echo "30"; echo "# Configuration du dépôt Etcher..."; sudo wget -O /etc/yum.repos.d/bintray-etcher.repo https://rpm.releases.frog.io/arch/rpm/bintray-etcher.repo 2>/dev/null || true
                echo "70"; echo "# Installation de BalenaEtcher..."; sudo dnf install -y balena-etcher-electron || sudo dnf install -y etcher-electron || true
                echo "100"; echo "# Terminé !"; sleep 1
            } | zenity --progress --title="BalenaEtcher" --text="Installation..." --percentage=0 --auto-close --width=450
            zenity --info --title="Succès" --text="BalenaEtcher installé." --width=300
            ;;
        6)
            NAV=$(zenity --list --title="Navigateurs Web" --text="Quel navigateur souhaitez-vous installer ?" --width=400 --height=220 \
                --column="Navigateur" \
                "Opera" \
                "Brave")
            
            if [ "$NAV" = "Opera" ]; then
                {
                    echo "40"; echo "# Ajout du dépôt Opera..."; sudo rpm --import https://rpm.opera.com/rpm.key
                    sudo dnf config-manager --add-repo https://rpm.opera.com/rpm || true
                    echo "80"; echo "# Installation d'Opera..."; sudo dnf install -y opera-stable
                    echo "100"; echo "# Terminé !"; sleep 1
                } | zenity --progress --title="Installation Opera" --text="En cours..." --percentage=0 --auto-close --width=450
                zenity --info --text="Opera installé avec succès !" --width=300
            elif [ "$NAV" = "Brave" ]; then
                {
                    echo "30"; echo "# Configuration de Brave..."; sudo dnf install -y dnf-plugins-core
                    sudo dnf config-manager --add-repo https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo || true
                    sudo rpm --import https://brave-browser-rpm-release.s3.brave.com/brave-core.asc || true
                    echo "80"; echo "# Installation de Brave..."; sudo dnf install -y brave-browser
                    echo "100"; echo "# Terminé !"; sleep 1
                } | zenity --progress --title="Installation Brave" --text="En cours..." --percentage=0 --auto-close --width=450
                zenity --info --text="Brave installé avec succès !" --width=300
            fi
            ;;
        7)
            zenity --info --title="Bazaar" --text="Bazaar : installation via Flatpak ou script en cours de liaison." --width=350
            ;;
        8)
            {
                echo "50"; echo "# Installation de Gnome Extension Manager..."; flatpak install -y flathub com.mattjakeman.ExtensionManager
                echo "100"; echo "# Terminé !"; sleep 1
            } | zenity --progress --title="Extension Manager" --text="Installation..." --percentage=0 --auto-close --width=450
            zenity --info --title="Succès" --text="Gnome Extension Manager installé !" --width=300
            ;;
    esac
done
