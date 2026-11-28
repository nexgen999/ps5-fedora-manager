# Sauvegardes de la version stable

Une copie de restauration est conservée ici avant chaque modification de la
version stable, dans `backup/stable/v<version>/` : le numéro est celui de
`version.txt` au moment de la copie.

```bash
./tools/backup_stable.sh          # crée backup/stable/v<version>/
```

Contenu : uniquement les fichiers réels de la version stable, ceux qu'il faut
pour restaurer l'application — `ps5_manager.py`, `version.txt`, `install.sh`,
`ps5-manager.desktop`, `icon.png` et le dossier `icons/`. Ni `beta/`, ni `doc/`,
ni les notes de version.

Restauration :

```bash
cp -a backup/stable/v0.15.17/. /opt/ps5-manager/
```

| Sauvegarde | Contenu |
|---|---|
| `v0.15.16` | dernière version avant la page d'accueil « PS5 Fedora Manager » |
| `v0.15.17` | version 0.15.17 avant le déplacement de « Langue de l'interface » |
| `v0.15.18` | version 0.15.18 avant la correction du mode Gamescope sous Budgie |
| `v0.15.19` | version 0.15.19 avant la réparation de la fenêtre « Système » |
| `v0.15.20` | version 0.15.20 avant la prise en charge de Steam en Flatpak |
| `v0.15.21` | version 0.15.21 avant le bus D-Bus du Flatpak et le garde-fou écran noir |
