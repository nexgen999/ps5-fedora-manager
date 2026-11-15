#!/bin/bash
# ==============================================================================
# Module 13 : Installation par lots (Software Presets) - Zenity
# ==============================================================================

while true; do
    PRESET=$(zenity --list \
        --title="Software Presets" \
        --text="Choisissez un pack à déployer :" \
        --width=650 --height=320 \
        --column="ID" --column="Pack et Description" \
        "1" "Preset Gaming (Steam, Heroic, ProtonUp, Decky)" \
        "2" "Preset Bureautique (LibreOffice, VLC, Firefox)" \
        "3" "Preset Développeur (Git, Python, VS Code, Outils build)" \
        "0" "Retour au menu principal")

    [ $? -ne 0 ] || [ "$PRESET" = "0" ] || [ -z "$PRESET" ] && break

    case "$PRESET" in
        1)
            {
                echo "10"; echo "# Installation de Steam et Vulkan..."; sudo dnf install -y steam vulkan-tools
                echo "40"; echo "# Installation des Flatpaks (Heroic, ProtonUp)..."; flatpak install -y flathub com.heroicgameslauncher.hgl net.davidotek.pupgui2
                echo "80"; echo "# Installation de Decky Loader..."; curl -L https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/install_release.sh | sh
                echo "100"; echo "# Déploiement terminé !"; sleep 1
            } | zenity --progress --title="Installation Preset Gaming" --text="Déploiement en cours..." --percentage=0 --auto-close --width=450
            zenity --info --title="Succès" --text="Preset Gaming déployé avec succès !" --width=300
            ;;
        2)
            {
                echo "20"; echo "# Installation de LibreOffice et VLC..."; sudo dnf install -y libreoffice vlc
                echo "60"; echo "# Installation de Firefox (Flatpak)..."; flatpak install -y flathub org.mozilla.firefox
                echo "100"; echo "# Déploiement terminé !"; sleep 1
            } | zenity --progress --title="Installation Preset Bureautique" --text="Installation en cours..." --percentage=0 --auto-close --width=450
            zenity --info --title="Succès" --text="Preset Bureautique déployé !" --width=300
            ;;
        3)
            {
                echo "25"; echo "# Installation des outils de dev (Git, Python, GCC)..."; sudo dnf install -y git python3 python3-pip make automake gcc kernel-devel
                echo "70"; echo "# Configuration et installation de VS Code..."; sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc && \
                    sudo sh -c 'echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" > /etc/yum.repos.d/vscode.repo' && \
                    sudo dnf install -y code
                echo "100"; echo "# Déploiement terminé !"; sleep 1
            } | zenity --progress --title="Installation Preset Développeur" --text="Installation en cours..." --percentage=0 --auto-close --width=450
            zenity --info --title="Succès" --text="Preset Développeur déployé avec succès !" --width=300
            ;;
    esac
done
