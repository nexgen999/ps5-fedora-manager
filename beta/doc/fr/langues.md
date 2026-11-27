# Langues

## Principe

L'interface ne contient aucune chaîne en dur : tout passe par `i18n.tr("clé")`.
Les traductions vivent dans `beta/langs/*.json`, un fichier par langue.

Langues livrées : `fr`, `en`, `es`, `it`, `de`, `pt` — 81 clés chacune.

## Ajouter une langue

```bash
cp beta/langs/en.json beta/langs/ja.json
python3 beta/tools/lang_status.py --missing ja   # clés à traduire
```

Renseigner `_meta` :

```json
"_meta": {"name": "日本語", "english": "Japanese", "direction": "ltr"}
```

`direction` vaut `ltr` ou `rtl` ; il est lu par `i18n.direction()`.

La langue apparaît ensuite dans le sélecteur et dans la page « Langue et
clavier », sans redémarrage de l'application.

## Vérifier

```bash
python3 beta/tools/lang_status.py     # couverture des 6 langues
python3 beta/tools/check.py           # toutes les langues ont les mêmes clés
```

Une clé absente n'est pas une erreur bloquante : `tr()` retombe sur l'anglais.

## Langues système

La section `lang` installe les paquets `langpacks-*` (fr, es, de, it, pt, ja).
Ce sont deux choses distinctes : l'interface (JSON) et les traductions du
système et des applications (RPM).
