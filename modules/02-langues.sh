#!/bin/bash
LANG_CHOICE=$(zenity --list --title="Langue & Clavier" --text="Choisissez la langue du système :" --width=450 --height=300 \
    --column="Code" --column="Langue" \
    "fr_FR.UTF-8" "Français (France)" \
    "en_US.UTF-8" "English (US)")

if [ -n "$LANG_CHOICE" ]; then
    sudo localectl set-locale LANG="$LANG_CHOICE"
    zenity --info --title="Succès" --text="Langue définie sur $LANG_CHOICE. Redémarrez la session pour appliquer." --width=300
fi
