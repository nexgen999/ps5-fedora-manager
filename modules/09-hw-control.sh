#!/bin/bash
# ==============================================================================
# Module 09 : PS5 Hardware Control (GUI)
# ==============================================================================

REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || echo 'ps5')}"

ACTION=$(whiptail --title "PS5 Hardware Control (GUI)" --menu "Gestion de l'interface graphique matériel :" 16 65 4 \
"1" "Installer PS5 Hardware Control GUI" \
"2" "Vérifier / Mettre à jour PS5 Hardware Control" \
"3" "Vérifier la présence des sondes (/sys/class/hwmon/)" \
"4" "Désinstaller PS5 Hardware Control" 3>&1 1>&2 2>&3)

case $ACTION in
    1|2)
        dnf install -y python3-PyQt6
        sudo -u "$REAL_USER" bash -c 'curl -fsSL https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-gui/main/install.sh | bash'
        whiptail --title "Succès" --msgbox "PS5 Hardware Control GUI a été installé / mis à jour avec succès !" 8 55
        ;;
    3)
        HWMON_LIST=$(ls -l /sys/class/hwmon/)
        whiptail --title "Capteurs Matériels (/sys/class/hwmon/)" --msgbox "$HWMON_LIST" 16 70
        ;;
    4)
        if whiptail --yesno "Voulez-vous vraiment désinstaller PS5 Hardware Control GUI ?" 10 50; then
            rm -rf "/home/$REAL_USER/.local/share/ps5-hwcon-gui" \
                   "/home/$REAL_USER/.local/bin/ps5-hwcon-gui" \
                   "/home/$REAL_USER/.local/share/applications/ps5-hwcon-gui.desktop"
            whiptail --title "Désinstallé" --msgbox "PS5 Hardware Control GUI a été supprimé." 8 50
        fi
        ;;
esac
