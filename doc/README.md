# Documentation — PS5 Fedora Manager

Documentation des fonctions ajoutées à partir de la version **0.12** : installation
facile, serveur web, page Développement, services on/off, FX Sound (Easy Effects),
scripts Gamescope externes, Freebuff et réinitialisation.

La documentation existe en deux langues, avec le même contenu :

| Sujet | Français | English |
|---|---|---|
| Index | [doc/fr/README.md](fr/README.md) | [doc/en/README.md](en/README.md) |
| Installation facile (profils) | [fr/installation-facile.md](fr/installation-facile.md) | [en/easy-setup.md](en/easy-setup.md) |
| Serveur web (Apache, Nginx, PHP, MariaDB) | [fr/serveur-web.md](fr/serveur-web.md) | [en/web-server.md](en/web-server.md) |
| Page Développement | [fr/developpement.md](fr/developpement.md) | [en/development.md](en/development.md) |
| Services on/off | [fr/services.md](fr/services.md) | [en/services.md](en/services.md) |
| FX Sound (Easy Effects + presets) | [fr/fx-sound.md](fr/fx-sound.md) | [en/fx-sound.md](en/fx-sound.md) |
| Gamescope (scripts externes) | [fr/gamescope.md](fr/gamescope.md) | [en/gamescope.md](en/gamescope.md) |
| Freebuff | [fr/freebuff.md](fr/freebuff.md) | [en/freebuff.md](en/freebuff.md) |
| Réinitialisation / désinstallation | [fr/reinitialisation.md](fr/reinitialisation.md) | [en/reset.md](en/reset.md) |

## Conventions de lecture

- Les chemins sont ceux d'une installation standard (Fedora 41 → 45, x86_64).
- `$` = commande utilisateur, `#` = commande root (`sudo`).
- Toutes les actions de l'application s'exécutent déjà en root (lancement par
  `pkexec`), le mot de passe n'est donc demandé qu'une fois, à l'ouverture.
- Le journal complet de chaque action se trouve dans `/var/log/ps5-manager/`
  (bouton terminal de l'en-tête, ou menu ⋮ → *Informations système*).

## Pastilles d'état

Depuis la 0.15.1, chaque ligne qui installe quelque chose porte la même pastille que
les catalogues :

| Pastille | Sens |
|---|---|
| **● Installé** | tout est présent |
| **◐ 2/3** | installation partielle (le sous-titre donne le détail) |
| **○ Non installé** | rien n'est présent |

Sections concernées : *Installation facile*, *Services*, *FX Sound*, *Dépendances
supplémentaires*, *Add Fedora Feature*, *Gaming Mode*, *Mesa / Vulkan*, *Ventilateur*,
*Hardware Control*, *Dépôts*, *Logithèque* (AppImage Pool, Gear Lever), ainsi que les
catalogues *Développement* et *Serveur web*.

La détection se fait à l'ouverture de la page, sans commande bloquante : `rpm -q`
groupé (architecture comprise), fichiers et unités systemd, dépôts lus dans
`/usr/share/dnf5/repos.d`, `/etc/yum.repos.d` et les overrides
`/etc/dnf/repos.override.d` (dnf5), remotes Flatpak (`flatpak remotes`, `flatpak info`).
