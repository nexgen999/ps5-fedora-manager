#!/usr/bin/env bash
# Copie complète du projet avant modification : backup/stable/v<version>/
# <version> est lu dans version.txt ; refuse d'écraser une sauvegarde existante.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
version="$(tr -d '[:space:]' < "$root/version.txt")"
dest="$root/backup/stable/v$version"

if [ -e "$dest" ]; then
    echo "Sauvegarde déjà présente : backup/stable/v$version" >&2
    exit 1
fi

mkdir -p "$dest"
rsync -a --exclude .git --exclude backup --exclude __pycache__ "$root/" "$dest/"
echo "Sauvegarde créée : backup/stable/v$version ($(du -sh "$dest" | cut -f1))"
