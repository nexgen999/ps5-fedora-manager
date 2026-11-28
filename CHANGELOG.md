# Changelog

Historique des versions de **PS5 Fedora Manager** (application GTK4 / Libadwaita pour Fedora sur PS5).

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; le projet n'utilise pas encore de tags Git, les versions correspondent à `APP_VERSION` dans `ps5_manager.py`.

Version anglaise : [CHANGELOG_en.md](CHANGELOG_en.md)

## [0.15.21] — 2026-11-28

### Corrigé
- **Mode Gaming avec Steam en Flatpak** : sous Budgie, le paquet rpm `steam`
  ne s'installe pas, seul le Flatpak `com.valvesoftware.Steam` fonctionne.
  `gamescope-session` ne cherchait que la commande `steam` et renvoyait
  aussitôt au bureau (`steam introuvable : retour au bureau` dans
  `gaming-session.log`).
  - La session résout maintenant le lanceur : `steam` (rpm) sinon
    `flatpak run com.valvesoftware.Steam`, et lance
    `gamescope -e -- <lanceur> -steamdeck -steamos3`.
  - `steamos-session-select` ferme Steam de la même façon
    (`steam -shutdown` ou `flatpak run com.valvesoftware.Steam -shutdown`).
  - `--mangoapp` est réservé au paquet rpm : un Flatpak filtre `LD_PRELOAD`,
    l'option restait sans effet.
  - L'installation ne prévient plus que Steam est absent quand le Flatpak est
    présent.

## [0.15.20] — 2026-11-28

### Corrigé
- **Fenêtre « Système » du menu burger qui ne s'ouvrait plus** : la
  construction de ses lignes testait une variable `sec_id` restée d'un
  copier-coller du générateur de lignes de la barre latérale. L'exception
  (`NameError`) survenait à la première ligne, la fenêtre n'était jamais créée
  et le clic sur « Système » ne montrait rien, sans message. La ligne utilise
  désormais directement l'icône demandée.

## [0.15.19] — 2026-11-28

### Corrigé
- **Mode Gaming (Gamescope) sous Budgie** : Budgie 10.10 (Fedora 44) est
  passé de X11/LightDM à Wayland/SDDM et le nom de session écrit dans
  AccountsService et dans l'auto-connexion n'était plus forcément installé.
  Le gestionnaire de connexion retombait alors sur sa session par défaut : la
  console restait sur l'écran de connexion au lieu de revenir au bureau, et le
  mode Gaming semblait ne pas fonctionner.
  - La session du bureau est désormais **résolue à l'exécution** dans
    `/usr/share/wayland-sessions` puis `/usr/share/xsessions`, avec les noms
    connus de chaque bureau (`budgie-desktop`, `budgie`, `budgie-wayland`,
    `ubuntu-budgie-desktop` pour Budgie).
  - « Basculer Session » employait le nom figé au moment de l'installation ;
    il le revérifie à chaque bascule et **refuse la bascule** (message clair,
    code 3) plutôt que d'écrire une session inexistante.
  - Une session enregistrée par une ancienne installation (par exemple
    `gnome` sur une machine passée à Budgie) ne prime plus sur le bureau
    détecté.

### Ajouté
- **Journal de bascule de session** : `/var/log/ps5-manager/session-switch.log`
  note chaque demande (session visée, session courante, bureau et gestionnaire
  de connexion) ; il s'affiche avec le journal de session depuis Gaming Mode.
- **Diagnostic de l'écran noir** : le journal de session indique la carte DRM
  ouverte et les groupes de l'utilisateur (`video`, `render`).

## [0.15.18] — 2026-11-27

### Modifié
- **« Bon à savoir » d'« Add Fedora Feature » rangé dans une sous-page** : les
  six notes sur les presets, les codecs et FFmpeg occupaient une demi-page ;
  un bouton « Bon à savoir » les ouvre désormais en sous-page, texte présenté
  comme un changelog, avec le bouton retour.
- **Ligne de version de l'accueil dédoublonnée** : « Version stable · build
  v0.15.18 » au lieu du numéro de build répété deux fois.

## [0.15.17] — 2026-11-27

### Modifié
- **Nouvelle page d'accueil « PS5 Fedora Manager »** en tête de la barre
  latérale : logos PlayStation et Fedora, nom de l'application et numéro de la
  version stable installée, puis un accès rapide à « Mise à jour du manager »,
  « Langues & clavier » et « Journal / Logs ». Ces trois pages s'ouvrent en
  sous-page, avec un bouton retour vers l'accueil.
