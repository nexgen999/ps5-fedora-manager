#!/usr/bin/env bash
# Copie de restauration de la version stable avant modification :
# backup/stable/v<version>/ — uniquement les fichiers réels de la stable.
# <version> est lu dans version.txt ; refuse d'écraser une sauvegarde existante.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
version="$(tr -d '[:space:]' < "$root/version.txt")"
dest="$root/backup/stable/v$version"

FILES=(icons icon.png install.sh ps5_manager.py ps5-manager.desktop version.txt)

for item in "${FILES[@]}"; do
    if [ ! -e "$root/$item" ]; then
        echo "Fichier de la version stable introuvable : $item" >&2
        exit 1
    fi
done

if [ -e "$dest" ]; then
    echo "Sauvegarde déjà présente : backup/stable/v$version" >&2
    exit 1
fi

mkdir -p "$dest"
for item in "${FILES[@]}"; do
    cp -a "$root/$item" "$dest/"
done

echo "Sauvegarde créée : backup/stable/v$version ($(du -sh "$dest" | cut -f1))"
ls -1 "$dest"
