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

Steam peut être le paquet rpm (commande `steam`) **ou** le Flatpak
`com.valvesoftware.Steam` — le cas de Budgie, où le rpm ne s'installe pas. La
session Gaming choisit le lanceur disponible au démarrage ; `--mangoapp` n'est
utilisé qu'avec le rpm, un Flatpak filtrant `LD_PRELOAD`.

Un Flatpak a besoin d'un **bus de session D-Bus** : sur un TTY, logind crée
`/run/user/<uid>/bus` sans l'exporter, et le bac à sable se refermait aussitôt
(`Primary child shut down`). La session l'exporte désormais elle-même (repli
`dbus-run-session` s'il n'existe pas), et journalise le bus retenu ainsi que la
ligne de commande complète de Gamescope.

## KDE Plasma (Fedora 45) et Steam en RPM

Sous KDE Plasma, la session Gaming utilise le **paquet rpm** `steam` (RPM
Fusion nonfree). Le script d'installation l'installe quand la commande manque :
RPM Fusion est activé pour la version courante de Fedora (`rpm -E %fedora`, 45
incluse), puis `steam` et `steam-devices` sont installés ; le Flatpak ne sert
que de repli si l'installation échoue. L'auto-connexion SDDM
(`/etc/sddm.conf.d/zz-ps5-manager-autologin.conf`) et le nom de session
(`plasma`) sont résolus à l'exécution, donc la bascule et le retour au bureau
fonctionnent sans réglage supplémentaire.

## HDR / DTM et compatibilité des pilotes

Gamescope n'active le HDR — et son tone mapping dynamique (DTM) — que si les
trois conditions sont réunies :

| Condition | Trace dans le journal |
|---|---|
| pilote **amdgpu/RADV** (NVIDIA et Intel restent en SDR) | `pilote : amd, Mesa 25.x, sortie DP-1 2560x1440` |
| écran annonçant le HDR dans son **EDID** (bloc CTA-861, tag étendu `0x06`) | idem |
| sortie non 4K/60 (le 10 bits n'a pas la bande passante du lien) | idem |

La session ajoute alors `--hdr-enabled --hdr-itm-enabled` et écrit
`HDR/DTM : actif (…)` ; sinon elle écrit
`HDR/DTM : inactif (<raison>) : sortie SDR 8 bits` et lance Gamescope en 8 bits.
Pour forcer ou couper le HDR : `PS5_GAMING_HDR=1` ou `PS5_GAMING_HDR=0` dans
l'environnement de la session.

Le HDR du bureau KDE (Configuration du système > Affichage) n'est pas transmis à
Gamescope : la session repart de l'EDID. Si l'image reste délavée en HDR,
relancer avec `PS5_GAMING_HDR=0`.

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
| La session Gaming revient aussitôt au bureau | `gaming-session.log` : `steam introuvable` (Steam Flatpak), `aucun /dev/dri/card* lisible` (groupes `video`/`render`), `Primary child shut down` (bus D-Bus absent) ou `gamescope termine (code N)` |
| Écran noir puis « affichage impossible » | HDR activé par Steam en 4K60 : l'enchaînement `HDR output enabled` / `Failed to prepare 1-layer flip` montre que le lien n'a pas la bande passante du 10 bits. Dans Steam : *Paramètres > Affichage* → désactiver HDR, puis relancer le mode Gaming |
| Steam Flatpak se referme aussitôt | le bac à sable exige un bus D-Bus de session : la session exporte `unix:path=/run/user/<uid>/bus` (ou se replie sur `dbus-run-session`) ; vérifier la ligne `bus de session` dans le journal |
| `HDR/DTM : inactif` alors que l'écran est HDR | la session n'active le HDR que sur amdgpu, avec un EDID HDR et hors 4K/60 : vérifier `pilote :` et la raison entre parenthèses ; `PS5_GAMING_HDR=1` force l'essai |
| `gamescope: unrecognized option` en HDR | le build installé refuse les options HDR : le journal affiche `HDR/DTM : desactive (…)` puis une seconde ligne `lancement : gamescope …` sans HDR — c'est le repli SDR 8 bits, voulu. Le nom du tone mapping inverse est repris de `gamescope --help` ; vérifier la version avec `gamescope --version` |
| Image délavée ou blanche en HDR | le tone mapping ne correspond pas à l'écran : relancer avec `PS5_GAMING_HDR=0` (SDR) et laisser HDR désactivé dans Steam |
| Steam rpm absent sous KDE Plasma | relancer l'installation du mode Gaming (RPM Fusion + `steam`) ou installer Steam depuis la Logithèque, puis vérifier `Steam rpm : …` dans le journal |
| `switch-session` demande un mot de passe | règle polkit absente : relancer le script d'installation |
| Steam ne démarre pas en Big Picture | lancer `steam -gamepadui` en terminal pour voir l'erreur |
| Deux sessions « Gaming » | ancien script d'un autre bureau : lancer le script `uninstall` correspondant |