- Elles quittent la liste principale : la barre latérale garde ses trois
  groupes d'outils, inchangés, sous l'accueil.
- L'application démarre sur l'accueil (le journal reste accessible en un clic
  depuis l'accueil et depuis le bouton journal de chaque page).
- « Langues & clavier » (réglage Fedora) revient dans la liste principale ;
  l'accueil pointe désormais vers « Langue de l'interface », le réglage du
  manager lui-même.
- Page d'accueil affinée après essai : un seul logo PlayStation à côté du
  nom, logos Fedora et bureau en petit avec le nom du système, version
  stable et build sur une ligne discrète, icônes réduites.
- « Langue de l'interface » ne figure plus deux fois : elle quitte la liste
  principale et reste accessible depuis l'accueil. « FX Sound & Vidéo »
  (codecs audio/vidéo et FFmpeg compris) et « Gaming Mode » sont transférés
  dans « Add Fedora Feature », aux côtés de la gestion mobile et des
  imprimantes.
- « Divers Fix » quitte la barre latérale : « Relancer Steam » rejoint le
  sous-menu de Steam dans la logithèque, à côté des actions d'installation.
- Aucune modification du setup en 1 clic : son plan de 9 étapes ne dépend pas
  des sections de la barre latérale.

### Ajouté
- `backup/stable/v<version>/` : copie complète du projet avant chaque
  modification de la version stable, avec `tools/backup_stable.sh` pour la créer
  et `backup/README.md` pour la restauration.

## [0.15.16] — 2026-11-27

### Corrigé
- **Le raccourci réservé ignorait le 1 du pavé numérique.** Le pavé envoie
  `KP_1` (Verr Num actif) ou `KP_End` (Verr Num inactif), pas `KEY_1` : les
  trois variantes sont désormais reconnues, avec Ctrl.

## [0.15.15] — 2026-11-27

### Modifié
- **Le bloc « version bêta » quitte la page de mise à jour.** L'édition bêta se
  pilote désormais depuis un menu réservé, ouvert par un raccourci clavier
  interne : aucune ligne, aucun bouton et aucune note de version ne le signale
  dans l'interface.

### Ajouté
- **« Désinstaller la version bêta »** dans ce menu : supprime
  `/opt/ps5-manager/beta` et `/tmp/ps5-manager-beta.log` après confirmation.
  Une mise à jour du manager réinstalle la bêta au besoin.
- Les cinq actions du menu (installer et lancer, lancer, terminal, journal,
  désinstaller) sont traduites dans les six langues, 24 clés au total.

## [0.15.14] — 2026-11-27

### Corrigé
- **La bêta s'arrêtait au démarrage (`code 1`).** Deux causes, toutes deux
  visibles seulement avec un vrai PyGObject :
  1. `RuntimeError: could not create new GType … (subclass of AdwSwitchRow)` :
     libadwaita déclare `Adw.SwitchRow` et `Adw.PreferencesPage` **finaux**, et
     PyGObject 3.54 refuse désormais d'en dériver une classe Python. Les pages
     Services, Logithèque, Noyau, Dépôts et Utilisateurs construisent
     maintenant leurs lignes et leurs pages par des fabriques
     (`service_row()`, `build(win)`), sans aucune sous-classe de widget.
  2. `Authorization required, but no authorization protocol specified` : le
     cookie X de root (`/root/.Xauthority`, 0600) n'est pas lisible par
     l'utilisateur. Le lanceur exécute `xhost +SI:localuser:<utilisateur>`
     avant de démarrer la bêta, ce qui autorise l'affichage par UID (X11 et
     Xwayland), et le journal indique si l'accès a été accordé.

### Ajouté
- `beta/tools/check.py` refuse maintenant toute sous-classe d'un widget
  Adw/Gtk (`gtypes`), pour que cette erreur ne puisse plus revenir sans être
  vue : elle n'apparaît qu'avec GTK réel, jamais avec le GTK factice.

## [0.15.13] — 2026-11-27

