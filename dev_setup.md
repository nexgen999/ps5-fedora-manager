# Setup recommandé — configuration de référence

Ce document décrit le **setup recommandé par le développeur** appliqué par
PS5 Fedora Manager (version 0.8). Il est proposé au premier lancement de
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
| Désactiver la mise en veille de l'écran | selon le bureau (voir [Compatibilité](#compatibilité-des-environnements-de-bureau)) : `gsettings set org.gnome.desktop.session idle-delay 0` (GNOME / Budgie), `gsettings set org.cinnamon.desktop.session idle-delay 0` (Cinnamon), `kwriteconfig6 --file powermanagementprofilesrc --group AC --group DimDisplay --key idleTime 0` et `--group DPMSControl --key idleTime 0` (KDE) |
| Désactiver la veille complète | selon le bureau : `sleep-inactive-ac-type nothing` (GNOME / Budgie), `org.cinnamon.settings-daemon.plugins.power sleep-inactive-ac-type nothing` (Cinnamon), `--group SuspendSession --key idleTime 0 --key suspendType 0` (KDE) — utilisateur |

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
| GNOME Extension Manager (GNOME uniquement, retiré ailleurs) | `flatpak install --system -y flathub com.mattjakeman.ExtensionManager` |
| Bypass script compatibility (GNOME uniquement, dans la Logithèque) | `gsettings set org.gnome.shell disable-extension-version-validation true` (utilisateur) |
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

## Compatibilité des environnements de bureau

L'application détecte le bureau au démarrage (variable `PS5_MANAGER_DESKTOP` si
elle est définie, puis `XDG_CURRENT_DESKTOP` / `XDG_SESSION_DESKTOP` /
`DESKTOP_SESSION`, puis l'environnement des processus de l'utilisateur réel,
puis `loginctl show-session -p Desktop`). Le gestionnaire de connexion est
celui que systemd démarre réellement (`systemctl show -p Id
display-manager.service`, puis `gdm.service` / `sddm.service` / `lightdm.service`
en secours).

| Élément | GNOME | KDE Plasma | Cinnamon | Budgie |
| --- | --- | --- | --- | --- |
| Veille écran | `gsettings org.gnome.desktop.session idle-delay` | `kwriteconfig6` + Powerdevil (`DimDisplay`, `DPMSControl`) | `gsettings org.cinnamon.desktop.session idle-delay` | `gsettings org.gnome.desktop.session idle-delay` |
| Veille complète | `sleep-inactive-ac-type` (gnome-settings-daemon) | `SuspendSession` (`idleTime`, `suspendType`) | `org.cinnamon.settings-daemon.plugins.power` | `sleep-inactive-ac-type` (gnome-settings-daemon) |
| Veille système (`systemctl mask …`) | oui | oui | oui | oui |
| Logithèque : Extension Manager | affiché | masqué | masqué | masqué |
| Gestion mobile | GSConnect + Nautilus | KDE Connect + Dolphin | MTP / SSHFS + Nemo | MTP / SSHFS + Nautilus |
| Imprimantes & scanners | CUPS + `system-config-printer` | CUPS + `print-manager` | CUPS + `system-config-printer` | CUPS + `system-config-printer` |
| Gamescope / session Steam | GDM | SDDM | GDM ou LightDM | GDM ou LightDM |
| Locale & clavier | `localectl` + AccountsService + `gsettings org.gnome.system.locale` | `localectl` + AccountsService (pas de `gsettings`) | `localectl` + AccountsService | `localectl` + AccountsService + `gsettings` |
| Déconnexion après changement de langue | `gnome-session-quit --logout --force` | `qdbus6 org.kde.Shutdown /Shutdown org.kde.Shutdown.logout` | `cinnamon-session-quit --logout --force` | `gnome-session-quit --logout --force` |
| Couleur d'accentuation | groupe affiché | masqué | masqué | masqué |
| Kernel PS5 (installation, choix au démarrage, suppression) | identique partout : `dnf` / `rpm`, `depmod`, `dracut`, copie sur l'ESP `/boot/efi` | idem | idem | idem |

Remarques :

- Sous KDE Plasma, la configuration est écrite dans
  `~/.config/powermanagementprofilesrc` puis Powerdevil est rechargé
  (`qdbus … org.kde.Solid.PowerManagement.reparseConfiguration`).
- Le **setup recommandé (1 clic)** réutilise exactement ces commandes : l'étape
  1 applique la veille du bureau détecté, le plan ignore l'Extension Manager hors
  GNOME (**28 éléments** au lieu de 29) et l'étape 9 génère le script Gamescope du
  gestionnaire de connexion. Le journal du setup commence par
  « Environnement détecté : bureau · gestionnaire de connexion · session ».
- Gamescope : l'auto-connexion est écrite dans `[daemon]` de
  `/etc/gdm/custom.conf`, dans `/etc/sddm.conf.d/zz-ps5-manager-autologin.conf`
  ou dans `[Seat:*]` de `/etc/lightdm/lightdm.conf`. La session restaurée est
  celle du bureau détecté (`gnome`, `plasma`, `cinnamon`, `budgie-desktop`) et
  non plus « gnome » en dur. Le facteur d'échelle 1.5 de l'écran de connexion
  n'est appliqué que sous GDM.
