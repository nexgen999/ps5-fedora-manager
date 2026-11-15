#!/bin/bash
# ==============================================================================
# Module 02 : Gestion des langues et du clavier
# ==============================================================================

ACTION=$(whiptail --title "Gestion des Langues" --menu "Choisissez une option :" 15 60 3 \
"1" "Voir les packs installés & langues actuelles" \
"2" "Installer un nouveau pack de langue" \
"3" "Configurer la langue système & redémarrer la session" 3>&1 1>&2 2>&3)

case $ACTION in
    1)
        LOCALES=$(localectl status)
        whiptail --title "Langues actuelles" --msgbox "$LOCALES" 15 60
        ;;
    2)
        LANG_CODE=$(whiptail --inputbox "Entrez le code de la langue (ex: es, de, it, ja) :" 10 50 "" 3>&1 1>&2 2>&3)
        if [ -n "$LANG_CODE" ]; then
            dnf install -y "langpacks-$LANG_CODE" "firefox-langpacks-$LANG_CODE" || true
            whiptail --title "Succès" --msgbox "Pack de langue pour '$LANG_CODE' installé !" 8 40
        fi
        ;;
    3)
        TARGET_LANG=$(whiptail --inputbox "Entrez la locale complète à appliquer (ex: fr_FR.UTF-8 ou en_US.UTF-8) :" 10 50 "fr_FR.UTF-8" 3>&1 1>&2 2>&3)
        if [ -n "$TARGET_LANG" ]; then
            localectl set-locale LANG="$TARGET_LANG"
            whiptail --title "Configuration enregistrée" --msgbox "La langue a été définie sur $TARGET_LANG.\n\nLa session va maintenant se fermer pour appliquer les changements." 10 60
            
            # Forcer la déconnexion de la session GNOME pour recharger la langue
            pkill -u "$(whoami)" || loginctl terminate-user "$(whoami)"
        fi
        ;;
esac
