# Reset / uninstall

**Easy setup** section, **Reset** group — to start from a clean base without leaving
orphan configuration behind.

## Three tools

| Tool | Effect |
|---|---|
| **Uninstall components…** | page listing the components actually installed, one switch each, then `dnf remove` through the progress window |
| **Clean the manager's files** | removes the configuration written by the application |
| **Clear the DNF cache** | `dnf clean all` (disk space only) |

## Uninstalling components

1. Open *Easy setup* → **Uninstall components…**.
2. The page only lists what is installed (otherwise “No installed component to
   uninstall”).
3. Uncheck what must stay, then **Uninstall selection** → confirmation.
4. Every component becomes a `dnf remove` step in the progress window, with its log.
   A failure does not stop the following ones.

Cleanup options (configuration files, DNF cache) are part of the same run and checked by
default.

## What “Clean the manager's files” removes

```bash
rm -f /etc/httpd/conf.d/ps5-easy.conf
rm -f /etc/nginx/conf.d/ps5-easy.conf
rm -f /etc/php.d/99-ps5-easy.ini
rm -f /var/www/html/adminer.php
rm -f /etc/yum.repos.d/webmin.repo
# removed only when Docker is no longer installed:
rm -f /etc/yum.repos.d/docker-ce.repo
rm -f /tmp/ps5-easy-db.sql
systemctl daemon-reload
# reloads httpd / nginx when their configuration is still valid
```

Running a profile again rewrites these files cleanly.

## What is **not** removed

- **databases** (`/var/lib/mysql`) and site files (`/var/www/html`, including
  `wp-config.php`);
- **packages**, as long as the uninstall is not started;
- **Forgejo data** (`/var/lib/forgejo`);
- the manager logs (`/var/log/ps5-manager/`).

Manual deletion, only when really intended:

```bash
# Database (irreversible)
# mariadb -u root -e 'DROP DATABASE app;'

# Website
# rm -rf /var/www/html/*

# Forgejo data
# systemctl disable --now forgejo
# rm -rf /var/lib/forgejo

# Manager log
# rm -rf /var/log/ps5-manager
```

## Full reset, step by step

```bash
# 1. Stop the relevant services (Services page)
# systemctl disable --now httpd nginx php-fpm mariadb forgejo docker

# 2. Uninstall the components (Reset page)

# 3. Clean the configuration (Reset page)

# 4. Clear the cache
# dnf clean all

# 5. Check
# rpm -qa | grep -E 'httpd|nginx|php|mariadb|mysql|forgejo|docker'
# ss -tlnp | grep -E ':80|:443|:3306|:3000|:9090'
```

## Reinstalling after a reset

Profiles are idempotent: running *Easy setup* again on a cleaned system starts from
scratch (packages + configuration). The 1-click setup in the ⋮ menu stays available and
is unchanged.

## Troubleshooting

| Symptom | Hint |
|---|---|
| A component stays installed | dependency of another package: `dnf remove` then read the message |
| `httpd -t` fails after cleanup | a config file was edited by hand: `httpd -t` names the line |
| Site still reachable | browser cache or service not restarted: `systemctl restart httpd` |
| `dnf remove` wants to remove more than expected | read the list before confirming (the log shows it) |
