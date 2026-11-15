#!/bin/bash
# ==============================================================================
# Module 08 : PS5 Fan Manager & ps5-linux-tools
# ==============================================================================

PS5_CTL="/usr/local/sbin/ps5_control"
SERVICE_NAME="ps5-performance.service"

while true; do
    ACTION=$(whiptail --title "PS5 Fan Manager & Performance" --menu "Contrôle du refroidissement et du mode Boost PS5 :" 20 68 8 \
    "1" "Voir le statut (Service + Capteurs hwmon)" \
    "2" "Fan ON (Activer la ventilation)" \
    "3" "Fan OFF (Désactiver la ventilation)" \
    "4" "Boost ON (Activer le mode Boost)" \
    "5" "Boost OFF (Désactiver le mode Boost)" \
    "6" "Voir l'état détaillé de $SERVICE_NAME" \
    "7" "Redémarrer / Réactiver $SERVICE_NAME" \
    "8" "Mettre à jour ps5_control depuis ps5-linux-tools" \
    "0" "Retour au menu principal" 3>&1 1>&2 2>&3)

    [ $? -ne 0 ] || [ "$ACTION" = "0" ] && break

    case $ACTION in
        1)
            SVC_STATUS=$(systemctl is-active "$SERVICE_NAME" 2>/dev/null || echo "inactif")
            SVC_ENABLED=$(systemctl is-enabled "$SERVICE_NAME" 2>/dev/null || echo "désactivé")
            TEMPS=$(sensors 2>/dev/null || grep -H . /sys/class/thermal/thermal_zone*/temp 2>/dev/null || echo "Capteurs non lus.")
            whiptail --title "Statut PS5 Fan & Températures" --msgbox "Service ($SERVICE_NAME) : $SVC_STATUS ($SVC_ENABLED)\nBinaire ps5_control : $([ -x "$PS5_CTL" ] && echo "Présent" || echo "Manquant")\n\n--- Capteurs ---\n$TEMPS" 20 72
            ;;
        2)
            if [ -x "$PS5_CTL" ]; then
                "$PS5_CTL" --fan on
                whiptail --title "Ventilation" --msgbox "Commande envoyée : Fan ON." 8 45
            else
                whiptail --title "Erreur" --msgbox "Binaire $PS5_CTL introuvable." 8 45
            fi
            ;;
        3)
            if [ -x "$PS5_CTL" ]; then
                "$PS5_CTL" --fan off
                whiptail --title "Ventilation" --msgbox "Commande envoyée : Fan OFF." 8 45
            else
                whiptail --title "Erreur" --msgbox "Binaire $PS5_CTL introuvable." 8 45
            fi
            ;;
        4)
            if [ -x "$PS5_CTL" ]; then
                "$PS5_CTL" --boost on
                whiptail --title "Mode Boost" --msgbox "Commande envoyée : Boost ON." 8 45
            else
                whiptail --title "Erreur" --msgbox "Binaire $PS5_CTL introuvable." 8 45
            fi
            ;;
        5)
            if [ -x "$PS5_CTL" ]; then
                "$PS5_CTL" --boost off
                whiptail --title "Mode Boost" --msgbox "Commande envoyée : Boost OFF." 8 45
            else
                whiptail --title "Erreur" --msgbox "Binaire $PS5_CTL introuvable." 8 45
            fi
            ;;
        6)
            FULL_STATUS=$(systemctl status "$SERVICE_NAME" --no-pager 2>&1)
            whiptail --title "État de $SERVICE_NAME" --msgbox "$FULL_STATUS" 20 76
            ;;
        7)
            systemctl enable "$SERVICE_NAME" 2>/dev/null || true
            systemctl restart "$SERVICE_NAME"
            whiptail --title "Service Redémarré" --msgbox "Le service $SERVICE_NAME a été redémarré (Fan ON + Boost ON réappliqués)." 9 60
            ;;
        8)
            TMP_TOOLS="/tmp/ps5-linux-tools"
            rm -rf "$TMP_TOOLS"
            if git clone --depth 1 https://github.com/ps5-linux/ps5-linux-tools.git "$TMP_TOOLS"; then
                if make -C "$TMP_TOOLS" && [ -f "$TMP_TOOLS/ps5_control" ]; then
                    install -m 0755 "$TMP_TOOLS/ps5_control" "$PS5_CTL"
                    rm -rf "$TMP_TOOLS"
                    whiptail --title "Mise à jour réussie" --msgbox "ps5_control a été recompilé et installé dans $PS5_CTL !" 9 60
                else
                    rm -rf "$TMP_TOOLS"
                    whiptail --title "Erreur de compilation" --msgbox "La compilation (make) a échoué. Vérifiez que make et gcc sont installés." 9 60
                fi
            else
                whiptail --title "Erreur réseau" --msgbox "Impossible de cloner le dépôt ps5-linux-tools." 8 55
            fi
            ;;
    esac
done
