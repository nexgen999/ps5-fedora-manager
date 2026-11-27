# Ce qui manque encore par rapport à la 0.15.11

Comparaison faite par `tools/compare_stable.py` : lecture statique de
`ps5_manager.py` (sections, fonctions `build_page_*`, catalogues `DEV_CATALOG` /
`WEB_CATALOG`, paquets des `dnf install`), puis rapprochement avec les 51
greffons de `addons/index.json`. Les tableaux complets, option par option, sont
dans [comparaison-0.15.11.md](comparaison-0.15.11.md).

Résultat brut : **149 options** lues dans la stable, **51 greffons**,
**79 paquets** sans équivalent — dont 75 dans la seule page Développement
(catalogue groupé) et 4 dans Serveur web.

## 1. Installations encore absentes

### Développement (`dev`)

La stable propose un catalogue de 20 entrées. La bêta n'a que `dev-git-tools` et
`dev-python`. Manquent, par ordre d'intérêt :

| Entrée stable | Paquets | Proposition |
|---|---|---|
| Socle de compilation | gcc, gcc-c++, make, cmake, meson, ninja-build, pkgconf, autoconf, automake, libtool, patch, rpmdevtools, rpmlint | un greffon `dev-build` (le `deps-build` actuel est un sous-ensemble) |
| Python + GTK4 / Libadwaita | python3-devel, python3-pip, python3-virtualenv, python3-pytest, gtk4-devel, libadwaita-devel, blueprint-compiler, devhelp… | `dev-python-gtk` |
| Conteneurs | podman, podman-docker, buildah, skopeo, distrobox, toolbox | `dev-containers` |
| Virtualisation | qemu-kvm, libvirt, virt-install, virt-manager, virt-viewer, gnome-boxes, edk2-ovmf, swtpm | `dev-virt` |
| Rust / Cargo | rust, cargo, rustfmt, clippy | `dev-rust` |
| Recherche & navigation | ripgrep, fd-find, bat, eza, fzf, zoxide | `dev-cli-search` |
| Git & plateformes | git, git-lfs, gh, glab, lazygit, git-delta | compléter `dev-git-tools` (1.1.0) |
| Terminal | tmux, zellij | `dev-terminal` |
| Diagnostic | lsof, strace, ltrace, sysstat, perf, ncdu, duf, hyperfine | `dev-diagnostic` |
| Debug & profilage | gdb, lldb, valgrind, heaptrack, sysprof | `dev-debug` |
| Qualité Python | uv, ruff, mypy, pre-commit | `dev-python-quality` |
| Données & HTTP | jq, yq, httpie, sqlite, sqlitebrowser | `dev-data` |
| Automatisation | just, direnv, shellcheck | `dev-automation` |
| Éditeurs terminal | neovim, helix | `dev-editors` |
| Node.js / npm | nodejs, npm | fait (`deps-node`) mais rangé dans Dépendances |

Entrées sans liste de paquets, donc impossibles à convertir en greffon
« dnf install » : Docker Engine (dépôt docker-ce), VSCodium (dépôt + panneau),
GitHub Desktop, Forgejo (serveur + service).

### Serveur web (`websrv`)

- `certbot`, `python3-certbot-apache`, `python3-certbot-nginx` (HTTPS Let's Encrypt) → `web-certbot`.
- `openssh-server` (accès distant) → `web-openssh`.
- PHP + extensions, MySQL community, phpMyAdmin, Adminer, Webmin, pare-feu web :
  installés par des scripts dédiés (dépôts, configuration FastCGI) et non par une
  simple liste de paquets — à porter en greffons `install`/`remove` avec `--check`.

## 2. Actions qui ne sont pas des installations

Ces lignes de la stable ne peuvent pas devenir un `dnf install` : il leur faut
une page dédiée (comme `services` ou `ui_lang`) ou un greffon `action: yes`.

| Section | Option stable | État dans la bêta |
|---|---|---|
| logs | journal en direct, session, anciens journaux, effacer | partiel : page Journal + fenêtre de log ; « effacer » absent |
| library | AppImage : installer, mettre à jour, désinstaller ; recherche Flathub | absent |
| aidev | Open WebUI, VSCodium, Freebuff, tout démarrer/arrêter, `podman ps/logs`, modèles Ollama, diagnostic RAM/GPU, nettoyage Podman | absent (seuls `ai-ollama` et `ai-python` existent) |
| easy | profils, désinstallation de composants, nettoyage des fichiers du manager, purge du cache dnf | partiel : enchaînement recommandé seulement |
| services | « couper les daemons inutiles » (action groupée) | absent (interrupteurs unité par unité) |
| deps | créer un venv, afficher les versions, changer de version majeure Node, désinstaller Node | absent |
| gaming | désinstaller, voir le journal | absent |
| features | partage mobile, imprimantes (installer, activer, couper, sockets, statut) | absent (Toolbox et Cockpit seulement) |
| update | désinstaller le manager | absent (mise à jour du système et du dépôt git : fait) |
| lang | voir les langues, installer, « tout installer » | partiel : 6 langpacks, pas de « tout » |
| repos | lister, rafraîchir, OpenH264, ajouter un dépôt, activer/désactiver, supprimer (dnf et Flatpak) | partiel : 5 dépôts + codecs, pas de gestion |
| users | ajouter, supprimer, passer root | **assumé absent** : opérations destructrices, hors périmètre d'une bêta |
| fedora | paquets, système, langues, métadonnées | partiel : page d'informations + `dnf check-update` |
| maint | tout, cache, autoremove, journal, /tmp, vignettes, base desktop, polices, vieux noyaux, disque, menu KDE | partiel : 3 actions (cache, Flatpak, TRIM) |
| power | activer / désactiver le profil complet | partiel : `power-profiles` et `power-tlp` |
| fan | statut, relancer le service, installer les outils | partiel : `fan-tools` (pas de statut ni de relance) |
| hw | vérifier le matériel, vérifier les mises à jour, désinstaller | partiel : 3 greffons d'installation |
| mesa | mettre à jour, activer RADV, résumé | partiel : freeworld, Vulkan, outils |
| kernel | choisir, démarrer sur, supprimer un noyau | **assumé absent** : risque de machine non démarrable |
| fix | réparation Steam | absent (`fix-dnf` seulement) |
| ui_lang | (aucune option : la page est faite d'interrupteurs) | **fait** dans la bêta |

## 3. Choix assumés

- **Comptes** (ajout/suppression/root), **noyaux** (choix/suppression) et
  **désinstallation du manager** : volontairement hors bêta tant que la
  validation matérielle n'est pas faite.
- **`xhost`** n'est pas porté : la bêta n'élève jamais l'interface entière
  (`pkexec` uniquement pour un greffon `root: yes`), donc l'autorisation X11 de
  root est inutile.
- Les entrées de catalogue qui compilent ou configurent (Docker, VSCodium,
  phpMyAdmin, Webmin, Forgejo) demandent un vrai script `install/remove`, pas une
  liste de paquets : elles sont listées ci-dessus plutôt que générées à moitié.

## 4. Ordre suggéré pour finir

1. `dev-*` : 13 greffons générés depuis le catalogue (le plus gros bloc, 75 paquets).
2. `web-certbot`, `web-openssh`, puis PHP/MySQL/phpMyAdmin en `install/remove`.
3. Pages dédiées : `maint` (10 actions), `repos` (gestion des dépôts), `fan`
   (statut + relance), `hw` (vérifier/désinstaller).
4. `aidev` : la pile Ollama + Open WebUI en `action: yes` (démarrer/arrêter/logs).
5. `library` : flux AppImage, puis `fix-steam`.
