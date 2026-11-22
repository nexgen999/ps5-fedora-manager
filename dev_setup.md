# Setup recommandé — configuration de référence

Ce document décrit le **setup recommandé par le développeur** appliqué par
PS5 Fedora Manager (version 0.5). Il est proposé au premier lancement de
l'application, puis reste accessible à tout moment via le **menu principal
(burger) → « Effectuer le setup recommandé »**.

Le setup s'exécute en une seule passe, dans l'ordre ci-dessous. Chaque élément
est indépendant : un échec est signalé (✖) et le setup continue avec l'élément
suivant. À la fin, un redémarrage est proposé.

Version anglaise : [dev_setup_en.md](dev_setup_en.md)

> La liste d'origine fournie par le mainteneur comportait deux « étape 4 » ;
> les étapes sont donc numérotées ici de 1 à 9 dans l'ordre réel d'exécution.

---

## 1. Alimentation — section « Alimentation »

| Élément | Commande |
| --- | --- |
| Désactiver la veille système | `systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target` |
| Désactiver la mise en veille de l'écran | `gsettings set org.gnome.desktop.session idle-delay 0` (utilisateur) |
| Désactiver la veille complète | `gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type nothing` (utilisateur) |

## 2. Ventilateur — section « Ventilateur »

| Élément | Commande |
| --- | --- |
| Installer / mettre à jour PS5 Linux Tools | `git clone --depth=1 https://github.com/ps5-linux/ps5-linux-tools` puis `./install.sh` |
| Activer le service ps5fan | `systemctl enable --now ps5fan.service` |
| Activer le service ps5boost (démarrage) | `systemctl enable --now ps5boost.service` |

## 3. Hardware Control — section « Hardware Control »

| Élément | Commande |
| --- | --- |
| Installer / mettre à jour Hardware Control | `dnf install -y python3-PyQt6` puis `curl -fsSL https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-gui/main/install.sh \| bash -s -- --passwordless` (utilisateur) |

## 4. Mesa / Vulkan — section « Mesa / Vulkan »

| Élément | Commande |
| --- | --- |
| Installer Vulkan Tools et Mesa Demos | `dnf install -y vulkan-tools mesa-demos` |

## 5. Dépôts — section « Dépôts »

| Élément | Commande |
| --- | --- |
| Installer RPM Fusion (free + nonfree) | `dnf install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-<VERSION>.noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-<VERSION>.noarch.rpm` |
| Installer Flatpak et Flathub | `dnf install -y flatpak` puis `flatpak remote-add --system --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo` |
| Mettre à jour les dépôts et nettoyer le cache | `dnf clean all && dnf makecache --refresh` puis `flatpak update --appstream -y` |

## 6. Dépendances supplémentaires — section « Dépendances Supplémentaires »

| Élément | Commande |
| --- | --- |
| Installer FUSE | `dnf install -y fuse fuse-libs` |
| Pilotes graphiques 32 bits pour Steam | `dnf install -y mesa-vulkan-drivers.i686 mesa-dri-drivers.i686 libva.i686` |
| Installer Python 3 et pip | `dnf install -y python3 python3-pip` |
| Créer l'environnement virtuel | `python3 -m venv my_project` (dossier personnel de l'utilisateur) |
| Installer Tkinter | `dnf install -y python3-tkinter` |
| Installer Node.js et npm | `dnf install -y nodejs npm` |
| Mettre à jour les paquets Fedora | `dnf upgrade -y --refresh` |

## 7. Logithèque — section « Logithèque »

| Élément | Commande |
| --- | --- |
| Bazaar | `flatpak install --system -y flathub io.github.kolunmi.Bazaar` |
| GNOME Extension Manager | `flatpak install --system -y flathub com.mattjakeman.ExtensionManager` |
| Steam | `dnf install -y steam` (RPM Fusion activé au préalable) |
| Heroic Games Launcher | `flatpak install --system -y flathub com.heroicgameslauncher.hgl` |
| ProtonUp-Qt | `flatpak install --system -y flathub net.davidotek.pupgui2` |
| Decky Loader | `curl -fsSL https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/install_release.sh \| bash` (utilisateur) |
| Universe | `dnf copr enable -y ilyasturki/universe`, `dnf install -y universe universe-desktop`, puis `universe setup` (utilisateur) |
| AppImage Pool | `flatpak install --system -y flathub io.github.prateekmedia.appimagepool` |
| Opera | `flatpak install --system -y flathub com.opera.Opera` |

## 8. Hardware Control — plugin — section « Hardware Control »

| Élément | Commande |
| --- | --- |
| Installer le plugin Hardware Control | `curl -fsSL https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-plugin/main/install.sh \| bash` (utilisateur) |

## 9. Gaming Mode — section « Gaming Mode »

| Élément | Commande |
| --- | --- |
| Installer Gamescope | script d'installation embarqué de la section « Gaming Mode » (Gamescope + session Steam Big Picture) |

---

## Déroulement dans l'application

1. **Premier lancement — langue** : la boîte bilingue « Choose your language ·
   Choisissez votre langue » (boutons *English* / *Français*) s'affiche en
   premier et applique immédiatement la langue choisie.
2. **Premier lancement — bienvenue** : une boîte propose « Setup recommandé
   (1 clic) » ou « Configurer moi-même ». Le choix « Configurer moi-même »
   ferme simplement la boîte ; le choix recommandé démarre le setup.
3. **Fenêtre de suivi** (1320 × 800) : à gauche la liste des 9 étapes et de
   leurs 29 éléments (`○` en attente, `●` en cours, `✔` validé, `✖` en
   échec), à droite le journal complet des commandes, avec une barre de
   progression.
4. **Fin du setup** : la fenêtre de suivi se ferme et un redémarrage est
   proposé (`systemctl reboot`).

La marque du premier lancement est stockée dans
`/etc/ps5-manager/setup-welcome-done` ; supprimer ce fichier réaffiche la
boîte de bienvenue au prochain démarrage.

## Remarques

- L'application s'exécute déjà avec les privilèges root (pkexec / sudo) : les
  commandes système sont lancées directement, et les commandes utilisateur
  (gsettings, venv, Decky, Hardware Control, Universe) avec l'identité de
  l'utilisateur réel.
- Le redémarrage est effectué avec `systemctl reboot` : `sudo dnf reboot`
  n'existe pas dans DNF/DNF5.
- Un dépôt ou un paquet absent (par exemple un service `ps5fan` non fourni par
  PS5 Linux Tools) apparaît en ✖ sans interrompre le reste du setup.
