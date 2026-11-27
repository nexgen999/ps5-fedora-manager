# PS5 Fedora Manager — édition bêta modulaire

Tout ce dossier est **indépendant de la version stable** : `install.sh` ne le
copie pas, `ps5_manager.py` ne l'importe pas, et rien ici ne modifie `/opt/ps5-manager`.
On prépare l'avenir sans toucher à ce qui fonctionne chez les utilisateurs.

Lancer la bêta (GTK4 + Libadwaita requis, comme la version stable) :

```bash
python3 beta/run.py            # langue française par défaut
PS5M_LANG=en python3 beta/run.py
```

## Architecture

```
beta/
├── run.py                 point d'entrée (ajoute beta/ au PYTHONPATH)
├── VERSION                version de l'édition bêta
├── ps5m/
│   ├── app.py             fenêtre, barre latérale, log en direct
│   ├── i18n.py            paquets de langue JSON + repli anglais
│   ├── catalog.py         greffons : en-têtes, versions, mises à jour
│   ├── system.py          état du système (rpm, chemins)
│   ├── runner.py          exécution des scripts (PTY, streaming)
│   ├── journal.py         journal fichier
│   ├── ui.py              pastilles, lignes, blocs de texte
│   ├── env/               environnements de bureau (gnome, kde, cinnamon, budgie…)
│   └── pages/             une page = un module (journal, à propos, sections)
├── addons/                un script .sh par option + index.json
├── langs/                 une langue = un fichier JSON
└── tools/                 build_catalog.py, lang_status.py, check.py
```

## 1. Ajouter ou modifier une option

Une option = **un script autonome** dans `addons/`, avec un en-tête de métadonnées :

```bash
#!/usr/bin/env bash
#@ id: mon-option              # identifiant unique, jamais réutilisé
#@ version: 1.0.0              # à incrémenter à chaque modification
#@ section: audio              # audio | video | repos | gaming | hardware | deps
#@ icon: audio-volume-high-symbolic
#@ title: My option            # anglais (repli)
#@ title_fr: Mon option
#@ desc: What it does.
#@ desc_fr: Ce que ça fait.
#@ packages: paquet1 paquet2   # état lu par rpm (facultatif)
#@ check_paths: ~/dossier      # chemins vérifiés, globs acceptés (facultatif)
#@ needs: autre-id             # greffons à installer d'abord (facultatif)
#@ root: yes                   # no = s'exécute avec les droits du compte de bureau
set -euo pipefail

if [ "${1:-}" = "--check" ]; then      # contrat : 0 = installé
    rpm -q paquet1 >/dev/null 2>&1 && exit 0
    exit 1
fi

dnf install -y paquet1 paquet2
```

Puis :

```bash
python3 beta/tools/build_catalog.py     # met à jour addons/index.json
python3 beta/tools/check.py             # valide en-têtes, versions, bash -n, langues
```

L'application relit `index.json` : elle ne télécharge que les scripts dont
`version` a augmenté (`catalog.refresh()`, empreinte SHA-256 vérifiée).
Modifier une commande = éditer ce seul fichier, incrémenter `version`, relancer
`build_catalog.py` et pousser : les utilisateurs reçoivent la mise à jour sans
réinstaller le manager.

## 2. Ajouter une langue

```bash
cp beta/langs/en.json beta/langs/nl.json     # traduire les valeurs, garder les clés
python3 beta/tools/lang_status.py            # couverture, clés manquantes
python3 beta/tools/lang_status.py --missing nl
```

Aucun code à toucher : la langue apparaît dans le menu dès que le fichier existe.
Une clé absente retombe sur l'anglais, une langue incomplète reste utilisable.
Le champ `_meta.direction` permet un affichage `rtl` (arabe, hébreu).

## 3. Ajouter un environnement de bureau

```python
# beta/ps5m/env/mate.py
class Mate(Environment):
    def __init__(self) -> None:
        super().__init__(id="mate", name="MATE", terminal=("mate-terminal", "--"))
```

Déclarer la classe dans `beta/ps5m/env/detect.py` (`FACTORIES` + `_TOKENS`).
Les pages n'utilisent que `Environment` (`open_terminal`, `set_theme_commands`,
`set_accent_commands`, `supports`), jamais le nom d'un bureau.

## 4. Ajouter une page

Créer `beta/ps5m/pages/xxx.py` avec `build(win) -> Gtk.Widget`, puis l'ajouter à
`STATIC` dans `pages/__init__.py`, ou créer une nouvelle section en ajoutant un
script avec `#@ section: xxx` (la page est générée automatiquement).

## 5. Contrôles avant de pousser

```bash
python3 beta/tools/check.py             # greffons + catalogue + langues
python3 beta/tools/selftest.py          # 37 vérifications de logique, sans GTK
python3 beta/tools/build_catalog.py --check
python3 beta/tools/lang_status.py
bash -n beta/addons/*.sh
python3 -m py_compile $(find beta -name '*.py')
```

## Limites assumées de cette première étape

- Toutes les pages de la version stable ne sont pas encore portées : la bêta
  fournit le socle (catalogue, journal, à propos) et les greffons audio/vidéo,
  dépôts, gaming et matériel, qui servent de modèle pour le reste.
- L'interface n'a pas de mode non-root dédié : les scripts `root: no` savent
  redescendre vers `$SUDO_USER`, comme la version stable.
- Rien n'est installé ni publié : cette édition s'exécute depuis le dépôt.
