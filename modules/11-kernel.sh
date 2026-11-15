#!/bin/bash
# ==============================================================================
# Module 11 : Installation et sélection du Kernel PS5 - Zenity
# ==============================================================================

while true; do
    ACTION=$(zenity --list \
        --title="Gestion du Kernel PS5" \
        --text="Choisissez une action :" \
        --width=650 --height=350 \
        --column="ID" --column="Action" \
        "1" "Installer / Mettre à jour le dernier Kernel PS5" \
        "2" "Sélectionner le Kernel par défaut au démarrage" \
        "3" "Voir les noyaux actuellement installés" \
        "4" "Nettoyer les anciens noyaux obsolètes" \
        "0" "Retour au menu principal")

    [ $? -ne 0 ] || [ "$ACTION" = "0" ] || [ -z "$ACTION" ] && break

    case "$ACTION" in
        1)
            TMP_KERNEL="/tmp/ps5-kernel"
            mkdir -p "$TMP_KERNEL"
            
            # Récupération de l'URL du RPM depuis l'API GitHub
            LATEST_URL=$(curl -s https://api.github.com/repos/ps5-linux/ps5-linux-patches/releases/latest | grep "browser_download_url" | cut -d '"' -f 4 | grep -E '\.rpm$' | head -n 1)
            
            if [ -n "$LATEST_URL" ]; then
                {
                    echo "20"; echo "# Téléchargement du kernel PS5..."; wget -q "$LATEST_URL" -P "$TMP_KERNEL"
                    echo "70"; echo "# Installation des paquets RPM..."; sudo dnf install -y "$TMP_KERNEL"/*.rpm
                    echo "100"; echo "# Installation terminée !"; sleep 1
                } | zenity --progress --title="Kernel PS5" --text="Téléchargement en cours..." --percentage=0 --auto-close --width=450
                
                zenity --info --title="Succès" --text="Nouveau kernel PS5 installé avec succès !" --width=300
            else
                zenity --error --title="Erreur" --text="Impossible de récupérer automatiquement le paquet RPM du kernel. Vérifiez votre connexion." --width=400
            fi
            rm -rf "$TMP_KERNEL"
            ;;
        2)
            # Récupération de la liste des noyaux et du noyau par défaut
            KERNELS=$(rpm -qa kernel --qf "%{VERSION}-%{RELEASE}.%{ARCH}\n" | sort -V)
            DEFAULT_K=$(grubby --default-kernel 2>/dev/null || echo "Inconnu")
            
            # Construction d'un tableau pour zenity --list
            LIST_ARGS=()
            while read -r k; do
                [ -n "$k" ] && LIST_ARGS+=("$k" "Kernel Linux $k")
            done <<< "$KERNELS"
            
            if [ ${#LIST_ARGS[@]} -eq 0 ]; then
                zenity --error --title="Erreur" --text="Aucun noyau trouvé sur le système." --width=300
                continue
            fi
            
            CHOICE_K=$(zenity --list \
                --title="Sélection du Kernel" \
                --text="Kernel actuel : $DEFAULT_K\n\nChoisissez le kernel par défaut :" \
                --width=600 --height=350 \
                --column="Version" --column="Description" \
                "${LIST_ARGS[@]}")
            
            if [ -n "$CHOICE_K" ]; then
                sudo grubby --set-default="/boot/vmlinuz-$CHOICE_K"
                zenity --info --title="Succès" --text="Kernel par défaut défini sur : $CHOICE_K" --width=350
            fi
            ;;
        3)
            INSTALLED_K=$(rpm -qa kernel --qf "%{VERSION}-%{RELEASE}.%{ARCH}\n" | sort -V)
            zenity --text-info --title="Noyaux installés" --filename=<(echo "$INSTALLED_K") --width=550 --height=350
            ;;
        4)
            if zenity --question --text="Voulez-vous nettoyer les anciens noyaux (en conservant les 2 plus récents) ?" --width=400; then
                {
                    echo "50"; echo "# Suppression des anciens noyaux..."; sudo dnf remove -y $(sudo dnf repoquery --installonly --latest-limit=-2 -q) 2>/dev/null || true
                    echo "100"; echo "# Nettoyage terminé !"; sleep 1
                } | zenity --progress --title="Nettoyage Kernel" --text="Nettoyage..." --percentage=0 --auto-close --width=450
                zenity --info --title="Nettoyage" --text="Les anciens noyaux ont été nettoyés (les 2 plus récents ont été conservés)." --width=400
            fi
            ;;
    esac
done
