# Couverture de la 0.15.11

État : **toutes les options de la version stable ont un équivalent dans la bêta**.

Mesure par `tools/compare_stable.py` : lecture statique de `ps5_manager.py`
(149 options dans 24 sections, catalogues `DEV_CATALOG` / `WEB_CATALOG` inclus)
puis rapprochement avec les **107 greffons** et les pages dédiées.
Tableaux complets, option par option : [comparaison-0.15.11.md](comparaison-0.15.11.md).

| Indicateur | Valeur |
|---|---|
| options lues dans la stable | 149 |
| greffons bêta | 107 |
| pages dédiées | 10 (journal, à propos, installation facile, logithèque, services, langue, comptes, version de Fedora, noyaux, dépôts) |
| paquets de la stable sans greffon | 1 (`xhost`, inutile ici) |

## Le seul paquet non installé

`xhost` servait à autoriser root à afficher l'interface GTK quand la stable
s'élevait entièrement. La bêta n'élève jamais l'interface : elle appelle
`pkexec` uniquement pour le script d'un greffon `root: yes`. L'autorisation X11
de root n'a donc aucun usage.

## Équivalences notables

| Option stable | Équivalent bêta |
|---|---|
| comptes : lister, ajouter, supprimer | page Utilisateurs (`useradd -m`, `userdel -r`, `passwd` dans un terminal, compte principal protégé) |
| noyaux : choisir, démarrer sur, supprimer | page Noyau (`grubby --set-default`, `dnf remove kernel-core-<v>`, confirmation) |
| dépôts : lister, activer/couper, ajouter, rafraîchir | page Dépôts (`dnf config-manager setopt`, `dnf makecache`, ajout d'un `.repo`) |
| AppImage : installer, lister, désinstaller | page Logithèque (copie dans `~/Applications`, entrée de menu, suppression) |
| installation facile : profils | page Installation facile : recommandé, gaming, streaming, bureautique + nettoyage |
| maintenance : 10 actions | 11 greffons d'action (`maint-*`) |
| IA : Open WebUI, démarrer/arrêter, logs, diagnostic | 8 greffons `ai-*` |
| imprimantes, partage mobile | `feature-print*`, `feature-mobile` |
| jeux : désinstaller, journal | `gaming-uninstall`, `gaming-log` |
| réparation Steam | `fix-steam` |
| dépôts : OpenH264, rafraîchissement | `repos-openh264`, `repos-refresh` |
| système : mise à jour, désinstallation du manager | `update-system`, `update-beta`, `update-uninstall` |
| langues : tout installer | `lang-all` |

## Différences assumées

- **Mode root** : la stable s'élève entièrement ; la bêta reste utilisateur et
  n'élève qu'un greffon à la fois (`pkexec`). C'est plus sûr, et c'est ce qui
  rend `xhost` inutile.
- **Suppression de compte** : `userdel -r` est proposé, mais le compte principal
  (uid 1000) est refusé pour éviter de casser la session.
- **Noyaux** : la suppression est proposée noyau par noyau avec confirmation ;
  aucun nettoyage automatique du noyau courant.
- **Greffons « action »** : les opérations sans état (nettoyage, redémarrage,
  diagnostics) n'affichent pas de pastille et demandent confirmation.

## Ce qui reste hors de portée d'une machine de développement

- Le rendu GTK4/Libadwaita et les boîtes polkit se valident sur la PS5
  (`python3 beta/run.py`), pas ici.
- Les traductions es/it/de/pt méritent une relecture native.
