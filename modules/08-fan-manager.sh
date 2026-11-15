#!/bin/bash
# ==============================================================================
# Module 08 : PS5 Fan Manager & ps5-linux-tools (Version Zenity)
# ==============================================================================

PS5_CTL="/usr/local/sbin/ps5_control"
SERVICE_NAME="ps5-performance.service"

while true; do
    ACTION=$(zenity --list \
        --title="PS5 Fan Manager & Performance" \
        --text="Contrôle du refroidissement et du mode Boost PS5 :" \
        --width=650 --height=420 \
        --column="ID" --column="Action" \
        "1" "Voir le statut (Service + Capteurs hwmon)" \
        "2" "Fan ON (Activer la ventilation)" \
        "3" "Fan OFF (Désactiver la ventilation)" \
        "4" "Boost ON (Activer le mode Boost)" \
        "5" "Boost OFF (Désactiver le mode Boost)" \
        "6" "Voir l'état détaillé du service" \
        "7" "Redémarrer / Réactiver le service" \
        "8" "Mettre à jour ps5_control depuis GitHub" \
        "0" "Retour au menu principal")

    [ $? -ne 0 ] || [ "$ACTION" = "0" ] || [ -z "$ACTION" ] && break

    case "$ACTION" in
        1)
            SVC_STATUS=$(systemctl is-active "$SERVICE_NAME" 2>/dev/null || echo "inactif")
            TEMPS=$(sensors 2>/dev/null || grep -H . /sys/class/thermal/thermal_zone*/temp 2>/dev/null || echo "Capteurs non disponibles.")
            zenity --info --title="Statut PS5" --text="Service : $SVC_STATUS\n\n--- Capteurs ---\n$TEMPS" --width=550 --height=350
            ;;
        2) 
            if [ -x "$PS5_CTL" ]; then
                sudo "$PS5_CTL" --fan on && zenity --info --text="Ventilation activée (Fan ON)." --width=300
            else
                zenity --error --text="Binaire ps5_control introuvable ou non exécutable." --width=300
            fi
            ;;
        3) 
            if [ -x "$PS5_CTL" ]; then
                sudo "$PS5_CTL" --fan off && zenity --info --text="Ventilation désactivée (Fan OFF)." --width=300
            else
                zenity --error --text="Binaire ps5_control introuvable ou non exécutable." --width=300
            fi
            ;;
        4) 
            if [ -x "$PS5_CTL" ]; then
                sudo "$PS5_CTL" --boost on && zenity --info --text="Mode Boost activé." --width=300
            else
                zenity --error --text="Binaire ps5_control introuvable ou non exécutable." --width=300
            fi
            ;;
        5) 
            if [ -x "$PS5_CTL" ]; then
                sudo "$PS5_CTL" --boost off && zenity --info --text="Mode Boost désactivé." --width=300
            else
                zenity --error --text="Binaire ps5_control introuvable ou non exécutable." --width=300
            fi
            ;;
        6)
            FULL_STATUS=$(systemctl status "$SERVICE_NAME" --no-pager 2>&1)
            zenity --text-info --title="État du Service" --filename=<(echo "$FULL_STATUS") --width=650 --height=400
            ;;
        7)
            sudo systemctl enable "$SERVICE_NAME" 2>/dev/null || true
            sudo systemctl restart "$SERVICE_NAME"
            zenity --info --text="Service redémarré avec succès." --width=300
            ;;
        8)
            TMP_TOOLS="/tmp/ps5-linux-tools"
            rm -rf "$TMP_TOOLS"
            {
                echo "20"; echo "# Clonage de ps5-linux-tools..."; git clone --depth 1 https://github.com/ps5-linux/ps5-linux-tools.git "$TMP_TOOLS"
                echo "60"; echo "# Compilation en cours (make)..."; make -C "$TMP_TOOLS"
                echo "90"; echo "# Installation du binaire..."; sudo install -m 0755 "$TMP_TOOLS/ps5_control" "$PS5_CTL"
                echo "100"; echo "# Terminé !"; sleep 1
            } | zenity --progress --title="Mise à jour ps5_control" --text="Compilation..." --percentage=0 --auto-close --width=450
            
            if [ -x "$PS5_CTL" ]; then
                rm -rf "$TMP_TOOLS"
                zenity --info --text="ps5_control mis à jour et compilé avec succès !" --width=350
            else
                rm -rf "$TMP_TOOLS"
                zenity --error --text="Échec de la compilation ou de l'installation de ps5_control." --width=350
            fi
            ;;
    esac
done
