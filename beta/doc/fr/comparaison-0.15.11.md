# Comparaison 0.15.11 → bêta

Généré par `tools/compare_stable.py` à partir de `ps5_manager.py` et de `addons/index.json`. Il liste, section par section, les options de la version stable et les greffons disponibles dans la bêta.

| Section | Options stable | Greffons bêta | Paquets stable non couverts |
|---|---|---|---|
| `logs` | 4 | 0 | 0 |
| `library` | 7 | 4 | 0 |
| `aidev` | 15 | 2 | 0 |
| `dev` | 20 | 2 | 74 |
| `websrv` | 13 | 3 | 4 |
| `easy` | 4 | 0 | 0 |
| `services` | 1 | 0 | 0 |
| `fx` | 8 | 4 | 0 |
| `deps` | 11 | 6 | 0 |
| `gaming` | 3 | 3 | 0 |
| `features` | 6 | 2 | 0 |
| `update` | 2 | 2 | 1 |
| `lang` | 3 | 6 | 0 |
| `repos` | 11 | 2 | 0 |
| `users` | 5 | 0 | 0 |
| `fedora` | 4 | 0 | 0 |
| `maint` | 11 | 3 | 0 |
| `power` | 2 | 2 | 0 |
| `fan` | 3 | 1 | 0 |
| `hw` | 6 | 3 | 0 |
| `mesa` | 4 | 3 | 0 |
| `kernel` | 5 | 2 | 0 |
| `fix` | 1 | 1 | 0 |
| `ui_lang` | 0 | 0 | 0 |

## `logs` → logs

Groupes : Suivi en direct & historique · Préférences des journaux

| Option 0.15.11 | Action |
|---|---|
| Fenêtre de log en direct | `—` |
| Journal de cette session | `—` |
| Anciens journaux | `—` |
| Effacer les journaux | `—` |


Tous les paquets de la stable sont couverts.

## `library` → library

Groupes : Logithèque PS5 · IA & Développeur

| Option 0.15.11 | Action |
|---|---|
| <sans titre> | `—` |
| IA & Développeur | `—` |
| Installer | `—` |
| Mettre à jour | `—` |
| Désinstaller | `—` |
| <dynamique> | `show_confirm` |
| Ouvrir la page Flathub | `—` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **app-btop** (`app-btop`) | 1.0.0 | `btop` |
| **app-fastfetch** (`app-fastfetch`) | 1.0.0 | `fastfetch` |
| **app-lutris** (`app-lutris`) | 1.0.0 | `lutris` |
| **app-steam** (`app-steam`) | 1.0.0 | `steam` |

Tous les paquets de la stable sont couverts.

## `aidev` → aidev

Groupes : Outils & Applications IA / Dev · Contrôle des services IA · Modèles IA locaux (Ollama) · Diagnostic & Maintenance IA (PS5)

| Option 0.15.11 | Action |
|---|---|
| Ollama (moteur IA local) | `—` |
| Open WebUI (interface web IA) | `—` |
| VSCodium (éditeur de code libre) | `—` |
| Freebuff (agent de code IA) | `—` |
| Tout démarrer (Ollama + Open WebUI) | `—` |
| Tout arrêter (libérer la RAM) | `—` |
| Ouvrir Open WebUI dans le navigateur | `—` |
| État des conteneurs Podman (podman ps -a) | `—` |
| Logs Open WebUI (podman logs --tail 30) | `—` |
| Gérer les modèles IA (catalogue & installés) | `—` |
| Voir les modèles installés (ollama list) | `—` |
| Modèles actifs en RAM (ollama ps) | `—` |
| Diagnostic RAM / GPU / Disque pour l'IA | `—` |
| Nettoyer les anciennes images Podman | `—` |
| <dynamique> | `—` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **ai-ollama** (`ai-ollama`) | 1.0.0 | — |
| **ai-python** (`ai-python`) | 1.0.0 | `python3`, `python3-pip`, `python3-virtualenv`, `python3-notebook` |

Tous les paquets de la stable sont couverts.

## `dev` → dev

