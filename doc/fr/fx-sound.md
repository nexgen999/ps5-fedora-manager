# FX Sound (Easy Effects)

Section **FX Sound** (`audio-volume-high-symbolic`, juste après *Services*).

Elle installe deux éléments, l'un après l'autre :

1. **Easy Effects** — l'égaliseur système pour PipeWire ;
2. **les presets communautaires** de JackHack96 — une dizaine de réglages prêts à
   l'emploi, appliqués en un clic.

Chaque ligne porte une **pastille d'état** lue sur le système :

- **● Installé** — le paquet `easyeffects` est présent (ou des presets existent) ;
- **○ Non installé** — rien n'est installé ;
- le sous-titre de la ligne des presets indique le **nombre de presets** trouvés.

## 1. Easy Effects

Commande exécutée par l'application (elle tourne déjà en root via `pkexec`, donc pas
de `sudo` interne) :

```bash
# dnf install -y easyeffects
```

Équivalent manuel dans un terminal :

```bash
$ sudo dnf install easyeffects

# Vérifier l'installation
$ rpm -q easyeffects
$ easyeffects --version

# Lancer l'application
$ easyeffects
```

Easy Effects est un greffon PipeWire : il n'y a **rien à configurer dans PipeWire**,
l'application crée ses propres nœuds virtuels au premier lancement.

## 2. Presets communautaires (option 1 : tout)

Commande d'origine, telle qu'elle est lancée dans l'application :

```bash
$ bash -c "$(curl -fsSL https://raw.githubusercontent.com/JackHack96/EasyEffects-Presets/master/install.sh)"
```

Ce script affiche un menu interactif :

```
Please select an option for presets installation (Default=1)
1) Install all presets
2) Install Perfect EQ preset
3) Install all bass boosting presets
4) Install Advanced Auto Gain
5) Install Laptop speaker preset
6) Install loudness + autogain laptop preset
7) Install Dolby Atmos preset
8) Install Speaker Sync preset
```

L'application **répond automatiquement `1`**, ce qui installe tous les presets sans
aucune question. La commande réellement exécutée est donc :

```bash
$ printf '1\n' | bash <(curl -fsSL https://raw.githubusercontent.com/JackHack96/EasyEffects-Presets/master/install.sh)
```

L'option 1 installe :

| Preset | Usage |
|---|---|
| Perfect EQ | égalisation neutre, bon point de départ |
| Bass Enhancing + Perfect EQ | basses renforcées |
| Bass Enhancing + Perfect EQ – Low Latency | idem, latence réduite (jeux) |
| Boosted | gain général plus fort |
| Bass Boosted | basses marquées |
| Advanced Auto Gain | volume constant entre les sources |
| Loudness + Autogain | loudness et gain automatique |
| Dolby Atmos | rendu spatial (casque / HDMI) |
| Speaker Sync | synchronisation des haut-parleurs |
| Laptop | rendu « petit haut-parleur » |
| Impulse responses | fichiers `.irs` utilisés par certains presets |

Les presets sont installés **pour le compte de bureau**, jamais dans `/root` : le
script est lancé avec l'identité de l'utilisateur réel (`PKEXEC_UID` / `SUDO_USER`).

```
~/.local/share/easyeffects/
├── output/    # presets de sortie (.json)
├── input/     # presets d'entrée (.json)
└── irs/       # réponses impulsionnelles (.irs)
```

## 3. Utiliser un preset

1. ouvrir **Easy Effects** depuis le menu des applications ;
2. onglet **Presets** (ou *Output* → *Presets*) ;
3. choisir par exemple **Dolby Atmos** ou **Perfect EQ** ;
4. vérifier la sortie dans **GNOME → Son** : la PS5 sort en général par **HDMI**.

Easy Effects doit **rester lancé** (fenêtre ou arrière-plan) pour que les effets
s'appliquent ; c'est un traitement temps réel, pas un réglage écrit dans le matériel.

## Vérifications utiles

```bash
# Presets présents
$ ls ~/.local/share/easyeffects/output | wc -l
$ ls ~/.local/share/easyeffects/irs | head

# Paquet installé et version
$ rpm -q easyeffects

# Périphériques PipeWire / sortie utilisée
$ pactl info | grep "Default Sink"
$ wpctl status

# Easy Effects tourne-t-il ?
$ pgrep -a easyeffects
```

## Dépannage

| Symptôme | Piste |
|---|---|
| « Aucun preset installé » après l'installation | le script a été lancé avec un autre compte : vérifier `~/.local/share/easyeffects` de l'utilisateur de bureau |
| Le script échoue tout de suite | pas de réseau, ou `curl` absent : `sudo dnf install curl` |
| Les presets n'apparaissent pas dans l'application | relancer Easy Effects (les presets sont lus au démarrage) |
| Aucun effet audible | Easy Effects n'est pas lancé, ou la mauvaise sortie est sélectionnée |
| Son coupé / grésillements | choisir un preset « Low Latency », ou baisser le nombre d'effets actifs |
| `easyeffects` introuvable dans le menu | relancer la session (fichier `.desktop` mis en cache) |

## Désinstallation

```bash
# Retirer les presets (compte de bureau)
$ rm -rf ~/.local/share/easyeffects

# Retirer l'application
$ sudo dnf remove easyeffects
```

La section ne modifie aucun fichier de configuration système : supprimer le paquet et
le dossier `~/.local/share/easyeffects` remet le son d'origine.
