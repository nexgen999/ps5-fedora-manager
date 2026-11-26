# Freebuff

Freebuff est proposé dans la section **IA & Développeur**, sous VSCodium. C'est un
outil en ligne de commande (paquet npm global `freebuff`), pas une application graphique.

## Ce que fait le gestionnaire

| Action | Détail |
|---|---|
| Installation | vérifie Node.js/npm, installe `freebuff` en global si absent |
| Détection | lit la version dans `package.json` du paquet global |
| Lancement | ouvre le terminal disponible (voir liste ci-dessous) et exécute `freebuff` |

Terminaux testés, dans l'ordre : `ptyxis`, `kgx` (GNOME Console), `gnome-terminal`,
`konsole`, `xfce4-terminal`, `mate-terminal`, `tilix`, `xterm`.

## Commandes manuelles

```bash
# Vérifier Node.js et npm
$ node --version
$ npm --version

# Installer / mettre à jour
# npm install -g freebuff
# npm update -g freebuff

# Version installée
$ npm ls -g freebuff --depth=0
$ freebuff --version

# Emplacement du binaire
$ which freebuff

# Désinstaller
# npm uninstall -g freebuff
```

Si `npm` est absent :

```bash
# dnf install -y nodejs npm
```

## Lancement

```bash
$ freebuff
```

Le gestionnaire ouvre un terminal puis lance la commande, pour que la session
interactive reste utilisable. Le journal de l'application enregistre la tentative.

## Dépannage

| Symptôme | Piste |
|---|---|
| « Freebuff introuvable » après installation | nouveau shell (PATH `/usr/local/bin`) |
| Version vide alors que le binaire existe | paquet installé hors npm global (binaire seul) |
| Aucun terminal trouvé | installer `ptyxis` ou `gnome-terminal`, ou lancer `freebuff` à la main |
| `EACCES` pendant l'installation | éviter `sudo npm` : utiliser un préfixe utilisateur (`npm config set prefix ~/.npm-global`) |

Pour retirer complètement : voir [reinitialisation.md](reinitialisation.md)
(`npm uninstall -g freebuff`).
