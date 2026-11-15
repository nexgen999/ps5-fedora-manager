#!/bin/bash
# ==============================================================================
# Module 07 : Management de l'alimentation (PS5) - Zenity
# ==============================================================================

REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || echo 'ps5')}"
USER_UID=$(id -u "$REAL_USER" 2>/dev/null || echo "1000")

while true; do
    ACTION=$(zenity --list \
        --title="Gestion de l'Alimentation" \
        --text="Configurer les options de veille :" \
        --width=650 --height=350 \
        --column="ID" --column="Action" \
        "1" "Désactiver la veille système complète (Recommandé PS5)" \
        "2" "Réactiver la veille système" \
        "3" "Désactiver l'extinction automatique de l'écran" \
        "4" "Activer l'extinction de l'écran après 15 min" \
        "5" "Voir l'état actuel des services de veille" \
        "0" "Retour au menu principal")

    [ $? -ne 0 ] || [ "$ACTION" = "0" ] || [ -z "$ACTION" ] && break

    case "$ACTION" in
        1)
            sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
            zenity --info --title="Sécurité PS5" --text="La mise en veille système a été désactivée (masquée) pour éviter tout plantage matériel." --width=400
            ;;
        2)
            sudo systemctl unmask sleep.target suspend.target hibernate.target hybrid-sleep.target
            zenity --info --title="Alimentation" --text="La mise en veille système a été réactivée." --width=300
            ;;
        3)
            sudo -u "$REAL_USER" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$USER_UID/bus" \
                gsettings set org.gnome.desktop.session idle-delay 0
            zenity --info --title="Écran" --text="L'écran ne s'éteindra plus automatiquement." --width=300
            ;;
        4)
            sudo -u "$REAL_USER" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$USER_UID/bus" \
                gsettings set org.gnome.desktop.session idle-delay 900
            zenity --info --title="Écran" --text="Extinction de l'écran réglée sur 15 minutes." --width=300
            ;;
        5)
            STATUS=$(systemctl status sleep.target suspend.target --no-pager 2>&1 | grep -E "Loaded:|Active:")
            zenity --text-info --title="État de la veille" --filename=<(echo "$STATUS") --width=600 --height=350
            ;;
    esac
done
