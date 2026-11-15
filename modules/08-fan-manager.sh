#!/bin/bash
# ==============================================================================
# Module 08 : PS5 Fan Manager & ps5-linux-tools
# ==============================================================================

ACTION=$(whiptail --title "PS5 Fan Manager" --menu "Contrôle du refroidissement PS5 :" 18 65 6 \
"1" "Voir le statut et les températures (hwmon)" \
"2" "Démarrer / Activer le service Fan Control" \
"3" "Arrêter le service Fan Control" \
"4" "Redémarrer le service Fan Control" \
"5" "Activer / Désactiver le mode Boost (Vitesse max)" \
"6" "Mettre à jour depuis ps5-linux-tools" 3>&1 1>&2 2>&3)

case $ACTION in
    1)
        STATUS=$(systemctl status ps5-fan* --no-pager 2>/dev/null || echo "Service ps5-fan non trouvé.")
        TEMPS=$(sensors 2>/dev/null || cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null || echo "Capteurs non lus.")
        whiptail --title "Statut Ventilation & Températures" --msgbox "$STATUS\n\n--- Capteurs ---\n$TEMPS" 20 70
        ;;
    2)
        systemctl enable --now ps5-fan-control 2>/dev/null || systemctl enable --now ps5-fan 2>/dev/null
        whiptail --title "Ventilation" --msgbox "Service de ventilation démarré et activé." 8 50
        ;;
    3)
        systemctl stop ps5-fan-control 2>/dev/null || systemctl stop ps5-fan 2>/dev/null
        whiptail --title "Ventilation" --msgbox "Service de ventilation arrêté." 8 45
        ;;
    4)
        systemctl restart ps5-fan-control 2>/dev/null || systemctl restart ps5-fan 2>/dev/null
        whiptail --title "Ventilation" --msgbox "Service de ventilation redémarré." 8 45
        ;;
    5)
        if whiptail --yesno "Voulez-vous forcer la ventilation en mode Boost (vitesse élevée) ?\n(Non = retour en mode automatique)" 10 60; then
            for pwm in /sys/class/hwmon/hwmon*/pwm1; do [ -f "$pwm" ] && echo 255 > "$pwm"; done
            whiptail --title "Boost Activé" --msgbox "Ventilateur forcé à pleine vitesse !" 8 45
        else
            systemctl restart ps5-fan-control 2>/dev/null || systemctl restart ps5-fan 2>/dev/null
            whiptail --title "Mode Auto" --msgbox "Retour à la régulation automatique." 8 45
        fi
        ;;
    6)
        mkdir -p /tmp/ps5-tools
        git clone --depth 1 https://github.com/ps5-linux/ps5-linux-tools.git /tmp/ps5-tools
        if [ -f "/tmp/ps5-tools/install.sh" ]; then
            bash /tmp/ps5-tools/install.sh
        elif [ -f "/tmp/ps5-tools/Makefile" ]; then
            make -C /tmp/ps5-tools install
        fi
        rm -rf /tmp/ps5-tools
        whiptail --title "Mise à jour" --msgbox "ps5-linux-tools mis à jour avec succès !" 8 50
        ;;
esac
