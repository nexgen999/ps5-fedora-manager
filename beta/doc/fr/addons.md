# Référence des greffons

Chaque option de l'application est un script `.sh` autonome dans `beta/addons/`. Ce tableau est **généré** depuis `addons/index.json` par `tools/docs.py` : il reflète exactement ce qui est livré.

## Alimentation

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **power-profiles** (`power-profiles`) | 1.0.0 | `power-profiles-daemon` | paquets RPM et/ou chemins |
| **power-tlp** (`power-tlp`) | 1.0.0 | `tlp`, `tlp-rdw` | paquets RPM et/ou chemins |

## Audio

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **audio-easyeffects** (`audio-easyeffects`) | 1.0.0 | `easyeffects` | paquets RPM et/ou chemins |
| **audio-presets-jackhack** (`audio-presets-jackhack`) | 1.0.0 | — | paquets RPM et/ou chemins |

## Dépendances

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **deps-build** (`deps-build`) | 1.0.0 | `gcc`, `gcc-c++`, `make`, `kernel-devel`, `dkms`, `openssl-devel` | paquets RPM et/ou chemins |
| **deps-network** (`deps-network`) | 1.0.0 | `curl`, `wget`, `rsync`, `openssh-clients` | paquets RPM et/ou chemins |

## Dépôts

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **repo-flathub** (`repo-flathub`) | 1.0.0 | — | paquets RPM et/ou chemins |
| **repo-rpmfusion** (`repo-rpmfusion`) | 1.0.0 | `rpmfusion-free-release`, `rpmfusion-nonfree-release` | paquets RPM et/ou chemins |

## Développement

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **dev-git-tools** (`dev-git-tools`) | 1.0.0 | `git`, `git-lfs`, `gh` | paquets RPM et/ou chemins |
| **dev-python** (`dev-python`) | 1.0.0 | `python3-devel`, `python3-debugpy`, `python3-flake8`, `python3-black` | paquets RPM et/ou chemins |

## Fonctionnalités

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **feature-cockpit** (`feature-cockpit`) | 1.0.0 | `cockpit`, `cockpit-storaged`, `cockpit-networkmanager` | paquets RPM et/ou chemins |
| **feature-toolbox** (`feature-toolbox`) | 1.0.0 | `toolbox` | paquets RPM et/ou chemins |

## Gaming

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **gaming-gamemode** (`gaming-gamemode`) | 1.0.0 | `gamemode` | paquets RPM et/ou chemins |
| **gaming-gamescope** (`gaming-gamescope`) | 1.0.0 | `gamescope`, `mangohud` | paquets RPM et/ou chemins |
| **gaming-mangohud** (`gaming-mangohud`) | 1.0.0 | `mangohud` | paquets RPM et/ou chemins |

## Graphismes

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **mesa-freeworld** (`mesa-freeworld`) | 1.0.0 | `mesa-va-drivers-freeworld`, `mesa-vdpau-drivers-freeworld` | paquets RPM et/ou chemins |
| **mesa-vulkan** (`mesa-vulkan`) | 1.0.0 | `vulkan-tools`, `vulkan-loader-devel` | paquets RPM et/ou chemins |

## IA & développeur

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **ai-ollama** (`ai-ollama`) | 1.0.0 | — | paquets RPM et/ou chemins |
| **ai-python** (`ai-python`) | 1.0.0 | `python3`, `python3-pip`, `python3-virtualenv`, `python3-notebook` | paquets RPM et/ou chemins |

## Langues

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **lang-de** (`lang-de`) | 1.0.0 | `langpacks-de` | paquets RPM et/ou chemins |
| **lang-es** (`lang-es`) | 1.0.0 | `langpacks-es` | paquets RPM et/ou chemins |
| **lang-fr** (`lang-fr`) | 1.0.0 | `langpacks-fr` | paquets RPM et/ou chemins |
| **lang-it** (`lang-it`) | 1.0.0 | `langpacks-it` | paquets RPM et/ou chemins |
| **lang-ja** (`lang-ja`) | 1.0.0 | `langpacks-ja` | paquets RPM et/ou chemins |
| **lang-pt** (`lang-pt`) | 1.0.0 | `langpacks-pt` | paquets RPM et/ou chemins |