| Option 0.15.11 | Action |
|---|---|
| Socle de compilation | `_build_catalog_page` |
| Python + GTK4 / Libadwaita | `_build_catalog_page` |
| Conteneurs (Podman, Distrobox, Toolbox) | `_build_catalog_page` |
| Docker Engine + Compose | `_build_catalog_page` |
| Virtualisation KVM / QEMU | `_build_catalog_page` |
| Node.js / npm | `_build_catalog_page` |
| Rust / Cargo | `_build_catalog_page` |
| Recherche & navigation | `_build_catalog_page` |
| Git & plateformes (GitHub, GitLab) | `_build_catalog_page` |
| Terminal (tmux, zellij) | `_build_catalog_page` |
| Diagnostic système | `_build_catalog_page` |
| Debug & profilage | `_build_catalog_page` |
| Qualité Python (uv, ruff, mypy) | `_build_catalog_page` |
| JSON & HTTP (jq, yq, httpie) | `_build_catalog_page` |
| Automatisation (just, direnv, shellcheck) | `_build_catalog_page` |
| VSCodium | `_build_catalog_page` |
| GitHub Desktop | `_build_catalog_page` |
| Forgejo (serveur Git local) | `_build_catalog_page` |
| Éditeurs terminal (Neovim, Helix) | `_build_catalog_page` |
| Bases de données (SQLite) | `_build_catalog_page` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **dev-git-tools** (`dev-git-tools`) | 1.0.0 | `git`, `git-lfs`, `gh` |
| **dev-python** (`dev-python`) | 1.0.0 | `python3-devel`, `python3-debugpy`, `python3-flake8`, `python3-black` |

Paquets de la stable sans équivalent dans les greffons : `cmake`, `meson`, `ninja-build`, `pkgconf-pkg-config`, `autoconf`, `automake`, `libtool`, `patch`, `rpmdevtools`, `rpmlint`, `python3-pytest`, `gobject-introspection-devel`, `gtk4-devel`, `libadwaita-devel`, `libsecret-devel`, `blueprint-compiler`, `desktop-file-utils`, `appstream`, `gtk4-devel-tools`, `devhelp`, `podman`, `podman-docker`, `buildah`, `skopeo`, `distrobox`, `qemu-kvm`, `libvirt`, `virt-install`, `virt-manager`, `virt-viewer`, `gnome-boxes`, `edk2-ovmf`, `swtpm`, `swtpm-tools`, `rust`, `cargo`, `rustfmt`, `clippy`, `ripgrep`, `fd-find`, `bat`, `eza`, `fzf`, `zoxide`, `glab`, `lazygit`, `git-delta`, `tmux`, `ncdu`, `duf`, `hyperfine`, `lsof`, `strace`, `ltrace`, `sysstat`, `perf`, `gdb`, `lldb`, `valgrind`, `heaptrack`, `sysprof`, `ruff`, `mypy`, `pre-commit`, `jq`, `yq`, `httpie`, `just`, `direnv`, `shellcheck`, `neovim`, `helix`, `sqlite`, `sqlitebrowser`

## `websrv` → websrv

