# Freebuff

Freebuff is offered in the **AI & Developer** section, below VSCodium. It is a
command-line tool (global npm package `freebuff`), not a graphical application.

## What the manager does

| Action | Detail |
|---|---|
| Install | checks Node.js/npm, installs `freebuff` globally when missing |
| Detect | reads the version from the global package `package.json` |
| Launch | opens the available terminal (list below) and runs `freebuff` |

Terminals tried, in order: `ptyxis`, `kgx` (GNOME Console), `gnome-terminal`,
`konsole`, `xfce4-terminal`, `mate-terminal`, `tilix`, `xterm`.

## Manual commands

```bash
# Check Node.js and npm
$ node --version
$ npm --version

# Install / update
# npm install -g freebuff
# npm update -g freebuff

# Installed version
$ npm ls -g freebuff --depth=0
$ freebuff --version

# Binary location
$ which freebuff

# Uninstall
# npm uninstall -g freebuff
```

If `npm` is missing:

```bash
# dnf install -y nodejs npm
```

## Launching

```bash
$ freebuff
```

The manager opens a terminal and then runs the command, so the interactive session stays
usable. The application log records the attempt.

## Troubleshooting

| Symptom | Hint |
|---|---|
| “Freebuff not found” after install | new shell (`/usr/local/bin` PATH) |
| Empty version while the binary exists | installed outside npm global (binary only) |
| No terminal found | install `ptyxis` or `gnome-terminal`, or run `freebuff` manually |
| `EACCES` during install | avoid `sudo npm`: use a user prefix (`npm config set prefix ~/.npm-global`) |

To remove it completely: see [reset.md](reset.md) (`npm uninstall -g freebuff`).
