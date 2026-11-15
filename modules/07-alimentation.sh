#!/bin/bash
# ==============================================================================
# Module 07 : Management de l'alimentation (PS5)
# ==============================================================================

REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || echo 'ps5')}"

ACTION=$(whiptail --title "Gestion de l'Alimentation" --menu "Configurer les options de veille :" 16 65 5 \
"1" "Désactiver la veille système complète (Recommandé PS5)" \
"2" "Réactiver la veille système" \
"3" "Désactiver l'extinction automatique de l'écran" \
"4" "Activer l'extinction de l'écran après 15 min" \
"5" "Voir l'état actuel des services de veille" 3>&1 1>&2 2>&3)

case $ACTION in
    1)
        systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
        whiptail --title "Sécurité PS5" --msgbox "La mise en veille système a été désactivée (masquée) pour éviter tout plantage matériel." 10 60
        ;;
    2)
        systemctl unmask sleep.target suspend.target hibernate.target hybrid-sleep.target
        whiptail --title "Alimentation" --msgbox "La mise en veille système a été réactivée." 8 50
        ;;
    3)
        sudo -u "$REAL_USER" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u "$REAL_USER")/bus" \
            gsettings set org.gnome.desktop.session idle-delay 0
        whiptail --title "Écran" --msgbox "L'écran ne s'éteindra plus automatiquement." 8 50
        ;;
    4)
        sudo -u "$REAL_USER" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u "$REAL_USER")/bus" \
            gsettings set org.gnome.desktop.session idle-delay 900
        whiptail --title "Écran" --msgbox "Extinction de l'écran réglée sur 15 minutes." 8 50
        ;;
    5)
        STATUS=$(systemctl status sleep.target suspend.target --no-pager | grep -E "Loaded:|Active:")
        whiptail --title "État de la veille" --msgbox "$STATUS" 12 65
        ;;
esac
