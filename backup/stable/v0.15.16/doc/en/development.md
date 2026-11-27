# Development page

The **Development** section (`applications-engineering-symbolic`). One catalogue per
category, with a status badge (**● Installed**, **◐ partial**, **○ Not installed**)
and a detail sheet per component (install / update / uninstall).

## Catalogues

### Components (base)

| Entry | Main packages |
|---|---|
| Build essentials | `git`, `gcc`, `gcc-c++`, `make`, `cmake`, `meson`, `ninja-build`, `pkgconf-pkg-config`, `autoconf`, `automake`, `libtool`, `patch`, `rpmdevtools`, `rpmlint` |
| Python + GTK4 / Libadwaita | `python3-devel`, `python3-pip`, `python3-virtualenv`, `python3-pytest`, `gtk4-devel`, `libadwaita-devel`, `gobject-introspection-devel`, `libsecret-devel`, `blueprint-compiler`, `devhelp` |
| Containers | `podman`, `podman-docker`, `buildah`, `skopeo`, `distrobox`, `toolbox` |
| Docker Engine | `docker-ce` repository (script), `docker-ce`, `containerd`, `docker-compose-plugin`, `docker-buildx-plugin` |
| KVM/QEMU virtualisation | `virt-manager`, `libvirt`, `qemu-kvm`, `libvirt`/`kvm` groups |
| Node.js / npm | `nodejs`, `npm` |
| Rust / Cargo | `rust`, `cargo` |

### Command-line tools

`cli-search` (ripgrep, fd, fzf, bat, eza) · `git-tools` (git-lfs, gh, glab, tig) ·
`terminal` (tmux, zellij) · `diag` (htop, btop, iotop, nvme-cli, smartmontools) ·
`debug` (gdb, lldb, strace, ltrace, perf) · `python-quality` (uv, ruff, mypy) ·
`data` (jq, yq, httpie) · `automation` (just, direnv, shellcheck).

### Applications

VSCodium (official repository + key) · GitHub Desktop (`github-desktop` script) ·
Forgejo (local Git server, dedicated systemd unit) · Terminal editors (Neovim, Helix) ·
SQLite (sqlite, sqlitebrowser, sqlite-utils).

## Dedicated scripts

Some components are not plain packages: the manager runs a script written by the
application (full log in the progress window).

| Script | What it does |
|---|---|
| Docker | adds the `docker-ce` repository (GPG key), installs the engine, enables `docker.service`, adds the user to the `docker` group |
| Forgejo | downloads the binary, writes `/etc/systemd/system/forgejo.service` and `/etc/forgejo/app.ini`, creates the system user, enables the service |
| GitHub Desktop | adds the Flatpak remote, installs `io.github.shiftey.Desktop` |

After Docker, KVM or libvirt, **signing in again is required** for the groups to apply.

## Useful commands

```bash
# Versions
$ gcc --version; python3 --version; node --version; cargo --version
$ podman --version; docker --version

# User groups (after signing in again)
$ groups

# Docker
# systemctl status docker
$ docker ps
$ docker compose version

# Rootless Podman
$ podman info

# Forgejo
# systemctl status forgejo
$ curl -s http://127.0.0.1:3000/api/v1/version

# Virtualisation
# systemctl status libvirtd
$ virsh list --all

# Rust / Node
$ cargo install --list
$ npm ls -g --depth=0
```

## Displayed state

- The badge and subtitle (`2/3 · …`) come from real detection: grouped `rpm -q` for
  packages (30 s cache), dedicated commands for Docker, VSCodium and Forgejo.
- A component sheet recalls the state and offers the three actions; every action goes
  through the progress window and the log.

## Troubleshooting

| Symptom | Hint |
|---|---|
| `docker`: permission denied | `docker` group not active yet: sign in again |
| VSCodium missing from the menu | `desktop-file-utils`, then `update-desktop-database` |
| Forgejo does not start | `journalctl -u forgejo -n 50` and check `/etc/forgejo/app.ini` |
| `npm` not found after install | open a new shell (updated `/usr/bin` PATH) |
| GTK4 build fails | missing `gtk4-devel`: re-run the Python + GTK4 entry |