### Corrigé
- **« Lancer la version bêta » n'ouvrait aucune fenêtre.** La bêta était lancée
  avec l'environnement de root (hérité de l'élévation du manager) : `HOME`,
  `XAUTHORITY`, `XDG_RUNTIME_DIR` et le bus de session ne correspondaient pas à
  l'utilisateur réel, donc GTK ne trouvait ni l'affichage ni le bus et le
  processus mourait sans rien montrer. Le lancement construit désormais un
  environnement de session propre (`HOME`, `USER`, `XDG_RUNTIME_DIR`,
  `WAYLAND_DISPLAY` détecté dans `/run/user/<uid>`, `XAUTHORITY` de
  l'utilisateur, `DBUS_SESSION_BUS_ADDRESS`), passe par `Popen(user=…,
  group=…, extra_groups=…)` et **retente en X11** (`GDK_BACKEND=x11`) si le
  premier essai s'arrête.

### Ajouté
- **Diagnostic visible** : vérification de GTK4/libadwaita par l'utilisateur
  avant le lancement (message explicite si PyGObject ou libadwaita manque),
  sortie conservée dans `/tmp/ps5-manager-beta.log`, et deux nouvelles lignes
  « Lancer dans un terminal » (erreurs en direct) et « Voir le journal de la
  bêta ». Un échec affiche le journal au lieu d'un simple toast.
- Textes des six langues complétés (9 clés de plus).

## [0.15.12] — 2026-11-27

### Ajouté
- **Essayer la bêta depuis la version stable.** La page « Mise à jour du
  manager » contient un nouveau groupe « Version bêta » :
  - « Installer et essayer la version bêta » : récupère `origin/main` dans
    `/opt/ps5-manager` (`fetch` + `reset --hard`, ou `git clone` pour une
    installation historique), vérifie que `beta/run.py` est là, puis lance
    l'édition bêta **en tant qu'utilisateur réel** (`subprocess.Popen` avec
    `user`/`group`/`env` de la session, `start_new_session`) ;
  - « Lancer la version bêta » : relance simplement l'édition bêta installée.

  Le sous-titre de la première ligne affiche la version bêta détectée
  (`beta/VERSION`). La stable continue de tourner : la bêta ouvre sa propre
  fenêtre, sans droits root. La sortie de la bêta est écrite dans
  `/tmp/ps5-manager-beta.log`.

### Traductions
- Nouveaux textes de la section bêta en fr, en, es, it, de et pt, plus une
  entrée dans les notes de version des six langues.

## [0.15.11] — 2026-11-27

### Corrigé
- **Textes restés en anglais.** Sept chaînes étaient appelées avec `_L()` sans entrée dans `_L_TABLE` : elles s'affichaient en français/anglais seulement, quelle que soit la langue choisie. Traduites en es, it, de et pt :
  - « Actif » (sous-titre d'un service actif mais non activé au démarrage) ;
  - « Raccourcis » (groupe de la page Services) ;
  - « Aucun de ces services n'est installé. » ;
  - « Un service coupé ne consomme plus de mémoire ni de CPU, mais reste installé. » ;
  - « Désinstaller les composants installés et repartir d'une base propre. » ;
  - « Choisis ce qui doit être retiré, puis nettoie les fichiers du manager. » ;
  - « Supprimer les configurations écrites par l'application ? ».

### Ajouté
- **Lien « Historique complet »** dans la fenêtre À propos : ouvre le `CHANGELOG.md` (français) ou `CHANGELOG_en.md` (autres langues) sur GitHub, puisque la carte des nouveautés n'affiche que les 5 dernières entrées.

## [0.15.10] — 2026-11-27

### Modifié
- **Fenêtre « À propos » repensée.** `Adw.AboutDialog` impose une colonne de ~450 px : la fenêtre devenait un rectangle vertical haut et étroit, pénible à lire. Remplacée par une fenêtre `Adw.Window` de **900 × 740 px** (contenu limité à 760 px, centré) qui contient :
  - l'en-tête avec le logo de l'application, le nom, la version et la description ;
  - un groupe **Liens** (site web, signalement de problème) ouvrant le navigateur ;
  - un groupe **Informations techniques** (version, GTK, Libadwaita, Python, chemin du fichier, valeurs sélectionnables) ;
  - les **nouveautés** (5 dernières entrées) dans une carte avec retour à la ligne ;
  - le pied de page « © 2026 nexgen999 · Développé par nexgen999 ».
- Nouvelles chaînes traduites dans les 6 langues (« À propos », « Liens », « Site web », « Signaler un problème », « Informations techniques », « Nouveautés », « Développé par nexgen999 »).

## [0.15.9] — 2026-11-27

### Corrigé
- **« Quoi de neuf » cassé** : les notes de version contenaient un « & » brut (« FX Sound & Vidéo ») dans un texte interprété comme du markup Pango. La boîte « À propos » affichait « Impossible d'analyser les notes de version » à la place du texte. `release_notes_html()` échappe désormais le titre et chaque point (`&`, `<`, `>`), donc les notes s'affichent quelle que soit la langue.

## [0.15.8] — 2026-11-27

### Corrigé
- **Codecs : 10/11 sur Fedora 43 et plus récent.** Fedora a renommé le greffon GStreamer libav en `gstreamer1-plugin-libav` (singulier) ; l'ancien `gstreamer1-plugins-libav` n'existe plus, `dnf` répondait « Aucune correspondance pour l'argument » et la ligne restait à 10/11. La liste utilise désormais le nom actuel : 11/11 après installation.

## [0.15.7] — 2026-11-27

### Modifié
- **Pastille partielle explicite** : quand une ligne affiche ◐ 10/11, son infobulle (et celle de la ligne) donne le nom du paquet manquant — par exemple `10/11 · manquant : gstreamer1-plugin-openh264`. Le journal d'installation liste aussi les paquets indisponibles à la fin de l'opération.
- Aucun changement sur la liste des codecs ni sur les commandes `dnf` : seule la lecture de l'état est plus précise.

## [0.15.6] — 2026-11-27

### Ajouté
- **FX Sound & Vidéo** : la section s'appelle désormais « FX Sound & Vidéo » et gagne un groupe **Vidéo**.
  - **Codecs audio et vidéo** : GStreamer complet (`good`, `bad-free`, `bad-free-extras`, `ugly`, `libav`, `bad-freeworld`), `libavcodec-freeworld`, `lame`, `x264-libs`, `x265-libs`, `gstreamer1-plugin-openh264` — RPM Fusion activé automatiquement si nécessaire, `--skip-unavailable` pour les paquets absents d'une version.
  - **FFmpeg (codecs complets)** : `ffmpeg` + `libavcodec-freeworld` (remplace le `libavcodec-free` bridé de Fedora).
  - Pastilles d'état sur les deux lignes, notes sur RPM Fusion et sur le redémarrage des applications après installation.

### Modifié
- `sec_fx` traduit dans les 6 langues : « FX Sound & Vidéo » (fr), « FX Sound & Video » (en/de), « FX Sound y Vídeo » (es), « FX Sound e Video » (it), « FX Sound e Vídeo » (pt).

## [0.15.5] — 2026-11-27

### Corrigé
- **Hardware Control — plugin Decky** : la pastille restait « ○ Non installé » alors que le plugin était bien présent. L'installateur officiel copie le plugin dans `~/homebrew/plugins/ps5-hardware-control`, alors que la détection ne cherchait que « hwcon » dans le nom du dossier. Elle reconnaît désormais `ps5-hardware-control`, `ps5-hwcon` et `hwcon`, dans le home de l'utilisateur de bureau, dans `/root` et dans tous les `/home/*/homebrew/plugins`.

## [0.15.4] — 2026-11-27

### Corrigé
- **Mise à jour du manager depuis le menu** : elle échouait en « code 1 » sur Fedora 45 car `polkit-gnome` n'existe plus dans les dépôts et **un seul nom introuvable annule toute la transaction dnf**. Le paquet est retiré des dépendances de l'interface (l'agent PolicyKit est fourni par le bureau et déjà détecté par l'application).
- Le `dnf install` des dépendances utilise `--skip-unavailable` : un paquet absent est ignoré au lieu de faire échouer la commande.
- Une erreur de dépendances **ne bloque plus la mise à jour du manager** : elle est signalée dans le journal, puis le dépôt est récupéré et l'application réinstallée normalement.
- `install.sh` : même correction (`--skip-unavailable`, plus de `polkit-gnome`), une installation neuve ne s'arrête plus sur ce paquet.
- Le message d'aide au lancement ne recommande plus d'installer `polkit-gnome` mais l'agent PolicyKit du bureau (gnome-shell, polkit-kde, mate-polkit, xfce-polkit…).

## [0.15.3] — 2026-11-27

### Modifié
- **Logithèque** : chaque application (Steam, Heroic, Opera, Brave, Etcher, Bazaar…) affiche désormais la **pastille d'état** de l'application — **● Installé**, **○ Non installé** — à gauche du chevron, exactement comme *AppImage Pool* et *Gear Lever* en bas de page. Le texte « · Installé (RPM) » / « · Installé (Flatpak) » du sous-titre est supprimé : le sous-titre ne garde que la description.
- La détection reste en arrière-plan (`rpm -q`, `flatpak info`) : la page s'affiche immédiatement, les pastilles se remplissent dès que le statut est connu, sans gel de l'interface.

## [0.15.2] — 2026-11-27

### Corrigé
- **Dépôts détectés correctement sous Fedora 41+ (dnf5)** : la lecture des dépôts couvre désormais `/usr/share/dnf5/repos.d` (définitions livrées, dont **RPM Fusion**), `/etc/yum.repos.d` puis les overrides `/usr/share/dnf5/repos.override.d` et `/etc/dnf/repos.override.d` — l'ordre réel d'application de dnf5.
- **RPM Fusion** : plus de faux « ○ Non installé ». La détection reconnaît les dépôts `rpmfusion-*` actifs quel que soit leur emplacement, et se replie sur les paquets `rpmfusion-free-release` / `rpmfusion-nonfree-release`. L'installation ne relance plus les RPM de release inutilement.
- **fedora-cisco-openh264** : la pastille lit l'activation écrite par `dnf config-manager` dans `/etc/dnf/repos.override.d/99-config_manager.repo`, pas seulement le fichier `.repo` d'origine.

## [0.15.1] — 2026-11-27

### Modifié
- **Pastilles d'état partout** : les sections qui ne montraient pas ce qui est installé affichent désormais la même pastille que les catalogues — **● Installé**, **◐ n/total** (partiel), **○ Non installé**, avec infobulle.
  - *Dépendances supplémentaires* : FUSE, pilotes 32 bits Steam, Python/pip, Tkinter, Node.js/npm.
  - *Add Fedora Feature* : gestion mobile et impression & scanners (selon les paquets du bureau détecté).
  - *Gaming Mode* : gamescope + session `switch-session`.
  - *Mesa / Vulkan* : `vulkan-tools` et `mesa-demos`.
  - *Ventilateur* : PS5 Linux Tools (`ps5_control`, service `ps5fan`).
  - *Hardware Control* : interface `ps5-hwcon-gui` et plugin Decky.
  - *Dépôts* : RPM Fusion, Flathub, OpenH264 activé, codecs GStreamer.
  - *Logithèque* : AppImage Pool et Gear Lever (Flatpak, système ou utilisateur).
- Détection faite à l'ouverture de la page : `rpm -q` groupé (architecture comprise), fichiers et services systemd, dépôts lus dans `/etc/yum.repos.d`, remotes Flatpak — aucune commande bloquante.

## [0.15.0] — 2026-11-27

### Ajouté
- **Section « FX Sound »** (icône `audio-volume-high-symbolic`, juste après *Services*) : installation d'**Easy Effects** (`dnf install easyeffects`) puis des **presets communautaires JackHack96**, chaque ligne avec sa pastille d'état (● installé / ○ non installé) et le nombre de presets détectés dans `~/.local/share/easyeffects`.
- L'installation des presets **répond automatiquement `1`** au menu du script officiel (tous les presets : Perfect EQ, basses, Dolby Atmos, haut-parleur de portable, réponses impulsionnelles) ; le script tourne avec l'identité du **compte de bureau**, pas de root.
- **Documentation** `doc/fr/fx-sound.md` et `doc/en/fx-sound.md` : commandes exactes, contenu de l'option 1, fichiers écrits, vérifications, dépannage et désinstallation ; index `doc/` mis à jour.

### Modifié
- `SECTIONS` et `PAGE_BUILDERS` accueillent la section `fx` ; `sec_fx` et les nouveaux libellés sont traduits dans les 6 langues et les notes de version de la boîte « À propos » sont à jour.

## [0.14.0] — 2026-11-26

### Ajouté
- **Pastilles d'état** dans les catalogues *Développement* et *Serveur web* comme sur les profils d'*Installation facile* : **● Installé** (vert), **◐ 2/3** (partiel), **○ Non installé** (gris), avec infobulle ; l'état vient de la détection réelle (`rpm -q` groupé, commandes dédiées).
- **Section « Services »** : un interrupteur par unité systemd (`httpd`, `nginx`, `php-fpm`, `mariadb`, `mysqld`, `docker`, `podman.socket`, `forgejo`, `firewalld`, `sshd`, `cockpit.socket`, `bluetooth`, `cups`, `avahi-daemon`, `ModemManager`). L'interrupteur allume (`enable --now`) ou éteint (`disable --now`) le service, avec retour arrière automatique si l'action est refusée.
- **Raccourci « Couper les daemons inutiles »** : désactive Bluetooth, CUPS, Avahi et ModemManager en une confirmation, puis recharge la page.
- **Documentation** `doc/` en français et en anglais : index bilingue, installation facile, serveur web, développement, services, Gamescope, Freebuff, réinitialisation — commandes, fichiers écrits, dépannage.

### Modifié
- `SECTIONS` et `PAGE_BUILDERS` accueillent la section `services` ; `sec_services` traduit en 6 langues.
- Le `README.md` renvoie vers `doc/`.

## [0.13.0] — 2026-11-26

### Ajouté
- **Deux profils supplémentaires** dans « Installation facile » : **WordPress** (Apache, PHP, MariaDB, phpMyAdmin puis téléchargement de WordPress et génération d'un `wp-config.php` complet, sel aléatoire inclus) et **Tout-en-un** (outils de développement, conteneurs, Cockpit, pare-feu).
- **Quinze options de configuration** au lieu de six : port HTTP (hôte virtuel Apache/Nginx et ouverture du pare-feu), `memory_limit`, `upload_max_filesize`/`post_max_size`, `date.timezone` (fichier `/etc/php.d/99-ps5-easy.ini`), domaine + e-mail **Let's Encrypt** (émission et redirection HTTPS automatiques), port Forgejo et **création du compte administrateur** Forgejo.
- **MySQL** proposé à côté de MariaDB dans les profils web, avec les mêmes étapes de base de données.
- **Outil de réinitialisation** dans la section : page listant les composants réellement installés (interrupteur par composant), option « supprimer les fichiers de configuration créés par le manager » (`ps5-easy.conf`, `99-ps5-easy.ini`, `adminer.php`, dépôts docker/webmin), option « vider le cache DNF », et désinstallation confirmée qui repart d'une base propre.
- Désinstallation d'un profil ou d'une sélection, avec la **même fenêtre de progression** que l'installation (étapes `dnf remove` par composant).

### Corrigé
- `_easy_path` normalise désormais les chemins (`..` supprimés) : un DocumentRoot saisi ne peut plus sortir de l'arborescence prévue.
- `wp-config.php` est généré en une fois (plus de `sed` fragile sur un mot de passe contenant apostrophe ou antislash).

## [0.12.0] — 2026-11-26

### Ajouté
- **Section « Installation facile »** : quatre profils pré-configurés qui réutilisent le catalogue des pages « Développement » et « Serveur web ».
  - **Serveur web LAMP** : Apache, PHP + handler FastCGI, MariaDB, phpMyAdmin, pare-feu (au choix : Adminer, Cockpit, Certbot, OpenSSH).
  - **Serveur web LEMP** : la même pile avec Nginx.
  - **Code & outils** : compilation, Python + GTK4, recherche/Git/terminal/diagnostic/qualité (au choix : debug, Node, Rust, Docker, KVM, GitHub Desktop, éditeurs, SQLite).
  - **Conteneurs & services** : Podman, Forgejo local, pare-feu (au choix : Docker, Cockpit, OpenSSH).
- **Fenêtre de configuration** (`EasySetupConfigWindow`) : un interrupteur par composant (déjà installé signalé), et pour les profils web les champs ServerName, DocumentRoot, mot de passe root MariaDB/MySQL, base et utilisateur à créer (champs sensibles masqués).
- **Fenêtre de progression identique au setup 1 clic** (`EasySetupWindow`, sous-classe de `SetupWindow`) : mêmes étapes cochées en direct, même journal, même barre de progression — sans proposition de redémarrage. Le **setup 1 clic d'origine reste totalement inchangé**.
- **Configuration serveur générée** : hôte virtuel Apache ou Nginx (test `httpd -t` / `nginx -t` avant rechargement, sauvegarde possible), page `index.php` de test, contexte SELinux, `httpd_can_network_connect_db`, et création de la base/utilisateur avec mot de passe root facultatif (MariaDB via socket, MySQL en `caching_sha2_password`), valeurs SQL échappées.

### Modifié
- `APP_VERSION` passe à `0.12.0`, notes de version FR/EN de la boîte « À propos » mises à jour.

## [0.11.0] — 2026-11-26

### Ajouté
- **Section « Serveur web »** (juste après « Développement »), en trois catégories :
  - **Serveurs & langages** : Apache (httpd, mod_ssl), Nginx, PHP 8 + extensions (FPM, mysqlnd, pdo, gd, mbstring, xml, opcache, zip, intl), **PHP ↔ Apache / Nginx** (écrit le handler FastCGI vers `/run/php-fpm/www.sock`, teste `httpd -t` / `nginx -t` avant de recharger), MariaDB, MySQL community, Certbot (Let's Encrypt).
  - **Panneaux & bases de données** : Cockpit (+ paquets, stockage, réseau, Podman, machines virtuelles), phpMyAdmin, Adminer (un seul fichier PHP), Webmin (dépôt officiel).
  - **Réseau & accès** : pare-feu web (http/https), serveur OpenSSH.
- Chaque entrée suit le même modèle : état réel, **installer**, **mettre à jour**, **lancer** (navigateur pour les panneaux, `http://localhost` pour les serveurs) et **désinstaller**, avec notes utiles (port 80 partagé Apache/Nginx, durcissement MariaDB/MySQL, phpMyAdmin limité à localhost, ports Cockpit/Webmin).
- Les services sont activés et démarrés (`systemctl enable --now`), le pare-feu est ouvert pour http/https/cockpit, et les échecs de configuration sont signalés sans casser le serveur en place (test de configuration avant rechargement).

### Modifié
- Le rendu des catalogues est mutualisé (`_build_catalog_page`) entre « Développement » et « Serveur web » ; `_push_dev_entry` revient désormais sur la section d'origine.
- `APP_VERSION` passe à `0.11.0`, notes de version FR/EN de la boîte « À propos » mises à jour.

## [0.10.0] — 2026-11-26

### Ajouté
- **Page « Développement »** (nouvelle section, juste après « IA & Développeur »), organisée en trois catégories :
  - **Composants (socle système)** : compilation (gcc, g++, cmake, meson, ninja, autotools, rpmdevtools), Python + GTK4/Libadwaita (gtk4-devel, libadwaita-devel, blueprint-compiler, appstream), conteneurs (Podman, Distrobox, Toolbox), Docker Engine + Compose, virtualisation KVM/QEMU (virt-manager, GNOME Boxes, OVMF, swtpm), Node.js/npm, Rust.
  - **Outils en ligne de commande** : recherche (ripgrep, fd, bat, eza, fzf, zoxide), Git & plateformes (gh, glab, lazygit, git-delta, git-lfs), terminal (tmux, zellij), diagnostic système (btop, ncdu, duf, fastfetch, hyperfine, lsof, strace, sysstat, perf), debug et profilage (gdb, lldb, valgrind, heaptrack, sysprof), qualité Python (uv, ruff, mypy, pre-commit), JSON/HTTP (jq, yq, httpie), automatisation (just, direnv, shellcheck, shfmt).
  - **Applications graphiques** : VSCodium (renvoie vers son panneau existant), GitHub Desktop (Flatpak Flathub), Forgejo en serveur Git local (binaire officiel, service systemd, SQLite, `http://localhost:3000`), éditeurs terminal (Neovim, Helix), SQLite Browser.
- Chaque entrée affiche son état (`installés/total` ou installé/absent) et propose **installer**, **mettre à jour**, **lancer** (quand pertinent) et **désinstaller** avec confirmation.
- Détection groupée en une seule requête `rpm` (cache 30 s) pour ne pas figer l'interface, et scripts dédiés pour Docker (dépôt docker-ce + compose/buildx), Forgejo (téléchargement Codeberg + unité `forgejo.service`, données dans `/var/lib/forgejo`) et GitHub Desktop.

### Modifié
- `APP_VERSION` passe à `0.10.0`, notes de version FR/EN de la boîte « À propos » mises à jour.
- `_launch_in_terminal()` mutualise le lancement d'une commande dans un terminal (utilisé par Freebuff, Neovim et les autres outils).

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
