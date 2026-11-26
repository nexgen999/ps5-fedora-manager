# Services (on/off)

Section **Services (marche/arrêt)** (`system-run-symbolic`, juste après
*Installation facile*).

Chaque ligne de la page est un **interrupteur** relié à une unité systemd :

- interrupteur **allumé** → le service tourne **et** redémarre au boot ;
- interrupteur **éteint** → service arrêté **et** désactivé (`disable`).

L'état affiché est réel : il est lu avec `systemctl show` au moment de l'ouverture de
la page. Un service absent du système apparaît automatiquement masqué, aucun
interrupteur n'est proposé pour lui.

## Unités suivies

| Groupe | Unités |
|---|---|
| Serveurs web & bases | `httpd`, `nginx`, `php-fpm`, `mariadb`, `mysqld` |
| Conteneurs & forges | `docker`, `podman.socket`, `forgejo` |
| Système & accès distant | `firewalld`, `sshd`, `cockpit.socket` |
| À couper pour gagner en performance | `bluetooth`, `cups`, `avahi-daemon`, `ModemManager` |

## Raccourci « Couper les daemons inutiles »

Bouton rouge en bas de page, avec confirmation : il exécute

```bash
# systemctl disable --now bluetooth cups avahi-daemon ModemManager
```

(uniquement pour les unités réellement présentes). La page se recharge ensuite pour
afficher les nouveaux états. C'est **réversible** : rallumer l'interrupteur suffit.

Gain typique sur une PS5 transformée en console de jeu ou en serveur : plusieurs
dizaines de Mo de RAM et des réveils CPU en moins. Les paquets restent installés, donc
aucune réinstallation n'est nécessaire pour revenir en arrière.

## Commandes correspondantes

```bash
# Voir l'état exact (actif / activé au démarrage)
# systemctl show -p ActiveState -p UnitFileState httpd

# Équivalents manuels des interrupteurs
# systemctl enable --now httpd      # allumer
# systemctl disable --now httpd     # éteindre

# Redémarrer sans changer l'état au boot
# systemctl restart php-fpm

# Liste des services actifs, triés par mémoire
$ systemctl list-units --type=service --state=running
$ systemd-cgtop -m --iterations=1

# Vérifier ce qui démarre au boot
$ systemctl list-unit-files --state=enabled
```

## Points d'attention

- **`sshd`** : le couper supprime l'accès distant (garder un accès clavier/écran).
- **`firewalld`** : le couper désactive le filtrage réseau.
- **`mariadb` / `mysqld`** : un site PHP tombera en erreur de connexion.
- **`httpd` / `nginx`** : ne pas les laisser actifs ensemble sur le port 80.
- **`cockpit.socket`** : coupé, `https://<hôte>:9090` ne répond plus.
- Les services activés par socket (`podman.socket`, `cockpit.socket`) démarrent à la
  demande : l'interrupteur les active/désactive proprement.

## Dépannage

| Symptôme | Piste |
|---|---|
| L'interrupteur revient en arrière | action refusée (droits, unité masquée) : lire le message et le journal |
| Service « introuvable » | composant non installé : l'installer depuis *Serveur web* ou *Développement* |
| Service redémarre tout seul | dépendance ou socket : `systemctl status <unité>` |
| Besoin de masquer complètement | `systemctl mask <unité>` (plus fort que `disable`) |
