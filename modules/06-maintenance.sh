#!/bin/bash
# ==============================================================================
# Module 06 : Maintenance et nettoyage du système
# ==============================================================================

ACTION=$(whiptail --title "Maintenance & Nettoyage" --menu "Choisissez une opération de maintenance :" 18 65 6 \
"1" "Nettoyer le cache DNF et les paquets orphelins" \
"2" "Nettoyer les runtimes Flatpak inutilisés" \
"3" "Vider les journaux système (Logs > 7 jours)" \
"4" "Nettoyer les fichiers temporaires (/tmp & caches)" \
"5" "Vérifier l'espace disque disponible" \
"6" "Nettoyage complet (Tout-en-un)" 3>&1 1>&2 2>&3)

case $ACTION in
    1)
        dnf autoremove -y && dnf clean all
        whiptail --title "Terminé" --msgbox "Cache DNF nettoyé et paquets orphelins supprimés !" 8 50
        ;;
    2)
        if command -v flatpak &>/dev/null; then
            flatpak uninstall --unused -y
            whiptail --title "Terminé" --msgbox "Runtimes Flatpak inutilisés supprimés !" 8 50
        else
            whiptail --title "Info" --msgbox "Flatpak n'est pas installé." 8 40
        fi
        ;;
    3)
        journalctl --vacuum-time=7d
        whiptail --title "Terminé" --msgbox "Anciens journaux système nettoyés !" 8 45
        ;;
    4)
        rm -rf /tmp/* /var/tmp/*
        whiptail --title "Terminé" --msgbox "Fichiers temporaires supprimés !" 8 45
        ;;
    5)
        DISK_INFO=$(df -h / /home)
        whiptail --title "Espace Disque" --msgbox "$DISK_INFO" 15 70
        ;;
    6)
        {
            echo "20"; dnf autoremove -y && dnf clean all
            echo "50"; command -v flatpak &>/dev/null && flatpak uninstall --unused -y
            echo "80"; journalctl --vacuum-time=7d
            echo "100"; rm -rf /tmp/*
        } | whiptail --title "Nettoyage Complet" --gauge "Nettoyage du système en cours..." 7 60 0
        whiptail --title "Succès" --msgbox "Nettoyage complet terminé !" 8 40
        ;;
esac
