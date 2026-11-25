# Changelog

Historique des versions de **PS5 Fedora Manager** (application GTK4 / Libadwaita pour Fedora sur PS5).

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; le projet n'utilise pas encore de tags Git, les versions correspondent à `APP_VERSION` dans `ps5_manager.py`.

Version anglaise : [CHANGELOG_en.md](CHANGELOG_en.md)

## [0.6] — 2026-11-25

### Ajouté
- **Compatibilité GNOME / KDE Plasma / Cinnamon / Budgie** : détection automatique du bureau (variables de session, processus de l'utilisateur, `loginctl`) et du gestionnaire de connexion (GDM / SDDM / LightDM), avec adaptation des commandes concernées.
- **Setup 1 clic adapté au bureau** : l'étape Alimentation applique les commandes du bureau détecté, l'Extension Manager est retiré du plan hors GNOME (28 éléments au lieu de 29) et l'étape Gamescope suit le gestionnaire de connexion ; le journal du setup commence par une ligne « Environnement détecté » (bureau · gestionnaire de connexion · session).

### Modifié
- **Alimentation par bureau** : veille de l'écran et veille complète via `gsettings` (GNOME, Cinnamon, Budgie) ou `kwriteconfig6` + Powerdevil (KDE Plasma), rechargement de Powerdevil inclus.
- **Éléments propres à GNOME** : l'Extension Manager disparaît de la Logithèque et du setup recommandé (28 éléments hors GNOME) ; la gestion mobile utilise KDE Connect (KDE), Nemo (Cinnamon) ou Nautilus (GNOME / Budgie) ; les imprimantes ajoutent `print-manager` sous KDE.
- **Gamescope multi-bureau** : auto-connexion écrite pour GDM, SDDM ou LightDM et bascule vers la session du bureau détecté (`gnome`, `plasma`, `cinnamon`, `budgie-desktop`) au lieu de « gnome » codé en dur.
- `APP_VERSION` passe à `0.6`, notes de version FR/EN de la boîte « À propos » mises à jour.

### Corrigé
- **Notes de version (« Quoi de neuf »)** : plus aucune balise `<b>` dans le texte, et nouveau filtre `_safe_release_notes()` qui ne conserve que `p` / `ul` / `ol` / `li` / `a` — Libadwaita refusait l'analyse et affichait « Impossible d'analyser les notes de version : Unexpected element 'b' » à la place du texte.
- **Titres de groupes** : `pref_group()` n'échappe plus le markup, car `Adw.PreferencesGroup` affiche titre et description en texte brut ; `IA &amp; Développeur` redevient `IA & Développeur` (idem `Imprimantes &amp; scanners`, `Langues &amp; clavier`, `Suivi en direct &amp; historique`, `Système &amp; Utilitaires`).

## [0.5] — 2026-11-22

### Ajouté
- **Choix de la langue au premier lancement** : la boîte « Choose your language · Choisissez votre langue » (texte bilingue, boutons *English* / *Français*) s'affiche avant le message de setup, pour que chacun comprenne les deux options ; l'interface bascule immédiatement dans la langue choisie.
- **Boîte de bienvenue au premier lancement** : propose le **setup recommandé en 1 clic** ou la configuration manuelle (fermeture de la boîte). Le choix est mémorisé dans `/etc/ps5-manager/setup-welcome-done`, donc la boîte ne réapparaît plus ensuite.
- **Setup recommandé** en 9 étapes et 29 éléments : alimentation (veille système, écran, veille complète), ventilateur (PS5 Linux Tools, `ps5fan`, `ps5boost`), Hardware Control, Mesa / Vulkan, dépôts (RPM Fusion, Flatpak/Flathub, cache), dépendances supplémentaires (fuse, pilotes 32 bits Steam, Python 3 + pip, environnement virtuel `my_project`, Tkinter, Node.js/npm, mise à jour Fedora), logithèque (Bazaar, GNOME Extension Manager, Steam, Heroic, ProtonUp-Qt, Decky Loader, Universe, AppImage Pool, Opera en Flatpak `com.opera.Opera`), plugin Hardware Control et Gaming Mode (Gamescope).
- **Fenêtre de suivi du setup** : liste des éléments à gauche avec état en direct (`○` en attente, `●` en cours, `✔` validé, `✖` en échec), journal complet des commandes à droite et barre de progression. Un élément en échec n'interrompt pas les suivants.
- **Reboot proposé à la fin du setup** : la fenêtre de suivi se ferme et une boîte propose le redémarrage immédiat (`systemctl reboot`) ou plus tard.
- **Menu principal (burger)** : nouvelle entrée « Effectuer le setup recommandé » pour relancer le setup à tout moment, avec confirmation.
- Documentation [`dev_setup.md`](dev_setup.md) : configuration de référence, commandes exactes et correspondance avec les sections de l'application.

### Modifié
- **Langues & clavier** : `gsettings org.gnome.system.locale` n'est appliqué que sous GNOME / Budgie, et la déconnexion proposée utilise la commande du bureau détecté (`gnome-session-quit`, `cinnamon-session-quit`, `qdbus … org.kde.Shutdown.logout`) avec repli `loginctl terminate-user` — plus de `gnome-session-quit` codé en dur.
- **Couleur d'accentuation GNOME** : le groupe est masqué et le sondage dconf toutes les 3 s est désactivé hors GNOME.
- **Kernel PS5** : section vérifiée sans aucune dépendance au bureau ni au gestionnaire de connexion (`dnf`/`rpm`, `depmod`, `dracut`, copie sur `/boot/efi`) — comportement identique sur les 4 environnements.
- **Fenêtre de suivi du setup élargie** (1320 × 800 au lieu de 1120 × 740) et colonne de gauche plus large, pour une lecture plus confortable de la liste et du journal.
- `APP_VERSION` passe à `0.5`, notes de version FR/EN de la boîte « À propos » mises à jour.

## [0.4] — 2026-11-22

### Ajouté
- **Nouvelle catégorie « Add Fedora Feature »** dans la barre latérale (groupe 1, juste après « Gaming Mode ») : regroupe l'activation de fonctionnalités Fedora en une seule action par fonctionnalité.
- **Gestion mobile (Mobile Management)** : installation en une commande de GSConnect (téléphone Android en Wi-Fi), du support USB MTP / SSHFS, des intégrations Nautilus et d'ADB / Fastboot — `gnome-shell-extension-gsconnect gvfs-mtp fuse-sshfs nautilus-python android-tools`.
- **Imprimantes & scanners** : installation de la gestion complète des imprimantes (CUPS, `cups-filters`, `system-config-printer`, pilotes HP `hplip`, Brother / Epson `gutenprint-cups` et `splix`, génériques, découverte réseau) et des scanners (SANE, pilotes `sane-backends-drivers-scanners`, `libsane-hpaio`, application GNOME `simple-scan`) — `cups cups-filters system-config-printer hplip gutenprint-cups splix sane-backends sane-backends-drivers-scanners libsane-hpaio simple-scan`.
- Actions CUPS : activation (`systemctl enable --now cups`), coupure et désactivation (`systemctl disable --now cups`) avec confirmation, désactivation des sockets d'activation automatique (`systemctl disable --now cups.socket cups.path`) avec confirmation, et affichage de `systemctl status cups`.

### Modifié
- `APP_VERSION` passe à `0.4`, notes de version FR/EN de la boîte « À propos » mises à jour (19 sections).

## [0.3] — 2026-11-22

### Ajouté
- **Kernel PS5 — installation d'un kernel précis** : nouvelle entrée « Installer un kernel précis (toutes les releases) » qui liste les releases de [`ps5-linux/ps5-linux-patches`](https://github.com/ps5-linux/ps5-linux-patches/releases) (tags `kernel-X.Y.Z-<commit>`, jusqu'à 60 releases, toutes pages confondues) avec la version, le commit, l'état (« Démarré », « Installé », « Non installé ») et une ligne « Ouvrir la page GitHub des releases ».
- Téléchargement du RPM `linux-ps5-<version>-1.x86_64.rpm` de la release choisie, puis `rpm -ivh --nosignature --replacefiles --replacepkgs`, `depmod -a`, génération de l'initramfs si absent (`dracut --force --no-hostonly`) et déploiement sur l'ESP (`/boot/efi/bzImage` + `initrd.img`, avec sauvegarde `.old`) : permet de **revenir sur un ancien kernel**.
- `--replacepkgs` permet de réinstaller une même version de kernel issue d'un autre commit.
- Les releases sans RPM (paquet Arch uniquement, ex. `kernel-7.0.5-d8d6674`) sont détectées et signalées avant tout téléchargement.
- **Logithèque — Mister Download Manager** (`anefzaoui/misterdownloadmanager`) : installation / mise à jour / désinstallation du RPM publié sur GitHub (`misterdownloadmanager`), avec version installée et dernière version disponibles.
- Le type d'entrée `ghrpm` de la Logithèque accepte désormais n'importe quel dépôt GitHub (`gh_repo`, `gh_asset_pattern`) au lieu du seul dépôt Etcher.
- Fichier `CHANGELOG.md` (ce fichier).

