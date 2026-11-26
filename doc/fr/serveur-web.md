# Serveur web

Section **Serveur web** (`network-server-symbolic`). Trois groupes : *Serveurs*,
*Panneaux*, *Réseau*.

## Composants disponibles

| Composant | Paquets / action | Notes |
|---|---|---|
| Apache | `httpd` | écoute le port 80 |
| Nginx | `nginx` | ne peut pas partager le port 80 avec Apache |
| PHP 8 + extensions | `php`, `php-cli`, `php-fpm`, `php-mysqlnd`, `php-gd`, `php-mbstring`, `php-xml`, `php-json`, `php-opcache`, `php-intl`, `php-zip`, `php-curl` | |
| Handler PHP ↔ Apache/Nginx | script dédié | écrit la passerelle FastCGI puis teste la config |
| MariaDB | `mariadb-server` | `systemctl enable --now mariadb` |
| MySQL (community) | `mysql-server` | alternative à MariaDB |
| Certbot | `certbot`, `python3-certbot-apache`, `python3-certbot-nginx` | HTTPS Let's Encrypt |
| phpMyAdmin | `phpmyadmin` | dans `/usr/share/phpmyadmin`, alias Apache |
| Adminer | script dédié | fichier unique `/var/www/html/adminer.php` |
| Cockpit | `cockpit`, `cockpit-storaged`, `cockpit-networkmanager`, `cockpit-podman` | `https://<hôte>:9090` |
| Webmin | dépôt officiel + `webmin` | `https://<hôte>:10000` |
| Pare-feu web | `firewalld` + ouverture 80/443/9090 | `firewall-cmd --permanent` |
| OpenSSH | `openssh-server` | accès distant |

## Ce que fait le handler PHP

Pour **Apache**, il écrit la configuration `mod_php`/FastCGI et recharge `httpd`.
Pour **Nginx**, il écrit le bloc `location ~ \.php$` vers `php-fpm` (socket
`/run/php-fpm/www.sock`) et recharge `nginx`.

Les deux vérifient la syntaxe avant de recharger :

```bash
# httpd -t
# nginx -t
```

Si le test échoue, le serveur en place continue de tourner avec l'ancienne
configuration : rien n'est cassé.

## Commandes essentielles

```bash
# État des services
# systemctl status httpd nginx php-fpm mariadb --no-pager

# Démarrer / arrêter / relancer
# systemctl enable --now httpd
# systemctl disable --now nginx
# systemctl restart php-fpm

# Journaux
# journalctl -u httpd -n 50 --no-pager
# journalctl -u nginx -n 50 --no-pager
# tail -f /var/log/httpd/error_log
# tail -f /var/log/nginx/error.log

# Ports écoutés
# ss -tlnp | grep -E ':80|:443|:8080'

# SELinux (contexte des fichiers web + accès réseau des bases)
# semanage fcontext -a -t httpd_sys_content_t "/var/www/html(/.*)?"
# restorecon -Rv /var/www/html
# setsebool -P httpd_can_network_connect_db on

# Pare-feu
# firewall-cmd --list-all
# firewall-cmd --permanent --add-service=http --add-service=https
# firewall-cmd --reload
```

## Bases de données

MariaDB sur Fedora utilise l'authentification par socket pour `root` : aucun mot de
passe n'est nécessaire en local.

```bash
# mariadb -u root
```

Le profil *WordPress* / *LAMP* peut définir un mot de passe root (connexion TCP
possible ensuite) et créer une base + un utilisateur :

```sql
CREATE DATABASE IF NOT EXISTS `app` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'appuser'@'localhost' IDENTIFIED BY 'motdepasse';
GRANT ALL PRIVILEGES ON `app`.* TO 'appuser'@'localhost';
FLUSH PRIVILEGES;
```

MySQL utilise `caching_sha2_password` ; le même script est généré avec les bonnes
instructions pour les deux moteurs.

## HTTPS avec Certbot

Renseigner **Domaine pour HTTPS** et **E-mail Let's Encrypt** dans le profil, cocher
Certbot. L'étape lancée est :

```bash
# certbot --apache -d site.example.com --non-interactive --agree-tos -m moi@example.com --redirect
```

Prérequis : le domaine doit résoudre vers la PS5 et le port 80 être joignable depuis
Internet. Vérification et renouvellement :

```bash
# certbot certificates
# systemctl list-timers | grep certbot
# certbot renew --dry-run
```

## Panneaux d'administration

| Panneau | URL | Compte |
|---|---|---|
| Cockpit | `https://<hôte>:9090` | utilisateur Linux (sudo) |
| phpMyAdmin | `http://<hôte>/phpmyadmin/` | utilisateur MariaDB |
| Adminer | `http://<hôte>/adminer.php` | idem |
| Webmin | `https://<hôte>:10000` | root |

## Dépannage

| Symptôme | Piste |
|---|---|
| 403 Forbidden | contexte SELinux : `restorecon -Rv /var/www/html` |
| 502 Bad Gateway (Nginx) | `php-fpm` arrêté ou mauvais socket : `systemctl status php-fpm` |
| Page PHP affichée en texte | handler PHP absent : relancer le composant *Handler PHP* |
| `Address already in use` | Apache et Nginx sur le même port : en garder un seul |
| Base inaccessible depuis PHP | `setsebool -P httpd_can_network_connect_db on` |
| Pas d'accès depuis une autre machine | pare-feu : `firewall-cmd --add-service=http` |

Pour tout retirer : voir [reinitialisation.md](reinitialisation.md).