## Logithèque

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **app-btop** (`app-btop`) | 1.0.0 | `btop` | paquets RPM et/ou chemins |
| **app-fastfetch** (`app-fastfetch`) | 1.0.0 | `fastfetch` | paquets RPM et/ou chemins |
| **app-lutris** (`app-lutris`) | 1.0.0 | `lutris` | paquets RPM et/ou chemins |
| **app-steam** (`app-steam`) | 1.0.0 | `steam` | paquets RPM et/ou chemins |

## Maintenance

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **maint-clean** (`maint-clean`) | 1.0.0 | — | action (aucun état) |
| **maint-flatpak** (`maint-flatpak`) | 1.0.0 | — | action (aucun état) |
| **maint-trim** (`maint-trim`) | 1.0.0 | `util-linux` | paquets RPM et/ou chemins |

## Matériel

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **hw-decky-loader** (`hw-decky-loader`) | 1.0.0 | — | paquets RPM et/ou chemins |
| **hw-decky-ps5-plugin** (`hw-decky-ps5-plugin`) | 1.0.0 | — | paquets RPM et/ou chemins |
| **hw-hwcon-gui** (`hw-hwcon-gui`) | 1.0.0 | — | paquets RPM et/ou chemins |

## Mises à jour

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **update-beta** (`update-beta`) | 1.0.0 | — | action (aucun état) |
| **update-system** (`update-system`) | 1.0.0 | — | action (aucun état) |

## Noyau

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **kernel-headers** (`kernel-headers`) | 1.0.0 | `kernel-headers`, `kernel-devel` | paquets RPM et/ou chemins |
| **kernel-ps5** (`kernel-ps5`) | 1.0.0 | — | paquets RPM et/ou chemins |

## Réparation

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **fix-dnf** (`fix-dnf`) | 1.0.0 | — | action (aucun état) |

## Serveur web

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **web-db** (`web-db`) | 1.0.0 | `mariadb-server` | paquets RPM et/ou chemins |
| **web-httpd** (`web-httpd`) | 1.0.0 | `httpd`, `php`, `php-mysqlnd` | paquets RPM et/ou chemins |
| **web-nginx** (`web-nginx`) | 1.0.0 | `nginx` | paquets RPM et/ou chemins |

## Ventilateur

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **fan-tools** (`fan-tools`) | 1.0.0 | — | paquets RPM et/ou chemins |

## Vidéo

| Greffon | Version | Paquets | État |
|---|---|---|---|
| **codecs-av** (`codecs-av`) | 1.0.1 | `gstreamer1-plugins-good`, `gstreamer1-plugins-bad-free`, `gstreamer1-plugins-bad-free-extras`, `gstreamer1-plugins-ugly`, `gstreamer1-plugin-libav`, `gstreamer1-plugins-bad-freeworld`, `gstreamer1-plugin-openh264`, `libavcodec-freeworld`, `lame`, `x264-libs`, `x265-libs` | paquets RPM et/ou chemins |
| **ffmpeg-full** (`ffmpeg-full`) | 1.0.0 | `ffmpeg`, `libavcodec-freeworld` | paquets RPM et/ou chemins |


## En-tête d'un script

```bash
#!/usr/bin/env bash
#@ id: codecs-av            # identifiant unique = nom du fichier
#@ version: 1.0.1           # comparée par le catalogue (x.y.z)
#@ section: video           # section de la barre latérale
#@ icon: video-x-generic-symbolic
#@ title: Video codecs      # titre anglais
#@ title_fr: Codecs vidéo   # titre français
#@ desc: ...                # description anglaise
#@ desc_fr: ...             # description française
#@ packages: a b c          # état : rpm -q
#@ check_paths: /x /y/*     # état : chemins/globs
#@ needs: repo-rpmfusion    # greffons installés avant
#@ action: yes              # action pure : pas de pastille
#@ root: yes                # exécuté via pkexec
```

Contrat : `--check` renvoie 0 si l'option est déjà installée. Sans paquets, sans chemins et sans `action`, `tools/check.py` refuse le greffon.

_46 addons, 19 sections._