### Modifié
- `APP_VERSION` passe à `0.3`, notes de version FR/EN de la boîte « À propos » mises à jour.
- Détection de version des applications `ghrpm` généralisée (extraction `X.Y[.Z]` du nom du fichier publié).

## [0.2] — 2026-11-21

### Ajouté
- **Gaming Mode** : installation et désinstallation de Gamescope / session Steam Big Picture, avec scripts embarqués (sauvegarde de `/etc/gdm/custom.conf`, fichiers du guide `steam-using-gamescope-guide`, ciblage de l'utilisateur réel et non du compte `ps5`).
- **Dépendances Supplémentaires** : `fuse` + `fuse-libs`, pilotes graphiques 32 bits pour Steam (`mesa-vulkan-drivers.i686`, `mesa-dri-drivers.i686`, `libva.i686`).
- **Python 3** : `python3` + `python3-pip`, création et activation automatique de l'environnement virtuel `my_project`, affichage de `python3 --version` / `pip3 --version`, installation de `python3-tkinter`.
- **Node.js / npm** : installation, mise à jour via les dépôts Fedora, passage à la version majeure récente (dépôt NodeSource 26 LTS), vérification des versions et désinstallation.
- **Divers Fix** : redémarrage forcé de Steam (`pkill -9 steam; steam`).
- **Gestion d'AppImage** dans la Logithèque : AppImage Pool (`io.github.prateekmedia.appimagepool`) et Gear Lever (`it.mijorus.gearlever`), avec installer / mettre à jour / désinstaller / ouvrir la page Flathub.
- **Hardware Control** : installateur en mode `--passwordless` et plugin Decky « Hardware Control Plugin ».
- Groupe « Hardware Control Plugin » dans la Logithèque.

### Modifié
- Interface native GTK4 / Libadwaita : 18 sections (`APP_VERSION = "0.2"`), notes de version FR/EN dans « À propos ».
- Corrections de fermeture Python sur les actions AppImage (Gear Lever héritait de la commande d'AppImage Pool).

## [0.1] — 2026-11-17

### Ajouté
- Première version de l'interface graphique **GTK4 / Libadwaita** (`ps5_manager.py`, fichier unique installé dans `/usr/local/bin/ps5-manager`) remplaçant progressivement les scripts Bash.
- 15 sections : journaux, Logithèque, IA & Développeur, mise à jour du manager, langues, dépôts, utilisateurs, Fedora, maintenance, alimentation, ventilateur, hardware, Mesa/Vulkan, kernel PS5, langue de l'interface.
- Lancement élevé via `pkexec` avec détection de l'utilisateur réel (`PKEXEC_UID`), exécution des commandes en root ou en utilisateur selon les cas.
- Gestion des kernels PS5 : vérification de la dernière release, installation du dernier kernel RPM, choix du kernel à démarrer sur `/boot/efi`, nettoyage des anciens kernels en protégeant le noyau actif.

## Historique antérieur — scripts Bash (2025 → 2026-11)

Avant l'interface graphique, le projet était une suite de scripts Bash lancés par `ps5-manager.sh` :

- `02-langues.sh` — configuration des langues
- `03-depots.sh` — ajout / suppression de dépôts (RPM Fusion, COPR…)
- `04-utilisateurs.sh` — gestion des comptes
- `05-maj-systeme.sh` — mises à jour du système
- `06-maintenance.sh` — nettoyage et maintenance
- `07-alimentation.sh` — alimentation / gestion d'énergie
- `08-fan-manager.sh` — ventilateur
- `09-hw-control.sh` — Hardware Control
- `10-mesa-vulkan.sh` — Mesa / Vulkan
- `11-kernel.sh` — kernel PS5
- `12-logiciels.sh` — installation de logiciels
- `13-presets.sh` — presets

Ces scripts ont été remplacés par l'application Python, puis retirés du dépôt.
