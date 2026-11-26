# Documentation — PS5 Fedora Manager

Documentation des fonctions ajoutées à partir de la version **0.12** : installation
facile, serveur web, page Développement, services on/off, scripts Gamescope externes,
Freebuff et réinitialisation.

La documentation existe en deux langues, avec le même contenu :

| Sujet | Français | English |
|---|---|---|
| Index | [doc/fr/README.md](fr/README.md) | [doc/en/README.md](en/README.md) |
| Installation facile (profils) | [fr/installation-facile.md](fr/installation-facile.md) | [en/easy-setup.md](en/easy-setup.md) |
| Serveur web (Apache, Nginx, PHP, MariaDB) | [fr/serveur-web.md](fr/serveur-web.md) | [en/web-server.md](en/web-server.md) |
| Page Développement | [fr/developpement.md](fr/developpement.md) | [en/development.md](en/development.md) |
| Services on/off | [fr/services.md](fr/services.md) | [en/services.md](en/services.md) |
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