| Option 0.15.11 | Action |
|---|---|
| Apache (httpd) | `_build_catalog_page` |
| Nginx | `_build_catalog_page` |
| PHP 8 + extensions | `_build_catalog_page` |
| PHP ↔ Apache / Nginx (FastCGI) | `_build_catalog_page` |
| MariaDB | `_build_catalog_page` |
| MySQL (community) | `_build_catalog_page` |
| Certbot (HTTPS Let's Encrypt) | `_build_catalog_page` |
| Panneau web Cockpit | `_build_catalog_page` |
| phpMyAdmin | `_build_catalog_page` |
| Adminer | `_build_catalog_page` |
| Webmin | `_build_catalog_page` |
| Pare-feu web (80 / 443 / 9090) | `_build_catalog_page` |
| Serveur OpenSSH (accès distant) | `_build_catalog_page` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **web-db** (`web-db`) | 1.0.0 | `mariadb-server` |
| **web-httpd** (`web-httpd`) | 1.0.0 | `httpd`, `php`, `php-mysqlnd` |
| **web-nginx** (`web-nginx`) | 1.0.0 | `nginx` |

Paquets de la stable sans équivalent dans les greffons : `certbot`, `python3-certbot-apache`, `python3-certbot-nginx`, `openssh-server`

## `easy` → easy

Groupes : Installation facile · Réinitialiser · Bon à savoir

| Option 0.15.11 | Action |
|---|---|
| <sans titre> | `—` |
| Désinstaller des composants… | `—` |
| Nettoyer les fichiers du manager | `—` |
| Purger le cache DNF (dnf clean all) | `—` |


Tous les paquets de la stable sont couverts.

## `services` → services

Groupes : Raccourcis

| Option 0.15.11 | Action |
|---|---|
| Couper les daemons inutiles | `show_confirm` |


Tous les paquets de la stable sont couverts.

## `fx` → audio / video

Groupes : Effets audio (FX Sound) · Vidéo · Bon à savoir

| Option 0.15.11 | Action |
|---|---|
| Installer Easy Effects | `show_confirm` |
| Easy Effects | `—` |
| Presets communautaires (JackHack96) | `—` |
| Installer les presets communautaires (option 1 : tout) | `show_confirm` |
| Codecs audio et vidéo | `—` |
| Installer les codecs audio et vidéo | `show_confirm` |
| FFmpeg (codecs complets) | `—` |
| Installer FFmpeg | `show_confirm` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **audio-easyeffects** (`audio-easyeffects`) | 1.0.0 | `easyeffects` |
| **audio-presets-jackhack** (`audio-presets-jackhack`) | 1.0.0 | — |
| **codecs-av** (`codecs-av`) | 1.0.1 | `gstreamer1-plugins-good`, `gstreamer1-plugins-bad-free`, `gstreamer1-plugins-bad-free-extras`, `gstreamer1-plugins-ugly`, `gstreamer1-plugin-libav`, `gstreamer1-plugins-bad-freeworld`, `gstreamer1-plugin-openh264`, `libavcodec-freeworld`, `lame`, `x264-libs`, `x265-libs` |
| **ffmpeg-full** (`ffmpeg-full`) | 1.0.0 | `ffmpeg`, `libavcodec-freeworld` |

Tous les paquets de la stable sont couverts.

## `deps` → deps

Groupes : Paquets système · Python 3 · Node.js / npm

| Option 0.15.11 | Action |
|---|---|
| Fuse (fusermount) | `—` |
| Steam — pilotes graphiques 32 bits | `—` |
| Python 3 + pip | `—` |
| Créer l'environnement virtuel my_project | `—` |
| Vérifier les versions Python | `—` |
| Tkinter (python3-tkinter) | `—` |
| Installer Node.js + npm | `—` |
| Mettre à jour (dépôts Fedora) | `—` |
| Passer à la version majeure récente (NodeSource 26 LTS) | `—` |
| Vérifier les versions Node.js | `—` |
| Désinstaller Node.js + npm | `—` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **deps-32bit** (`deps-32bit`) | 1.0.0 | `mesa-vulkan-drivers.i686`, `mesa-dri-drivers.i686`, `libva.i686` |
| **deps-build** (`deps-build`) | 1.0.0 | `gcc`, `gcc-c++`, `make`, `kernel-devel`, `dkms`, `openssl-devel` |
| **deps-fuse** (`deps-fuse`) | 1.0.0 | `fuse`, `fuse-libs` |
| **deps-network** (`deps-network`) | 1.0.0 | `curl`, `wget`, `rsync`, `openssh-clients` |
| **deps-node** (`deps-node`) | 1.0.0 | `nodejs`, `npm` |
| **deps-tkinter** (`deps-tkinter`) | 1.0.0 | `python3-tkinter` |

Tous les paquets de la stable sont couverts.

## `gaming` → gaming

Groupes : Gamescope / session Steam Big Picture

| Option 0.15.11 | Action |
|---|---|
| Installer Gamescope | `—` |
| Désinstaller Gamescope | `—` |
| Journal du mode Gaming | `—` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **gaming-gamemode** (`gaming-gamemode`) | 1.0.0 | `gamemode` |
| **gaming-gamescope** (`gaming-gamescope`) | 1.0.0 | `gamescope`, `mangohud` |
| **gaming-mangohud** (`gaming-mangohud`) | 1.0.0 | `mangohud` |

Tous les paquets de la stable sont couverts.

## `features` → features

Groupes : Gestion mobile · Imprimantes & scanners

| Option 0.15.11 | Action |
|---|---|
| Installer GSConnect, MTP / SSHFS et ADB / Fastboot | `—` |
| Installer l'impression et la numérisation | `—` |
| Activer le service d'impression (CUPS) | `—` |
| Couper et désactiver le service CUPS | `—` |
| Désactiver les sockets d'activation automatique | `—` |
| Voir l'état du service CUPS | `—` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **feature-cockpit** (`feature-cockpit`) | 1.0.0 | `cockpit`, `cockpit-storaged`, `cockpit-networkmanager` |
| **feature-toolbox** (`feature-toolbox`) | 1.0.0 | `toolbox` |

Tous les paquets de la stable sont couverts.

## `update` → update

Groupes : PS5 Fedora Manager

| Option 0.15.11 | Action |
|---|---|
| Mettre à jour le manager + ses dépendances | `—` |
| Désinstaller complètement le manager | `—` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **update-beta** (`update-beta`) | 1.0.0 | — |
| **update-system** (`update-system`) | 1.0.0 | — |

Paquets de la stable sans équivalent dans les greffons : `xhost`

## `lang` → lang

Groupes : Langues & clavier

| Option 0.15.11 | Action |
|---|---|
| Voir les langpacks installés (système + clavier) | `—` |
| Installer une langue | `—` |
| Configuration intégrale (langue + clavier + compte) | `—` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **lang-de** (`lang-de`) | 1.0.0 | `langpacks-de` |
| **lang-es** (`lang-es`) | 1.0.0 | `langpacks-es` |
| **lang-fr** (`lang-fr`) | 1.0.0 | `langpacks-fr` |
| **lang-it** (`lang-it`) | 1.0.0 | `langpacks-it` |
| **lang-ja** (`lang-ja`) | 1.0.0 | `langpacks-ja` |
| **lang-pt** (`lang-pt`) | 1.0.0 | `langpacks-pt` |

Tous les paquets de la stable sont couverts.

## `repos` → repos

Groupes : Dépôts · <dynamique>

| Option 0.15.11 | Action |
|---|---|
| Voir tous les dépôts (RPM + Flatpak) | `—` |
| Installer RPM Fusion (free + nonfree) | `—` |
| Installer Flathub (portée système) | `—` |
| Mettre à jour les dépôts & nettoyer le cache | `—` |
| Activer le dépôt fedora-cisco-openh264 | `—` |
| Installer les codecs multimédias (RPM Fusion) | `—` |
| Ajouter un dépôt personnalisé (URL .repo) | `—` |
| Installer / réparer les paquets du bureau | `—` |
| Désactiver un dépôt DNF | `—` |
| Supprimer un dépôt DNF (fichier .repo) | `—` |
| Supprimer un dépôt Flatpak | `—` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **repo-flathub** (`repo-flathub`) | 1.0.0 | — |
| **repo-rpmfusion** (`repo-rpmfusion`) | 1.0.0 | `rpmfusion-free-release`, `rpmfusion-nonfree-release` |

Tous les paquets de la stable sont couverts.

## `users` → users

Groupes : Utilisateurs

| Option 0.15.11 | Action |
|---|---|
| Voir la liste des utilisateurs | `—` |
| <dynamique> | `—` |
| Ajouter un utilisateur | `—` |
| Supprimer un compte utilisateur | `—` |
| Compte root : état et mot de passe | `—` |


Tous les paquets de la stable sont couverts.

## `fedora` → fedora

Groupes : Mises à jour Fedora

| Option 0.15.11 | Action |
|---|---|
| Mettre à jour les applications (DNF & Flatpak) | `—` |
| Mettre à jour le système complet | `—` |
| Mettre à jour les langpacks | `—` |
| Rafraîchir les métadonnées des dépôts | `—` |


Tous les paquets de la stable sont couverts.

## `maint` → maint

Groupes : Maintenance · Maintenance KDE Plasma

| Option 0.15.11 | Action |
|---|---|
| Nettoyage complet | `—` |
| Nettoyer uniquement le cache DNF | `—` |
| Supprimer les paquets orphelins (autoremove) | `—` |
| Réduire les journaux systemd (7 jours) | `—` |
| Nettoyer /tmp et /var/tmp | `—` |
| Nettoyer les vignettes utilisateur | `—` |
| Reconstruire la base des applications | `—` |
| Reconstruire le cache des polices | `—` |
| Supprimer les anciens kernels (garder 2) | `—` |
| Voir l'espace disque utilisé (df -h) | `—` |
| Reconstruire le cache des menus KDE | `—` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **maint-clean** (`maint-clean`) | 1.0.0 | — |
| **maint-flatpak** (`maint-flatpak`) | 1.0.0 | — |
| **maint-trim** (`maint-trim`) | 1.0.0 | `util-linux` |

Tous les paquets de la stable sont couverts.

## `power` → power

Groupes : Alimentation

| Option 0.15.11 | Action |
|---|---|
| Activer la veille complète | `—` |
| Désactiver la veille complète | `—` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **power-profiles** (`power-profiles`) | 1.0.0 | `power-profiles-daemon` |
| **power-tlp** (`power-tlp`) | 1.0.0 | `tlp`, `tlp-rdw` |

Tous les paquets de la stable sont couverts.

## `fan` → fan

Groupes : Ventilateur

| Option 0.15.11 | Action |
|---|---|
| Voir le status complet (services + ps5_control) | `—` |
| Relancer ps5fan.service | `—` |
| Installer / mettre à jour ps5-linux-tools | `—` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **fan-tools** (`fan-tools`) | 1.0.0 | — |

Tous les paquets de la stable sont couverts.

## `hw` → hardware

Groupes : Hardware Control · Hardware Control Plugin

| Option 0.15.11 | Action |
|---|---|
| Vérifier la présence du matériel PS5 | `—` |
| Installer / Mettre à jour PS5 Hardware Control | `—` |
| Vérifier les mises à jour sur GitHub | `—` |
| Désinstaller PS5 Hardware Control | `—` |
| Installer le plugin Hardware Control | `—` |
| Désinstaller le plugin Hardware Control | `—` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **hw-decky-loader** (`hw-decky-loader`) | 1.0.0 | — |
| **hw-decky-ps5-plugin** (`hw-decky-ps5-plugin`) | 1.0.0 | — |
| **hw-hwcon-gui** (`hw-hwcon-gui`) | 1.0.1 | `python3-PyQt6` |

Tous les paquets de la stable sont couverts.

## `mesa` → mesa

Groupes : Mesa / Vulkan

| Option 0.15.11 | Action |
|---|---|
| Installer les outils Vulkan & Mesa demos | `—` |
| Mettre à jour les paquets Mesa & Vulkan | `—` |
| Vérifier la prise en charge RADV (GPU AMD PS5) | `—` |
| Afficher le résumé Vulkan complet | `—` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **mesa-freeworld** (`mesa-freeworld`) | 1.0.0 | `mesa-va-drivers-freeworld`, `mesa-vdpau-drivers-freeworld` |
| **mesa-tools** (`mesa-tools`) | 1.0.0 | `mesa-demos` |
| **mesa-vulkan** (`mesa-vulkan`) | 1.0.0 | `vulkan-tools`, `vulkan-loader-devel` |

Tous les paquets de la stable sont couverts.

## `kernel` → kernel

Groupes : Kernel PS5

| Option 0.15.11 | Action |
|---|---|
| Vérifier la dernière version disponible | `—` |
| Installer le dernier kernel PS5 (RPM) | `—` |
| Installer un kernel précis (toutes les releases) | `—` |
| Choisir le kernel à démarrer (/boot/efi) | `—` |
| Nettoyer / supprimer d'anciens kernels | `—` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **kernel-headers** (`kernel-headers`) | 1.0.0 | `kernel-headers`, `kernel-devel` |
| **kernel-ps5** (`kernel-ps5`) | 1.0.0 | — |

Tous les paquets de la stable sont couverts.

## `fix` → fix

Groupes : Steam

| Option 0.15.11 | Action |
|---|---|
| Relancer Steam | `—` |

| Greffon bêta | Version | Paquets |
|---|---|---|
| **fix-dnf** (`fix-dnf`) | 1.0.0 | — |

Tous les paquets de la stable sont couverts.

## `ui_lang` → ui_lang

Groupes : Langue de l'interface · Couleur d'accentuation GNOME

| Option 0.15.11 | Action |
|---|---|


Tous les paquets de la stable sont couverts.
