# Journal de la bêta

## [0.16.0-beta1] — 2026-11-27

Première étape de l'architecture modulaire, entièrement sous `beta/`. La version
stable (`ps5_manager.py`, 0.15.x) n'est ni modifiée ni remplacée.

### Architecture
- Package `ps5m/` : `app`, `i18n`, `catalog`, `system`, `runner`, `journal`, `ui`,
  `env/` (gnome, kde, cinnamon, budgie, generic) et `pages/` (journal, à propos,
  sections générées depuis le catalogue).
- `addons/` : **un script `.sh` autonome par option** (10 greffons livrés), chacun
  avec `id`, `version`, `section`, `packages`, `needs` et `check_paths` dans un
  en-tête `#@`.
- `addons/index.json` : catalogue publié, régénéré par `tools/build_catalog.py`
  (version + empreinte SHA-256 par greffon).
- `langs/` : une langue = un fichier JSON (fr, en, es, it, de, pt livrés,
  39 clés identiques). Une nouvelle langue est prise en compte sans code.
- `tools/` : `build_catalog.py`, `check.py`, `lang_status.py`, `selftest.py`.

### Mises à jour
- `catalog.refresh()` télécharge uniquement les scripts dont la version a
  augmenté, vérifie le SHA-256 et écrit de façon atomique ; un bouton de la
  barre latérale applique la mise à jour, et un contrôle au lancement signale
  les greffons en retard sans bloquer l'application.

### Environnements
- Un module par bureau, avec seulement ce qui diffère : terminal, gestionnaire
  de fichiers, commandes de thème et d'accentuation, variables de session.
- `Environment.supports()` permet à l'interface de masquer ce qu'un bureau ne
  sait pas faire (accent sous KDE, par exemple).

### Contrôles
- `tools/check.py` : en-têtes, identifiants uniques, `needs` valides, `bash -n`,
  index à jour, langues complètes.
- `tools/selftest.py` : 37 vérifications (versions, dépendances, index, langues,
  environnements, chemins, journal).

### Limites de cette étape
- Toutes les pages de la version stable ne sont pas encore portées.
- Pas de mode non-root dédié dans l'interface (les scripts `root: no` gèrent la
  descente de privilèges).
- Interface non testée ici (pas de GTK dans l'environnement de développement).
