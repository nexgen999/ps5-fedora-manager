# `ps5m/system.py`

Lecture seule de l'état du système, sans GTK ni root.

| Fonction | Rôle |
|---|---|
| `rpm_present(packages)` | `{paquet: bool}` en un seul appel `rpm -q --qf` |
| `expand_path(pattern)` | `~`, `$HOME`, `/home/*/x` → chemins existants |
| `path_present(patterns)` | `{motif: bool}` |
| `home()` | dossier personnel |

`rpm_present` gère l'architecture : demander `mesa-va-drivers-freeworld` trouve
aussi `mesa-va-drivers-freeworld.x86_64`, et demander `paquet.i686` ne confond
pas avec la version 64 bits.

Ces fonctions ne lèvent rien : sans `rpm`, tout est simplement considéré absent,
et la pastille affiche `○`.
