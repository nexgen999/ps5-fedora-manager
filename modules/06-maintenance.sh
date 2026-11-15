#!/bin/bash
# ==============================================================================
# Module 06 : Maintenance et nettoyage du système - Zenity
# ==============================================================================

while true; do
    ACTION=$(zenity --list \
        --title="Maintenance & Nettoyage" \
        --text="Choisissez une opération de maintenance :" \
        --width=650 --height=380 \
        --column="ID" --column="Action" \
        "1" "Nettoyer le cache DNF et les paquets orphelins" \
        "2" "Nettoyer les runtimes Flatpak inutilisés" \
        "3" "Vider les journaux système (Logs > 7 jours)" \
        "4" "Nettoyer les fichiers temporaires (/tmp & caches)" \
        "5" "Vérifier l'espace disque disponible" \
        "6" "Nettoyage complet (Tout-en-un)" \
        "0" "Retour au menu principal")

    [ $? -ne 0 ] || [ "$ACTION" = "0" ] || [ -z "$ACTION" ] && break

    case "$ACTION" in
        1)
            {
                echo "50"; echo "# Nettoyage DNF en cours..."; sudo dnf autoremove -y && sudo dnf clean all
                echo "100"; echo "# Terminé !"; sleep 1
            } | zenity --progress --title="Maintenance DNF" --text="Nettoyage..." --percentage=0 --auto-close --width=450
            zenity --info --title="Terminé" --text="Cache DNF nettoyé et paquets orphelins supprimés !" --width=350
            ;;
        2)
            if command -v flatpak &>/dev/null; then
                {
                    echo "50"; echo "# Suppression des runtimes Flatpak inutilisés..."; flatpak uninstall --unused -y
                    echo "100"; echo "# Terminé !"; sleep 1
                } | zenity --progress --title="Maintenance Flatpak" --text="Nettoyage..." --percentage=0 --auto-close --width=450
                zenity --info --title="Terminé" --text="Runtimes Flatpak inutilisés supprimés !" --width=350
            else
                zenity --info --title="Info" --text="Flatpak n'est pas installé." --width=300
            fi
            ;;
        3)
            {
                echo "50"; echo "# Nettoyage des journaux systemd..."; sudo journalctl --vacuum-time=7d
                echo "100"; echo "# Terminé !"; sleep 1
            } | zenity --progress --title="Journaux Système" --text="Nettoyage des logs..." --percentage=0 --auto-close --width=450
            zenity --info --title="Terminé" --text="Anciens journaux système nettoyés !" --width=350
            ;;
        4)
            {
                echo "50"; echo "# Suppression des fichiers temporaires..."; sudo rm -rf /tmp/* /var/tmp/* 2>/dev/null || true
                echo "100"; echo "# Terminé !"; sleep 1
            } | zenity --progress --title="Fichiers Temporaires" --text="Nettoyage..." --percentage=0 --auto-close --width=450
            zenity --info --title="Terminé" --text="Fichiers temporaires supprimés !" --width=300
            ;;
        5)
            DISK_INFO=$(df -h / /home)
            zenity --text-info --title="Espace Disque" --filename=<(echo "$DISK_INFO") --width=550 --height=350
            ;;
        6)
            {
                echo "20"; echo "# 1/4 : Nettoyage DNF..."; sudo dnf autoremove -y && sudo dnf clean all
                echo "50"; echo "# 2/4 : Nettoyage Flatpak..."; command -v flatpak &>/dev/null && flatpak uninstall --unused -y
                echo "80"; echo "# 3/4 : Purge des logs systemd..."; sudo journalctl --vacuum-time=7d
                echo "100"; echo "# 4/4 : Nettoyage des fichiers temporaires..."; sudo rm -rf /tmp/* /var/tmp/* 2>/dev/null || true
            } | zenity --progress --title="Nettoyage Complet" --text="Nettoyage du système en cours..." --percentage=0 --auto-close --width=450
            zenity --info --title="Succès" --text="Nettoyage complet terminé !" --width=300
            ;;
    esac
done
