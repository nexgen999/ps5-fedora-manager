# Changelog

Historique des versions de **PS5 Fedora Manager** (application GTK4 / Libadwaita pour Fedora sur PS5).

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; le projet n'utilise pas encore de tags Git, les versions correspondent à `APP_VERSION` dans `ps5_manager.py`.

Version anglaise : [CHANGELOG_en.md](CHANGELOG_en.md)

## [0.9.1] — 2026-11-26

### Ajouté
- **Freebuff (agent de code IA)** dans la page « IA & Développeur », sous VSCodium : installation (`npm install -g freebuff`, avec Node.js + npm installés s'ils manquent), mise à jour (`npm install -g freebuff@latest`), désinstallation (`npm uninstall -g freebuff`) et lancement dans un terminal sous la session utilisateur. La version du paquet npm global est lue sur disque et affichée en sous-titre ; libellés traduits dans les six langues.

### Modifié
- `APP_VERSION` passe à `0.9.1`, notes de version FR/EN de la boîte « À propos » mises à jour.
- Sous-titre de la page « IA & Développeur » : Ollama, Open WebUI, VSCodium, Freebuff et modèles IA locaux.

## [0.9.0] — 2026-11-25

### Ajouté
- **Mise à jour automatique au lancement** : l'application lit `version.txt` du dépôt (quelques octets) dans un fil de fond, juste après l'ouverture de la fenêtre. Si une version plus récente existe, elle télécharge `ps5_manager.py`, vérifie sa taille, son `APP_VERSION` et sa compilation Python, l'installe dans `/usr/local/bin/ps5-manager` (`root:root`, `0755`, droits et contextes SELinux réappliqués), affiche un toast puis redémarre automatiquement sur la nouvelle version.
- **Silencieux en cas de problème** : hors ligne, dépôt injoignable ou script invalide, l'application s'ouvre normalement sans message ; si l'installation échoue, un toast renvoie vers la page « Mise à jour du manager ».
- **Garde-fous** : pas de seconde tentative pour la même version (`PS5_MANAGER_SKIP_UPDATE`), redémarrage reporté si une action est en cours, et vérification désactivable avec `PS5_MANAGER_NO_UPDATE_CHECK=1`.
- `version.txt` publié dans le dépôt : c'est la seule information téléchargée lors de la vérification.

### Modifié
- `APP_VERSION` passe à `0.9.0`.

## [0.8.3] — 2026-11-25

### Corrigé
- **Lancement depuis l'icône du menu** : faute d'agent PolicyKit graphique dans la session (constaté sous Budgie), `pkexec` retombait sur son agent texte ; appelé depuis une icône il n'y a plus de terminal, l'authentification échouait et l'application ne s'ouvrait jamais — seul le lancement en terminal fonctionnait. L'application démarre désormais un agent PolicyKit (`polkit-gnome`, `polkit-kde`, `mate-polkit`, `lxpolkit`…) avant l'élévation, réessaie une fois, puis affiche une explication claire et copiable si l'authentification reste impossible.
- **Journal de lancement** : les échecs d'élévation sont écrits dans `~/.cache/ps5-manager/launcher.log` (bureau détecté, code de retour, commande) au lieu de disparaître faute de terminal.
- **Avertissements GTK « L'entité ne se termine pas par un point-virgule »** : les titres de lignes contenant « & » (« IA & Développeur », « Langues & clavier », « Suivi en direct & historique ») étaient transmis au constructeur Adwaita alors que le markup est actif par défaut. Le texte est maintenant posé après la désactivation du markup : plus aucun avertissement et le « & » s'affiche tel quel.

### Modifié
- `polkit-gnome` rejoint les dépendances de l'interface pour les bureaux qui ne fournissent pas d'agent d'authentification.
- `APP_VERSION` passe à `0.8.3`.

## [0.8.2] — 2026-11-25

### Corrigé
- **Menu principal (« burger ») non rafraîchi** : c'est un `Gio.Menu` construit une seule fois au démarrage ; après un changement de langue il conservait les libellés de l'ancienne langue jusqu'au redémarrage. `rebuild_ui_for_language()` reconstruit désormais ses trois entrées (`setup_menu`, `system_info`, `about`) et l'infobulle du bouton de recherche.
- **Boîte « À propos » traduite** : les notes de version et les informations de débogage (« Version », « Fichier ») n'existaient qu'en français et en anglais. Elles sont maintenant disponibles dans les six langues (`_RELEASE_NOTES_ITEMS`, repli anglais si une langue manque).
- Vérification de tous les menus : les 20 entrées de la barre latérale et les 3 entrées du menu burger passent par `T()` et sont traduites dans les six langues.
- **Page IA & Développeur** : les deux descriptions encore écrites en dur (état d'Open WebUI et icône GNOME, nombre de modèles installés et actifs) passent par `STRINGS`.
- `APP_VERSION` passe à `0.8.2`.

### Ajouté
- Traductions des notes de version (`release_notes_html()`) : 11 points d'historique × 6 langues.

## [0.8.1] — 2026-11-25

### Corrigé
- **Icône du raccourci de session** : le raccourci « Basculer Session » et le lanceur du menu utilisaient `Icon=steam` (logo Steam). L'installation du mode Gaming écrit désormais l'icône Gamescope fournie (Steam Deck) dans `/usr/share/pixmaps/ps5-gaming-mode.png` et `/usr/share/icons/hicolor/96x96/apps/`, puis la déclare dans `switch-session.desktop` et dans la session `steam.desktop` (le sélecteur de session GDM / SDDM / LightDM affiche donc lui aussi cette icône).
- La désinstallation du mode Gaming supprime les deux fichiers d'icône et rafraîchit le cache du thème.
- `APP_VERSION` passe à `0.8.1`.

## [0.8] — 2026-11-25

### Ajouté
- **Fenêtre « Système » entièrement repensée** : en-tête avec le logo Fedora, le nom de l'application et le logo du bureau détecté (GNOME, KDE Plasma, Cinnamon, Budgie), puis quatre groupes Adwaita lisibles — *Système* (OS, noyau, architecture, gestionnaire de paquets), *Session* (bureau, gestionnaire de connexion, session graphique, utilisateur, couleur d'accentuation), *Logiciels* (Gamescope, Steam) et *Application* (version, fichier, journal de session avec ouverture directe).
- **Icônes importées dans le dépôt** : le dossier `icons/` contient les PNG 96 px (Fedora, Gamescope, Budgie, Cinnamon, KDE, GNOME) ; ils sont aussi embarqués en base64 dans `ps5_manager.py` pour que l'installation par `curl` reste un fichier unique, sans accès réseau. Les logos monochromes sont posés sur une pastille sombre afin de rester lisibles sur les thèmes clair et sombre.
- **Copie en un clic** : un bouton dans l'en-tête copie toutes les informations (utile pour joindre un rapport de bug).
- **Traductions complétées** : les 64 textes qui ne passaient pas par `STRINGS` (page « IA & Développeur », à propos) sont traduits en espagnol, italien, allemand et portugais via `LSTRINGS` ; les 18 ternaires `... if UI_LANG == "fr" else ...` sont convertis en `_L()` et deux libellés calculés (raccourci de session, maintien de session Podman) passent par `STRINGS`. Toutes les clés `T()` sont couvertes : **377 clés × 6 langues, aucune manquante**.

### Modifié
- `_show_sysinfo()` ouvre la fenêtre `SystemInfoWindow` (Adw.Window) au lieu d'une boîte de dialogue en texte brut.
- `_L(fr, en)` s'appuie sur une table `_L_TABLE` et les dictionnaires `LSTRINGS` (es, it, de, pt).
- `APP_VERSION` passe à `0.8`, notes de version FR/EN de la boîte « À propos » mises à jour.

## [0.7.1] — 2026-11-25

### Corrigé
- **Mode Gaming sous Cinnamon et Budgie (et KDE)** : la session Gamescope ne relance plus Steam en boucle. L'application écrit désormais son propre `/usr/bin/gamescope-session` (le guide amont ne faisait que lancer `gamescope … steam` puis mourir, et le gestionnaire de connexion réouvrait la session `steam` indéfiniment). À la fermeture de Steam, la console revient sur la session du bureau détecté.
- **Retour au bureau depuis Steam Big Picture** : `/usr/bin/steamos-session-select` enregistre la session demandée (bureau ou Gaming) puis ferme Steam (`steam -shutdown`) ; `gamescope-session` lit cette demande après la sortie de Gamescope et bascule en conséquence (plus de retour bloqué sur Steam).
- **Bascule de session fiable** : `/usr/local/bin/switch-session` réécrit maintenant **aussi** l'auto-connexion du gestionnaire de connexion, pas seulement AccountsService. Sous SDDM (`Session=` dans `/etc/sddm.conf.d/zz-ps5-manager-autologin.conf`) et sous LightDM (`autologin-session=` dans `[Seat:*]`), l'ancienne session restait codée en dur et le gestionnaire relançait Steam à chaque fois.
- **Erreur DRM au lancement de Gamescope** : installation de `gamescope` s'il est absent, ajout de l'utilisateur aux groupes `video` et `render` (accès `/dev/dri/card*`), suppression de `WAYLAND_DISPLAY` / `DISPLAY` de l'environnement de la session (Gamescope tentait une composition imbriquée) et attente de la fermeture effective de la session avant redémarrage du gestionnaire de connexion (le GPU restait occupé).
- **Détection du gestionnaire de connexion** : `display-manager.service` est lu en premier (`systemctl show -p Id`). Cinnamon et Budgie démarrent souvent LightDM alors que `gdm.service` reste « enabled » : l'application redémarrait le mauvais service et la bascule ne se faisait jamais.
- **Scripts de session** : plus de blocage si le guide `shahnawazshahin` est inaccessible (avertissement seulement) et les scripts fournis par l'application sont écrits après ceux du guide, donc prioritaires.
- `APP_VERSION` passe à `0.7.1`, notes de version FR/EN de la boîte « À propos » mises à jour.

### Ajouté
- **Journal du mode Gaming** : nouvelle entrée dans la page « Gaming Mode » qui affiche `/var/log/ps5-manager/gaming-session.log` (commande lancée, code de sortie de Gamescope, erreurs DRM éventuelles). Trois libellés traduits dans les six langues (353 clés).

## [0.7] — 2026-11-25

### Ajouté
- **Interface en 6 langues** : français, anglais, **espagnol**, **italien**, **allemand** et **portugais du Brésil**. Les 350 libellés de `STRINGS` sont traduits intégralement dans chaque langue (aucune clé manquante).
- **Sélecteur de langue** : la page « Langue de l'interface » liste les six langues avec leur nom natif (Français, English, Español, Italiano, Deutsch, Português (Brasil)) ; la boîte de bienvenue du premier lancement propose les six choix.
- `LANG_ORDER` / `LANG_LABELS` centralisent l'ordre d'affichage et les noms natifs.

### Modifié
- **`read_ui_lang()`** accepte les variantes (`pt_BR`, `pt-BR`, `es_ES`…) et se replie sur la langue de base enregistrée dans `/etc/ps5-manager/language`.
- **`T()`** se replie désormais sur l'anglais puis sur le français : une clé absente n'affiche plus le nom technique de la clé.
- **`_L(fr, en)`** consulte un dictionnaire `LSTRINGS` (aujourd'hui vide) avant de retomber sur l'anglais, pour traduire plus tard les textes hors `STRINGS` sans toucher aux appels.
- `APP_VERSION` passe à `0.7`, notes de version FR/EN de la boîte « À propos » mises à jour.

## [0.6.1] — 2026-11-25

### Ajouté
- **Dépôts par bureau** : la page Dépôts installe ou répare le groupe comps officiel du bureau détecté (`@gnome-desktop`, `@kde-desktop-environment`, `@cinnamon-desktop-environment`, `@budgie-desktop-environment`), active `fedora-cisco-openh264` (H.264) et propose l'installation des codecs GStreamer via RPM Fusion — aucun dépôt tiers n'est nécessaire pour les quatre bureaux.

### Modifié
- **Mises à jour Fedora** : `fed_apps` met à jour Flatpak côté système **et** utilisateur ; DNF, langpacks, Flatpak et rafraîchissement des dépôts restent identiques sur les 4 bureaux.
- **Maintenance** : ajout de `update-desktop-database` et `fc-cache -f` (communs), et d'un groupe « Maintenance KDE Plasma » avec `kbuildsycoca6 --noincremental` (KDE uniquement).
- **Langues & clavier** : `gsettings org.gnome.system.locale` n'est appliqué que sous GNOME / Budgie, et la déconnexion utilise la commande du bureau détecté (`gnome-session-quit`, `cinnamon-session-quit`, `qdbus … org.kde.Shutdown.logout`) avec repli `loginctl terminate-user`.
- **Couleur d'accentuation GNOME** : groupe masqué et sondage dconf désactivé hors GNOME.
- **Kernel PS5** : section auditée sans dépendance au bureau ni au gestionnaire de connexion ; ses textes passent par les traductions FR/EN.
- `APP_VERSION` passe à `0.6.1`, notes de version FR/EN de la boîte « À propos » mises à jour.

### Corrigé
- **Logithèque** : les statuts RPM / Flatpak sont calculés dans un thread et remplis après le rendu — plus de gel à l'ouverture de la page.
- **IA & Développeur** : l'état Podman / Open WebUI et la liste des modèles Ollama sont lus hors du fil GTK (cache 30 s, reconstruction de la section quand les données arrivent).
- **Page Dépôts** : la vérification du groupe comps s'exécute au lancement de l'action, plus jamais à l'ouverture de la page.
- **Notes de version (« Quoi de neuf »)** : plus aucune balise `<b>` et filtre `_safe_release_notes()` (Libadwaita refusait l'analyse).
- **Titres de groupes** : `pref_group()` n'échappe plus le texte brut (`IA &amp;` redevient `IA &`).
- **Textes codés en dur** : kernel, utilisateurs, dépôts, Mesa et IA passent désormais par `STRINGS` (FR/EN).
- **Page IA & Développeur** : les 49 libellés, sous-titres et confirmations encore en français dur (Open WebUI, Ollama, VSCodium, modèles) sont bilingues via le nouvel assistant `_L(fr, en)`, donc l'interface anglaise est complète.

## [0.6] — 2026-11-25

### Ajouté
- **Compatibilité GNOME / KDE Plasma / Cinnamon / Budgie** : détection automatique du bureau (variables de session, processus de l'utilisateur, `loginctl`) et du gestionnaire de connexion (GDM / SDDM / LightDM), avec adaptation des commandes concernées.
- **Setup 1 clic adapté au bureau** : l'étape Alimentation applique les commandes du bureau détecté, l'Extension Manager est retiré du plan hors GNOME (28 éléments au lieu de 29) et l'étape Gamescope suit le gestionnaire de connexion ; le journal du setup commence par une ligne « Environnement détecté » (bureau · gestionnaire de connexion · session).

### Modifié
- **Alimentation par bureau** : veille de l'écran et veille complète via `gsettings` (GNOME, Cinnamon, Budgie) ou `kwriteconfig6` + Powerdevil (KDE Plasma), rechargement de Powerdevil inclus.
- **Éléments propres à GNOME** : l'Extension Manager disparaît de la Logithèque et du setup recommandé (28 éléments hors GNOME) ; la gestion mobile utilise KDE Connect (KDE), Nemo (Cinnamon) ou Nautilus (GNOME / Budgie) ; les imprimantes ajoutent `print-manager` sous KDE.
- **Gamescope multi-bureau** : auto-connexion écrite pour GDM, SDDM ou LightDM et bascule vers la session du bureau détecté (`gnome`, `plasma`, `cinnamon`, `budgie-desktop`) au lieu de « gnome » codé en dur.
- **Fenêtre de suivi du setup élargie** (1320 × 800 au lieu de 1120 × 740) et colonne de gauche plus large.
- `APP_VERSION` passe à `0.6`, notes de version FR/EN de la boîte « À propos » mises à jour.

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
