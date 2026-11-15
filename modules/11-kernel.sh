#!/bin/bash
# ==============================================================================
# Module 11 : Installation et sélection du Kernel PS5
# ==============================================================================

ACTION=$(whiptail --title "Gestion du Kernel PS5" --menu "Choisissez une action :" 16 65 4 \
"1" "Installer / Mettre à jour le dernier Kernel PS5" \
"2" "Sélectionner le Kernel par défaut au démarrage" \
"3" "Voir les noyaux actuellement installés" \
"4" "Nettoyer les anciens noyaux obsolètes" 3>&1 1>&2 2>&3)

case $ACTION in
    1)
        whiptail --title "Kernel PS5" --msgbox "Téléchargement et installation du dernier kernel depuis GitHub (ps5-linux-patches)..." 10 60
        TMP_KERNEL="/tmp/ps5-kernel"
        mkdir -p "$TMP_KERNEL"
        
        # Récupération de la dernière release ou paquets RPM depuis les patches ps5-linux
        LATEST_URL=$(curl -s https://api.github.com/repos/ps5-linux/ps5-linux-patches/releases/latest | grep "browser_download_url" | cut -d '"' -f 4 | grep -E '\.rpm$' | head -n 1)
        
        if [ -n "$LATEST_URL" ]; then
            wget -q "$LATEST_URL" -P "$TMP_KERNEL"
            dnf install -y "$TMP_KERNEL"/*.rpm
            whiptail --title "Succès" --msgbox "Nouveau kernel PS5 installé avec succès !" 8 50
        else
            whiptail --title "Erreur" --msgbox "Impossible de récupérer automatiquement le paquet RPM du kernel. Vérifiez votre connexion." 10 60
        fi
        rm -rf "$TMP_KERNEL"
        ;;
    2)
        KERNELS=$(rpm -qa kernel --qf "%{VERSION}-%{RELEASE}.%{ARCH}\n" | sort -V)
        DEFAULT_K=$(grubby --default-kernel)
        CHOICE_K=$(whiptail --title "Sélection du Kernel" --menu "Kernel actuel : $DEFAULT_K\n\nChoisissez le kernel par défaut :" 18 70 6 $(echo "$KERNELS" | awk '{print $1 " kernel"}') 3>&1 1>&2 2>&3)
        if [ -n "$CHOICE_K" ]; then
            grubby --set-default="/boot/vmlinuz-$CHOICE_K"
            whiptail --title "Succès" --msgbox "Kernel par défaut défini sur : $CHOICE_K" 10 50
        fi
        ;;
    3)
        INSTALLED_K=$(rpm -qa kernel --qf "%{VERSION}-%{RELEASE}.%{ARCH}\n")
        whiptail --title "Noyaux installés" --msgbox "$INSTALLED_K" 15 60
        ;;
    4)
        dnf remove -y $(dnf repoquery --installonly --latest-limit=-2 -q) 2>/dev/null || whiptail --msgbox "Aucun ancien kernel à nettoyer." 8 40
        whiptail --title "Nettoyage" --msgbox "Les anciens noyaux ont été nettoyés (les 2 plus récents ont été conservés)." 10 50
        ;;
esac
