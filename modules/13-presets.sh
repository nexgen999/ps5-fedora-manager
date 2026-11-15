#!/bin/bash
# ==============================================================================
# Module 13 : Installation par lots (Software Presets)
# ==============================================================================

PRESET=$(whiptail --title "Software Presets" --menu "Choisissez un pack à déployer :" 15 65 3 \
"1" "Preset Gaming (Steam, Heroic, ProtonUp, Decky)" \
"2" "Preset Bureautique (LibreOffice, VLC, Firefox-langpacks)" \
"3" "Preset Développeur (Git, Python, VS Code, Outils build)" 3>&1 1>&2 2>&3)

case $PRESET in
    1)
        {
            echo "10"; dnf install -y steam vulkan-tools
            echo "40"; flatpak install -y flathub com.heroicgameslauncher.hgl net.davidotek.pupgui2
            echo "80"; curl -L https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/install_release.sh | sh
            echo "100";
        } | whiptail --title "Installation Preset Gaming" --gauge "Déploiement des outils de jeu en cours..." 7 60 0
        whiptail --title "Succès" --msgbox "Preset Gaming déployé avec succès !" 8 50
        ;;
    2)
        {
            echo "20"; dnf install -y libreoffice vlc
            echo "60"; flatpak install -y flathub org.mozilla.firefox
            echo "100";
        } | whiptail --title "Installation Preset Bureautique" --gauge "Installation des logiciels de bureau..." 7 60 0
        whiptail --title "Succès" --msgbox "Preset Bureautique déployé !" 8 40
        ;;
    3)
        {
            echo "25"; dnf install -y git python3 python3-pip make automake gcc kernel-devel
            echo "70"; rpm --import https://packages.microsoft.com/keys/microsoft.asc && \
                          sh -c 'echo -e "[code]\name=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" > /etc/yum.repos.d/vscode.repo' && \
                          dnf install -y code
            echo "100";
        } | whiptail --title "Installation Preset Développeur" --gauge "Installation des outils de dev et VS Code..." 7 60 0
        whiptail --title "Succès" --msgbox "Preset Développeur déployé avec succès !" 8 50
        ;;
esac
