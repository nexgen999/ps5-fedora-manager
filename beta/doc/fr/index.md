# Documentation de la bêta (français)

La bêta vit entièrement dans `beta/`. Elle ne modifie ni `ps5_manager.py`, ni
`install.sh`, ni `version.txt` : la version stable continue de fonctionner
pendant que cette édition est développée.

## Lancer

```bash
cd ps5-fedora-manager
python3 beta/run.py            # interface
PS5M_LANG=en python3 beta/run.py   # forcer la langue de départ
```

## Par où commencer

| Document | Contenu |
|---|---|
| [architecture.md](architecture.md) | couches, flux d'une installation, arborescence |
| [modules/](modules/) | un document par module Python |
| [addons.md](addons.md) | référence **générée** de tous les greffons |
| [langues.md](langues.md) | ajouter ou corriger une langue |
| [environnements.md](environnements.md) | GNOME, KDE, Cinnamon, Budgie, générique |
| [outils.md](outils.md) | scripts de contrôle et de génération |
| [contribuer.md](contribuer.md) | ajouter une option, une page, un test |
| [couverture](couverture-0.15.11.md) | équivalences avec la 0.15.11, différences assumées |
| [comparaison](comparaison-0.15.11.md) | tableaux générés, option par option |
| [../TASKS.md](../TASKS.md) | ce qui est fait, ce qui reste |

## Trois règles

1. **La stable ne bouge pas.** Aucun fichier hors de `beta/` n'est modifié.
2. **Une option = un script.** `beta/addons/*.sh`, versionné, avec `--check`.
3. **Une langue = un fichier.** `beta/langs/xx.json`, sans code à écrire.
