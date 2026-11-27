# Addon reference

Every option is a self-contained `.sh` script in `beta/addons/`. This table is **generated** from `addons/index.json` by `tools/docs.py`: it always matches what ships.

## AI & developer

| Addon | Version | Packages | State |
|---|---|---|---|
| **ai-clean** (`ai-clean`) | 1.0.0 | — | action (no state) |
| **ai-diagnostic** (`ai-diagnostic`) | 1.0.0 | — | action (no state) |
| **ai-logs** (`ai-logs`) | 1.0.0 | — | action (no state) |
| **ai-models** (`ai-models`) | 1.0.0 | — | action (no state) |
| **ai-ollama** (`ai-ollama`) | 1.0.0 | — | RPM packages and/or paths |
| **ai-openwebui** (`ai-openwebui`) | 1.0.0 | `podman` | action (no state) |
| **ai-python** (`ai-python`) | 1.0.0 | `python3`, `python3-pip`, `python3-virtualenv`, `python3-notebook` | RPM packages and/or paths |
| **ai-start** (`ai-start`) | 1.0.0 | — | action (no state) |
| **ai-status** (`ai-status`) | 1.0.0 | — | action (no state) |
| **ai-stop** (`ai-stop`) | 1.0.0 | — | action (no state) |

## Applications

| Addon | Version | Packages | State |
|---|---|---|---|
| **app-btop** (`app-btop`) | 1.0.0 | `btop` | RPM packages and/or paths |
| **app-fastfetch** (`app-fastfetch`) | 1.0.0 | `fastfetch` | RPM packages and/or paths |
| **app-lutris** (`app-lutris`) | 1.0.0 | `lutris` | RPM packages and/or paths |
| **app-steam** (`app-steam`) | 1.0.0 | `steam` | RPM packages and/or paths |

## Audio

| Addon | Version | Packages | State |
|---|---|---|---|
| **audio-easyeffects** (`audio-easyeffects`) | 1.0.0 | `easyeffects` | RPM packages and/or paths |
| **audio-presets-jackhack** (`audio-presets-jackhack`) | 1.0.0 | — | RPM packages and/or paths |

## Dependencies

| Addon | Version | Packages | State |
|---|---|---|---|
| **deps-32bit** (`deps-32bit`) | 1.0.0 | `mesa-vulkan-drivers.i686`, `mesa-dri-drivers.i686`, `libva.i686` | RPM packages and/or paths |
| **deps-build** (`deps-build`) | 1.0.0 | `gcc`, `gcc-c++`, `make`, `kernel-devel`, `dkms`, `openssl-devel` | RPM packages and/or paths |
| **deps-fuse** (`deps-fuse`) | 1.0.0 | `fuse`, `fuse-libs` | RPM packages and/or paths |
| **deps-network** (`deps-network`) | 1.0.0 | `curl`, `wget`, `rsync`, `openssh-clients` | RPM packages and/or paths |
| **deps-node** (`deps-node`) | 1.0.0 | `nodejs`, `npm` | RPM packages and/or paths |
| **deps-node-uninstall** (`deps-node-uninstall`) | 1.0.0 | — | action (no state) |
| **deps-python-venv** (`deps-python-venv`) | 1.0.0 | — | action (no state) |
| **deps-python-versions** (`deps-python-versions`) | 1.0.0 | — | action (no state) |
| **deps-tkinter** (`deps-tkinter`) | 1.0.0 | `python3-tkinter` | RPM packages and/or paths |

## Development

