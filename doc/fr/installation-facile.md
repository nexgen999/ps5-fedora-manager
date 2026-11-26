# Installation facile

Section **Installation facile** du gestionnaire (icône `preferences-other-symbolic`).

Chaque profil ouvre un assistant en trois temps :

1. **Choix des composants** — un interrupteur par composant, rien n'est obligatoire ;
   ceux déjà présents portent la mention *installé*.
2. **Configuration** — selon le profil : port HTTP, ServerName, DocumentRoot,
   réglages PHP, base de données, certificat Let's Encrypt, port et admin Forgejo.
3. **Progression** — la même fenêtre que le setup 1 clic (étapes cochées en direct,
   journal complet, barre de progression), sans proposition de redémarrage.

> Le **setup 1 clic** du menu ⋮ n'a pas été modifié : il reste la voie « console de
> jeu » d'origine. Les profils réutilisent son moteur et sa fenêtre.

## Les 6 profils

| Profil | Composants par défaut | Options |
|---|---|---|
| **Serveur web LAMP** | Apache, PHP + handler FastCGI, MariaDB, phpMyAdmin, pare-feu | MySQL, Adminer, Cockpit, Certbot, OpenSSH |
| **Serveur web LEMP** | Nginx, PHP + handler FastCGI, MariaDB, phpMyAdmin, pare-feu | idem |
| **WordPress** | LAMP + téléchargement de WordPress + `wp-config.php` généré | idem |
| **Code & outils** | compilation, Python/GTK4, recherche CLI, Git, terminal, diagnostic, qualité Python | debug, données, automatisation, Node, Rust, Docker, KVM, GitHub Desktop, éditeurs, SQLite |
| **Conteneurs & services** | Podman, Forgejo, Cockpit, pare-feu | Docker, OpenSSH |
| **Tout-en-un** | outils de développement + conteneurs + Cockpit + pare-feu | toute la liste dev + services |

## Les 15 options de configuration

| Champ | Défaut | Effet |
|---|---|---|
| Nom du serveur (ServerName) | `localhost` | directive `ServerName` du vhost |
| Port HTTP | `80` | `Listen`/`listen`, ouverture `firewall-cmd` si ≠ 80 |
| Dossier web (DocumentRoot) | `/var/www/html` | racine du site (chemins normalisés) |
| Mémoire PHP (`memory_limit`) | `256M` | `/etc/php.d/99-ps5-easy.ini` |
| Taille d'envoi PHP (`upload_max_filesize`) | `64M` | idem, + `post_max_size` |
| Fuseau horaire PHP (`date.timezone`) | `Europe/Paris` | idem |
| Mot de passe root MariaDB/MySQL | *(vide)* | `ALTER USER root` (socket côté MariaDB) |
| Base de données à créer | `app` | `CREATE DATABASE … utf8mb4` |
| Utilisateur de la base | `appuser` | `CREATE USER` + `GRANT ALL` sur la base |
| Mot de passe de la base | *(vide)* | mot de passe de cet utilisateur |
| Domaine pour HTTPS | *(vide)* | `certbot --apache|--nginx -d … --redirect` |
| E-mail Let's Encrypt | *(vide)* | `-m` de Certbot (obligatoire avec le domaine) |
| Port Forgejo | `3000` | `HTTP_PORT` dans `/etc/forgejo/app.ini` |
| Compte admin Forgejo | *(vide)* | `forgejo admin user create --admin` |
| Mot de passe admin Forgejo | *(vide)* | mot de passe de ce compte |

Les champs sensibles sont masqués. Les valeurs sont assainies avant écriture :
port 1–65535, tailles `N[KMG]`, fuseau `Area/City`, nom d'hôte `[A-Za-z0-9.-]`,
identifiants SQL `[A-Za-z0-9_]`, chaînes SQL échappées (`'` → `''`).

## Ce qui est écrit sur le disque

| Fichier | Contenu |
|---|---|
| `/etc/httpd/conf.d/ps5-easy.conf` | hôte virtuel Apache + page `index.php` de test |
| `/etc/nginx/conf.d/ps5-easy.conf` | bloc `server` Nginx |
| `/etc/php.d/99-ps5-easy.ini` | `memory_limit`, `upload_max_filesize`, `post_max_size`, `max_execution_time`, `date.timezone` |
| `<docroot>/index.php` | page de test PHP |
| `<docroot>/wp-config.php` | uniquement profil WordPress, sel aléatoire (`openssl rand -hex 32`) |
| `/etc/forgejo/app.ini` | port HTTP réécrit (profil Conteneurs & services) |
| `/tmp/ps5-easy-db.sql` | script SQL temporaire, supprimé après exécution |

## Commandes utiles

```bash
# Vérifier la syntaxe puis recharger
# httpd -t && systemctl reload httpd
# nginx -t && systemctl reload nginx

# Vérifier PHP
# php -v
# php -i | grep -E 'memory_limit|upload_max_filesize|date.timezone'

# Tester le site
$ curl -I http://ps5.local:8080/
$ curl -s http://127.0.0.1/index.php

# Base de données
# mariadb -u root -e 'SHOW DATABASES;'
# mysql -u appuser -p -e 'SHOW TABLES;' app

# Certificat
# certbot certificates

# Forgejo
# systemctl status forgejo
# journalctl -u forgejo -n 50 --no-pager
```

## Comportement en cas d'échec

- Une étape en erreur est marquée **✖** et l'installation continue : les autres
  composants ne sont pas bloqués.
- Si `httpd -t` ou `nginx -t` refuse la configuration, **le serveur en place n'est
  pas rechargé** : le message indique le fichier à corriger.
- Un profil peut être relancé : les paquets déjà installés sont mis à jour, les
  fichiers de configuration réécrits.

## Après l'installation

1. Ouvrir `http://<nom-du-serveur>:<port>/` depuis la PS5 ou une autre machine.
2. phpMyAdmin : `http://<serveur>/phpmyadmin/` · Adminer : `/adminer.php`.
3. WordPress : `http://<serveur>/wp-admin/install.php` pour finir l'assistant.
4. Cockpit : `https://<serveur>:9090`.

Voir [serveur-web.md](serveur-web.md) pour les détails Apache/Nginx/PHP et
[reinitialisation.md](reinitialisation.md) pour tout retirer proprement.
