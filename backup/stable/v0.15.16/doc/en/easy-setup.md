# Easy setup

The **Easy setup** section of the manager (`preferences-other-symbolic`).

Each profile opens a three-step assistant:

1. **Component selection** — one switch per component, nothing is mandatory;
   already-installed ones are tagged *installed*.
2. **Configuration** — depending on the profile: HTTP port, ServerName, DocumentRoot,
   PHP settings, database, Let's Encrypt certificate, Forgejo port and admin account.
3. **Progress** — the same window as the 1-click setup (steps checked live, full log,
   progress bar), without the reboot prompt.

> The **1-click setup** in the ⋮ menu is untouched: it remains the original
> “gaming console” path. Profiles reuse its engine and its window.

## The 6 profiles

| Profile | Default components | Options |
|---|---|---|
| **LAMP web server** | Apache, PHP + FastCGI handler, MariaDB, phpMyAdmin, firewall | MySQL, Adminer, Cockpit, Certbot, OpenSSH |
| **LEMP web server** | Nginx, PHP + FastCGI handler, MariaDB, phpMyAdmin, firewall | same |
| **WordPress** | LAMP + WordPress download + generated `wp-config.php` | same |
| **Code & tools** | build tools, Python/GTK4, CLI search, Git, terminal, diagnostics, Python quality | debug, data, automation, Node, Rust, Docker, KVM, GitHub Desktop, editors, SQLite |
| **Containers & services** | Podman, Forgejo, Cockpit, firewall | Docker, OpenSSH |
| **All-in-one** | development tools + containers + Cockpit + firewall | full dev + services list |

## The 15 configuration options

| Field | Default | Effect |
|---|---|---|
| Server name (ServerName) | `localhost` | vhost `ServerName` |
| HTTP port | `80` | `Listen`/`listen`, `firewall-cmd` opening when ≠ 80 |
| Web root (DocumentRoot) | `/var/www/html` | site root (normalised paths) |
| PHP memory (`memory_limit`) | `256M` | `/etc/php.d/99-ps5-easy.ini` |
| PHP upload size (`upload_max_filesize`) | `64M` | same file, plus `post_max_size` |
| PHP timezone (`date.timezone`) | `Europe/Paris` | same file |
| MariaDB/MySQL root password | *(empty)* | `ALTER USER root` (socket for MariaDB) |
| Database to create | `app` | `CREATE DATABASE … utf8mb4` |
| Database user | `appuser` | `CREATE USER` + `GRANT ALL` on the database |
| Database password | *(empty)* | password of that user |
| Domain for HTTPS | *(empty)* | `certbot --apache|--nginx -d … --redirect` |
| Let's Encrypt email | *(empty)* | Certbot `-m` (required with the domain) |
| Forgejo port | `3000` | `HTTP_PORT` in `/etc/forgejo/app.ini` |
| Forgejo admin account | *(empty)* | `forgejo admin user create --admin` |
| Forgejo admin password | *(empty)* | password of that account |

Sensitive fields are masked. Values are sanitised before use: port 1–65535,
sizes `N[KMG]`, timezone `Area/City`, hostname `[A-Za-z0-9.-]`, SQL identifiers
`[A-Za-z0-9_]`, SQL strings escaped (`'` → `''`).

## What is written to disk

| File | Content |
|---|---|
| `/etc/httpd/conf.d/ps5-easy.conf` | Apache virtual host + test `index.php` |
| `/etc/nginx/conf.d/ps5-easy.conf` | Nginx `server` block |
| `/etc/php.d/99-ps5-easy.ini` | `memory_limit`, `upload_max_filesize`, `post_max_size`, `max_execution_time`, `date.timezone` |
| `<docroot>/index.php` | PHP test page |
| `<docroot>/wp-config.php` | WordPress profile only, random salt (`openssl rand -hex 32`) |
| `/etc/forgejo/app.ini` | HTTP port rewritten (Containers & services profile) |
| `/tmp/ps5-easy-db.sql` | temporary SQL script, removed after execution |

## Useful commands

```bash
# Check syntax, then reload
# httpd -t && systemctl reload httpd
# nginx -t && systemctl reload nginx

# Check PHP
# php -v
# php -i | grep -E 'memory_limit|upload_max_filesize|date.timezone'

# Test the site
$ curl -I http://ps5.local:8080/
$ curl -s http://127.0.0.1/index.php

# Database
# mariadb -u root -e 'SHOW DATABASES;'
# mysql -u appuser -p -e 'SHOW TABLES;' app

# Certificate
# certbot certificates

# Forgejo
# systemctl status forgejo
# journalctl -u forgejo -n 50 --no-pager
```

## When something fails

- A failing step is marked **✖** and the install continues: other components are not blocked.
- If `httpd -t` or `nginx -t` rejects the configuration, **the running server is not
  reloaded**: the message names the file to fix.
- A profile can be run again: installed packages are updated, configuration files rewritten.

## After the install

1. Open `http://<server-name>:<port>/` from the PS5 or another machine.
2. phpMyAdmin: `http://<server>/phpmyadmin/` · Adminer: `/adminer.php`.
3. WordPress: `http://<server>/wp-admin/install.php` to finish the wizard.
4. Cockpit: `https://<server>:9090`.

See [web-server.md](web-server.md) for Apache/Nginx/PHP details and
[reset.md](reset.md) to remove everything cleanly.
