# Architecture

## Couches

```
run.py                  point d'entrée (python3 beta/run.py)
└── ps5m/
    ├── app.py          fenêtre, barre latérale, journal en direct
    ├── pages/          une page par besoin (générique ou dédiée)
    ├── catalog.py      lit les scripts, gère versions et mises à jour
    ├── i18n.py         charge langs/*.json, repli anglais
    ├── env/            ce qui change d'un bureau à l'autre
    ├── runner.py       exécute les scripts (PTY, pkexec)
    ├── system.py       état du système (rpm, chemins)
    ├── journal.py      journal persistant
    └── ui.py           pastilles, lignes, blocs de texte
```

Aucun module sous `ps5m/` n'importe GTK sauf `app.py`, `pages/*` et `ui.py` :
le catalogue, les langues, les environnements et le runner sont testables sans
affichage (c'est ce que fait `tools/selftest.py`).

## Flux d'une installation

1. La page liste les greffons de sa section (`catalog.load_local()`), triés par
   `catalog.order()` pour respecter les `needs`.
2. La pastille vient de `system.rpm_present()` et `system.path_present()` ;
   l'infobulle nomme ce qui manque.
3. Un clic ouvre la confirmation (`BetaWindow.show_install_confirm`).
4. `pages/addons._install` lance `runner.run_script(path, emit, root=addon.root)`.
   Si le greffon déclare `root: yes` et que l'application n'est pas root, la
   commande passe par `pkexec` : polkit demande le mot de passe une fois.
5. Chaque ligne de sortie va au journal (`journal.write`) et à la fenêtre de log.
6. À la fin, `refresh_addons_state()` relit les scripts, donc les pastilles.

## Flux d'une mise à jour de greffon

1. Au lancement, un fil appelle `catalog.fetch_index()` : `index.json` du dépôt.
2. `catalog.pending()` compare les versions (`1.10 > 1.9`) et renvoie seulement
   les scripts plus récents.
3. Le bouton de la barre latérale appelle `catalog.refresh()` : téléchargement
   du script, vérification du SHA-256 publié, écriture atomique.
4. Un script déjà à jour n'est jamais réécrit : une modification locale faite
   sans incrémenter la version est conservée.

## Arborescence

```
beta/
├── run.py · VERSION · README.md · CHANGELOG.md · TASKS.md
├── ps5m/        le code (voir modules/)
├── addons/      un .sh par option + index.json généré
├── langs/       un .json par langue
├── doc/fr/      cette documentation
├── doc/en/      la même, en anglais
└── tools/       build_catalog, check, lang_status, selftest, docs, new_addon
```

## Garanties

- Rien hors de `beta/` n'est lu ni écrit par l'application.
- Aucun `sudo` implicite : uniquement `pkexec` pour les greffons `root: yes`.
- Le mode `--check` ne modifie jamais le système (il ne fait que lire).
