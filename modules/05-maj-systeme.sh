#!/bin/bash
# ==============================================================================
# Module 05 : Mises à jour globales de Fedora - Zenity
# ==============================================================================

while true; do
    ACTION=$(zenity --list \
        --title="Mises à jour Globales" \
        --text="Que souhaitez-vous mettre à jour ?" \
        --width=600 --height=320 \
        --column="ID" --column="Action" \
        "1" "Mettre à jour le système complet (DNF Upgrade)" \
        "2" "Mettre à jour les applications Flatpak" \
        "3" "Mettre à jour les packs de langues" \
        "4" "Tout mettre à jour d'un coup (Système + Flatpak + Langs)" \
        "0" "Retour au menu principal")

    [ $? -ne 0 ] || [ "$ACTION" = "0" ] || [ -z "$ACTION" ] && break

    case "$ACTION" in
        1)
            {
                echo "10"; echo "# Mise à jour des paquets DNF en cours..."; sudo dnf upgrade -y
                echo "100"; echo "# Mise à jour terminée !"; sleep 1
            } | zenity --progress --title="Mise à jour Système" --text="Mise à jour en cours..." --percentage=0 --auto-close --width=450
            zenity --info --title="Terminé" --text="Mise à jour du système terminée !" --width=300
            ;;
        2)
            if command -v flatpak &>/dev/null; then
                {
                    echo "20"; echo "# Mise à jour des applications Flatpak..."; flatpak update -y
                    echo "100"; echo "# Applications à jour !"; sleep 1
                } | zenity --progress --title="Mise à jour Flatpak" --text="Mise à jour en cours..." --percentage=0 --auto-close --width=450
                zenity --info --title="Terminé" --text="Applications Flatpak à jour !" --width=300
            else
                zenity --info --title="Info" --text="Flatpak n'est pas installé sur ce système." --width=300
            fi
            ;;
        3)
            {
                echo "20"; echo "# Mise à jour des packs de langues..."; sudo dnf upgrade -y "langpacks-*" "firefox-langpacks-*"
                echo "100"; echo "# Packs de langues mis à jour !"; sleep 1
            } | zenity --progress --title="Mise à jour Langues" --text="Mise à jour en cours..." --percentage=0 --auto-close --width=450
            zenity --info --title="Terminé" --text="Packs de langues mis à jour !" --width=300
            ;;
        4)
            {
                echo "10"; echo "# Étape 1/3 : Système DNF..."; sudo dnf upgrade -y
                echo "50"; echo "# Étape 2/3 : Applications Flatpak..."; command -v flatpak &>/dev/null && flatpak update -y
                echo "80"; echo "# Étape 3/3 : Packs de langues..."; sudo dnf upgrade -y "langpacks-*" "firefox-langpacks-*"
                echo "100"; echo "# Mise à jour globale terminée !"; sleep 1
            } | zenity --progress --title="Mise à jour Globale" --text="Mise à jour complète en cours..." --percentage=0 --auto-close --width=450
            zenity --info --title="Succès" --text="Toutes les mises à jour ont été appliquées avec succès !" --width=350
            ;;
    esac
done
