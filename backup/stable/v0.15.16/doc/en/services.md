# Services (on/off)

The **Services (on/off)** section (`system-run-symbolic`, right after *Easy setup*).

Every row is a **switch** bound to a systemd unit:

- switch **on** → the service runs **and** starts at boot;
- switch **off** → service stopped **and** disabled (`disable`).

The displayed state is real: it is read with `systemctl show` when the page opens.
A unit that does not exist on the system is hidden, no switch is offered for it.

## Tracked units

| Group | Units |
|---|---|
| Web servers & databases | `httpd`, `nginx`, `php-fpm`, `mariadb`, `mysqld` |
| Containers & forges | `docker`, `podman.socket`, `forgejo` |
| System & remote access | `firewalld`, `sshd`, `cockpit.socket` |
| Safe to turn off for performance | `bluetooth`, `cups`, `avahi-daemon`, `ModemManager` |

## “Turn off unneeded daemons” shortcut

Red button at the bottom of the page, with confirmation, running:

```bash
# systemctl disable --now bluetooth cups avahi-daemon ModemManager
```

(only for units actually present). The page reloads afterwards to show the new states.
It is **reversible**: switching back on is enough.

Typical saving on a PS5 turned into a gaming console or a server: tens of MB of RAM and
fewer CPU wake-ups. Packages stay installed, so no reinstall is needed to go back.

## Matching commands

```bash
# Exact state (running / enabled at boot)
# systemctl show -p ActiveState -p UnitFileState httpd

# Manual equivalents of the switches
# systemctl enable --now httpd      # turn on
# systemctl disable --now httpd     # turn off

# Restart without changing the boot state
# systemctl restart php-fpm

# Running services, by memory
$ systemctl list-units --type=service --state=running
$ systemd-cgtop -m --iterations=1

# What starts at boot
$ systemctl list-unit-files --state=enabled
```

## Cautions

- **`sshd`**: turning it off removes remote access (keep keyboard/screen access).
- **`firewalld`**: turning it off disables network filtering.
- **`mariadb` / `mysqld`**: a PHP site will fail to connect.
- **`httpd` / `nginx`**: never keep both active on port 80.
- **`cockpit.socket`**: when off, `https://<host>:9090` no longer answers.
- Socket-activated services (`podman.socket`, `cockpit.socket`) start on demand: the
  switch enables/disables them cleanly.

## Troubleshooting

| Symptom | Hint |
|---|---|
| The switch flips back | action refused (permissions, masked unit): read the message and the log |
| Service “not found” | component not installed: install it from *Web server* or *Development* |
| Service restarts by itself | dependency or socket: `systemctl status <unit>` |
| Need to block it completely | `systemctl mask <unit>` (stronger than `disable`) |
