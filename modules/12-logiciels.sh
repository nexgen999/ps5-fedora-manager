#!/bin/bash
# ==============================================================================
# Module 12 : Gestion unitaire des logiciels recommandés
# ==============================================================================

REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || echo 'ps5')}"

SOFTWARE=$(whiptail --title "Logiciels Recommandés" --menu "Sélectionnez un logiciel à gérer :" 22 65 9 \
"1" "Steam (DNF)" \
"2" "Heroic Games Launcher (Flatpak)" \
"3" "ProtonUp-Qt (Flatpak)" \
"4" "Decky Loader (Script officiel)" \
"5" "Etcher (Dépôt RPM GitHub)" \
"6" "Opera / Brave (Navigateurs)" \
"7" "Bazaar (Gestionnaire de mods/jeux)" \
"8" "Gnome Extension Manager (Flatpak)" 3>&1 1>&2 2>&3)

case $SOFTWARE in
    1)
        ACTION_S=$(whiptail --title "Steam" --menu "Action :" 10 40 3 "Installer" "" "Mettre à jour" "" "Désinstaller" "" 3>&1 1>&2 2>&3)
        [ "$ACTION_S" = "Installer" ] && dnf install -y steam
        [ "$ACTION_S" = "Mettre à jour" ] && dnf upgrade -y steam
        [ "$ACTION_S" = "Désinstaller" ] && dnf remove -y steam
        ;;
    2)
        flatpak install -y flathub com.heroicgameslauncher.hgl
        whiptail --msgbox "Heroic Games Launcher géré." 8 40
        ;;
    3)
        flatpak install -y flathub net.davidotek.pupgui2
        whiptail --msgbox "ProtonUp-Qt installé." 8 40
        ;;
    4)
        curl -L https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/install_release.sh | sh
        whiptail --msgbox "Decky Loader installé." 8 40
        ;;
    5)
        # Etcher repository configuration
        wget -O /etc/yum.repos.d/bintray-etcher.repo https://rpm.releases.frog.io/arch/rpm/bintray-etcher.repo 2>/dev/null || true
        dnf install -y balena-etcher-electron || dnf install -y etcher-electron
        whiptail --msgbox "BalenaEtcher installé." 8 40
        ;;
    6)
        NAV=$(whiptail --title "Navigateurs" --menu "Quel navigateur ?" 10 45 2 "Opera" "" "Brave" "" 3>&1 1>&2 2>&3)
        if [ "$NAV" = "Opera" ]; then
            rpm --import https://rpm.opera.com/rpm.key
            dnf config-manager --add-repo https://rpm.opera.com/rpm
            dnf install -y opera-stable
        elif [ "$NAV" = "Brave" ]; then
            dnf install -y dnf-plugins-core
            dnf config-manager --add-repo https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo
            rpm --import https://brave-browser-rpm-release.s3.brave.com/brave-core.asc
            dnf install -y brave-browser
        fi
        whiptail --msgbox "Navigateur installé !" 8 40
        ;;
    7)
        whiptail --msgbox "Bazaar : installation via Flatpak ou script en cours de liaison." 10 50
        ;;
    8)
        flatpak install -y flathub com.mattjakeman.ExtensionManager
        whiptail --msgbox "Gnome Extension Manager installé !" 8 40
        ;;
esac
