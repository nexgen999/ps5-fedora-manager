#!/bin/bash
# ==============================================================================
# Module 02 : Gestion des langues et du clavier (Zenity)
# ==============================================================================

while true; do
    ACTION=\$(zenity --list --title="Gestion des Langues" --text="Choisissez une option :" --width=550 --height=300 \
        --column="ID" --column="Action" \
        "1" "Voir les packs installés & langues actuelles" \
        "2" "Installer un nouveau pack de langue" \
        "3" "Configurer la langue système & redémarrer la session" \
        "0" "Retour")

    [ \$? -ne 0 ] || [ "$ACTION" = "0" ] \vert{}\vert{} [ -z "$ACTION" ] && break

    case "\$ACTION" in
        1)
            LOCALES=\$(localectl status)
            zenity --info --title="Langues actuelles" --text="\$LOCALES" --width=500 --height=300
            ;;
        2)
            LANG_CODE=\$(zenity --entry --title="Installer un pack de langue" --text="Entrez le code de la langue (ex: es, de, it, ja, pt_BR) :" --width=400)
            if [ -n "\$LANG_CODE" ]; then
                zenity --info --text="Installation du pack pour '\$LANG_CODE' en cours..." --width=300
                sudo dnf install -y "langpacks-$LANG_CODE" "firefox-langpacks-$LANG_CODE" || true
                zenity --info --title="Succès" --text="Pack de langue pour '\$LANG_CODE' installé !" --width=350
            fi
            ;;
        3)
            TARGET_LANG=\$(zenity --entry --title="Configurer la locale" --text="Entrez la locale complète à appliquer (ex: fr_FR.UTF-8, en_US.UTF-8) :" --entry-text="fr_FR.UTF-8" --width=450)
            if [ -n "\$TARGET_LANG" ]; then
                sudo localectl set-locale LANG="\$TARGET_LANG"
                zenity --info --title="Configuration enregistrée" --text="La langue a été définie sur \$TARGET_LANG.\n\nLa session va se fermer pour appliquer les changements." --width=450
                pkill -u "\$(whoami)" || loginctl terminate-user "\$(whoami)"
            fi
            ;;
    esac
done
