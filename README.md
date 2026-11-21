<div align="center">

  <h1>PS5 Fedora Manager</h1>

  <p>
    <img src="assets/Logo_fedoralogo.png" alt="PS5 Fedora Project Logo" width="180" />
  </p>

  <p>
    <a href="https://fedoraproject.org/">
      <img src="https://img.shields.io/badge/OS-Fedora%2045-blue?logo=fedora" alt="Fedora" />
    </a>
    <a href="https://github.com/ps5-linux">
      <img src="https://img.shields.io/badge/Hardware-PlayStation%205-black?logo=playstation" alt="Hardware" />
    </a>
    <a href="LICENSE">
      <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
    </a>
  </p>

</div>

---

Gestionnaire système, matériel et logiciel conçu pour **Fedora Linux (Fedora 45 / GNOME)** sur **PlayStation 5**, doté d'une interface native **Python + PyGObject (GTK4 & Libadwaita)** harmonisée automatiquement avec la couleur d'accentuation et le mode clair/sombre de GNOME.

---

## Présentation du projet

**PS5 Fedora Manager** centralise la configuration et la maintenance d'une console PS5 sous Fedora Linux dans une interface inspirée des **Paramètres GNOME** :

* **Interface native GTK4 / Libadwaita** : `AdwNavigationSplitView`, `AdwPreferencesPage`, `AdwAlertDialog`, support complet de l'accentuation système GNOME (`org.gnome.desktop.interface accent-color` & `color-scheme`) même lors de l'exécution en `root` via `pkexec`.
* **Journal en direct (PTY)** : suivi temps réel des commandes DNF, Flatpak, Git et RPM avec historique des 14 derniers jours dans `/var/log/ps5-manager`.
* **Logithèque PS5 organisée par catégories** :
  * **Gaming** : Steam (active RPM Fusion automatiquement), Heroic Games Launcher, ProtonUp-Qt, Decky Loader, **Universe** (COPR `ilyasturki/universe` + `universe setup`).
  * **Navigateurs** : Opera, Brave (choix RPM officiel ou Flatpak).
  * **Système & Utilitaires** : Etcher (RPM GitHub), Bazaar, GNOME Extension Manager.
* **Gestion du Kernel PS5 (`ps5-linux-patches`)** : vérification des releases GitHub, installation RPM (`rpm -ivh --nosignature --replacefiles`), `depmod`, `zz-update-boot` sur `/boot/efi`, choix du noyau au démarrage et suppression sécurisée des anciens paquets `linux-ps5-*` (avec protection du noyau actif et de `/boot/efi/bzImage`).
* **Matériel PS5 & Graphique** : contrôle des services `ps5fan.service` / `ps5boost.service`, installation de `ps5-linux-tools` et `ps5-hwcon-gui`, vérification des nœuds `hwmon`/`sysfs`, diagnostic Mesa / Vulkan / RADV.
* **Alimentation GNOME & Système** : gestion de la mise en veille système (`systemd`), écran (`gsettings idle-delay`) et veille complète.
* **Système Fedora** : langues & clavier (`localectl` + AccountsService), dépôts RPM Fusion & Flathub, utilisateurs, mises à jour DNF/Flatpak, maintenance & nettoyage.
* **Bilingue FR / EN** : changement immédiat depuis l'interface, mémorisé dans `/etc/ps5-manager/language`.

---

## Prérequis

* **Fedora Linux 41 à 45** (Workstation / GNOME recommandé) sur architecture `x86_64`
* Connexion Internet (pour DNF, Flatpak, COPR et GitHub)
* Droits administrateur (`sudo` / `pkexec`)

Le script `install.sh` installe automatiquement toutes les dépendances nécessaires :
`python3`, `python3-gobject`, `gtk4`, `libadwaita`, `gobject-introspection`, `polkit`, `glib2`, `xhost`, `curl`, `git`, `desktop-file-utils`, `util-linux`.

---

## Installation

### Méthode recommandée (via Git)

```bash
git clone https://github.com/nexgen999/ps5-fedora-manager.git
cd ps5-fedora-manager
chmod +x install.sh
./install.sh
```

L'installeur effectue automatiquement :
1. L'installation des paquets GTK4 / Libadwaita / Polkit requis.
2. Le déploiement des fichiers dans `/opt/ps5-manager` et `/usr/local/bin/ps5-manager` (avec les droits `root:root`, `0755`/`0644`).
3. La création du raccourci bureau (`/usr/share/applications/ps5-manager.desktop`) et de la règle Polkit (`allow_gui=true`).
4. L'application des contextes SELinux (`restorecon`).

### Lancement

* Depuis le menu des applications GNOME : recherchez **PS5 Fedora Manager**
* Ou depuis un terminal :

```bash
ps5-manager
```

*(L'application demande automatiquement l'authentification administrateur via `pkexec` au démarrage.)*

---

## Mise à jour

### Depuis l'interface graphique (recommandé)

1. Ouvrez **PS5 Fedora Manager**.
2. Allez dans la section **Mise à jour du manager**.
3. Cliquez sur **Mettre à jour le manager + ses dépendances**.

Le gestionnaire met à jour les dépendances GTK4/Libadwaita si besoin, récupère la dernière version depuis GitHub (`git fetch` + `reset --hard origin/main`), réinstalle le binaire et réapplique automatiquement les permissions, la règle Polkit et les contextes SELinux.

### Depuis le terminal

```bash
cd /opt/ps5-manager
sudo git fetch --all --prune
sudo git reset --hard origin/main
sudo ./install.sh
```

---

## Désinstallation

### Depuis l'interface graphique

1. Ouvrez **PS5 Fedora Manager** → **Mise à jour du manager**.
2. Cliquez sur **Désinstaller complètement le manager** puis confirmez.

### Depuis le terminal

```bash
sudo rm -rf \
  /opt/ps5-manager \
  /usr/local/bin/ps5-manager \
  /usr/share/applications/ps5-manager.desktop \
  /usr/share/pixmaps/ps5-manager.png \
  /usr/share/polkit-1/actions/io.github.nexgen999.ps5-manager.policy
sudo update-desktop-database /usr/share/applications/ >/dev/null 2>&1 || true
```

*(Optionnel — pour supprimer également la configuration de langue et les journaux :)*

```bash
sudo rm -rf /etc/ps5-manager /var/log/ps5-manager
```

---

## Structure du dépôt

```text
ps5-fedora-manager/
├── ps5_manager.py        # Application principale Python (GTK4 / Libadwaita)
├── install.sh            # Script d'installation (dépendances, droits, Polkit, SELinux)
├── ps5-manager.desktop   # Lanceur d'application GNOME
├── icon.png              # Icône de l'application (optionnelle)
└── README.md             # Documentation du projet
```
