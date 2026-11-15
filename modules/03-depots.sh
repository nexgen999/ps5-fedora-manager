#!/bin/bash
# ==============================================================================
# Module 03 : Gestion des dépôts (RPM, Flatpak, Personnalisés)
# ==============================================================================

ACTION=$(whiptail --title "Gestion des Dépôts" --menu "Choisissez une action :" 18 65 6 \
"1" "Voir tous les dépôts actifs (DNF & Flatpak)" \
"2" "Installer RPM Fusion (Free & Nonfree)" \
"3" "Installer le dépôt Flatpak (Flathub)" \
"4" "Ajouter un dépôt personnalisé par URL" \
"5" "Mettre à jour et nettoyer le cache des dépôts" \
"6" "Désinstaller / Supprimer un dépôt" 3>&1 1>&2 2>&3)

case $ACTION in
    1)
        REPOS=$(dnf repolist && echo -e "\n--- Flatpak Remotes ---\n" && flatpak remotes)
        whiptail --title "Dépôts Actifs" --msgbox "$REPOS" 20 70
        ;;
    2)
        if whiptail --yesno "Voulez-vous installer RPM Fusion (Free et Nonfree) ?" 10 50; then
            dnf install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm \
                           https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
            whiptail --title "Succès" --msgbox "RPM Fusion installé avec succès !" 8 40
        fi
        ;;
    3)
        if ! command -v flatpak &>/dev/null; then
            dnf install -y flatpak
        fi
        flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
        whiptail --title "Succès" --msgbox "Dépôt Flathub configuré !" 8 40
        ;;
    4)
        REPO_URL=$(whiptail --inputbox "Entrez l'URL ou la commande d'installation du dépôt :" 10 60 "" 3>&1 1>&2 2>&3)
        if [ -n "$REPO_URL" ]; then
            dnf install -y "$REPO_URL" || rpm -ivh "$REPO_URL"
            whiptail --title "Succès" --msgbox "Dépôt ajouté avec succès !" 8 40
        fi
        ;;
    5)
        dnf clean all && dnf makecache && dnf upgrade --refresh -y
        whiptail --title "Maintenance" --msgbox "Cache nettoyé et dépôts mis à jour !" 8 40
        ;;
    6)
        REPO_ID=$(whiptail --inputbox "Entrez l'identifiant (ID) du dépôt DNF à supprimer (ex: rpmfusion-free) :" 10 60 "" 3>&1 1>&2 2>&3)
        if [ -n "$REPO_ID" ]; then
            rm -f /etc/yum.repos.d/*"${REPO_ID}"*
            whiptail --title "Suppression" --msgbox "Dépôt supprimé." 8 40
        fi
        ;;
esac
