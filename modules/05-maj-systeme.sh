#!/bin/bash
# ==============================================================================
# Module 05 : Mises à jour globales de Fedora
# ==============================================================================

ACTION=$(whiptail --title "Mises à jour Globales" --menu "Que souhaitez-vous mettre à jour ?" 15 60 4 \
"1" "Mettre à jour le système complet (DNF Upgrade)" \
"2" "Mettre à jour les applications Flatpak" \
"3" "Mettre à jour les packs de langues" \
"4" "Tout mettre à jour d'un coup (Système + Flatpak + Langs)" 3>&1 1>&2 2>&3)

case $ACTION in
    1)
        {
            dnf upgrade -y
        } | whiptail --title "Mise à jour Système" --gauge "Mise à jour des paquets DNF en cours..." 7 60 0
        whiptail --title "Terminé" --msgbox "Mise à jour du système terminée !" 8 40
        ;;
    2)
        if command -v flatpak &>/dev/null; then
            {
                flatpak update -y
            } | whiptail --title "Mise à jour Flatpak" --gauge "Mise à jour des applications Flatpak..." 7 60 0
            whiptail --title "Terminé" --msgbox "Applications Flatpak à jour !" 8 40
        else
            whiptail --title "Info" --msgbox "Flatpak n'est pas installé sur ce système." 8 40
        fi
        ;;
    3)
        dnf upgrade -y "langpacks-*" "firefox-langpacks-*"
        whiptail --title "Terminé" --msgbox "Packs de langues mis à jour !" 8 40
        ;;
    4)
        {
            echo "10"; dnf upgrade -y
            echo "50"; command -v flatpak &>/dev/null && flatpak update -y
            echo "80"; dnf upgrade -y "langpacks-*"
            echo "100";
        } | whiptail --title "Mise à jour Globale" --gauge "Mise à jour complète en cours..." 7 60 0
        whiptail --title "Succès" --msgbox "Toutes les mises à jour ont été appliquées avec succès !" 10 50
        ;;
esac
