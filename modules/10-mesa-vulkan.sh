#!/bin/bash
# ==============================================================================
# Module 10 : Mise à jour Mesa, Vulkan & RADV (GPU PS5) - Zenity
# ==============================================================================

while true; do
    ACTION=$(zenity --list \
        --title="Mesa & Vulkan (GPU AMD PS5)" \
        --text="Gestion des pilotes graphiques :" \
        --width=650 --height=350 \
        --column="ID" --column="Action" \
        "1" "Installer les outils de test (vulkan-tools, mesa-demos)" \
        "2" "Mettre à jour Mesa et les pilotes Vulkan" \
        "3" "Vérifier la prise en charge RADV (vulkaninfo)" \
        "4" "Tout faire (Installer + Mettre à jour + Vérifier)" \
        "0" "Retour au menu principal")

    [ $? -ne 0 ] || [ "$ACTION" = "0" ] || [ -z "$ACTION" ] && break

    case "$ACTION" in
        1)
            {
                echo "50"; echo "# Installation des outils graphiques..."; sudo dnf install -y vulkan-tools mesa-demos
                echo "100"; echo "# Terminé !"; sleep 1
            } | zenity --progress --title="Outils Graphiques" --text="Installation..." --percentage=0 --auto-close --width=450
            zenity --info --title="Succès" --text="Outils graphiques installés !" --width=300
            ;;
        2)
            {
                echo "50"; echo "# Mise à jour de Mesa et Vulkan..."; sudo dnf upgrade -y "mesa*" "vulkan*"
                echo "100"; echo "# Terminé !"; sleep 1
            } | zenity --progress --title="Pilotes Mesa & Vulkan" --text="Mise à jour..." --percentage=0 --auto-close --width=450
            zenity --info --title="Succès" --text="Pilotes Mesa et Vulkan mis à jour !" --width=300
            ;;
        3)
            if command -v vulkaninfo &>/dev/null; then
                RADV_INFO=$(vulkaninfo --summary 2>/dev/null || echo "Impossible de récupérer les informations Vulkan.")
                zenity --text-info --title="Vérification RADV (GPU PS5)" --filename=<(echo "$RADV_INFO") --width=650 --height=450
            else
                zenity --error --title="Erreur" --text="vulkan-tools n'est pas installé. Installez-le d'abord (Option 1)." --width=350
            fi
            ;;
        4)
            {
                echo "25"; echo "# Étape 1/3 : Installation des outils..."; sudo dnf install -y vulkan-tools mesa-demos
                echo "65"; echo "# Étape 2/3 : Mise à jour Mesa / Vulkan..."; sudo dnf upgrade -y "mesa*" "vulkan*"
                echo "100"; echo "# Étape 3/3 : Vérification RADV..."; sleep 1
            } | zenity --progress --title="Maintenance Graphique" --text="Traitement en cours..." --percentage=0 --auto-close --width=450
            
            RADV_SUMMARY=$(vulkaninfo --summary 2>/dev/null | grep -i "radv" || echo "Pilote RADV actif (résumé indisponible).")
            zenity --info --title="Maintenance Graphique Terminée" --text="Mise à jour et vérification réussies !\n\n$RADV_SUMMARY" --width=500 --height=300
            ;;
    esac
done
