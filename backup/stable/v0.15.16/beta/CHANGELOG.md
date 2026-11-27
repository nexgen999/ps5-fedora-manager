# Journal de la bêta

## [0.16.0-beta5] — 2026-11-27

Premier démarrage réel sur la PS5 : deux blocages corrigés.

### Corrigé
- **Types Adwaita finaux.** `Adw.SwitchRow` et `Adw.PreferencesPage` sont
  `final` ; PyGObject 3.54 lève `RuntimeError: could not create new GType` à
  l'import. Les cinq pages concernées n'ont plus aucune sous-classe de widget :
  `services.service_row()`, `appimage.build()`, `kernel.build()`,
  `repos.build()`, `users.build()`, et `users.name_dialog()` remplacent les
  classes. `pages/__init__.py` pointe sur les nouvelles fabriques.
- **Contrôle anti-régression.** `tools/check.py` gagne le groupe `gtypes` :
  toute sous-classe de `Adw.*`/`Gtk.*` hors `Adw.Application`,
  `Adw.ApplicationWindow` et `Adw.Window` fait échouer le contrôle.

### Ajouté
- Documentation de la règle « pas de sous-classe de widget » dans
  `doc/fr/modules/pages.md` et `doc/en/modules/pages.md`.

## [0.16.0-beta4] — 2026-11-27

Quatrième étape : **couverture complète de la 0.15.11**. Toutes les options de la
version stable ont un équivalent.

### Greffons
- 107 greffons : catalogue Développement complet (14 entrées), `web-certbot`,
  `web-openssh`, `feature-print` (+ on/off/status), `feature-mobile`,
  `kernel-latest`, `lang-all`.
- Actions : 11 `maint-*`, 8 `ai-*` (Open WebUI, démarrage, logs, diagnostic,
  nettoyage), `fan-status`, `fan-restart`, `hw-check`, `hw-update-check`,
  `hw-uninstall`, `mesa-radv`, `mesa-summary`, `mesa-update`, `repos-refresh`,
  `repos-openh264`, `gaming-log`, `gaming-uninstall`, `fix-steam`,
  `deps-python-venv`, `deps-python-versions`, `deps-node-uninstall`,
  `services-bulk`, `update-uninstall`.
- `new_addon.py` accepte `--action`.

### Pages
- `library` : gestion des AppImage (installation par sélecteur de fichier,
  entrée de menu, désinstallation) + greffons de la section.
- `repos` : activation/désactivation d'un dépôt, rafraîchissement, ajout d'un
  fichier `.repo`.
- `kernel` : noyaux installés, noyau courant, `grubby --set-default`,
  suppression avec confirmation.
- `users` : création (`useradd -m` + `passwd` dans un terminal) et suppression
  (`userdel -r`), compte principal protégé.
- `easy` : quatre profils (recommandé, gaming, streaming, bureautique) et
  groupe de nettoyage.
- `logs` : bouton « Effacer ».
- `services` : action groupée « couper les daemons inutiles ».

### Documentation
- `doc/{fr,en}/couverture-0.15.11.md` : équivalences, seul paquet non porté
  (`xhost`) et différences assumées.
- 112 clés × 6 langues.

## [0.16.0-beta3] — 2026-11-27

Troisième étape : fiabilisation de la page Services, test d'imports, comparaison
automatique avec la 0.15.11.

### Page Services
- Un seul appel `systemctl show -p LoadState -p UnitFileState` par service :
  présence et état d'activation lus ensemble, plus de double interrogation.
- Annulation de la demande polkit (code 126) : l'interrupteur revient à sa
  position, aucun message d'erreur, sous-titre rechargé depuis le système.
- Services absents (`not-found`) et statiques (`static`, `indirect`, `alias`)
  neutralisés avec un sous-titre explicite.
- `run_background` transmet désormais un tuple de résultat variable, ce qui
  permet de distinguer une annulation d'une erreur.

### Test d'imports sans affichage
- `tools/import_check.py` importe les 25 modules : GTK réel quand `gi` est
  présent (PS5), `gi` factice sinon (machine de développement, CI). Il vérifie
  aussi que `Gtk 4.0` et `Adw 1` sont bien demandés.
- Intégré à `tools/check.py` : `imports : ok` fait partie des contrôles.

### Comparaison avec la stable
- `tools/compare_stable.py` lit `ps5_manager.py` par AST (sections,
  `build_page_*`, `DEV_CATALOG` / `WEB_CATALOG`, paquets des `dnf install`) et
  génère `doc/fr/comparaison-0.15.11.md` + `doc/en/comparison-0.15.11.md`.
- Analyse écrite : `doc/fr/manques-0.15.11.md` et `doc/en/gaps-0.15.11.md`
  (149 options lues, 51 greffons, ce qui reste à porter et les choix assumés).

### Greffons
- 51 greffons : ajout de `deps-fuse`, `deps-32bit`, `deps-tkinter`, `deps-node`,
  `mesa-tools` ; `hw-hwcon-gui` 1.0.1 déclare `python3-PyQt6`.
- 3 clés ajoutées (`services.subtitle`, `services.cancelled`, `services.static`),
  81 clés × 6 langues.

## [0.16.0-beta2] — 2026-11-27

Deuxième étape : la bêta couvre désormais toutes les sections de la stable.

### Greffons
- 46 scripts `.sh` (contre 10) répartis sur 24 sections : dépôts, codecs,
  FFmpeg, Easy Effects, presets JackHack96, Gamescope, GameMode, MangoHud,
  Steam, Lutris, Decky Loader, plugin PS5, Hardware Control, Mesa freeworld,
  Vulkan, noyau, alimentation, ventilateur, maintenance, mises à jour,
  langues système, serveur web, développement, IA, logithèque.
- Nouveau champ `action: yes` : les actions pures (nettoyage, `dnf upgrade`,
  vérification) n'affichent pas de pastille d'état.
- `run_script(root=…)` : un greffon `root: yes` passe par `pkexec` quand
  l'application n'est pas root.

### Pages
- `easy` (enchaînement recommandé), `services` (interrupteurs systemd),
  `ui_lang` (choix de langue avec couverture), `users` (comptes, lecture seule),
  `fedora` (version, noyau, `dnf check-update`).
- 78 clés de langue × 6 langues (fr, en, es, it, de, pt).

### Outils et documentation
- `tools/new_addon.py` : génère un greffon conforme.
- `tools/docs.py` : génère `doc/{fr,en}/addons.md` depuis l'index.
- Documentation complète FR/EN : architecture, un document par module,
  langues, environnements, outils, contribuer.
- `TASKS.md` : suivi fait / à faire.

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
