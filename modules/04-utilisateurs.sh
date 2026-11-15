#!/bin/bash
# ==============================================================================
# Module 04 : Gestion des utilisateurs et du compte Root - Zenity
# ==============================================================================

while true; do
    ACTION=$(zenity --list \
        --title="Gestion des Utilisateurs" \
        --text="Choisissez une action :" \
        --width=600 --height=350 \
        --column="ID" --column="Action" \
        "1" "Voir la liste des utilisateurs" \
        "2" "Ajouter un nouvel utilisateur" \
        "3" "Éditer un utilisateur (Mot de passe)" \
        "4" "Supprimer un utilisateur" \
        "5" "Changer le mot de passe Root" \
        "0" "Retour au menu principal")

    [ $? -ne 0 ] || [ "$ACTION" = "0" ] || [ -z "$ACTION" ] && break

    case "$ACTION" in
        1)
            USERS=$(awk -F: '$3 >= 1000 {print "User: " $1 " | Home: " $6 " | Shell: " $7}' /etc/passwd)
            zenity --text-info --title="Utilisateurs du Système" --filename=<(echo "$USERS") --width=600 --height=400
            ;;
        2)
            NEW_USER=$(zenity --entry --title="Nouvel utilisateur" --text="Entrez le nom du nouvel utilisateur :" --width=400)
            if [ -n "$NEW_USER" ]; then
                NEW_PASS=$(zenity --password --title="Mot de passe" --text="Entrez le mot de passe pour $NEW_USER :" --width=400)
                if [ -n "$NEW_PASS" ]; then
                    sudo useradd -m -s /bin/bash "$NEW_USER"
                    echo "$NEW_USER:$NEW_PASS" | sudo chpasswd
                    sudo usermod -aG wheel,video,input,render "$NEW_USER" # Ajout aux groupes sudo/hw
                    zenity --info --title="Succès" --text="Utilisateur $NEW_USER créé avec succès (droits sudo activés)." --width=350
                fi
            fi
            ;;
        3)
            EDIT_USER=$(zenity --entry --title="Édition d'utilisateur" --text="Nom de l'utilisateur à modifier :" --width=400)
            if [ -n "$EDIT_USER" ] && id "$EDIT_USER" &>/dev/null; then
                NEW_P=$(zenity --password --title="Nouveau mot de passe" --text="Nouveau mot de passe pour $EDIT_USER (laisser vide pour annuler) :" --width=400)
                if [ -n "$NEW_P" ]; then
                    echo "$EDIT_USER:$NEW_P" | sudo chpasswd
                    zenity --info --title="Succès" --text="Compte de $EDIT_USER mis à jour !" --width=300
                fi
            else
                zenity --error --title="Erreur" --text="Cet utilisateur n'existe pas." --width=300
            fi
            ;;
        4)
            DEL_USER=$(zenity --entry --title="Suppression d'utilisateur" --text="Nom de l'utilisateur à supprimer :" --width=400)
            if [ -n "$DEL_USER" ] && [ "$DEL_USER" != "root" ]; then
                if zenity --question --text="Voulez-vous aussi supprimer son dossier personnel (/home/$DEL_USER) ?" --width=400; then
                    sudo userdel -r "$DEL_USER"
                else
                    sudo userdel "$DEL_USER"
                fi
                zenity --info --title="Supprimé" --text="Utilisateur $DEL_USER supprimé." --width=300
            fi
            ;;
        5)
            ROOT_PASS=$(zenity --password --title="Mot de passe Root" --text="Entrez le nouveau mot de passe pour Root :" --width=400)
            if [ -n "$ROOT_PASS" ]; then
                echo "root:$ROOT_PASS" | sudo chpasswd
                zenity --info --title="Succès" --text="Mot de passe root mis à jour !" --width=300
            fi
            ;;
    esac
done
