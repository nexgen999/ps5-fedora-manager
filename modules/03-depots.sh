#!/bin/bash
# ==============================================================================
# Module 03 : Gestion des dépôts (RPM, Flatpak, Personnalisés) - Zenity
# ==============================================================================

while true; do
    ACTION=$(zenity --list \
        --title="Gestion des Dépôts" \
        --text="Choisissez une action :" \
        --width=650 --height=380 \
        --column="ID" --column="Action" \
        "1" "Voir tous les dépôts actifs (DNF & Flatpak)" \
        "2" "Installer RPM Fusion (Free & Nonfree)" \
        "3" "Installer le dépôt Flatpak (Flathub)" \
        "4" "Ajouter un dépôt personnalisé par URL" \
        "5" "Mettre à jour et nettoyer le cache des dépôts" \
        "6" "Désinstaller / Supprimer un dépôt" \
        "0" "Retour au menu principal")

    [ $? -ne 0 ] || [ "$ACTION" = "0" ] || [ -z "$ACTION" ] && break

    case "$ACTION" in
        1)
            REPOS=$(dnf repolist 2>/dev/null && echo -e "\n--- Flatpak Remotes ---\n" && flatpak remotes 2>/dev/null)
            zenity --text-info --title="Dépôts Actifs" --filename=<(echo "$REPOS") --width=650 --height=450
            ;;
        2)
            if zenity --question --text="Voulez-vous installer RPM Fusion (Free et Nonfree) ?" --width=400; then
                {
                    echo "30"; echo "# Téléchargement de RPM Fusion..."; 
                    sudo dnf install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm \
                                      https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
                    echo "100"; echo "# Installation terminée !"; sleep 1
                } | zenity --progress --title="RPM Fusion" --text="Installation en cours..." --percentage=0 --auto-close --width=400
                zenity --info --title="Succès" --text="RPM Fusion installé avec succès !" --width=300
            fi
            ;;
        3)
            if ! command -v flatpak &>/dev/null; then
                sudo dnf install -y flatpak
            fi
            flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
            zenity --info --title="Succès" --text="Dépôt Flathub configuré avec succès !" --width=300
            ;;
        4)
            REPO_URL=$(zenity --entry --title="Dépôt personnalisé" --text="Entrez l'URL ou la commande d'installation du dépôt :" --width=500)
            if [ -n "$REPO_URL" ]; then
                sudo dnf install -y "$REPO_URL" || sudo rpm -ivh "$REPO_URL"
                zenity --info --title="Succès" --text="Dépôt ajouté avec succès !" --width=300
            fi
            ;;
        5)
            {
                echo "20"; echo "# Nettoyage des caches DNF..."; sudo dnf clean all
                echo "60"; echo "# Création du nouveau cache..."; sudo dnf makecache
                echo "90"; echo "# Rafraîchissement des paquets..."; sudo dnf upgrade --refresh -y
                echo "100"; echo "# Terminé !"; sleep 1
            } | zenity --progress --title="Maintenance Dépôts" --text="Nettoyage et mise à jour..." --percentage=0 --auto-close --width=450
            zenity --info --title="Maintenance" --text="Cache nettoyé et dépôts mis à jour !" --width=300
            ;;
        6)
            REPO_ID=$(zenity --entry --title="Suppression de dépôt" --text="Entrez l'identifiant (ID) du dépôt DNF à supprimer (ex: rpmfusion-free) :" --width=500)
            if [ -n "$REPO_ID" ]; then
                sudo rm -f /etc/yum.repos.d/*"${REPO_ID}"*
                zenity --info --title="Suppression" --text="Dépôt '${REPO_ID}' supprimé." --width=300
            fi
            ;;
    esac
done