| Addon | Version | Packages | State |
|---|---|---|---|
| **dev-automation** (`dev-automation`) | 1.0.0 | `just`, `direnv`, `shellcheck` | RPM packages and/or paths |
| **dev-build** (`dev-build`) | 1.0.0 | `gcc`, `gcc-c++`, `make`, `cmake`, `meson`, `ninja-build`, `pkgconf-pkg-config`, `autoconf`, `automake`, `libtool`, `patch`, `rpmdevtools`, `rpmlint` | RPM packages and/or paths |
| **dev-cli-search** (`dev-cli-search`) | 1.0.0 | `ripgrep`, `fd-find`, `bat`, `eza`, `fzf`, `zoxide` | RPM packages and/or paths |
| **dev-containers** (`dev-containers`) | 1.0.0 | `podman`, `podman-docker`, `buildah`, `skopeo`, `distrobox`, `toolbox` | RPM packages and/or paths |
| **dev-data** (`dev-data`) | 1.0.0 | `jq`, `yq`, `httpie`, `sqlite`, `sqlitebrowser` | RPM packages and/or paths |
| **dev-debug** (`dev-debug`) | 1.0.0 | `gdb`, `lldb`, `valgrind`, `heaptrack`, `sysprof` | RPM packages and/or paths |
| **dev-diagnostic** (`dev-diagnostic`) | 1.0.0 | `lsof`, `strace`, `ltrace`, `sysstat`, `perf`, `ncdu`, `duf`, `hyperfine` | RPM packages and/or paths |
| **dev-editors** (`dev-editors`) | 1.0.0 | `neovim`, `helix` | RPM packages and/or paths |
| **dev-git-tools** (`dev-git-tools`) | 1.1.0 | `git`, `git-lfs`, `gh`, `glab`, `lazygit`, `git-delta` | RPM packages and/or paths |
| **dev-python** (`dev-python`) | 1.0.0 | `python3-devel`, `python3-debugpy`, `python3-flake8`, `python3-black` | RPM packages and/or paths |
| **dev-python-gtk** (`dev-python-gtk`) | 1.0.0 | `python3-devel`, `python3-pip`, `python3-virtualenv`, `python3-pytest`, `gobject-introspection-devel`, `gtk4-devel`, `libadwaita-devel`, `libsecret-devel`, `blueprint-compiler`, `desktop-file-utils`, `appstream`, `gtk4-devel-tools`, `devhelp` | RPM packages and/or paths |
| **dev-python-quality** (`dev-python-quality`) | 1.0.0 | `uv`, `ruff`, `mypy`, `pre-commit` | RPM packages and/or paths |
| **dev-rust** (`dev-rust`) | 1.0.0 | `rust`, `cargo`, `rustfmt`, `clippy` | RPM packages and/or paths |
| **dev-terminal** (`dev-terminal`) | 1.0.0 | `tmux`, `zellij` | RPM packages and/or paths |
| **dev-virt** (`dev-virt`) | 1.0.0 | `qemu-kvm`, `libvirt`, `virt-install`, `virt-manager`, `virt-viewer`, `gnome-boxes`, `edk2-ovmf`, `swtpm`, `swtpm-tools` | RPM packages and/or paths |

## Fan

| Addon | Version | Packages | State |
|---|---|---|---|
| **fan-restart** (`fan-restart`) | 1.0.0 | — | action (no state) |
| **fan-status** (`fan-status`) | 1.0.0 | — | action (no state) |
| **fan-tools** (`fan-tools`) | 1.0.0 | — | RPM packages and/or paths |

## Features

| Addon | Version | Packages | State |
|---|---|---|---|
| **feature-cockpit** (`feature-cockpit`) | 1.0.0 | `cockpit`, `cockpit-storaged`, `cockpit-networkmanager` | RPM packages and/or paths |
| **feature-mobile** (`feature-mobile`) | 1.0.0 | `gnome-shell-extension-gsconnect`, `nautilus-gsconnect` | RPM packages and/or paths |
| **feature-print** (`feature-print`) | 1.0.0 | `cups`, `cups-filters`, `system-config-printer` | RPM packages and/or paths |
| **feature-print-off** (`feature-print-off`) | 1.0.0 | — | action (no state) |
| **feature-print-on** (`feature-print-on`) | 1.0.0 | — | action (no state) |
| **feature-print-status** (`feature-print-status`) | 1.0.0 | — | action (no state) |
| **feature-toolbox** (`feature-toolbox`) | 1.0.0 | `toolbox` | RPM packages and/or paths |

## Gaming

| Addon | Version | Packages | State |
|---|---|---|---|
| **gaming-gamemode** (`gaming-gamemode`) | 1.0.0 | `gamemode` | RPM packages and/or paths |
| **gaming-gamescope** (`gaming-gamescope`) | 1.0.0 | `gamescope`, `mangohud` | RPM packages and/or paths |
| **gaming-log** (`gaming-log`) | 1.0.0 | — | action (no state) |
| **gaming-mangohud** (`gaming-mangohud`) | 1.0.0 | `mangohud` | RPM packages and/or paths |
| **gaming-uninstall** (`gaming-uninstall`) | 1.0.0 | — | action (no state) |

