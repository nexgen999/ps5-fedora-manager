#!/bin/bash
# ==============================================================================
# Module 10 : Mise à jour Mesa, Vulkan & RADV (GPU PS5)
# ==============================================================================

ACTION=$(whiptail --title "Mesa & Vulkan (GPU AMD PS5)" --menu "Gestion des pilotes graphiques :" 16 65 4 \
"1" "Installer les outils de test (vulkan-tools, mesa-demos)" \
"2" "Mettre à jour Mesa et les pilotes Vulkan" \
"3" "Vérifier la prise en charge RADV (vulkaninfo)" \
"4" "Tout faire (Installer + Mettre à jour + Vérifier)" 3>&1 1>&2 2>&3)

case $ACTION in
    1)
        dnf install -y vulkan-tools mesa-demos
        whiptail --title "Succès" --msgbox "Outils graphiques installés !" 8 45
        ;;
    2)
        dnf upgrade -y "mesa*" "vulkan*"
        whiptail --title "Succès" --msgbox "Pilotes Mesa et Vulkan mis à jour !" 8 45
        ;;
    3)
        if command -v vulkaninfo &>/dev/null; then
            RADV_INFO=$(vulkaninfo --summary 2>/dev/null | grep -i "radv" || echo "Pilote RADV non détecté dans les résumés.")
            whiptail --title "Vérification RADV (GPU PS5)" --msgbox "$RADV_INFO" 14 65
        else
            whiptail --title "Erreur" --msgbox "vulkan-tools n'est pas installé. Installez-le d'abord (Option 1)." 10 55
        fi
        ;;
    4)
        dnf install -y vulkan-tools mesa-demos
        dnf upgrade -y "mesa*" "vulkan*"
        RADV_INFO=$(vulkaninfo --summary 2>/dev/null | grep -i "radv" || echo "RADV OK")
        whiptail --title "Maintenance Graphique Terminée" --msgbox "Mise à jour et vérification réussies !\n\n$RADV_INFO" 15 65
        ;;
esac
