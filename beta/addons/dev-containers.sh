#!/usr/bin/env bash
#@ id: dev-containers
#@ version: 1.0.0
#@ section: dev
#@ icon: application-x-executable-symbolic
#@ title: Containers (Podman, Distrobox, Toolbox)
#@ title_fr: Conteneurs (Podman, Distrobox, Toolbox)
#@ desc: Rootless containers and the tools built on them.
#@ desc_fr: Conteneurs sans root et les outils construits dessus.
#@ packages: podman podman-docker buildah skopeo distrobox toolbox
#@ root: yes
set -euo pipefail

PKGS=(podman podman-docker buildah skopeo distrobox toolbox)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-containers…"
dnf install -y --skip-unavailable "${PKGS[@]}"