## Graphics

| Addon | Version | Packages | State |
|---|---|---|---|
| **mesa-freeworld** (`mesa-freeworld`) | 1.0.0 | `mesa-va-drivers-freeworld`, `mesa-vdpau-drivers-freeworld` | RPM packages and/or paths |
| **mesa-radv** (`mesa-radv`) | 1.0.0 | — | RPM packages and/or paths |
| **mesa-summary** (`mesa-summary`) | 1.0.0 | — | action (no state) |
| **mesa-tools** (`mesa-tools`) | 1.0.0 | `mesa-demos` | RPM packages and/or paths |
| **mesa-update** (`mesa-update`) | 1.0.0 | — | action (no state) |
| **mesa-vulkan** (`mesa-vulkan`) | 1.0.0 | `vulkan-tools`, `vulkan-loader-devel` | RPM packages and/or paths |

## Hardware

| Addon | Version | Packages | State |
|---|---|---|---|
| **hw-check** (`hw-check`) | 1.0.0 | — | action (no state) |
| **hw-decky-loader** (`hw-decky-loader`) | 1.0.0 | — | RPM packages and/or paths |
| **hw-decky-ps5-plugin** (`hw-decky-ps5-plugin`) | 1.0.0 | — | RPM packages and/or paths |
| **hw-hwcon-gui** (`hw-hwcon-gui`) | 1.0.1 | `python3-PyQt6` | RPM packages and/or paths |
| **hw-uninstall** (`hw-uninstall`) | 1.0.0 | — | action (no state) |
| **hw-update-check** (`hw-update-check`) | 1.0.0 | — | action (no state) |

## Kernel

| Addon | Version | Packages | State |
|---|---|---|---|
| **kernel-headers** (`kernel-headers`) | 1.0.0 | `kernel-headers`, `kernel-devel` | RPM packages and/or paths |
| **kernel-latest** (`kernel-latest`) | 1.0.0 | `kernel` | RPM packages and/or paths |
| **kernel-ps5** (`kernel-ps5`) | 1.0.0 | — | RPM packages and/or paths |

## Languages

| Addon | Version | Packages | State |
|---|---|---|---|
| **lang-all** (`lang-all`) | 1.0.0 | `langpacks-fr`, `langpacks-es`, `langpacks-it`, `langpacks-de`, `langpacks-pt`, `langpacks-ja`, `langpacks-zh_CN`, `langpacks-ru` | RPM packages and/or paths |
| **lang-de** (`lang-de`) | 1.0.0 | `langpacks-de` | RPM packages and/or paths |
| **lang-es** (`lang-es`) | 1.0.0 | `langpacks-es` | RPM packages and/or paths |
| **lang-fr** (`lang-fr`) | 1.0.0 | `langpacks-fr` | RPM packages and/or paths |
| **lang-it** (`lang-it`) | 1.0.0 | `langpacks-it` | RPM packages and/or paths |
| **lang-ja** (`lang-ja`) | 1.0.0 | `langpacks-ja` | RPM packages and/or paths |
| **lang-pt** (`lang-pt`) | 1.0.0 | `langpacks-pt` | RPM packages and/or paths |

## Maintenance

| Addon | Version | Packages | State |
|---|---|---|---|
| **maint-clean** (`maint-clean`) | 1.0.0 | — | action (no state) |
| **maint-desktop-db** (`maint-desktop-db`) | 1.0.0 | — | action (no state) |
| **maint-disk** (`maint-disk`) | 1.0.0 | — | action (no state) |
| **maint-flatpak** (`maint-flatpak`) | 1.0.0 | — | action (no state) |
| **maint-fonts** (`maint-fonts`) | 1.0.0 | — | action (no state) |
| **maint-journal** (`maint-journal`) | 1.0.0 | — | action (no state) |
| **maint-kde-menu** (`maint-kde-menu`) | 1.0.0 | — | action (no state) |
| **maint-old-kernels** (`maint-old-kernels`) | 1.0.0 | — | action (no state) |
| **maint-thumbs** (`maint-thumbs`) | 1.0.0 | — | action (no state) |
| **maint-tmp** (`maint-tmp`) | 1.0.0 | — | action (no state) |
| **maint-trim** (`maint-trim`) | 1.0.0 | `util-linux` | RPM packages and/or paths |

