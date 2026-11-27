#!/usr/bin/env bash
#@ id: dev-virt
#@ version: 1.0.0
#@ section: dev
#@ icon: computer-symbolic
#@ title: Virtualisation (KVM / QEMU)
#@ title_fr: Virtualisation (KVM / QEMU)
#@ desc: libvirt, virt-manager, GNOME Boxes and UEFI firmware.
#@ desc_fr: libvirt, virt-manager, GNOME Boxes et firmware UEFI.
#@ packages: qemu-kvm libvirt virt-install virt-manager virt-viewer gnome-boxes edk2-ovmf swtpm swtpm-tools
#@ root: yes
set -euo pipefail

PKGS=(qemu-kvm libvirt virt-install virt-manager virt-viewer gnome-boxes edk2-ovmf swtpm swtpm-tools)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-virt…"
dnf install -y --skip-unavailable "${PKGS[@]}"
