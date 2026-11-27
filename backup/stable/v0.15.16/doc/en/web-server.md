# Web server

The **Web server** section (`network-server-symbolic`). Three groups: *Servers*,
*Panels*, *Network*.

## Available components

| Component | Packages / action | Notes |
|---|---|---|
| Apache | `httpd` | listens on port 80 |
| Nginx | `nginx` | cannot share port 80 with Apache |
| PHP 8 + extensions | `php`, `php-cli`, `php-fpm`, `php-mysqlnd`, `php-gd`, `php-mbstring`, `php-xml`, `php-json`, `php-opcache`, `php-intl`, `php-zip`, `php-curl` | |
| PHP ↔ Apache/Nginx handler | dedicated script | writes the FastCGI bridge, then tests the config |
| MariaDB | `mariadb-server` | `systemctl enable --now mariadb` |
| MySQL (community) | `mysql-server` | MariaDB alternative |
| Certbot | `certbot`, `python3-certbot-apache`, `python3-certbot-nginx` | Let's Encrypt HTTPS |
| phpMyAdmin | `phpmyadmin` | in `/usr/share/phpmyadmin`, Apache alias |
| Adminer | dedicated script | single file `/var/www/html/adminer.php` |
| Cockpit | `cockpit`, `cockpit-storaged`, `cockpit-networkmanager`, `cockpit-podman` | `https://<host>:9090` |
| Webmin | official repository + `webmin` | `https://<host>:10000` |
| Web firewall | `firewalld` + ports 80/443/9090 | `firewall-cmd --permanent` |
| OpenSSH | `openssh-server` | remote access |

## What the PHP handler does

For **Apache** it writes the `mod_php`/FastCGI configuration and reloads `httpd`.
For **Nginx** it writes the `location ~ \.php$` block pointing at `php-fpm`
(`/run/php-fpm/www.sock`) and reloads `nginx`.

Both check the syntax before reloading:

```bash
# httpd -t
# nginx -t
```

If the test fails, the running server keeps serving with the previous
configuration: nothing breaks.

## Essential commands

```bash
# Service state
# systemctl status httpd nginx php-fpm mariadb --no-pager

# Start / stop / restart
# systemctl enable --now httpd
# systemctl disable --now nginx
# systemctl restart php-fpm

# Logs
# journalctl -u httpd -n 50 --no-pager
# journalctl -u nginx -n 50 --no-pager
# tail -f /var/log/httpd/error_log
# tail -f /var/log/nginx/error.log

# Listening ports
# ss -tlnp | grep -E ':80|:443|:8080'

# SELinux (web file context + database network access)
# semanage fcontext -a -t httpd_sys_content_t "/var/www/html(/.*)?"
# restorecon -Rv /var/www/html
# setsebool -P httpd_can_network_connect_db on

# Firewall
# firewall-cmd --list-all
# firewall-cmd --permanent --add-service=http --add-service=https
# firewall-cmd --reload
```

## Databases

MariaDB on Fedora uses socket authentication for `root`: no password is needed locally.

```bash
# mariadb -u root
```

The *WordPress* / *LAMP* profiles can set a root password (TCP login then works) and
create a database plus a user:

```sql
CREATE DATABASE IF NOT EXISTS `app` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'appuser'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON `app`.* TO 'appuser'@'localhost';
FLUSH PRIVILEGES;
```

MySQL uses `caching_sha2_password`; the same script is generated with the right
statement for both engines.

## HTTPS with Certbot

Fill in **Domain for HTTPS** and **Let's Encrypt email** in the profile, tick Certbot.
The step that runs is:

```bash
# certbot --apache -d site.example.com --non-interactive --agree-tos -m me@example.com --redirect
```

Requirements: the domain must resolve to the PS5 and port 80 must be reachable from
the Internet. Checking and renewing:

```bash
# certbot certificates
# systemctl list-timers | grep certbot
# certbot renew --dry-run
```

## Admin panels

| Panel | URL | Account |
|---|---|---|
| Cockpit | `https://<host>:9090` | Linux user (sudo) |
| phpMyAdmin | `http://<host>/phpmyadmin/` | MariaDB user |
| Adminer | `http://<host>/adminer.php` | same |
| Webmin | `https://<host>:10000` | root |

## Troubleshooting

| Symptom | Hint |
|---|---|
| 403 Forbidden | SELinux context: `restorecon -Rv /var/www/html` |
| 502 Bad Gateway (Nginx) | `php-fpm` stopped or wrong socket: `systemctl status php-fpm` |
| PHP shown as text | PHP handler missing: re-run the *PHP handler* component |
| `Address already in use` | Apache and Nginx on the same port: keep only one |
| Database unreachable from PHP | `setsebool -P httpd_can_network_connect_db on` |
| No access from another machine | firewall: `firewall-cmd --add-service=http` |

To remove everything: see [reset.md](reset.md).