## Power

| Addon | Version | Packages | State |
|---|---|---|---|
| **power-profiles** (`power-profiles`) | 1.0.0 | `power-profiles-daemon` | RPM packages and/or paths |
| **power-tlp** (`power-tlp`) | 1.0.0 | `tlp`, `tlp-rdw` | RPM packages and/or paths |

## Repair

| Addon | Version | Packages | State |
|---|---|---|---|
| **fix-dnf** (`fix-dnf`) | 1.0.0 | — | action (no state) |
| **fix-steam** (`fix-steam`) | 1.0.0 | — | action (no state) |

## Repositories

| Addon | Version | Packages | State |
|---|---|---|---|
| **repo-flathub** (`repo-flathub`) | 1.0.0 | — | RPM packages and/or paths |
| **repo-rpmfusion** (`repo-rpmfusion`) | 1.0.0 | `rpmfusion-free-release`, `rpmfusion-nonfree-release` | RPM packages and/or paths |
| **repos-openh264** (`repos-openh264`) | 1.0.0 | — | RPM packages and/or paths |
| **repos-refresh** (`repos-refresh`) | 1.0.0 | — | action (no state) |

## Updates

| Addon | Version | Packages | State |
|---|---|---|---|
| **update-beta** (`update-beta`) | 1.0.0 | — | action (no state) |
| **update-system** (`update-system`) | 1.0.0 | — | action (no state) |
| **update-uninstall** (`update-uninstall`) | 1.0.0 | — | action (no state) |

## Video

| Addon | Version | Packages | State |
|---|---|---|---|
| **codecs-av** (`codecs-av`) | 1.0.1 | `gstreamer1-plugins-good`, `gstreamer1-plugins-bad-free`, `gstreamer1-plugins-bad-free-extras`, `gstreamer1-plugins-ugly`, `gstreamer1-plugin-libav`, `gstreamer1-plugins-bad-freeworld`, `gstreamer1-plugin-openh264`, `libavcodec-freeworld`, `lame`, `x264-libs`, `x265-libs` | RPM packages and/or paths |
| **ffmpeg-full** (`ffmpeg-full`) | 1.0.0 | `ffmpeg`, `libavcodec-freeworld` | RPM packages and/or paths |

## Web server

| Addon | Version | Packages | State |
|---|---|---|---|
| **web-certbot** (`web-certbot`) | 1.0.0 | `certbot`, `python3-certbot-apache`, `python3-certbot-nginx` | RPM packages and/or paths |
| **web-db** (`web-db`) | 1.0.0 | `mariadb-server` | RPM packages and/or paths |
| **web-httpd** (`web-httpd`) | 1.0.0 | `httpd`, `php`, `php-mysqlnd` | RPM packages and/or paths |
| **web-nginx** (`web-nginx`) | 1.0.0 | `nginx` | RPM packages and/or paths |
| **web-openssh** (`web-openssh`) | 1.0.0 | `openssh-server` | action (no state) |

## services

| Addon | Version | Packages | State |
|---|---|---|---|
| **services-bulk** (`services-bulk`) | 1.0.0 | — | action (no state) |


## Script header

```bash
#!/usr/bin/env bash
#@ id: codecs-av            # unique id = file name
#@ version: 1.0.1           # compared by the catalog (x.y.z)
#@ section: video           # sidebar section
#@ icon: video-x-generic-symbolic
#@ title: Video codecs      # English title
#@ title_fr: Codecs vidéo   # French title
#@ desc: ...                # English description
#@ desc_fr: ...             # French description
#@ packages: a b c          # state: rpm -q
#@ check_paths: /x /y/*     # state: paths/globs
#@ needs: repo-rpmfusion    # installed first
#@ action: yes              # pure action: no badge
#@ root: yes                # run through pkexec
```

Contract: `--check` exits 0 when the option is already installed. Without packages, paths or `action`, `tools/check.py` rejects it.

_107 addons, 20 sections._