- **KDE Plasma et Steam rpm** : le script de la section Gaming installe Steam
  en paquet rpm (RPM Fusion nonfree, aligné sur `rpm -E %fedora`) et la session
  l'utilise en priorité. Le HDR/DTM de Gamescope n'est activé que pour amdgpu,
  avec un écran qui annonce le HDR dans son EDID et hors 4K/60 ; sinon la
  session sort en SDR (`HDR/DTM : inactif (raison)` dans `gaming-session.log`).
  `PS5_GAMING_HDR=1` force le HDR, `PS5_GAMING_HDR=0` le coupe. Si Gamescope
  refuse une option HDR (`unrecognized option`), sort aussitôt ou affiche un
  écran noir, la session relance une fois sans HDR
  (`HDR/DTM : desactive (…) : relance en SDR 8 bits`).
- **Mode Gaming** : la session `steam`
  (`/usr/share/wayland-sessions/steam.desktop`) lance `/usr/bin/gamescope-session`,
  qui exécute Gamescope puis, à la fermeture de Steam, rebascule la console sur la
  session du bureau au lieu de relancer la session Gaming en boucle.
  `/usr/bin/steamos-session-select` enregistre la session demandée (bureau ou Gaming)
  et ferme Steam ; `/usr/local/bin/switch-session` met à jour AccountsService **et**
  l'auto-connexion du gestionnaire de connexion, attend la fermeture de la session
  puis redémarre le gestionnaire. Le journal de la session est écrit dans
  `/var/log/ps5-manager/gaming-session.log` et affiché depuis la page « Gaming Mode ».
- **Kernel PS5** : la section n'utilise que des outils système (`dnf` / `rpm`, `depmod`, `dracut`,
  `/etc/kernel/postinst.d/zz-update-boot`, copie de `vmlinuz-*` / `initrd.img-*` vers
  `/boot/efi/bzImage` et `initrd.img`) : aucune commande liée au bureau ou au gestionnaire
  de connexion, donc comportement identique sur les quatre environnements.
- La déconnexion après un changement de langue utilise la commande du bureau détecté et
  retombe sur `loginctl terminate-user` si elle est absente.
- Un bureau non identifié (`unknown`) applique les commandes GNOME par défaut ;
  les interrupteurs de veille apparaissent alors désactivés si `gsettings`
  n'est pas disponible.

## Dépôts, mises à jour et maintenance par bureau

| Élément | Commande / valeur | GNOME | KDE Plasma | Cinnamon | Budgie |
| --- | --- | --- | --- | --- | --- |
| Dépôt du bureau lui-même | aucun dépôt tiers : groupe comps officiel | `@gnome-desktop` | `@kde-desktop-environment` | `@cinnamon-desktop-environment` | `@budgie-desktop-environment` |
| Codecs H.264 | dépôt `fedora-cisco-openh264` (activé depuis la page Dépôts) | oui | oui | oui | oui |
| Codecs multimédias | RPM Fusion (free + nonfree) puis `gstreamer1-plugins-ugly`, `gstreamer1-plugins-bad-free-extras` | oui | oui | oui | oui |
| Applications Flatpak | Flathub (`flatpak remote-add --system --if-not-exists flathub …`) | oui | oui | oui | oui |
| Mises à jour Fedora | `dnf upgrade -y`, `dnf upgrade --refresh -y`, `dnf upgrade -y langpacks-* glibc-langpack-*` | idem | idem | idem | idem |
| Mises à jour Flatpak | `flatpak update --system` **et** `--user --noninteractive` | idem | idem | idem | idem |
| Maintenance commune | `dnf clean all`, `dnf autoremove -y`, `journalctl --vacuum-time=7d`, `/tmp` + `/var/tmp`, vignettes, `update-desktop-database`, `fc-cache -f` | idem | idem | idem | idem |
| Maintenance spécifique | `kbuildsycoca6 --noincremental` (cache des menus) | — | oui | — | — |

Remarques :

- **Aucun dépôt spécifique n'est nécessaire pour KDE Plasma, Cinnamon ou Budgie** : les
  quatre bureaux sont fournis par les dépôts Fedora officiels. La page Dépôts propose
  d'installer ou de réparer le groupe du bureau détecté ; la vérification du groupe
  s'exécute au lancement de l'action (jamais à l'ouverture de la page) et signale
  « groupe introuvable » si la version de Fedora ne le fournit pas.
- Les seuls dépôts complémentaires utiles sont les mêmes partout : **RPM Fusion**
  (codecs, Steam, pilotes), **Flathub** et **fedora-cisco-openh264** (H.264).
- Les commandes de mise à jour et la maintenance commune sont identiques sur les quatre
  environnements ; seul KDE ajoute la reconstruction du cache des menus.

## Déroulement dans l'application

1. **Premier lancement — langue** : la boîte bilingue « Choose your language ·
   Choisissez votre langue » (boutons *English* / *Français*) s'affiche en
   premier et applique immédiatement la langue choisie.
2. **Premier lancement — bienvenue** : une boîte propose « Setup recommandé
   (1 clic) » ou « Configurer moi-même ». Le choix « Configurer moi-même »
   ferme simplement la boîte ; le choix recommandé démarre le setup.
3. **Fenêtre de suivi** (1320 × 800) : à gauche la liste des 9 étapes et de
   leurs 28 ou 29 éléments selon le bureau (`○` en attente, `●` en cours, `✔` validé, `✖` en
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

## Sauvegardes avant modification

Chaque évolution de la version stable commence par une copie complète du projet
dans `backup/stable/v<version>/`, où `<version>` est le numéro courant de
`version.txt` :

```bash
./tools/backup_stable.sh
```

La copie contient tout le dépôt sauf `.git/` et `backup/` : pour restaurer, il
suffit de recopier son contenu par-dessus l'arbre de travail. Voir
`backup/README.md`.
