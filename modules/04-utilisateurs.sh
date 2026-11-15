#!/bin/bash
# ==============================================================================
# Module 04 : Gestion des utilisateurs et du compte Root
# ==============================================================================

ACTION=$(whiptail --title "Gestion des Utilisateurs" --menu "Choisissez une action :" 16 60 5 \
"1" "Voir la liste des utilisateurs" \
"2" "Ajouter un nouvel utilisateur" \
"3" "Éditer un utilisateur (Mot de passe / Langue)" \
"4" "Supprimer un utilisateur" \
"5" "Changer le mot de passe Root" 3>&1 1>&2 2>&3)

case $ACTION in
    1)
        USERS=$(awk -F: '$3 >= 1000 {print "User: " $1 " | Home: " $6 " | Shell: " $7}' /etc/passwd)
        whiptail --title "Utilisateurs du Système" --msgbox "$USERS" 15 60
        ;;
    2)
        NEW_USER=$(whiptail --inputbox "Entrez le nom du nouvel utilisateur :" 10 50 "" 3>&1 1>&2 2>&3)
        if [ -n "$NEW_USER" ]; then
            NEW_PASS=$(whiptail --passwordbox "Entrez le mot de passe pour $NEW_USER :" 10 50 3>&1 1>&2 2>&3)
            if [ -n "$NEW_PASS" ]; then
                useradd -m -s /bin/bash "$NEW_USER"
                echo "$NEW_USER:$NEW_PASS" | chpasswd
                usermod -aG wheel "$NEW_USER" # Ajout aux sudoers
                whiptail --title "Succès" --msgbox "Utilisateur $NEW_USER créé avec succès (droits sudo activés)." 10 50
            fi
        fi
        ;;
    3)
        EDIT_USER=$(whiptail --inputbox "Nom de l'utilisateur à modifier :" 10 50 "" 3>&1 1>&2 2>&3)
        if id "$EDIT_USER" &>/dev/null; then
            NEW_P=$(whiptail --passwordbox "Nouveau mot de passe pour $EDIT_USER (laisser vide pour ne pas changer) :" 10 50 3>&1 1>&2 2>&3)
            [ -n "$NEW_P" ] && echo "$EDIT_USER:$NEW_P" | chpasswd
            whiptail --title "Succès" --msgbox "Compte de $EDIT_USER mis à jour !" 8 40
        else
            whiptail --title "Erreur" --msgbox "Cet utilisateur n'existe pas." 8 40
        fi
        ;;
    4)
        DEL_USER=$(whiptail --inputbox "Nom de l'utilisateur à supprimer :" 10 50 "" 3>&1 1>&2 2>&3)
        if [ -n "$DEL_USER" ] && [ "$DEL_USER" != "root" ]; then
            if whiptail --yesno "Voulez-vous aussi supprimer son dossier personnel (/home/$DEL_USER) ?" 10 50; then
                userdel -r "$DEL_USER"
            else
                userdel "$DEL_USER"
            fi
            whiptail --title "Supprimé" --msgbox "Utilisateur $DEL_USER supprimé." 8 40
        fi
        ;;
    5)
        ROOT_PASS=$(whiptail --passwordbox "Entrez le nouveau mot de passe pour Root :" 10 50 3>&1 1>&2 2>&3)
        if [ -n "$ROOT_PASS" ]; then
            echo "root:$ROOT_PASS" | chpasswd
            whiptail --title "Succès" --msgbox "Mot de passe root mis à jour !" 8 40
        fi
        ;;
esac
