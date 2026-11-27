# Sauvegardes de la version stable

Une copie complète du projet est conservée ici avant chaque modification de la
version stable, dans `backup/stable/v<version>/` : le numéro est celui de
`version.txt` au moment de la copie.

```bash
./tools/backup_stable.sh          # crée backup/stable/v<version>/
```

Contenu : tout le dépôt (code, `beta/`, documentation, ressources) sauf `.git/`
et `backup/`. Restauration :

```bash
rsync -a backup/stable/v0.15.16/ ./
```

Les sauvegardes sont versionnées dans Git : elles sont donc aussi sur GitHub,
même si le dossier de travail est perdu.

| Sauvegarde | Contenu |
|---|---|
| `v0.15.16` | dernière version avant la page d'accueil « PS5 Fedora Manager » (0.15.17) |
