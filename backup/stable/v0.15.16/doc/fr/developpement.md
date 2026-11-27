# Page Développement

Section **Développement** (`applications-engineering-symbolic`). Un catalogue par
catégorie, avec pastille d'état (**● Installé**, **◐ partiel**, **○ Non installé**)
et fiche détaillée par composant (installer / mettre à jour / désinstaller).

## Catalogues

### Composants (socle)

| Entrée | Paquets principaux |
|---|---|
| Socle de compilation | `git`, `gcc`, `gcc-c++`, `make`, `cmake`, `meson`, `ninja-build`, `pkgconf-pkg-config`, `autoconf`, `automake`, `libtool`, `patch`, `rpmdevtools`, `rpmlint` |
| Python + GTK4 / Libadwaita | `python3-devel`, `python3-pip`, `python3-virtualenv`, `python3-pytest`, `gtk4-devel`, `libadwaita-devel`, `gobject-introspection-devel`, `libsecret-devel`, `blueprint-compiler`, `devhelp` |
| Conteneurs | `podman`, `podman-docker`, `buildah`, `skopeo`, `distrobox`, `toolbox` |
| Docker Engine | dépôt `docker-ce` (script), `docker-ce`, `containerd`, `docker-compose-plugin`, `docker-buildx-plugin` |
| Virtualisation KVM/QEMU | `virt-manager`, `libvirt`, `qemu-kvm`, groupes `libvirt`/`kvm` |
| Node.js / npm | `nodejs`, `npm` |
| Rust / Cargo | `rust`, `cargo` |

### Outils en ligne de commande

`cli-search` (ripgrep, fd, fzf, bat, eza) · `git-tools` (git-lfs, gh, glab, tig) ·
`terminal` (tmux, zellij) · `diag` (htop, btop, iotop, nvme-cli, smartmontools) ·
`debug` (gdb, lldb, strace, ltrace, perf) · `python-quality` (uv, ruff, mypy) ·
`data` (jq, yq, httpie) · `automation` (just, direnv, shellcheck).

### Applications

VSCodium (dépôt officiel + clé) · GitHub Desktop (script `github-desktop`) ·
Forgejo (serveur Git local, unité systemd dédiée) · Éditeurs terminal (Neovim, Helix) ·
SQLite (sqlite, sqlitebrowser, sqlite-utils).

## Scripts dédiés

Certains composants ne sont pas de simples paquets : le gestionnaire exécute un script
écrit par l'application (journal complet dans la fenêtre de progression).

| Script | Ce qu'il fait |
|---|---|
| Docker | ajoute le dépôt `docker-ce` (clé GPG), installe le moteur, active `docker.service`, ajoute l'utilisateur au groupe `docker` |
| Forgejo | télécharge le binaire, écrit `/etc/systemd/system/forgejo.service` et `/etc/forgejo/app.ini`, crée l'utilisateur système, active le service |
| GitHub Desktop | ajoute le dépôt Flatpak (COPR/flatpak), installe `io.github.shiftey.Desktop` |

Après Docker, KVM ou libvirt, **une reconnexion est nécessaire** pour que les groupes
soient pris en compte.

## Commandes utiles

```bash
# Versions
$ gcc --version; python3 --version; node --version; cargo --version
$ podman --version; docker --version

# Groupes de l'utilisateur (après reconnexion)
$ groups

# Docker
# systemctl status docker
$ docker ps
$ docker compose version

# Podman sans root
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

## État affiché

- La pastille et le sous-titre (`2/3 · …`) viennent d'une détection réelle :
  `rpm -q` groupé pour les paquets (cache de 30 s), commandes dédiées pour Docker,
  VSCodium et Forgejo.
- Une fiche de composant rappelle l'état et propose les trois actions ; chaque action
  passe par la fenêtre de progression et le journal.

## Dépannage

| Symptôme | Piste |
|---|---|
| `docker` : permission denied | groupe `docker` non actif : se reconnecter |
| VSCodium absent du menu | `desktop-file-utils` puis `update-desktop-database` |
| Forgejo ne démarre pas | `journalctl -u forgejo -n 50` et vérifier `/etc/forgejo/app.ini` |
| `npm` introuvable après installation | nouveau shell (PATH `/usr/bin` mis à jour) |
| Compilation GTK4 échoue | paquet `gtk4-devel` manquant : relancer l'entrée Python + GTK4 |
