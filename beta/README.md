# PS5 Fedora Manager — édition bêta modulaire

Tout ce dossier est **indépendant de la version stable** : `install.sh` ne le
copie pas, `ps5_manager.py` ne l'importe pas, et rien ici ne modifie
`/opt/ps5-manager`. La stable reste en 0.15.x et continue de fonctionner.

```bash
python3 beta/run.py                 # interface (français par défaut)
PS5M_LANG=en python3 beta/run.py    # langue de départ forcée
```

## Documentation

| FR | EN |
|---|---|
| [doc/fr/index.md](doc/fr/index.md) | [doc/en/index.md](doc/en/index.md) |
| [architecture](doc/fr/architecture.md) | [architecture](doc/en/architecture.md) |
| [un document par module](doc/fr/modules/) | [one document per module](doc/en/modules/) |
| [référence des greffons (générée)](doc/fr/addons.md) | [addon reference (generated)](doc/en/addons.md) |
| [langues](doc/fr/langues.md) | [languages](doc/en/languages.md) |
| [environnements](doc/fr/environnements.md) | [environments](doc/en/environments.md) |
| [outils](doc/fr/outils.md) | [tools](doc/en/tools.md) |
| [contribuer](doc/fr/contribuer.md) | [contributing](doc/en/contributing.md) |
| [ce qui manque](doc/fr/manques-0.15.11.md) | [what is missing](doc/en/gaps-0.15.11.md) |
| [comparaison complète](doc/fr/comparaison-0.15.11.md) | [full comparison](doc/en/comparison-0.15.11.md) |
| [TASKS.md](TASKS.md) — fait / à faire | [TASKS.md](TASKS.md) |

## Trois principes

1. **Une option = un script.** `addons/*.sh`, versionné, avec `--check`.
2. **Une langue = un fichier.** `langs/xx.json`, aucun code à écrire.
3. **Un environnement = un module.** `ps5m/env/`, seulement ce qui diffère.

## Architecture

```
beta/
├── run.py · VERSION · TASKS.md · CHANGELOG.md
├── ps5m/
│   ├── app.py        fenêtre, barre latérale, log en direct
│   ├── catalog.py    en-têtes, versions, mises à jour SHA-256
│   ├── i18n.py       langues JSON + repli anglais
│   ├── env/          gnome, kde, cinnamon, budgie, generic
│   ├── pages/        sections génériques + pages dédiées
│   ├── runner.py     exécution PTY, pkexec
│   ├── system.py     état rpm / chemins
│   ├── journal.py · ui.py
├── addons/           un .sh par option + index.json généré
├── langs/            6 langues, 81 clés
├── doc/fr · doc/en/  documentation
└── tools/            build_catalog, check, lang_status, selftest, docs, new_addon
```

## Sections

24 sections, 51 greffons. Les sections sans page dédiée utilisent la page
générique (une ligne par greffon, pastille, confirmation, installation) :

`library` `aidev` `dev` `websrv` `deps` `repos` `gaming` `audio` `video`
`hardware` `mesa` `kernel` `power` `fan` `maint` `update` `lang` `features`
`fix`

Pages dédiées : `easy` (enchaînement recommandé), `services` (interrupteurs
systemd), `ui_lang` (choix de langue), `users` (comptes, lecture seule),
`fedora` (version, noyau, `dnf check-update`), plus Journal et À propos.

## Ajouter une option

```bash
python3 beta/tools/new_addon.py --id app-htop --section library \
  --packages "htop" --title-en "htop" --title-fr "htop" \
  --desc-en "Process viewer." --desc-fr "Visionneuse de processus."
python3 beta/tools/build_catalog.py
python3 beta/tools/docs.py
python3 beta/tools/check.py
```

En-tête complet et contrat `--check` : [doc/fr/addons.md](doc/fr/addons.md).

## Contrôles

```bash
python3 beta/tools/build_catalog.py --check   # index à jour
python3 beta/tools/check.py                   # greffons + catalogue + langues
python3 beta/tools/selftest.py                # logique, sans GTK
python3 beta/tools/lang_status.py             # couverture des langues
python3 beta/tools/docs.py                    # doc des greffons
python3 beta/tools/import_check.py            # imports (GTK réel ou factice)
python3 beta/tools/compare_stable.py          # écart avec la 0.15.11
```

## Limites connues

- L'interface n'est pas testée dans l'environnement de développement (pas de
  GTK) : à valider sur la PS5.
- Le mode non-root n'est pas proposé comme un mode global : chaque greffon
  déclare `root: yes/no`.
- Les notes de version de la bêta sont dans [CHANGELOG.md](CHANGELOG.md).
