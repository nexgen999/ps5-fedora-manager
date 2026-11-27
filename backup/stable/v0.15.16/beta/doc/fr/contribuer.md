# Contribuer à la bêta

## Ajouter une option

1. `tools/new_addon.py` (ou copier un script voisin).
2. Renseigner l'en-tête : `id`, `version`, `section`, `title`/`title_fr`,
   `desc`/`desc_fr`, `packages` ou `check_paths` (ou `action: yes`), `needs`,
   `root`.
3. Implémenter `--check` (0 = installé) et l'installation.
4. `python3 beta/tools/build_catalog.py && python3 beta/tools/docs.py`
5. `python3 beta/tools/check.py && python3 beta/tools/selftest.py`

## Modifier une option existante

Modifier le script, **incrémenter `#@ version:`**, régénérer l'index et les
docs. Sans incrément, les installations existantes ne reçoivent pas la
correction.

## Ajouter une page

Voir [modules/pages.md](modules/pages.md).

## Ajouter une langue

Voir [langues.md](langues.md).

## Avant de livrer

```bash
python3 -m py_compile $(find beta -name '*.py')
for f in beta/addons/*.sh; do bash -n "$f"; done
python3 beta/tools/build_catalog.py --check
python3 beta/tools/check.py          # inclut le test d'imports
python3 beta/tools/compare_stable.py  # ce qui manque encore
python3 beta/tools/selftest.py
```

## Ce qu'il ne faut pas faire

- Modifier un fichier hors de `beta/` : la version stable est en production.
- Lancer une commande depuis le fil GTK : passer par `run_task`.
- Écrire du texte utilisateur en markup Pango.
- Mettre `root: yes` par défaut : seulement quand c'est nécessaire.
