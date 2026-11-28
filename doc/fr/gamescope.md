# Gamescope — scripts externes

Deux façons d'installer la session Gamescope / Steam Big Picture :

1. **Section Gaming du gestionnaire** (recommandé) : le script est intégré à
   l'application, adapté au bureau détecté.
2. **Scripts externes** dans `external_addons/` : autonomes, modifiables, sans
   dépendance à `ps5_manager.py`.

## Les 8 scripts

| Fichier | Bureau |
|---|---|
| `gamescope_install_gnome.sh` | GNOME (GDM) |
| `gamescope_uninstall_gnome.sh` | GNOME |
| `gamescope_install_kde.sh` | KDE Plasma (SDDM) |
| `gamescope_uninstall_kde.sh` | KDE |
| `gamescope_install_cinnamon.sh` | Cinnamon (LightDM) |
| `gamescope_uninstall_cinnamon.sh` | Cinnamon |
| `gamescope_install_budgie.sh` | Budgie (SDDM depuis Fedora 44, LightDM avant) |
| `gamescope_uninstall_budgie.sh` | Budgie |

## Utilisation

```bash
# Depuis un clone du dépôt
# sudo bash external_addons/gamescope_install_budgie.sh

# Choisir le compte qui sera auto-connecté
# sudo bash external_addons/gamescope_install_budgie.sh --user moncompte

# Ajouter la session sans basculer automatiquement au démarrage
# sudo bash external_addons/gamescope_install_budgie.sh --no-autologin

# Retour au bureau d'origine
# sudo bash external_addons/gamescope_uninstall_budgie.sh
```

Options communes : `--user <compte>`, `--no-autologin`. Sans option, le compte est
déduit de `SUDO_USER`.

## Ce que l'installation met en place

| Élément | Rôle |
|---|---|
| `/usr/bin/gamescope-session` | lance Gamescope + Steam en Big Picture |
| `/usr/local/bin/switch-session` | bascule bureau ↔ Gaming (`desktop` / `steam`) |
| `/usr/share/wayland-sessions/*.desktop` | session « Gaming » dans l'écran de connexion |
| `/etc/sddm.conf.d/zz-ps5-manager-autologin.conf` (KDE) ou LightDM/GDM équivalent | auto-connexion sur la session Gaming |
| règle polkit | `switch-session` utilisable sans mot de passe par le compte ciblé |
| unité / drop-in systemd | dépendances graphiques nécessaires |

Le script résout le nom **réel** de la session du bureau au runtime (par exemple
`budgie-desktop`, `budgie`, `ubuntu-budgie-desktop`), pour que le retour « desktop »
fonctionne même si l'identifiant de session a changé.

## Utilisation au quotidien

```bash
# Basculer vers la session Gaming (depuis le bureau)
$ switch-session steam
# ou, sans droits particuliers
$ sudo -n /usr/local/bin/switch-session steam

# Revenir au bureau
$ switch-session desktop

# Auto-connexion : vérifier la configuration
$ cat /etc/sddm.conf.d/zz-ps5-manager-autologin.conf
# cat /etc/lightdm/lightdm.conf

# Journal des bascules
$ tail -f /var/log/ps5-manager/session-switch.log
```

## Désinstallation

Le script `uninstall` retire : la session Wayland, `gamescope-session`,
`switch-session`, la règle polkit, l'auto-connexion et le drop-in système. Il
**conserve** les paquets (`gamescope`, `steam`) et les données Steam.

```bash
# Vérifier ce qui reste
$ ls /usr/share/wayland-sessions/
$ which gamescope-session switch-session
```

## Diagnostic (avant tout correctif)

`tools/diagnostic_gaming.sh` collecte en **lecture seule** tout ce qu'il faut
pour savoir pourquoi la session Gaming se referme — bureau et variables de
session, gestionnaire de connexion réel, sessions installées
(`wayland-sessions` / `xsessions`), `Session=` d'AccountsService, auto-connexion
SDDM / LightDM / GDM, fichiers du mode Gaming, accès `/dev/dri` et groupes,
présence de `gamescope`, `steam` et d'un Steam Flatpak, journaux du manager et
journal systemd.

```bash
cd /opt/ps5-manager
sudo bash tools/diagnostic_gaming.sh | tee ~/diagnostic-gaming.txt
```

Le fichier ne contient aucun mot de passe ni donnée Steam : il peut être
partagé tel quel. Il ne modifie rien.

À lire en premier, section 12 : `gaming-session.log` indique lequel des trois
cas s'est produit — `steam introuvable`, `aucun /dev/dri/card* lisible` ou
`gamescope termine (code N)`.

## Dépannage

| Symptôme | Piste |
|---|---|
| Écran noir au démarrage | `journalctl -b -u gdm` (ou `sddm`, `lightdm`) et `session-switch.log` |
| Retour bureau impossible | la session du bureau est mal résolue : vérifier `/usr/share/xsessions/` |
| La session Gaming revient aussitôt au bureau | `gaming-session.log` : `steam introuvable` (Steam Flatpak), `aucun /dev/dri/card* lisible` (groupes `video`/`render`) ou `gamescope termine (code N)` |
| `switch-session` demande un mot de passe | règle polkit absente : relancer le script d'installation |
| Steam ne démarre pas en Big Picture | lancer `steam -gamepadui` en terminal pour voir l'erreur |
| Deux sessions « Gaming » | ancien script d'un autre bureau : lancer le script `uninstall` correspondant |
