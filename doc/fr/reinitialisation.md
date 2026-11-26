# Réinitialisation / désinstallation

Section **Installation facile**, groupe **Réinitialiser** — pour repartir d'une base
propre sans laisser de configuration orpheline.

## Trois outils

| Outil | Effet |
|---|---|
| **Désinstaller des composants…** | page listant les composants réellement installés, un interrupteur par composant, puis `dnf remove` via la fenêtre de progression |
| **Nettoyer les fichiers du manager** | supprime les configurations écrites par l'application |
| **Purger le cache DNF** | `dnf clean all` (espace disque uniquement) |

## Désinstaller des composants

1. Ouvrir *Installation facile* → **Désinstaller des composants…**.
2. La page n'affiche que ce qui est installé (sinon le message « Aucun composant
   installé à désinstaller »).
3. Décocher ce qui doit rester, puis **Désinstaller la sélection** → confirmation.
4. Chaque composant devient une étape `dnf remove` dans la fenêtre de progression, avec
   son journal. Un échec n'arrête pas les suivants.

Les options de nettoyage (fichiers de configuration, cache DNF) sont incluses dans le
même passage et cochées par défaut.

## Ce que « Nettoyer les fichiers du manager » supprime

```bash
rm -f /etc/httpd/conf.d/ps5-easy.conf
rm -f /etc/nginx/conf.d/ps5-easy.conf
rm -f /etc/php.d/99-ps5-easy.ini
rm -f /var/www/html/adminer.php
rm -f /etc/yum.repos.d/webmin.repo
# supprimé seulement si Docker n'est plus installé :
rm -f /etc/yum.repos.d/docker-ce.repo
rm -f /tmp/ps5-easy-db.sql
systemctl daemon-reload
# recharge httpd / nginx si leur configuration reste valide
```

Ensuite, relancer l'un des profils réécrit ces fichiers proprement.

## Ce qui n'est **pas** supprimé

- les **bases de données** (`/var/lib/mysql`) et les fichiers de site (`/var/www/html`,
  y compris `wp-config.php`) ;
- les **paquets** tant que la désinstallation n'est pas lancée ;
- les **données Forgejo** (`/var/lib/forgejo`) ;
- les journaux du gestionnaire (`/var/log/ps5-manager/`).

Suppression manuelle, uniquement si c'est vraiment voulu :

```bash
# Base de données (irréversible)
# mariadb -u root -e 'DROP DATABASE app;'

# Site web
# rm -rf /var/www/html/*

# Données Forgejo
# systemctl disable --now forgejo
# rm -rf /var/lib/forgejo

# Journal du gestionnaire
# rm -rf /var/log/ps5-manager
```

## Tout remettre à zéro, étape par étape

```bash
# 1. Couper les services concernés (page Services)
# systemctl disable --now httpd nginx php-fpm mariadb forgejo docker

# 2. Désinstaller les composants (page Réinitialiser)

# 3. Nettoyer les configurations (page Réinitialiser)

# 4. Purger le cache
# dnf clean all

# 5. Vérifier
# rpm -qa | grep -E 'httpd|nginx|php|mariadb|mysql|forgejo|docker'
# ss -tlnp | grep -E ':80|:443|:3306|:3000|:9090'
```

## Réinstaller après un reset

Les profils sont idempotents : relancer *Installation facile* sur un système nettoyé
repart de zéro (paquets + configuration). Le setup 1 clic du menu ⋮ reste disponible et
n'a pas été modifié.

## Dépannage

| Symptôme | Piste |
|---|---|
| Un composant reste installé | dépendance d'un autre paquet : `dnf remove` puis lire le message |
| `httpd -t` échoue après nettoyage | un fichier de config a été modifié à la main : `httpd -t` indique la ligne |
| Site toujours accessible | cache navigateur ou service non redémarré : `systemctl restart httpd` |
| `dnf remove` veut retirer plus que prévu | lire la liste avant de confirmer (le journal la montre) |
