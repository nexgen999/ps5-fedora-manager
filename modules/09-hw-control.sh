#!/bin/bash
# ==============================================================================
# Module 09 : PS5 Hardware Control (GUI) - Zenity
# ==============================================================================

REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || echo 'ps5')}"
USER_HOME=$(eval echo "~$REAL_USER")

while true; do
    ACTION=$(zenity --list \
        --title="PS5 Hardware Control (GUI)" \
        --text="Gestion de l'interface graphique matériel :" \
        --width=650 --height=350 \
        --column="ID" --column="Action" \
        "1" "Installer PS5 Hardware Control GUI" \
        "2" "Vérifier / Mettre à jour PS5 Hardware Control" \
        "3" "Vérifier la présence des sondes (/sys/class/hwmon/)" \
        "4" "Désinstaller PS5 Hardware Control" \
        "0" "Retour au menu principal")

    [ $? -ne 0 ] || [ "$ACTION" = "0" ] || [ -z "$ACTION" ] && break

    case "$ACTION" in
        1|2)
            {
                echo "30"; echo "# Installation des dépendances PyQt6..."; sudo dnf install -y python3-PyQt6
                echo "70"; echo "# Téléchargement et installation de l'interface..."; sudo -u "$REAL_USER" bash -c 'curl -fsSL https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-gui/main/install.sh | bash'
                echo "100"; echo "# Terminé !"; sleep 1
            } | zenity --progress --title="Hardware Control GUI" --text="Installation en cours..." --percentage=0 --auto-close --width=450
            zenity --info --title="Succès" --text="PS5 Hardware Control GUI a été installé / mis à jour avec succès !" --width=350
            ;;
        3)
            HWMON_LIST=$(ls -l /sys/class/hwmon/ 2>/dev/null || echo "Aucun capteur trouvé dans /sys/class/hwmon/")
            zenity --text-info --title="Capteurs Matériels (/sys/class/hwmon/)" --filename=<(echo "$HWMON_LIST") --width=650 --height=400
            ;;
        4)
            if zenity --question --text="Voulez-vous vraiment désinstaller PS5 Hardware Control GUI ?" --width=400; then
                rm -rf "$USER_HOME/.local/share/ps5-hwcon-gui" \
                       "$USER_HOME/.local/bin/ps5-hwcon-gui" \
                       "$USER_HOME/.local/share/applications/ps5-hwcon-gui.desktop"
                zenity --info --title="Désinstallé" --text="PS5 Hardware Control GUI a été supprimé." --width=300
            fi
            ;;
    esac
done
