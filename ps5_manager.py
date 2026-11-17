#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PS5 Fedora Manager — GTK4 / Libadwaita (PyGObject)
==================================================
Interface native GTK4 + Libadwaita.
- Couvre les 15 sections (Journal, Logithèque, IA & Développeur, Manager, Langues,
  Dépôts, Utilisateurs, Mises à jour Fedora, Maintenance, Alimentation, Ventilateur,
  Hardware Control, Mesa/Vulkan, Kernel PS5, Langue de l'interface).
- Synchronisation dynamique de la couleur d'accentuation système GNOME
  (Adw.StyleManager + GSettings/dconf de l'utilisateur réel même sous pkexec).
- Exécution des commandes longues dans un pseudo-terminal (PTY) avec journal
  en direct dans /var/log/ps5-manager.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
import pty
import pwd
import re
import select
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import warnings
from dataclasses import dataclass
from typing import Any, Callable, Optional

# ------------------------------------------------------------------------------
# Constantes & URLs
# ------------------------------------------------------------------------------
APP_ID = "io.github.nexgen999.Ps5Manager"
APP_NAME = "PS5 Manager"
INSTALL_DIR = "/opt/ps5-manager"
REPO_URL = os.environ.get(
    "PS5_MANAGER_REPO", "https://github.com/nexgen999/ps5-fedora-manager.git"
)
KERNEL_REPO = "ps5-linux/ps5-linux-patches"
KERNEL_BASE = f"https://github.com/{KERNEL_REPO}"
TOOLS_REPO = "https://github.com/ps5-linux/ps5-linux-tools"
HWCON_INSTALL = (
    "https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-gui/main/install.sh"
)
HWCON_PYPROJECT = (
    "https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-gui/main/pyproject.toml"
)
HWCON_PREFIX = "/opt/ps5-hwcon-gui"
DECKY_INSTALL = (
    "https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/install_release.sh"
)
DECKY_UNINSTALL = (
    "https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/uninstall.sh"
)
FLATHUB_REPO = "https://dl.flathub.org/repo/flathub.flatpakrepo"
OPERA_KEY = "https://rpm.opera.com/rpmrepo.key"
OPERA_REPO_FILE = "/etc/yum.repos.d/opera.repo"
BRAVE_REPO = "https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo"
BRAVE_KEY = "https://brave-browser-rpm-release.s3.brave.com/brave-core.asc"

LANG_FILE = "/etc/ps5-manager/language"
LOG_DIR = "/var/log/ps5-manager"
LOG_WINDOW_FILE = "/etc/ps5-manager/log-window"


# ------------------------------------------------------------------------------
# Utilisateur réel + élévation de privilèges (pkexec / sudo)
# ------------------------------------------------------------------------------
def detect_real_user() -> tuple[str, int, str]:
    user = os.environ.get("PS5_MANAGER_USER", "").strip()
    if not user:
        if os.geteuid() == 0:
            sudo_user = os.environ.get("SUDO_USER", "").strip()
            pkexec_uid = os.environ.get("PKEXEC_UID", "").strip()
            if sudo_user and sudo_user != "root":
                user = sudo_user
            elif pkexec_uid.isdigit() and int(pkexec_uid) != 0:
                try:
                    user = pwd.getpwuid(int(pkexec_uid)).pw_name
                except KeyError:
                    user = ""
            if not user:
                try:
                    login = os.getlogin()
                    if login and login != "root":
                        user = login
                except OSError:
                    pass
            if not user:
                user = "root"
        else:
            try:
                user = pwd.getpwuid(os.getuid()).pw_name
            except KeyError:
                user = os.environ.get("USER", "root")
    if not user or user == "UNKNOWN":
        user = "root"
    try:
        pw = pwd.getpwnam(user)
        return user, pw.pw_uid, pw.pw_dir or "/root"
    except KeyError:
        return user, 0, "/root"


REAL_USER, REAL_UID, REAL_HOME = detect_real_user()
try:
    _pw_real = pwd.getpwnam(REAL_USER)
    REAL_GID = _pw_real.pw_gid
    try:
        REAL_GROUPS = os.getgrouplist(REAL_USER, REAL_GID)
    except (AttributeError, OSError):
        REAL_GROUPS = [REAL_GID]
except KeyError:
    REAL_GID = 0
    REAL_GROUPS = [0]

# pkexec restreint PATH à /usr/sbin:/usr/bin:/sbin:/bin : restaurer /usr/local/bin (ex: ollama)
_base_paths = ["/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin", "/sbin", "/bin"]
if REAL_HOME and REAL_HOME != "/root":
    _base_paths.append(os.path.join(REAL_HOME, ".local", "bin"))
_cur_paths = [p for p in os.environ.get("PATH", "").split(":") if p]
for _p in _cur_paths:
    if _p not in _base_paths:
        _base_paths.append(_p)
os.environ["PATH"] = ":".join(_base_paths)

if not os.environ.get("DISPLAY"):
    os.environ["DISPLAY"] = ":0"
if os.path.isfile(os.path.join(REAL_HOME, ".Xauthority")) and not os.environ.get("XAUTHORITY"):
    os.environ["XAUTHORITY"] = os.path.join(REAL_HOME, ".Xauthority")
runtime_dir = f"/run/user/{REAL_UID}"
if os.path.isdir(runtime_dir):
    cur_xdg = os.environ.get("XDG_RUNTIME_DIR", "").strip()
    if not cur_xdg or (REAL_UID != 0 and cur_xdg == "/run/user/0"):
        os.environ["XDG_RUNTIME_DIR"] = runtime_dir
    bus_path = os.path.join(runtime_dir, "bus")
    if os.path.exists(bus_path) and not os.environ.get("DBUS_SESSION_BUS_ADDRESS", "").strip():
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={bus_path}"
if os.environ.get("DBUS_SESSION_BUS_ADDRESS", "") == "":
    os.environ.pop("DBUS_SESSION_BUS_ADDRESS", None)


POLKIT_POLICY_PATH = "/usr/share/polkit-1/actions/io.github.nexgen999.ps5-manager.policy"

INTERFACE_DEPS = [
    "python3",
    "python3-gobject",
    "gtk4",
    "libadwaita",
    "gobject-introspection",
    "polkit",
    "glib2",
    "curl",
    "git",
    "desktop-file-utils",
    "util-linux",
]


def ensure_polkit_policy() -> None:
    policy_xml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
<policyconfig>
  <action id="io.github.nexgen999.ps5-manager.pkexec">
    <description>Run PS5 Fedora Manager as root</description>
    <description xml:lang="fr">Exécuter PS5 Fedora Manager en tant que root</description>
    <message>Authentication is required to run PS5 Fedora Manager</message>
    <message xml:lang="fr">Une authentification est requise pour exécuter PS5 Fedora Manager</message>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin_keep</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">/usr/local/bin/ps5-manager</annotate>
    <annotate key="org.freedesktop.policykit.exec.allow_gui">true</annotate>
  </action>
</policyconfig>
"""
    try:
        os.makedirs(os.path.dirname(POLKIT_POLICY_PATH), exist_ok=True)
        with open(POLKIT_POLICY_PATH, "w", encoding="utf-8") as fh:
            fh.write(policy_xml)
        os.chmod(POLKIT_POLICY_PATH, 0o644)
        os.chown(POLKIT_POLICY_PATH, 0, 0)
    except OSError:
        pass


def apply_install_permissions() -> None:
    """Applique les droits, propriétaires root:root et contextes SELinux."""
    for directory in (INSTALL_DIR, "/etc/ps5-manager", LOG_DIR):
        try:
            os.makedirs(directory, mode=0o755, exist_ok=True)
            os.chmod(directory, 0o755)
            os.chown(directory, 0, 0)
        except OSError:
            pass

    if os.path.isdir(INSTALL_DIR):
        for root_dir, dirs, files in os.walk(INSTALL_DIR):
            try:
                os.chown(root_dir, 0, 0)
                os.chmod(root_dir, 0o755)
            except OSError:
                pass
            for d in dirs:
                dp = os.path.join(root_dir, d)
                try:
                    os.chown(dp, 0, 0)
                    os.chmod(dp, 0o755)
                except OSError:
                    pass
            for f in files:
                fp = os.path.join(root_dir, f)
                try:
                    os.chown(fp, 0, 0)
                    mode = 0o755 if f.endswith((".py", ".sh")) else 0o644
                    os.chmod(fp, mode)
                except OSError:
                    pass

    ensure_polkit_policy()

    if shutil.which("restorecon"):
        targets = [
            p for p in (
                INSTALL_DIR,
                "/usr/local/bin/ps5-manager",
                "/usr/share/applications/ps5-manager.desktop",
                "/usr/share/pixmaps/ps5-manager.png",
                POLKIT_POLICY_PATH,
                "/etc/ps5-manager",
                LOG_DIR,
            )
            if os.path.exists(p)
        ]
        if targets:
            subprocess.run(["restorecon", "-RF", *targets], capture_output=True)


def elevate_if_needed() -> None:
    if os.geteuid() == 0 or os.environ.get("PS5_MANAGER_ELEVATED"):
        return
    # Autorise root à afficher l'interface GTK4 sur Xwayland (Fedora Wayland)
    xhost = shutil.which("xhost")
    if xhost:
        subprocess.run([xhost, "+SI:localuser:root"], capture_output=True)
    self_path = os.path.abspath(sys.argv[0])
    env_args = [
        "PS5_MANAGER_ELEVATED=1",
        f"PS5_MANAGER_USER={REAL_USER}",
        f"PATH={os.environ.get('PATH', '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin')}",
        f"DISPLAY={os.environ.get('DISPLAY', ':0')}",
        # Xwayland prioritaire en root, Wayland en secours
        "GDK_BACKEND=x11,wayland",
    ]
    for _k, _v in (
        ("WAYLAND_DISPLAY", os.environ.get("WAYLAND_DISPLAY", "")),
        ("XAUTHORITY", os.environ.get("XAUTHORITY", os.path.join(REAL_HOME, ".Xauthority"))),
        ("XDG_RUNTIME_DIR", os.environ.get("XDG_RUNTIME_DIR", runtime_dir if os.path.isdir(runtime_dir) else "")),
        ("DBUS_SESSION_BUS_ADDRESS", os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")),
    ):
        if _v:
            env_args.append(f"{_k}={_v}")
    pkexec = shutil.which("pkexec")
    if pkexec:
        try:
            os.execv(
                pkexec,
                [pkexec, "env", *env_args, sys.executable, self_path, *sys.argv[1:]],
            )
        except OSError:
            pass
    sudo = shutil.which("sudo")
    if sudo:
        os.execvp(
            sudo,
            [sudo, "-E", "env", *env_args, sys.executable, self_path, *sys.argv[1:]],
        )
    sys.stderr.write("Ce gestionnaire doit être lancé en root (pkexec ou sudo).\n")
    raise SystemExit(1)


if __name__ == "__main__":
    elevate_if_needed()
    os.environ["PS5_MANAGER_ELEVATED"] = "1"
    if os.geteuid() == 0:
        os.environ.setdefault("GDK_BACKEND", "x11,wayland")

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402


# ------------------------------------------------------------------------------
# Couleurs d'accentuation système GNOME (Fedora 41–45 / GNOME 47+)
# ------------------------------------------------------------------------------
# Valeurs Adwaita officielles (light/dark adaptées pour contraste >= 4.5:1)
GNOME_ACCENTS = {
    "blue": ("#3584e4", "#62a0ea", "#ffffff"),
    "teal": ("#2190a4", "#4eb2c5", "#ffffff"),
    "green": ("#3a944a", "#57c26a", "#ffffff"),
    "yellow": ("#c88800", "#e5a50a", "#1e1e1e"),
    "orange": ("#ed5b00", "#ff7800", "#ffffff"),
    "red": ("#e62d42", "#f66151", "#ffffff"),
    "pink": ("#d56199", "#e67fb1", "#ffffff"),
    "purple": ("#9141ac", "#c061cb", "#ffffff"),
    "slate": ("#6f8396", "#8ea1b4", "#ffffff"),
}

ADW_ACCENT_ENUM_MAP = {}
if hasattr(Adw, "AccentColor"):
    for _name in GNOME_ACCENTS:
        _enum_val = getattr(Adw.AccentColor, _name.upper(), None)
        if _enum_val is not None:
            ADW_ACCENT_ENUM_MAP[_enum_val] = _name


def user_env() -> dict[str, str]:
    env = dict(os.environ)
    env["DISPLAY"] = os.environ.get("DISPLAY", ":0")
    if REAL_USER != "root":
        user_cwd = REAL_HOME if (REAL_HOME and os.path.isdir(REAL_HOME)) else "/tmp"
        env["HOME"] = REAL_HOME
        env["PWD"] = user_cwd
        env["USER"] = REAL_USER
        env["LOGNAME"] = REAL_USER
        env.pop("OLDPWD", None)
        for xdg_k in (
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_CACHE_HOME",
            "XDG_STATE_HOME",
            "CONTAINERS_CONF",
            "CONTAINERS_STORAGE_CONF",
            "TMPDIR",
        ):
            val = env.get(xdg_k, "")
            if val.startswith("/root"):
                env.pop(xdg_k, None)
    if os.path.isdir(runtime_dir):
        env["XDG_RUNTIME_DIR"] = runtime_dir
        bus_path = os.path.join(runtime_dir, "bus")
        if os.path.exists(bus_path):
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={bus_path}"
        else:
            env.pop("DBUS_SESSION_BUS_ADDRESS", None)
    else:
        env.pop("DBUS_SESSION_BUS_ADDRESS", None)
    user_paths = ["/usr/local/bin", "/usr/bin", "/bin"]
    if REAL_HOME and REAL_HOME != "/root":
        user_paths.insert(0, os.path.join(REAL_HOME, ".local", "bin"))
    env["PATH"] = ":".join(user_paths)
    return env


def user_subprocess_kwargs() -> dict[str, Any]:
    """Paramètres subprocess pour exécuter directement en tant que REAL_USER sans sudo/PAM."""
    if os.geteuid() == 0 and REAL_USER != "root":
        user_cwd = REAL_HOME if (REAL_HOME and os.path.isdir(REAL_HOME)) else "/tmp"
        return {
            "user": REAL_UID,
            "group": REAL_GID,
            "extra_groups": REAL_GROUPS,
            "cwd": user_cwd,
            "env": user_env(),
        }
    return {"env": user_env()}


def run_as_user_cmd(cmd: list[str]) -> list[str]:
    if os.geteuid() == 0 and REAL_USER != "root":
        user_paths = ["/usr/local/bin", "/usr/bin", "/bin"]
        if REAL_HOME and REAL_HOME != "/root":
            user_paths.insert(0, os.path.join(REAL_HOME, ".local", "bin"))
        env_kv = [
            f"HOME={REAL_HOME}",
            f"USER={REAL_USER}",
            f"LOGNAME={REAL_USER}",
            f"DISPLAY={os.environ.get('DISPLAY', ':0')}",
            f"PATH={':'.join(user_paths)}",
        ]
        if os.path.isdir(runtime_dir):
            env_kv.append(f"XDG_RUNTIME_DIR={runtime_dir}")
            bus_path = os.path.join(runtime_dir, "bus")
            if os.path.exists(bus_path):
                env_kv.append(f"DBUS_SESSION_BUS_ADDRESS=unix:path={bus_path}")
        return [
            "sudo",
            "-n",
            "-u",
            REAL_USER,
            "-H",
            "env",
            *env_kv,
            *cmd,
        ]
    return cmd


class SystemThemeSync:
    """
    Synchronise le thème sombre/clair et la couleur d'accentuation GNOME
    (org.gnome.desktop.interface accent-color & color-scheme) même lorsque
    l'application est lancée en root via pkexec.
    """

    def __init__(self) -> None:
        self.style_manager = Adw.StyleManager.get_default()
        self.css_provider = Gtk.CssProvider()
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display,
                self.css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
        self.current_accent: str = "blue"
        self.current_dark: bool = True
        self.follow_system: bool = True
        self._timer_id: Optional[int] = None
        self._last_state: tuple[str, str] = ("", "")

    def start(self) -> None:
        self.refresh()
        self.style_manager.connect("notify::dark", lambda *_: self.refresh())
        if hasattr(self.style_manager, "props") and hasattr(
            self.style_manager.props, "accent_color"
        ):
            self.style_manager.connect("notify::accent-color", lambda *_: self.refresh())
        # Surveillance légère du dconf de REAL_USER (utile sous pkexec)
        self._timer_id = GLib.timeout_add_seconds(3, self._poll_user_gsettings)

    def _read_gsetting(self, key: str) -> str:
        try:
            res = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", key],
                capture_output=True,
                text=True,
                timeout=2,
                **user_subprocess_kwargs(),
            )
            if res.returncode == 0:
                return res.stdout.strip().strip("'\"")
        except (OSError, subprocess.SubprocessError):
            pass
        return ""

    def _poll_user_gsettings(self) -> bool:
        if not self.follow_system:
            return True
        accent = self._read_gsetting("accent-color")
        scheme = self._read_gsetting("color-scheme")
        if (accent, scheme) != self._last_state:
            self._last_state = (accent, scheme)
            self.apply(accent or self._native_accent_name(), scheme)
        return True

    def _native_accent_name(self) -> str:
        if hasattr(self.style_manager, "get_accent_color"):
            try:
                enum_val = self.style_manager.get_accent_color()
                if enum_val in ADW_ACCENT_ENUM_MAP:
                    return ADW_ACCENT_ENUM_MAP[enum_val]
            except Exception:
                pass
        return "blue"

    def refresh(self) -> None:
        accent = self._read_gsetting("accent-color") or self._native_accent_name()
        scheme = self._read_gsetting("color-scheme")
        self._last_state = (accent, scheme)
        self.apply(accent, scheme)

    def apply(self, accent_name: str, color_scheme: str = "") -> None:
        if accent_name not in GNOME_ACCENTS:
            accent_name = "blue"
        self.current_accent = accent_name

        if color_scheme == "prefer-dark":
            self.style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            is_dark = True
        elif color_scheme == "prefer-light":
            self.style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            is_dark = False
        else:
            self.style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)
            is_dark = bool(self.style_manager.get_dark())
        self.current_dark = is_dark

        bg_light, bg_dark, fg = GNOME_ACCENTS[accent_name]
        accent_bg = bg_light
        accent_text = bg_dark if is_dark else bg_light

        css = f"""
        @define-color accent_bg_color {accent_bg};
        @define-color accent_color {accent_text};
        @define-color accent_fg_color {fg};

        :root {{
            --accent-bg-color: {accent_bg};
            --accent-color: {accent_text};
            --accent-fg-color: {fg};
        }}

        .ps5-accent-pill {{
            background-color: alpha(@accent_bg_color, 0.16);
            color: @accent_color;
            border-radius: 9999px;
            padding: 2px 10px;
            font-size: 0.82em;
            font-weight: 600;
        }}

        .ps5-status-ok {{
            color: #57e389;
            font-weight: 600;
        }}

        .ps5-status-warn {{
            color: #f8e45c;
            font-weight: 600;
        }}

        .ps5-status-err {{
            color: #ff7b63;
            font-weight: 600;
        }}

        list.navigation-sidebar row.ps5-sidebar-sep,
        list.navigation-sidebar row.ps5-sidebar-sep:hover,
        list.navigation-sidebar row.ps5-sidebar-sep:active,
        list.navigation-sidebar row.ps5-sidebar-sep:selected {{
            min-height: 0px;
            padding: 6px 12px;
            margin: 2px 6px;
            background: transparent;
            box-shadow: none;
        }}

        list.navigation-sidebar row.ps5-sidebar-sep separator {{
            min-height: 1px;
            background-color: alpha(currentColor, 0.14);
        }}
        """
        self.css_provider.load_from_data(css.encode("utf-8"))


# ------------------------------------------------------------------------------
# Traductions FR / EN (UI Libadwaita)
# ------------------------------------------------------------------------------
STRINGS = {
    "fr": {
        "app_title": "PS5 Manager",
        "search_placeholder": "Rechercher une option ou un logiciel…",
        "system_info": "Système",
        "accent_label": "Couleur d'accentuation GNOME",
        "follow_gnome": "Synchronisée avec GNOME",
        "about": "À propos de PS5 Manager",
        "confirm": "Confirmer",
        "cancel": "Annuler",
        "ok": "Valider",
        "close": "Fermer",
        "running": "Traitement en cours…",
        "busy": "Une tâche est déjà en cours d'exécution.",
        "done": "Terminé.",
        "failed": "Échec (code %s)",
        "view_log": "Voir le journal",
        "clear": "Effacer",
        # Sections
        "sec_logs": "Journal / Logs",
        "sec_library": "Logithèque",
        "sec_aidev": "IA & Développeur",
        "sec_update": "Mise à jour du manager",
        "sec_lang": "Langues & clavier",
        "sec_repos": "Dépôts",
        "sec_users": "Utilisateurs",
        "sec_fedora": "Mises à jour Fedora",
        "sec_maint": "Maintenance",
        "sec_power": "Alimentation",
        "sec_fan": "Ventilateur",
        "sec_hw": "Hardware Control",
        "sec_mesa": "Mesa / Vulkan",
        "sec_kernel": "Kernel PS5",
        "sec_ui_lang": "Langue de l'interface",
        # 14. Logs
        "logs_group_main": "Suivi en direct & historique",
        "logs_group_opts": "Préférences des journaux",
        "logs_live": "Fenêtre de log en direct",
        "logs_live_sub": "Suivre en direct ce que fait le gestionnaire",
        "logs_session": "Journal de cette session",
        "logs_old": "Anciens journaux",
        "logs_old_sub": "14 derniers jours, consultables un par un",
        "logs_auto": "Ouverture automatique",
        "logs_auto_sub": "Ouvrir la fenêtre au premier travail long",
        "logs_clear": "Effacer les journaux",
        "logs_clear_sub": "Supprime les fichiers de /var/log/ps5-manager",
        "logs_clear_confirm": "Supprimer tous les journaux enregistrés dans /var/log/ps5-manager ?",
        "logs_cleared": "Journaux effacés.",
        "logs_none": "Aucun journal enregistré pour le moment.",
        # 12. Library
        "lib_title": "Logithèque PS5",
        "lib_sub": "Installer, mettre à jour, vérifier ou désinstaller les applications essentielles",
        "lib_cat_gaming": "Gaming",
        "lib_cat_gaming_sub": "Lanceurs de jeux, couches de compatibilité Proton et plugins Steam",
        "lib_cat_browser": "Navigateurs",
        "lib_cat_browser_sub": "Navigateurs web (RPM officiel ou Flatpak)",
        "lib_cat_system": "Système & Utilitaires",
        "lib_cat_system_sub": "Outils disque, boutique Flatpak et extensions GNOME",
        "install": "Installer",
        "remove": "Désinstaller",
        "update": "Mettre à jour",
        "check": "Vérifier les mises à jour",
        "installed_rpm": "Installé (RPM)",
        "installed_flatpak": "Installé (Flatpak)",
        "installed": "Installé",
        "not_installed": "Non installé",
        "choose_format": "Quel format d'installation pour %s ?",
        "format_rpm": "RPM (dépôt officiel)",
        "format_flatpak": "Flatpak (Flathub)",
        # 1. Manager
        "mgr_title": "Gestionnaire PS5 Fedora",
        "mgr_update": "Mettre à jour le manager + ses dépendances",
        "mgr_update_sub": "git fetch + reset depuis GitHub et installation dans /opt/ps5-manager",
        "mgr_uninstall": "Désinstaller complètement le manager",
        "mgr_uninstall_sub": "Supprime /opt/ps5-manager, le lanceur et le raccourci bureau",
        "mgr_uninstall_confirm": "Supprimer le gestionnaire et tous ses fichiers système ?",
        # 2. Langues
        "lang_view": "Voir les langpacks installés (système + clavier)",
        "lang_view_sub": "Affiche rpm -qa langpacks-* et localectl status",
        "lang_install": "Installer une langue",
        "lang_install_sub": "Ex : fr_FR.UTF-8, es_ES.UTF-8, de_DE.UTF-8",
        "lang_install_prompt": "Code de langue (ex : fr_FR.UTF-8) :",
        "lang_full": "Configuration intégrale (langue + clavier + compte)",
        "lang_full_sub": "Applique la locale système, le clavier X11/console et le compte utilisateur",
        "lang_pick_locale": "Choisir la locale système",
        "lang_pick_kb": "Choisir la disposition clavier",
        "lang_logout_confirm": "Langue (%s) et clavier (%s) appliqués.\nFermer la session GNOME maintenant pour appliquer les changements ?",
        # 3. Dépôts
        "repo_list": "Voir tous les dépôts (RPM + Flatpak)",
        "repo_list_sub": "dnf repolist --all et dépôts Flatpak système/utilisateur",
        "repo_rpmfusion": "Installer RPM Fusion (free + nonfree)",
        "repo_rpmfusion_sub": "Indispensable pour Steam, codecs multimédias et pilotes",
        "repo_flathub": "Installer Flathub (portée système)",
        "repo_flathub_sub": "Dépôt principal des applications Flatpak",
        "repo_refresh": "Mettre à jour les dépôts & nettoyer le cache",
        "repo_refresh_sub": "dnf clean all, makecache --refresh et appstream Flatpak",
        "repo_add": "Ajouter un dépôt personnalisé (URL .repo)",
        "repo_add_prompt": "URL du fichier .repo :",
        "repo_disable": "Désactiver un dépôt DNF",
        "repo_disable_sub": "Désactive sans supprimer le fichier .repo",
        "repo_rm_dnf": "Supprimer un dépôt DNF (fichier .repo)",
        "repo_rm_flatpak": "Supprimer un dépôt Flatpak",
        "repo_id_prompt": "ID du dépôt (ex : rpmfusion-nonfree) :",
        "repo_fp_prompt": "Nom du dépôt Flatpak (ex : flathub) :",
        # 4. Utilisateurs
        "usr_list": "Voir la liste des utilisateurs",
        "usr_list_sub": "Comptes humains (UID >= 1000) dans /etc/passwd",
        "usr_edit_me": "Éditer mon compte (%s)",
        "usr_edit_me_sub": "Changer le mot de passe et la langue du compte",
        "usr_add": "Ajouter un utilisateur",
        "usr_del": "Supprimer un compte utilisateur",
        "usr_root": "Compte root : état et mot de passe",
        "usr_name_prompt": "Nom du compte :",
        "usr_pass_prompt": "Mot de passe :",
        "usr_new_pass_prompt": "Nouveau mot de passe (laisser vide pour ne pas changer) :",
        "usr_del_confirm": "Supprimer définitivement le compte %s et son dossier personnel ?",
        # 5. Mises à jour Fedora
        "fed_apps": "Mettre à jour les applications (DNF & Flatpak)",
        "fed_apps_sub": "dnf upgrade -y suivi de flatpak update --system",
        "fed_sys": "Mettre à jour le système complet",
        "fed_sys_sub": "dnf upgrade --refresh -y",
        "fed_lang": "Mettre à jour les langpacks",
        "fed_lang_sub": "dnf upgrade -y langpacks-* glibc-langpack-*",
        "fed_meta": "Rafraîchir les métadonnées des dépôts",
        # 6. Maintenance
        "mnt_all": "Nettoyage complet",
        "mnt_all_sub": "Caches DNF, journaux > 7j, /tmp, vignettes et Flatpak inutilisés",
        "mnt_cache": "Nettoyer uniquement le cache DNF",
        "mnt_autoremove": "Supprimer les paquets orphelins (autoremove)",
        "mnt_journal": "Réduire les journaux systemd (7 jours)",
        "mnt_tmp": "Nettoyer /tmp et /var/tmp",
        "mnt_thumbs": "Nettoyer les vignettes utilisateur",
        "mnt_kernels": "Supprimer les anciens kernels (garder 2)",
        "mnt_disk": "Voir l'espace disque utilisé (df -h)",
        # 7. Alimentation
        "pwr_full": "Veille complète (système + écran)",
        "pwr_full_sub": "Masque/démasque sleep.target et configure l'extinction écran (5 min)",
        "pwr_sys": "Veille système (suspend / hibernate)",
        "pwr_sys_sub": "État de systemd sleep/suspend/hibernate.target",
        "pwr_scr": "Mise en veille de l'écran (5 min)",
        "pwr_scr_sub": "org.gnome.desktop.session idle-delay",
        "pwr_enable_full": "Activer la veille complète",
        "pwr_disable_full": "Désactiver la veille complète",
        # 8. Ventilateur
        "fan_status": "Voir le status complet (services + ps5_control)",
        "fan_svc": "Service ps5fan (ventilation)",
        "fan_svc_sub": "Activer / démarrer au boot (ps5fan.service)",
        "fan_boost": "Service ps5boost (mode boost)",
        "fan_boost_sub": "Activer / démarrer ps5boost.service",
        "fan_restart": "Relancer ps5fan.service",
        "fan_tools": "Installer / mettre à jour ps5-linux-tools",
        "fan_tools_sub": "Clone et compile ps5-linux/ps5-linux-tools",
        # 9. Hardware Control
        "hw_check": "Vérifier la présence du matériel PS5",
        "hw_check_sub": "Inspecte /sys/class/hwmon et les noeuds sysfs PS5",
        "hw_install": "Installer / Mettre à jour PS5 Hardware Control",
        "hw_install_sub": "Installe python3-PyQt6 et NotHavocc/ps5-hwcon-gui",
        "hw_check_upd": "Vérifier les mises à jour sur GitHub",
        "hw_uninstall": "Désinstaller PS5 Hardware Control",
        # 10. Mesa / Vulkan
        "mesa_tools": "Installer les outils Vulkan & Mesa demos",
        "mesa_tools_sub": "vulkan-tools et mesa-demos",
        "mesa_upd": "Mettre à jour les paquets Mesa & Vulkan",
        "mesa_upd_sub": "dnf upgrade -y mesa* vulkan*",
        "mesa_radv": "Vérifier la prise en charge RADV (GPU AMD PS5)",
        "mesa_summary": "Afficher le résumé Vulkan complet",
        # 11. Kernel PS5
        "krn_latest": "Vérifier la dernière version disponible",
        "krn_latest_sub": "Depuis ps5-linux/ps5-linux-patches sur GitHub",
        "krn_install": "Installer le dernier kernel PS5 (RPM)",
        "krn_install_sub": "rpm -ivh --nosignature --replacefiles puis déploiement EFI",
        "krn_boot": "Choisir le kernel à démarrer (/boot/efi)",
        "krn_boot_sub": "Copie vmlinuz et initrd.img sélectionnés vers l'ESP",
        "krn_remove": "Nettoyer / supprimer d'anciens kernels",
        "krn_remove_sub": "Supprime les anciens paquets linux-ps5 en protégeant le noyau actif",
        "krn_running": "Démarré",
        "krn_esp": "Sur /boot/efi",
        "krn_installed": "Installé",
        "krn_protected": "Protégé (actif / boot)",
        # 13. UI Lang
        "ui_lang_title": "Langue de l'interface",
        "ui_lang_sub": "Changement immédiat et mémorisé dans /etc/ps5-manager/language",
        "fr_label": "Français",
        "en_label": "English",
        # 15. IA & Développeur
        "aidev_open_sub": "Ollama, Open WebUI (Podman), VSCodium et modèles IA locaux",
        "aidev_stack": "Outils & Applications IA / Dev",
        "aidev_stack_sub": "Installation, mise à jour et désinstallation des briques locales",
        "aidev_services": "Contrôle des services IA",
        "aidev_services_sub": "Démarrer, arrêter ou désactiver au démarrage pour libérer la RAM",
        "aidev_models": "Modèles IA locaux (Ollama)",
        "aidev_models_sub": "Télécharger, inspecter, décharger de la RAM ou supprimer les modèles",
        "aidev_extras": "Diagnostic & Maintenance IA (PS5)",
        "aidev_extras_sub": "Vérification RAM/GPU, nettoyage Podman et persistance",
    },
    "en": {
        "app_title": "PS5 Manager",
        "search_placeholder": "Search an option or software…",
        "system_info": "System",
        "accent_label": "GNOME Accent Color",
        "follow_gnome": "Synced with GNOME",
        "about": "About PS5 Manager",
        "confirm": "Confirm",
        "cancel": "Cancel",
        "ok": "Apply",
        "close": "Close",
        "running": "Working…",
        "busy": "A task is already running.",
        "done": "Done.",
        "failed": "Failed (code %s)",
        "view_log": "View log",
        "clear": "Clear",
        # Sections
        "sec_logs": "Logs",
        "sec_library": "Software library",
        "sec_aidev": "AI & Developer",
        "sec_update": "Manager update",
        "sec_lang": "Languages & keyboard",
        "sec_repos": "Repositories",
        "sec_users": "Users",
        "sec_fedora": "Fedora updates",
        "sec_maint": "Maintenance",
        "sec_power": "Power",
        "sec_fan": "Fan",
        "sec_hw": "Hardware Control",
        "sec_mesa": "Mesa / Vulkan",
        "sec_kernel": "PS5 Kernel",
        "sec_ui_lang": "Interface language",
        # 14. Logs
        "logs_group_main": "Live monitoring & history",
        "logs_group_opts": "Log preferences",
        "logs_live": "Live log window",
        "logs_live_sub": "Watch what the manager is doing in real time",
        "logs_session": "This session's log",
        "logs_old": "Older logs",
        "logs_old_sub": "Last 14 days, inspectable one by one",
        "logs_auto": "Open automatically",
        "logs_auto_sub": "Open log window on the first long task",
        "logs_clear": "Clear logs",
        "logs_clear_sub": "Delete files from /var/log/ps5-manager",
        "logs_clear_confirm": "Delete all recorded logs in /var/log/ps5-manager?",
        "logs_cleared": "Logs cleared.",
        "logs_none": "No log recorded yet.",
        # 12. Library
        "lib_title": "PS5 Software Library",
        "lib_sub": "Install, update, check or uninstall essential applications",
        "lib_cat_gaming": "Gaming",
        "lib_cat_gaming_sub": "Game launchers, Proton compatibility tools and Steam plugins",
        "lib_cat_browser": "Web Browsers",
        "lib_cat_browser_sub": "Web browsers (official RPM or Flatpak)",
        "lib_cat_system": "System & Utilities",
        "lib_cat_system_sub": "Disk imaging, Flatpak store and GNOME extensions",
        "install": "Install",
        "remove": "Uninstall",
        "update": "Update",
        "check": "Check for updates",
        "installed_rpm": "Installed (RPM)",
        "installed_flatpak": "Installed (Flatpak)",
        "installed": "Installed",
        "not_installed": "Not installed",
        "choose_format": "Which installation format for %s?",
        "format_rpm": "RPM (official repository)",
        "format_flatpak": "Flatpak (Flathub)",
        # 1. Manager
        "mgr_title": "PS5 Fedora Manager",
        "mgr_update": "Update manager + dependencies",
        "mgr_update_sub": "git fetch + reset from GitHub and install to /opt/ps5-manager",
        "mgr_uninstall": "Completely uninstall manager",
        "mgr_uninstall_sub": "Removes /opt/ps5-manager, launcher and desktop entry",
        "mgr_uninstall_confirm": "Remove the manager and all its system files?",
        # 2. Langues
        "lang_view": "Show installed language packs (system + keyboard)",
        "lang_view_sub": "Shows rpm -qa langpacks-* and localectl status",
        "lang_install": "Install a language",
        "lang_install_sub": "E.g. fr_FR.UTF-8, es_ES.UTF-8, de_DE.UTF-8",
        "lang_install_prompt": "Language code (e.g. fr_FR.UTF-8):",
        "lang_full": "Full configuration (language + keyboard + account)",
        "lang_full_sub": "Applies system locale, X11/console keymap and user account",
        "lang_pick_locale": "Choose system locale",
        "lang_pick_kb": "Choose keyboard layout",
        "lang_logout_confirm": "Language (%s) and keyboard (%s) applied.\nLog out of GNOME now to apply changes?",
        # 3. Repos
        "repo_list": "List all repositories (RPM + Flatpak)",
        "repo_list_sub": "dnf repolist --all and system/user Flatpak remotes",
        "repo_rpmfusion": "Install RPM Fusion (free + nonfree)",
        "repo_rpmfusion_sub": "Required for Steam, multimedia codecs and drivers",
        "repo_flathub": "Install Flathub (system-wide)",
        "repo_flathub_sub": "Primary Flatpak application repository",
        "repo_refresh": "Refresh repositories & clean cache",
        "repo_refresh_sub": "dnf clean all, makecache --refresh and Flatpak appstream",
        "repo_add": "Add custom repository (.repo URL)",
        "repo_add_prompt": "URL of the .repo file:",
        "repo_disable": "Disable a DNF repository",
        "repo_disable_sub": "Disables without deleting the .repo file",
        "repo_rm_dnf": "Remove a DNF repository (.repo file)",
        "repo_rm_flatpak": "Remove a Flatpak repository",
        "repo_id_prompt": "Repository ID (e.g. rpmfusion-nonfree):",
        "repo_fp_prompt": "Flatpak remote name (e.g. flathub):",
        # 4. Users
        "usr_list": "List system users",
        "usr_list_sub": "Regular accounts (UID >= 1000) in /etc/passwd",
        "usr_edit_me": "Edit my account (%s)",
        "usr_edit_me_sub": "Change account password and language",
        "usr_add": "Add a user",
        "usr_del": "Delete a user account",
        "usr_root": "Root account: status & password",
        "usr_name_prompt": "Account name:",
        "usr_pass_prompt": "Password:",
        "usr_new_pass_prompt": "New password (leave empty to keep unchanged):",
        "usr_del_confirm": "Permanently delete account %s and its home directory?",
        # 5. Fedora updates
        "fed_apps": "Update applications (DNF & Flatpak)",
        "fed_apps_sub": "dnf upgrade -y followed by flatpak update --system",
        "fed_sys": "Update entire system",
        "fed_sys_sub": "dnf upgrade --refresh -y",
        "fed_lang": "Update language packs",
        "fed_lang_sub": "dnf upgrade -y langpacks-* glibc-langpack-*",
        "fed_meta": "Refresh repository metadata",
        # 6. Maintenance
        "mnt_all": "Full cleanup",
        "mnt_all_sub": "DNF caches, logs > 7d, /tmp, thumbnails & unused Flatpak runtimes",
        "mnt_cache": "Clean DNF cache only",
        "mnt_autoremove": "Remove orphaned packages (autoremove)",
        "mnt_journal": "Shrink systemd journal (7 days)",
        "mnt_tmp": "Clean /tmp and /var/tmp",
        "mnt_thumbs": "Clean user thumbnails",
        "mnt_kernels": "Remove old kernels (keep 2)",
        "mnt_disk": "Show disk usage (df -h)",
        # 7. Power
        "pwr_full": "Full sleep (system + screen)",
        "pwr_full_sub": "Masks/unmasks sleep.target and sets screen idle delay (5 min)",
        "pwr_sys": "System sleep (suspend / hibernate)",
        "pwr_sys_sub": "systemd sleep/suspend/hibernate.target status",
        "pwr_scr": "Screen blanking (5 min)",
        "pwr_scr_sub": "org.gnome.desktop.session idle-delay",
        "pwr_enable_full": "Enable full sleep",
        "pwr_disable_full": "Disable full sleep",
        # 8. Fan
        "fan_status": "Show full status (services + ps5_control)",
        "fan_svc": "ps5fan service (fan control)",
        "fan_svc_sub": "Enable / start at boot (ps5fan.service)",
        "fan_boost": "ps5boost service (boost mode)",
        "fan_boost_sub": "Enable / start ps5boost.service",
        "fan_restart": "Restart ps5fan.service",
        "fan_tools": "Install / update ps5-linux-tools",
        "fan_tools_sub": "Clones and builds ps5-linux/ps5-linux-tools",
        # 9. Hardware Control
        "hw_check": "Check PS5 hardware presence",
        "hw_check_sub": "Inspects /sys/class/hwmon and PS5 sysfs nodes",
        "hw_install": "Install / Update PS5 Hardware Control",
        "hw_install_sub": "Installs python3-PyQt6 and NotHavocc/ps5-hwcon-gui",
        "hw_check_upd": "Check GitHub for updates",
        "hw_uninstall": "Uninstall PS5 Hardware Control",
        # 10. Mesa / Vulkan
        "mesa_tools": "Install Vulkan tools & Mesa demos",
        "mesa_tools_sub": "vulkan-tools and mesa-demos",
        "mesa_upd": "Update Mesa & Vulkan packages",
        "mesa_upd_sub": "dnf upgrade -y mesa* vulkan*",
        "mesa_radv": "Check RADV support (PS5 AMD GPU)",
        "mesa_summary": "Show full Vulkan summary",
        # 11. Kernel PS5
        "krn_latest": "Check latest available release",
        "krn_latest_sub": "From ps5-linux/ps5-linux-patches on GitHub",
        "krn_install": "Install latest PS5 kernel (RPM)",
        "krn_install_sub": "rpm -ivh --nosignature --replacefiles then EFI deploy",
        "krn_boot": "Choose boot kernel (/boot/efi)",
        "krn_boot_sub": "Copies selected vmlinuz & initrd.img to ESP",
        "krn_remove": "Clean / remove old kernels",
        "krn_remove_sub": "Removes old linux-ps5 packages while protecting the active kernel",
        "krn_running": "Running",
        "krn_esp": "On /boot/efi",
        "krn_installed": "Installed",
        "krn_protected": "Protected (active / boot)",
        # 13. UI Lang
        "ui_lang_title": "Interface language",
        "ui_lang_sub": "Applies immediately and saved to /etc/ps5-manager/language",
        "fr_label": "Français",
        "en_label": "English",
        # 15. AI & Developer
        "aidev_open_sub": "Ollama, Open WebUI (Podman), VSCodium and local AI models",
        "aidev_stack": "AI & Developer Stack",
        "aidev_stack_sub": "Install, update and uninstall local AI and coding tools",
        "aidev_services": "AI Services Control",
        "aidev_services_sub": "Start, stop or disable at boot to save RAM on PS5",
        "aidev_models": "Local AI Models (Ollama)",
        "aidev_models_sub": "Pull, inspect, unload from RAM or remove models",
        "aidev_extras": "AI Diagnostics & Maintenance (PS5)",
        "aidev_extras_sub": "RAM/GPU check, Podman cleanup and rootless linger",
    },
}


def read_ui_lang() -> str:
    try:
        with open(LANG_FILE, encoding="utf-8") as fh:
            val = fh.readline().strip()
            if val in ("fr", "en"):
                return val
    except OSError:
        pass
    return "fr"


def write_ui_lang(code: str) -> None:
    try:
        os.makedirs(os.path.dirname(LANG_FILE), exist_ok=True)
        with open(LANG_FILE, "w", encoding="utf-8") as fh:
            fh.write(code + "\n")
    except OSError:
        pass


UI_LANG = read_ui_lang()


def T(key: str) -> str:
    return STRINGS.get(UI_LANG, STRINGS["fr"]).get(key, key)


# ------------------------------------------------------------------------------
# Utilitaires système & journalisation
# ------------------------------------------------------------------------------
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\r")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def dnf_is_v5() -> bool:
    try:
        res = subprocess.run(
            ["dnf", "--version"], capture_output=True, text=True, timeout=3
        )
        return "dnf5" in (res.stdout.splitlines()[0] if res.stdout else "").lower()
    except (OSError, subprocess.SubprocessError):
        return False


IS_DNF5 = dnf_is_v5()


class SessionLogger:
    def __init__(self) -> None:
        self.path: str = self._init_log_file()

    def _init_log_file(self) -> str:
        try:
            os.makedirs(LOG_DIR, mode=0o755, exist_ok=True)
            cutoff = datetime.datetime.now().timestamp() - (14 * 86400)
            for fname in glob.glob(os.path.join(LOG_DIR, "session-*.log")):
                try:
                    if os.path.getmtime(fname) < cutoff:
                        os.remove(fname)
                except OSError:
                    pass
            ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            path = os.path.join(LOG_DIR, f"session-{ts}-{os.getpid()}.log")
            with open(path, "w", encoding="utf-8") as fh:
                os.chmod(path, 0o644)
                fh.write(
                    f"════ PS5 Manager — {datetime.datetime.now():%F %T} — utilisateur : {REAL_USER} — PID {os.getpid()}\n"
                )
                fh.write(f"système : {' '.join(os.uname()[:3])}\n")
            latest = os.path.join(LOG_DIR, "latest.log")
            try:
                if os.path.islink(latest) or os.path.exists(latest):
                    os.remove(latest)
                os.symlink(path, latest)
            except OSError:
                pass
            return path
        except OSError:
            fd, tmp = tempfile.mkstemp(prefix="ps5-manager-", suffix=".log")
            os.close(fd)
            return tmp

    def write_line(self, msg: str) -> None:
        line = f"{datetime.datetime.now():%H:%M:%S}  {msg}\n"
        try:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError:
            pass

    def list_logs(self) -> list[str]:
        files = glob.glob(os.path.join(LOG_DIR, "session-*.log"))
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return files[:20]

    def clear_all(self) -> None:
        for fname in glob.glob(os.path.join(LOG_DIR, "session-*.log")):
            if fname != self.path:
                try:
                    os.remove(fname)
                except OSError:
                    pass
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                fh.write(f"{datetime.datetime.now():%H:%M:%S}  journaux effacés\n")
        except OSError:
            pass


def log_window_enabled() -> bool:
    try:
        with open(LOG_WINDOW_FILE, encoding="utf-8") as fh:
            return fh.readline().strip() != "off"
    except OSError:
        return True


def set_log_window_enabled(enabled: bool) -> None:
    try:
        os.makedirs(os.path.dirname(LOG_WINDOW_FILE), exist_ok=True)
        with open(LOG_WINDOW_FILE, "w", encoding="utf-8") as fh:
            fh.write("on\n" if enabled else "off\n")
    except OSError:
        pass


def get_os_summary() -> tuple[str, str]:
    pretty = "Fedora Linux"
    try:
        with open("/etc/os-release", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("PRETTY_NAME="):
                    val = line.split("=", 1)[1].strip().strip('"')
                    pretty = val.split(" (")[0]
                    break
    except OSError:
        pass
    return pretty, os.uname().release


def gh_latest_tag(repo: str) -> Optional[str]:
    url = f"https://github.com/{repo}/releases/latest"
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            final_url = resp.geturl()
            tag = final_url.rstrip("/").split("/")[-1]
            return tag if tag and tag != "latest" else None
    except (urllib.error.URLError, OSError):
        return None


def gh_latest_asset(repo: str, pattern: str) -> Optional[str]:
    tag = gh_latest_tag(repo)
    if not tag:
        return None
    expanded = f"https://github.com/{repo}/releases/expanded_assets/{tag}"
    try:
        with urllib.request.urlopen(expanded, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        matches = re.findall(rf"/{re.escape(repo)}/releases/download/[^\"]+", html)
        rx = re.compile(pattern)
        for m in matches:
            if rx.search(m):
                return f"https://github.com{m}"
    except (urllib.error.URLError, OSError):
        pass
    return None


# ------------------------------------------------------------------------------
# Modèle Logithèque
# ------------------------------------------------------------------------------
@dataclass
class SoftwareItem:
    name: str
    kind: str  # rpm | flatpak | decky | ghrpm | dual
    category: str = "system"  # gaming | browser | system
    rpm_name: str = ""
    extra_rpms: tuple[str, ...] = ()
    copr_repo: str = ""
    post_install_user_cmd: tuple[str, ...] = ()
    fp_id: str = ""
    description_fr: str = ""
    description_en: str = ""
    icon: str = "application-x-executable-symbolic"


SOFTWARE_CATEGORIES: list[tuple[str, str, str]] = [
    ("gaming", "lib_cat_gaming", "lib_cat_gaming_sub"),
    ("browser", "lib_cat_browser", "lib_cat_browser_sub"),
    ("system", "lib_cat_system", "lib_cat_system_sub"),
]


SOFTWARE_CATALOG: list[SoftwareItem] = [
    # --- Gaming ---
    SoftwareItem(
        name="Steam",
        kind="rpm",
        category="gaming",
        rpm_name="steam",
        description_fr="Client de jeu Valve (active RPM Fusion automatiquement)",
        description_en="Valve gaming client (auto-enables RPM Fusion)",
        icon="applications-games-symbolic",
    ),
    SoftwareItem(
        name="Heroic Games Launcher",
        kind="flatpak",
        category="gaming",
        fp_id="com.heroicgameslauncher.hgl",
        description_fr="Lanceur Epic Games, GOG et Amazon Games",
        description_en="Epic Games, GOG and Amazon Games launcher",
        icon="applications-games-symbolic",
    ),
    SoftwareItem(
        name="ProtonUp-Qt",
        kind="flatpak",
        category="gaming",
        fp_id="net.davidotek.pupgui2",
        description_fr="Gérer Proton-GE et Wine-GE pour Steam & Heroic",
        description_en="Manage Proton-GE and Wine-GE for Steam & Heroic",
        icon="system-software-install-symbolic",
    ),
    SoftwareItem(
        name="Decky Loader",
        kind="decky",
        category="gaming",
        description_fr="Gestionnaire de plugins pour Steam Big Picture / Game Mode",
        description_en="Plugin loader for Steam Big Picture / Game Mode",
        icon="application-x-addon-symbolic",
    ),
    SoftwareItem(
        name="Universe",
        kind="rpm",
        category="gaming",
        rpm_name="universe",
        extra_rpms=("universe-desktop",),
        copr_repo="ilyasturki/universe",
        post_install_user_cmd=("universe", "setup"),
        description_fr="Lanceur manette (GOG, Steam, Epic, émulateurs) · COPR + GTK",
        description_en="Controller game launcher (GOG, Steam, Epic, emulators) · COPR + GTK",
        icon="applications-games-symbolic",
    ),
    # --- Navigateurs ---
    SoftwareItem(
        name="Opera",
        kind="dual",
        category="browser",
        rpm_name="opera-stable",
        fp_id="com.opera.Opera",
        description_fr="Navigateur web (RPM officiel ou Flatpak)",
        description_en="Web browser (official RPM or Flatpak)",
        icon="web-browser-symbolic",
    ),
    SoftwareItem(
        name="Brave",
        kind="dual",
        category="browser",
        rpm_name="brave-browser",
        fp_id="com.brave.Browser",
        description_fr="Navigateur orienté confidentialité (RPM ou Flatpak)",
        description_en="Privacy-focused browser (RPM or Flatpak)",
        icon="web-browser-symbolic",
    ),
    # --- Système & Utilitaires ---
    SoftwareItem(
        name="Etcher",
        kind="ghrpm",
        category="system",
        rpm_name="balena-etcher",
        description_fr="Écrire des images ISO/IMG sur clé USB (RPM GitHub)",
        description_en="Flash OS images to USB drives (GitHub RPM)",
        icon="drive-removable-media-symbolic",
    ),
    SoftwareItem(
        name="Bazaar",
        kind="flatpak",
        category="system",
        fp_id="io.github.kolunmi.Bazaar",
        description_fr="Boutique Flatpak moderne pour GNOME",
        description_en="Modern Flatpak store for GNOME",
        icon="system-software-install-symbolic",
    ),
    SoftwareItem(
        name="GNOME Extension Manager",
        kind="flatpak",
        category="system",
        fp_id="com.mattjakeman.ExtensionManager",
        description_fr="Parcourir et gérer les extensions GNOME Shell",
        description_en="Browse and manage GNOME Shell extensions",
        icon="application-x-addon-symbolic",
    ),
]


def detect_software_status(item: SoftwareItem) -> tuple[str, str]:
    """Retourne (status_code, label) : rpm | flatpak | installed | none."""
    if item.kind == "decky":
        if os.path.isdir(os.path.join(REAL_HOME, "homebrew")):
            return "installed", T("installed")
        return "none", T("not_installed")
    if item.rpm_name:
        res = subprocess.run(
            ["rpm", "-q", item.rpm_name], capture_output=True, text=True
        )
        if res.returncode == 0:
            return "rpm", T("installed_rpm")
    if item.fp_id and shutil.which("flatpak"):
        for scope in ("--system", "--user"):
            res = subprocess.run(
                ["flatpak", "info", scope, item.fp_id],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                return "flatpak", T("installed_flatpak")
    return "none", T("not_installed")


# ------------------------------------------------------------------------------
# Fenêtre de journal / texte (GTK4 + Libadwaita)
# ------------------------------------------------------------------------------
class TextLogWindow(Adw.Window):
    def __init__(self, parent: Gtk.Window, title: str) -> None:
        super().__init__(
            transient_for=parent,
            title=title,
            default_width=920,
            default_height=580,
        )
        self._path: Optional[str] = None
        self._offset: int = 0
        self._timer_id: Optional[int] = None

        self.view = Gtk.TextView(
            editable=False, monospace=True, cursor_visible=False
        )
        self.view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.view.set_left_margin(16)
        self.view.set_right_margin(16)
        self.view.set_top_margin(12)
        self.view.set_bottom_margin(12)
        self.buf = self.view.get_buffer()

        header = Adw.HeaderBar()
        self.title_widget = Adw.WindowTitle(title=title)
        header.set_title_widget(self.title_widget)

        clear_btn = Gtk.Button(icon_name="edit-clear-all-symbolic")
        clear_btn.set_tooltip_text(T("clear"))
        clear_btn.connect("clicked", lambda *_: self.buf.set_text(""))
        header.pack_end(clear_btn)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        scroll = Gtk.ScrolledWindow(child=self.view, hexpand=True, vexpand=True)
        toolbar.set_content(scroll)
        self.set_content(toolbar)
        self.connect("close-request", self._on_close)

    def _on_close(self, *_args) -> bool:
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
        self.hide()
        return True

    def append(self, text: str) -> None:
        clean = strip_ansi(text)
        if not clean:
            return
        end_iter = self.buf.get_end_iter()
        existing = self.buf.get_text(
            self.buf.get_start_iter(), end_iter, False
        )
        if existing and not existing.endswith("\n"):
            self.buf.insert(end_iter, "\n")
            end_iter = self.buf.get_end_iter()
        self.buf.insert(end_iter, clean if clean.endswith("\n") else clean + "\n")
        end_iter = self.buf.get_end_iter()
        self.buf.place_cursor(end_iter)
        self.view.scroll_to_iter(end_iter, 0.0, False, 0.0, 0.0)

    def load_text(self, text: str) -> None:
        self.buf.set_text(strip_ansi(text))
        end_iter = self.buf.get_end_iter()
        self.view.scroll_to_iter(end_iter, 0.0, False, 0.0, 0.0)

    def follow(self, path: str) -> None:
        self._path = path
        self._offset = 0
        self.buf.set_text("")
        self._tick()
        if self._timer_id is None:
            self._timer_id = GLib.timeout_add(350, self._tick)

    def _tick(self) -> bool:
        if not self._path:
            return False
        try:
            with open(self._path, encoding="utf-8", errors="replace") as fh:
                fh.seek(self._offset)
                chunk = fh.read()
                self._offset = fh.tell()
        except OSError:
            return True
        if chunk:
            self.append(chunk)
        return True


# ------------------------------------------------------------------------------
# Définition des 15 sections de la barre latérale
# ------------------------------------------------------------------------------
SECTIONS = [
    # Groupe 1
    ("logs", "utilities-terminal-symbolic", "sec_logs", 1),
    ("library", "system-software-install-symbolic", "sec_library", 1),
    ("aidev", "applications-development-symbolic", "sec_aidev", 1),
    # Groupe 2
    ("update", "software-update-available-symbolic", "sec_update", 2),
    ("lang", "preferences-desktop-locale-symbolic", "sec_lang", 2),
    ("repos", "network-server-symbolic", "sec_repos", 2),
    ("users", "system-users-symbolic", "sec_users", 2),
    ("fedora", "system-software-update-symbolic", "sec_fedora", 2),
    ("maint", "applications-engineering-symbolic", "sec_maint", 2),
    # Groupe 3
    ("power", "preferences-system-power-symbolic", "sec_power", 3),
    ("fan", "weather-windy-symbolic", "sec_fan", 3),
    ("hw", "applications-system-symbolic", "sec_hw", 3),
    ("mesa", "video-display-symbolic", "sec_mesa", 3),
    ("kernel", "drive-harddisk-symbolic", "sec_kernel", 3),
    ("ui_lang", "preferences-desktop-keyboard-symbolic", "sec_ui_lang", 3),
]


# ------------------------------------------------------------------------------
# Fenêtre principale (GNOME Settings / Libadwaita NavigationSplitView)
# ------------------------------------------------------------------------------
class Ps5ManagerWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, theme_sync: SystemThemeSync) -> None:
        super().__init__(
            application=app,
            title=APP_NAME,
            default_width=1160,
            default_height=760,
        )
        self.theme_sync = theme_sync
        self.logger = SessionLogger()
        self.busy = False
        self.auto_log_opened = False
        self.log_window: Optional[TextLogWindow] = None
        self.active_section = "logs"
        self.sidebar_rows: dict[str, Adw.ActionRow] = {}

        self.busy_spinner = Gtk.Spinner()
        self.overlay = Adw.ToastOverlay()
        self.split = Adw.NavigationSplitView()
        self.split.set_min_sidebar_width(260)
        self.split.set_max_sidebar_width(330)

        # Breakpoint responsive pour petites fenêtres
        bp = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse("max-width: 720sp")
        )
        bp.add_setter(self.split, "collapsed", True)
        self.add_breakpoint(bp)

        self.split.set_sidebar(self._build_sidebar())
        self.split.set_content(self._build_content())
        self.overlay.set_child(self.split)
        self.set_content(self.overlay)

        self._select_section("logs")

    # ---- Barre latérale ----
    def _build_sidebar(self) -> Adw.NavigationPage:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_title_widget(Gtk.Label(label=APP_NAME, css_classes=["title"]))

        search_btn = Gtk.ToggleButton(icon_name="system-search-symbolic")
        search_btn.set_tooltip_text(T("search_placeholder"))
        header.pack_start(search_btn)

        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_model = Gio.Menu()
        menu_model.append(T("system_info"), "win.show-sysinfo")
        menu_model.append(T("about"), "win.show-about")
        menu_btn.set_menu_model(menu_model)
        header.pack_end(menu_btn)

        self._register_window_actions()
        box.append(header)

        # Barre de recherche
        self.search_entry = Gtk.SearchEntry(placeholder_text=T("search_placeholder"))
        search_bar = Gtk.SearchBar(child=self.search_entry)
        search_bar.connect_entry(self.search_entry)
        search_btn.bind_property(
            "active", search_bar, "search-mode-enabled",
            2  # BIDIRECTIONAL
        )
        self.search_entry.connect("search-changed", self._on_search_changed)
        box.append(search_bar)

        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.add_css_class("navigation-sidebar")
        self.sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.sidebar_list.set_filter_func(self._filter_sidebar_row)
        self.sidebar_list.connect("row-activated", self._on_sidebar_activated)

        prev_group = 1
        for sec_id, icon, label_key, grp in SECTIONS:
            if grp != prev_group:
                sep = Gtk.Separator(
                    orientation=Gtk.Orientation.HORIZONTAL,
                    valign=Gtk.Align.CENTER,
                    vexpand=False,
                )
                sep.set_size_request(-1, 1)
                sep_row = Gtk.ListBoxRow(
                    selectable=False, activatable=False, focusable=False
                )
                sep_row.add_css_class("ps5-sidebar-sep")
                sep_row.set_child(sep)
                sep_row.is_separator = True  # type: ignore[attr-defined]
                self.sidebar_list.append(sep_row)
                prev_group = grp

            row = Adw.ActionRow(
                title=GLib.markup_escape_text(T(label_key)),
                activatable=True,
            )
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            row.sec_id = sec_id  # type: ignore[attr-defined]
            row.label_key = label_key  # type: ignore[attr-defined]
            self.sidebar_rows[sec_id] = row
            self.sidebar_list.append(row)

        scroll = Gtk.ScrolledWindow(
            child=self.sidebar_list, hexpand=True, vexpand=True
        )
        box.append(scroll)
        return Adw.NavigationPage(child=box, title=APP_NAME)

    def _register_window_actions(self) -> None:
        act_sys = Gio.SimpleAction.new("show-sysinfo", None)
        act_sys.connect("activate", lambda *_: self._show_sysinfo())
        self.add_action(act_sys)

        act_about = Gio.SimpleAction.new("show-about", None)
        act_about.connect("activate", lambda *_: self._show_about())
        self.add_action(act_about)

    def _filter_sidebar_row(self, row: Gtk.ListBoxRow) -> bool:
        q = self.search_entry.get_text().strip().lower()
        if not q:
            return True
        if getattr(row, "is_separator", False):
            return False
        sec_id = getattr(row, "sec_id", "")
        label_key = getattr(row, "label_key", "")
        title = (T(label_key) if label_key else getattr(row, "get_title", lambda: "")()).lower()
        return q in title or q in sec_id

    def _on_search_changed(self, _entry: Gtk.SearchEntry) -> None:
        self.sidebar_list.invalidate_filter()

    def _on_sidebar_activated(self, _lb: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        sec_id = getattr(row, "sec_id", None)
        if sec_id:
            self._select_section(sec_id)
            self.split.set_show_content(True)

    # ---- Contenu principal ----
    def _build_content(self) -> Adw.NavigationPage:
        self.nav = Adw.NavigationView()
        placeholder = Adw.NavigationPage(child=Gtk.Box(), title=APP_NAME)
        self.nav.add(placeholder)
        return Adw.NavigationPage(child=self.nav, title=APP_NAME)

    def _select_section(self, sec_id: str) -> None:
        self.active_section = sec_id
        row = self.sidebar_rows.get(sec_id)
        if row:
            self.sidebar_list.select_row(row)
        page = self._make_section_page(sec_id)
        self.nav.replace([page])

    def rebuild_ui_for_language(self) -> None:
        for sec_id, row in self.sidebar_rows.items():
            row.set_title(GLib.markup_escape_text(T(row.label_key)))  # type: ignore[attr-defined]
        self.search_entry.set_placeholder_text(T("search_placeholder"))
        self._select_section(self.active_section)

    def _make_section_page(self, sec_id: str) -> Adw.NavigationPage:
        sec_meta = next((s for s in SECTIONS if s[0] == sec_id), SECTIONS[0])
        title = T(sec_meta[2])

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=title))

        header.pack_end(self.busy_spinner)
        log_btn = Gtk.Button(icon_name="utilities-terminal-symbolic")
        log_btn.set_tooltip_text(T("logs_live"))
        log_btn.connect("clicked", lambda *_: self.open_live_log(follow=True))
        header.pack_end(log_btn)

        toolbar.add_top_bar(header)

        pref_page = Adw.PreferencesPage()
        builder = PAGE_BUILDERS.get(sec_id)
        if builder:
            builder(self, pref_page)

        toolbar.set_content(pref_page)
        return Adw.NavigationPage(child=toolbar, title=title)

    # ---- Helpers d'interface Libadwaita ----
    def row(
        self,
        title: str,
        subtitle: Optional[str] = None,
        icon: Optional[str] = None,
        callback: Optional[Callable] = None,
        suffix_icon: Optional[str] = "go-next-symbolic",
    ) -> Adw.ActionRow:
        r = Adw.ActionRow(
            title=GLib.markup_escape_text(title),
            activatable=callback is not None,
        )
        if subtitle:
            r.set_subtitle(GLib.markup_escape_text(subtitle))
        if icon:
            r.add_prefix(Gtk.Image.new_from_icon_name(icon))
        if suffix_icon:
            r.add_suffix(Gtk.Image.new_from_icon_name(suffix_icon))
        if callback:
            r.connect("activated", callback)
        return r

    def toast(self, message: str) -> None:
        self.overlay.add_toast(Adw.Toast(title=message, timeout=4))

    def show_info(self, heading: str, body: str) -> None:
        dlg = Adw.AlertDialog(heading=heading, body=body)
        dlg.add_response("ok", T("close"))
        dlg.set_default_response("ok")
        dlg.present(self)

    def show_confirm(
        self,
        heading: str,
        body: str,
        on_confirm: Callable[[], None],
        destructive: bool = True,
    ) -> None:
        dlg = Adw.AlertDialog(heading=heading, body=body)
        dlg.add_response("cancel", T("cancel"))
        dlg.add_response("ok", T("confirm"))
        if destructive:
            dlg.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        else:
            dlg.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("cancel")
        dlg.set_close_response("cancel")

        def _on_resp(_d, resp):
            if resp == "ok":
                on_confirm()

        dlg.connect("response", _on_resp)
        dlg.present(self)

    def show_prompt(
        self,
        heading: str,
        body: str,
        placeholder: str,
        on_submit: Callable[[str], None],
        password: bool = False,
    ) -> None:
        dlg = Adw.AlertDialog(heading=heading, body=body)
        entry = (
            Gtk.PasswordEntry(show_peek_icon=True)
            if password
            else Gtk.Entry(placeholder_text=placeholder)
        )
        entry.set_margin_top(8)
        dlg.set_extra_child(entry)
        dlg.add_response("cancel", T("cancel"))
        dlg.add_response("ok", T("ok"))
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("ok")
        dlg.set_close_response("cancel")

        def _on_resp(_d, resp):
            if resp == "ok":
                on_submit(entry.get_text())

        dlg.connect("response", _on_resp)
        dlg.present(self)

    def show_text_modal(self, title: str, content: str) -> None:
        win = TextLogWindow(self, title)
        win.load_text(content or T("logs_none"))
        win.present()

    def open_live_log(self, follow: bool = True) -> None:
        if self.log_window is None:
            self.log_window = TextLogWindow(self, T("sec_logs"))
        self.log_window.title_widget.set_title(T("logs_live"))
        self.log_window.present()
        if follow:
            self.log_window.follow(self.logger.path)

    # ---- Exécuteur asynchrone via PTY ----
    def run_task(
        self,
        title: str,
        fn: Callable[[Callable[[str], None]], tuple[bool, str]],
        on_done: Optional[Callable[[bool, str], None]] = None,
    ) -> None:
        if self.busy:
            self.toast(T("busy"))
            return
        self.busy = True
        self.busy_spinner.start()
        self.logger.write_line(f"──── {title}")

        if log_window_enabled() and not self.auto_log_opened:
            self.auto_log_opened = True
            self.open_live_log(follow=True)

        def _emit(line: str) -> None:
            self.logger.write_line(line)

        def _worker() -> None:
            ok = False
            msg = ""
            try:
                ok, msg = fn(_emit)
            except Exception as exc:
                ok = False
                msg = str(exc)
            self.logger.write_line(f"──── fin : {title} ({'OK' if ok else 'ERR'})")
            GLib.idle_add(self._finish_task, title, ok, msg, on_done)

        threading.Thread(target=_worker, daemon=True).start()

    def _finish_task(
        self,
        title: str,
        ok: bool,
        msg: str,
        on_done: Optional[Callable[[bool, str], None]],
    ) -> bool:
        self.busy = False
        self.busy_spinner.stop()
        if msg:
            if ok:
                self.toast(f"{title} — {msg}")
            else:
                self.show_info(title, msg)
        else:
            self.toast(f"{title} — {T('done') if ok else T('failed') % 1}")
        if on_done:
            on_done(ok, msg)
        return False

    def run_cmd_pty(
        self,
        cmd: list[str] | str,
        emit: Callable[[str], None],
        as_user: bool = False,
        shell: bool = False,
    ) -> int:
        if isinstance(cmd, str) and not shell:
            full_cmd: list[str] | str = ["bash", "-c", cmd]
        else:
            full_cmd = cmd

        proc_kwargs: dict[str, Any] = user_subprocess_kwargs() if as_user else {"env": os.environ}
        prefix = f"[{REAL_USER}] " if as_user and REAL_USER != "root" else ""
        self.logger.write_line(f"commande : {prefix}{full_cmd}")
        master_fd, slave_fd = pty.openpty()
        proc = subprocess.Popen(
            full_cmd,
            shell=shell,
            stdin=subprocess.DEVNULL,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            **proc_kwargs,
        )
        os.close(slave_fd)

        buf = b""
        while True:
            rlist, _, _ = select.select([master_fd], [], [], 0.2)
            if rlist:
                try:
                    data = os.read(master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    raw_line, buf = buf.split(b"\n", 1)
                    emit(strip_ansi(raw_line.decode("utf-8", errors="replace")))
            elif proc.poll() is not None:
                break
        if buf:
            emit(strip_ansi(buf.decode("utf-8", errors="replace")))
        os.close(master_fd)
        return proc.wait()

    # ---- Actions menu global ----
    def _show_sysinfo(self) -> None:
        os_name, k_ver = get_os_summary()
        body = (
            f"OS : {os_name}\n"
            f"Kernel : {k_ver}\n"
            f"User : {REAL_USER} (uid={REAL_UID})\n"
            f"GNOME Accent : {self.theme_sync.current_accent}\n"
            f"DNF5 : {'yes' if IS_DNF5 else 'no'}\n"
            f"Session log : {self.logger.path}"
        )
        self.show_info(T("system_info"), body)

    def _show_about(self) -> None:
        if hasattr(Adw, "AboutDialog"):
            about = Adw.AboutDialog(
                application_name=APP_NAME,
                application_icon="applications-system-symbolic",
                version="2.0.0 (GTK4 / Libadwaita)",
                developer_name="nexgen999",
                website="https://github.com/nexgen999/ps5-fedora-manager",
                comments="Gestionnaire système, matériel et logiciels pour Fedora sur PS5.",
            )
            about.present(self)
        else:
            self.show_info(APP_NAME, "PS5 Fedora Manager — GTK4 / Libadwaita (nexgen999)")


# ------------------------------------------------------------------------------
# Builders des 15 pages
# ------------------------------------------------------------------------------
def build_page_logs(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    g1 = Adw.PreferencesGroup(title=T("logs_group_main"))
    g1.add(
        win.row(
            T("logs_live"),
            T("logs_live_sub"),
            "media-playback-start-symbolic",
            lambda *_: win.open_live_log(follow=True),
        )
    )
    g1.add(
        win.row(
            T("logs_session"),
            os.path.basename(win.logger.path),
            "text-x-generic-symbolic",
            lambda *_: win.open_live_log(follow=True),
        )
    )
    g1.add(
        win.row(
            T("logs_old"),
            T("logs_old_sub"),
            "folder-documents-symbolic",
            lambda *_: _push_old_logs(win),
        )
    )
    page.add(g1)

    g2 = Adw.PreferencesGroup(title=T("logs_group_opts"))
    sw = Adw.SwitchRow(
        title=GLib.markup_escape_text(T("logs_auto")),
        subtitle=GLib.markup_escape_text(T("logs_auto_sub")),
    )
    sw.add_prefix(Gtk.Image.new_from_icon_name("view-refresh-symbolic"))
    sw.set_active(log_window_enabled())
    sw.connect("notify::active", lambda r, _p: set_log_window_enabled(r.get_active()))
    g2.add(sw)

    def _do_clear():
        win.logger.clear_all()
        win.toast(T("logs_cleared"))

    g2.add(
        win.row(
            T("logs_clear"),
            T("logs_clear_sub"),
            "user-trash-symbolic",
            lambda *_: win.show_confirm(
                T("logs_clear"), T("logs_clear_confirm"), _do_clear
            ),
        )
    )
    page.add(g2)


def _push_old_logs(win: Ps5ManagerWindow) -> None:
    sub = Adw.PreferencesPage()
    grp = Adw.PreferencesGroup(title=T("logs_old"))
    files = win.logger.list_logs()
    if not files:
        grp.add(Adw.ActionRow(title=GLib.markup_escape_text(T("logs_none"))))
    for path in files:
        name = os.path.basename(path)
        size_kb = max(1, os.path.getsize(path) // 1024) if os.path.exists(path) else 0
        grp.add(
            win.row(
                name,
                f"{size_kb} Ko",
                "text-x-generic-symbolic",
                lambda _r, p=path, n=name: _open_file_log(win, p, n),
            )
        )
    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=T("logs_old")))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=T("logs_old")))


def _open_file_log(win: Ps5ManagerWindow, path: str, name: str) -> None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            win.show_text_modal(name, fh.read())
    except OSError as exc:
        win.show_info(name, str(exc))


def build_page_library(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    seen_categories: set[str] = set()
    for cat_id, title_key, sub_key in SOFTWARE_CATEGORIES:
        items = [it for it in SOFTWARE_CATALOG if it.category == cat_id]
        if not items:
            continue
        seen_categories.add(cat_id)
        grp = Adw.PreferencesGroup(title=T(title_key), description=T(sub_key))
        for item in items:
            _code, status_lbl = detect_software_status(item)
            desc = item.description_fr if UI_LANG == "fr" else item.description_en
            grp.add(
                win.row(
                    item.name,
                    f"{desc} · {status_lbl}",
                    item.icon,
                    lambda _r, it=item: _push_software_actions(win, it),
                )
            )
        page.add(grp)

    extra = [it for it in SOFTWARE_CATALOG if it.category not in seen_categories]
    if extra:
        grp = Adw.PreferencesGroup(title=T("lib_title"), description=T("lib_sub"))
        for item in extra:
            _code, status_lbl = detect_software_status(item)
            desc = item.description_fr if UI_LANG == "fr" else item.description_en
            grp.add(
                win.row(
                    item.name,
                    f"{desc} · {status_lbl}",
                    item.icon,
                    lambda _r, it=item: _push_software_actions(win, it),
                )
            )
        page.add(grp)

    g_ai = Adw.PreferencesGroup(title=T("sec_aidev"), description=T("aidev_open_sub"))
    g_ai.add(
        win.row(
            T("sec_aidev"),
            T("aidev_open_sub"),
            "applications-development-symbolic",
            lambda *_: win._select_section("aidev"),
        )
    )
    page.add(g_ai)


def _push_software_actions(win: Ps5ManagerWindow, item: SoftwareItem) -> None:
    code, status_lbl = detect_software_status(item)
    sub = Adw.PreferencesPage()
    grp = Adw.PreferencesGroup(
        title=item.name,
        description=f"{status_lbl}",
    )

    def _run_sw(action: str) -> None:
        if item.kind == "dual" and action == "install" and code == "none":
            dlg = Adw.AlertDialog(
                heading=item.name, body=T("choose_format") % item.name
            )
            dlg.add_response("cancel", T("cancel"))
            dlg.add_response("rpm", T("format_rpm"))
            dlg.add_response("flatpak", T("format_flatpak"))
            dlg.set_response_appearance("rpm", Adw.ResponseAppearance.SUGGESTED)

            def _resp(_d, resp):
                if resp in ("rpm", "flatpak"):
                    _exec_software_action(win, item, action, forced_fmt=resp)

            dlg.connect("response", _resp)
            dlg.present(win)
        else:
            _exec_software_action(win, item, action)

    actions = [
        ("install", T("install"), "system-software-install-symbolic"),
        ("update", T("update"), "software-update-available-symbolic"),
        ("check", T("check"), "dialog-question-symbolic"),
        ("remove", T("remove"), "user-trash-symbolic"),
    ]
    for act, lbl, ic in actions:
        grp.add(win.row(lbl, None, ic, lambda _r, a=act: _run_sw(a)))
    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=item.name))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=item.name))


def _ensure_rpmfusion(win: Ps5ManagerWindow, emit: Callable[[str], None]) -> bool:
    if os.path.isfile("/etc/yum.repos.d/rpmfusion-nonfree.repo"):
        return True
    fed = subprocess.run(["rpm", "-E", "%fedora"], capture_output=True, text=True).stdout.strip() or "45"
    rc = win.run_cmd_pty(
        [
            "dnf", "install", "-y",
            f"https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-{fed}.noarch.rpm",
            f"https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-{fed}.noarch.rpm",
        ],
        emit,
    )
    return rc == 0


def _ensure_copr_repo(win: Ps5ManagerWindow, copr_slug: str, emit: Callable[[str], None]) -> bool:
    slug_pattern = copr_slug.replace("/", "*")
    if glob.glob(f"/etc/yum.repos.d/*{slug_pattern}*.repo"):
        return True
    if subprocess.run(["dnf", "copr", "--help"], capture_output=True).returncode != 0:
        win.run_cmd_pty(["dnf", "install", "-y", "dnf5-plugins" if IS_DNF5 else "dnf-plugins-core"], emit)
    rc = win.run_cmd_pty(["dnf", "copr", "enable", "-y", copr_slug], emit)
    return rc == 0


def _ensure_flathub() -> bool:
    if not shutil.which("flatpak"):
        return False
    res = subprocess.run(
        ["flatpak", "remote-add", "--system", "--if-not-exists", "flathub", FLATHUB_REPO],
        capture_output=True,
    )
    return res.returncode == 0


def _exec_software_action(
    win: Ps5ManagerWindow,
    item: SoftwareItem,
    action: str,
    forced_fmt: Optional[str] = None,
) -> None:
    def _task(emit: Callable[[str], None]) -> tuple[bool, str]:
        fmt, _ = detect_software_status(item)
        kind = item.kind
        if kind == "dual":
            target_fmt = forced_fmt or (fmt if fmt != "none" else "rpm")
            if action == "install" and fmt != "none":
                return True, f"{item.name} ({fmt})"
            if action != "install" and fmt == "none":
                return False, f"{item.name} : {T('not_installed')}"
            if target_fmt == "rpm":
                if action == "install":
                    if item.name == "Opera":
                        win.run_cmd_pty(["rpm", "--import", OPERA_KEY], emit)
                        with open(OPERA_REPO_FILE, "w", encoding="utf-8") as fh:
                            fh.write(
                                "[opera]\nname=Opera packages\ntype=rpm-md\n"
                                "baseurl=https://rpm.opera.com/rpm\ngpgcheck=1\n"
                                f"gpgkey={OPERA_KEY}\nenabled=1\n"
                            )
                    else:
                        if IS_DNF5:
                            win.run_cmd_pty(["dnf", "config-manager", "addrepo", f"--from-repofile={BRAVE_REPO}"], emit)
                        else:
                            win.run_cmd_pty(["dnf", "config-manager", "--add-repo", BRAVE_REPO], emit)
                        win.run_cmd_pty(["rpm", "--import", BRAVE_KEY], emit)
                    rc = win.run_cmd_pty(["dnf", "install", "-y", item.rpm_name], emit)
                    return rc == 0, T("done") if rc == 0 else T("failed") % rc
                if action == "update":
                    rc = win.run_cmd_pty(["dnf", "upgrade", "-y", item.rpm_name], emit)
                    return rc == 0, T("done") if rc == 0 else T("failed") % rc
                if action == "remove":
                    rc = win.run_cmd_pty(["dnf", "remove", "-y", item.rpm_name], emit)
                    return rc == 0, T("done") if rc == 0 else T("failed") % rc
                if action == "check":
                    res = subprocess.run(["dnf", "check-update", "-q", item.rpm_name], capture_output=True)
                    if res.returncode == 0:
                        return True, f"{item.name} : à jour (RPM)"
                    if res.returncode == 100:
                        return True, f"{item.name} : mise à jour disponible (RPM)"
                    return False, "Vérification impossible"
            else:
                kind = "flatpak"

        if kind == "rpm":
            pkgs = [item.rpm_name, *item.extra_rpms]
            if action in ("install", "update"):
                if item.rpm_name == "steam":
                    _ensure_rpmfusion(win, emit)
                if item.copr_repo and not _ensure_copr_repo(win, item.copr_repo, emit):
                    return False, f"Impossible d'activer le dépôt COPR {item.copr_repo}"
                if action == "install":
                    rc = win.run_cmd_pty(["dnf", "install", "-y", *pkgs], emit)
                    if rc == 0 and item.post_install_user_cmd:
                        win.run_cmd_pty(list(item.post_install_user_cmd), emit, as_user=True)
                else:
                    if fmt == "none":
                        return False, f"{item.name} : {T('not_installed')}"
                    rc = win.run_cmd_pty(["dnf", "upgrade", "-y", "--refresh", *pkgs], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "remove":
                if fmt == "none":
                    return True, T("not_installed")
                rc = win.run_cmd_pty(["dnf", "remove", "-y", *pkgs], emit)
                if rc == 0 and item.copr_repo:
                    if win.run_cmd_pty(["dnf", "copr", "remove", "-y", item.copr_repo], emit) != 0:
                        win.run_cmd_pty(["dnf", "copr", "disable", "-y", item.copr_repo], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "check":
                if fmt == "none":
                    return True, T("not_installed")
                res = subprocess.run(["dnf", "check-update", "-q", *pkgs], capture_output=True)
                if res.returncode == 0:
                    return True, f"{item.name} : à jour"
                if res.returncode == 100:
                    return True, f"{item.name} : mise à jour disponible"
                return False, "Vérification impossible"

        if kind == "flatpak":
            if action == "install":
                if not _ensure_flathub():
                    return False, "Flathub indisponible"
                rc = win.run_cmd_pty(["flatpak", "install", "--system", "--noninteractive", "flathub", item.fp_id], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "update":
                rc = win.run_cmd_pty(["flatpak", "update", "--system", "--noninteractive", item.fp_id], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "remove":
                rc = win.run_cmd_pty(["flatpak", "uninstall", "--system", "--noninteractive", item.fp_id], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "check":
                if fmt == "none":
                    return True, T("not_installed")
                res = subprocess.run(["flatpak", "remote-ls", "--system", "--updates", "flathub"], capture_output=True, text=True)
                has_upd = any(line.split()[0] == item.fp_id for line in res.stdout.splitlines() if line.strip())
                return True, f"{item.name} : {'mise à jour disponible' if has_upd else 'à jour'}"

        if kind == "decky":
            if action in ("install", "update"):
                rc = win.run_cmd_pty(f"curl -fsSL '{DECKY_INSTALL}' | bash", emit, as_user=True)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "remove":
                rc = win.run_cmd_pty(f"curl -fsSL '{DECKY_UNINSTALL}' | bash", emit, as_user=True)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "check":
                return True, T("installed") if fmt == "installed" else T("not_installed")

        if kind == "ghrpm":
            if action in ("install", "update"):
                url = gh_latest_asset("balena-io/etcher", r"x86_64\.rpm$")
                if not url:
                    return False, "RPM introuvable sur GitHub"
                rc = win.run_cmd_pty(["dnf", "install", "-y", "--setopt=localpkg_gpgcheck=0", url], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "remove":
                rc = win.run_cmd_pty(["dnf", "remove", "-y", item.rpm_name], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "check":
                inst = subprocess.run(["rpm", "-q", "--qf", "%{VERSION}", item.rpm_name], capture_output=True, text=True)
                if inst.returncode != 0:
                    return True, T("not_installed")
                url = gh_latest_asset("balena-io/etcher", r"x86_64\.rpm$") or ""
                latest = url.split("balena-etcher-")[-1].split("-")[0] if "balena-etcher-" in url else ""
                if latest and latest != inst.stdout.strip():
                    return True, f"{inst.stdout.strip()} -> {latest}"
                return True, f"{inst.stdout.strip()} (à jour)"
        return False, "Action inconnue"

    win.run_task(f"{item.name} — {T(action)}", _task, lambda *_: win._select_section("library"))


def build_page_update(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = Adw.PreferencesGroup(title=T("mgr_title"))

    def _do_update():
        def _task(emit):
            rc_deps = win.run_cmd_pty(["dnf", "install", "-y", *INTERFACE_DEPS], emit)
            if rc_deps != 0:
                return False, T("failed") % rc_deps
            # xhost est optionnel mais recommandé sous GNOME Wayland/Xwayland
            win.run_cmd_pty(["dnf", "install", "-y", "xhost"], emit)

            if os.path.isdir(os.path.join(INSTALL_DIR, ".git")):
                rc = win.run_cmd_pty(["git", "-C", INSTALL_DIR, "fetch", "--all", "--prune"], emit)
                if rc == 0:
                    rc = win.run_cmd_pty(["git", "-C", INSTALL_DIR, "reset", "--hard", "origin/main"], emit)
            else:
                rc = win.run_cmd_pty(["git", "clone", REPO_URL, INSTALL_DIR], emit)
            if rc != 0:
                return False, T("failed") % rc

            # Détecte le point d'entrée GTK4 dans le dépôt cloné
            script_src = None
            for cand in ("ps5_manager.py", "ps5-manager.py"):
                cand_path = os.path.join(INSTALL_DIR, cand)
                if os.path.isfile(cand_path):
                    script_src = cand
                    break

            install_pairs = []
            if script_src:
                install_pairs.append((script_src, "/usr/local/bin/ps5-manager", "0755"))
            install_pairs.extend([
                ("ps5-manager.desktop", "/usr/share/applications/ps5-manager.desktop", "0644"),
                ("icon.png", "/usr/share/pixmaps/ps5-manager.png", "0644"),
            ])

            for src, dst, mode in install_pairs:
                p = os.path.join(INSTALL_DIR, src)
                if os.path.isfile(p):
                    rc_inst = win.run_cmd_pty(["install", "-o", "root", "-g", "root", "-m", mode, p, dst], emit)
                    if rc_inst != 0:
                        return False, T("failed") % rc_inst

            apply_install_permissions()
            win.run_cmd_pty(["update-desktop-database", "/usr/share/applications/"], emit)
            emit("Droits (root:root, 0755/0644, Polkit GUI, SELinux) appliqués.")
            emit("Redémarrage automatique de PS5 Manager…")
            return True, T("done")

        def _on_update_done(ok: bool, _msg: str) -> None:
            if not ok:
                return
            win.toast(
                "Mise à jour terminée — redémarrage automatique…"
                if UI_LANG == "fr"
                else "Update finished — restarting…"
            )

            def _do_restart() -> bool:
                app = win.get_application()
                if app is not None:
                    app.restart_on_exit = True  # type: ignore[attr-defined]
                if win.log_window is not None:
                    win.log_window.destroy()
                    win.log_window = None
                win.destroy()
                if app is not None:
                    app.quit()
                return False

            GLib.timeout_add(900, _do_restart)

        win.run_task(T("mgr_update"), _task, _on_update_done)

    def _do_uninstall():
        for target in (
            INSTALL_DIR,
            "/usr/local/bin/ps5-manager",
            "/usr/share/applications/ps5-manager.desktop",
            "/usr/share/pixmaps/ps5-manager.png",
            POLKIT_POLICY_PATH,
        ):
            shutil.rmtree(target, ignore_errors=True) if os.path.isdir(target) else (
                os.remove(target) if os.path.exists(target) else None
            )
        win.toast(T("done"))
        GLib.timeout_add_seconds(1, lambda: win.close() or False)

    grp.add(win.row(T("mgr_update"), T("mgr_update_sub"), "software-update-available-symbolic", lambda *_: _do_update()))
    grp.add(
        win.row(
            T("mgr_uninstall"),
            T("mgr_uninstall_sub"),
            "user-trash-symbolic",
            lambda *_: win.show_confirm(T("mgr_uninstall"), T("mgr_uninstall_confirm"), _do_uninstall),
        )
    )
    page.add(grp)


def build_page_lang(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = Adw.PreferencesGroup(title=T("sec_lang"))

    def _view_packs():
        packs = subprocess.run(["rpm", "-qa", "langpacks-*", "glibc-langpack-*"], capture_output=True, text=True).stdout
        loc = subprocess.run(["localectl", "status"], capture_output=True, text=True).stdout
        win.show_text_modal(T("lang_view"), f"===== Langpacks =====\n{packs}\n===== localectl =====\n{loc}")

    def _install_lang(code: str):
        code = code.strip().split(".")[0]
        if not code:
            return
        def _task(emit):
            rc = win.run_cmd_pty(["dnf", "install", "-y", f"langpacks-{code}", f"glibc-langpack-{code}"], emit)
            if rc != 0:
                short = code.split("_")[0]
                rc = win.run_cmd_pty(["dnf", "install", "-y", f"langpacks-{short}", f"glibc-langpack-{short}"], emit)
            return rc == 0, T("done") if rc == 0 else T("failed") % rc
        win.run_task(T("lang_install"), _task)

    grp.add(win.row(T("lang_view"), T("lang_view_sub"), "preferences-desktop-locale-symbolic", lambda *_: _view_packs()))
    grp.add(
        win.row(
            T("lang_install"),
            T("lang_install_sub"),
            "system-software-install-symbolic",
            lambda *_: win.show_prompt(T("lang_install"), T("lang_install_prompt"), "fr_FR.UTF-8", _install_lang),
        )
    )
    grp.add(win.row(T("lang_full"), T("lang_full_sub"), "preferences-system-symbolic", lambda *_: _push_full_lang_config(win)))
    page.add(grp)


def _push_full_lang_config(win: Ps5ManagerWindow) -> None:
    locales = subprocess.run(["localectl", "list-locales"], capture_output=True, text=True).stdout.splitlines() or ["fr_FR.UTF-8", "en_US.UTF-8"]
    keymaps = subprocess.run(["localectl", "list-x11-keymap-layouts"], capture_output=True, text=True).stdout.splitlines() or ["fr", "us", "de", "es"]

    sub = Adw.PreferencesPage()
    grp = Adw.PreferencesGroup(title=T("lang_full"))

    loc_row = Adw.ComboRow(title=GLib.markup_escape_text(T("lang_pick_locale")), model=Gtk.StringList.new(sorted(set(locales))[:80]))
    kb_row = Adw.ComboRow(title=GLib.markup_escape_text(T("lang_pick_kb")), model=Gtk.StringList.new(sorted(set(keymaps))[:80]))
    grp.add(loc_row)
    grp.add(kb_row)

    def _apply(*_):
        loc = loc_row.get_selected_item().get_string()
        kb = kb_row.get_selected_item().get_string()
        def _task(emit):
            short = loc.split(".")[0]
            win.run_cmd_pty(["dnf", "install", "-y", f"langpacks-{short}", f"glibc-langpack-{short}"], emit)
            win.run_cmd_pty(["localectl", "set-locale", f"LANG={loc}"], emit)
            win.run_cmd_pty(
                ["gdbus", "call", "--system", "--dest", "org.freedesktop.Accounts",
                 "--object-path", f"/org/freedesktop/Accounts/User{REAL_UID}",
                 "--method", "org.freedesktop.Accounts.User.SetLanguage", loc],
                emit,
            )
            win.run_cmd_pty(["gsettings", "set", "org.gnome.system.locale", "region", loc], emit, as_user=True)
            win.run_cmd_pty(["localectl", "set-keymap", kb], emit)
            win.run_cmd_pty(["localectl", "set-x11-keymap", kb], emit)
            return True, f"{loc} / {kb}"
        def _after(ok, _m):
            if ok:
                win.show_confirm(
                    T("lang_full"),
                    T("lang_logout_confirm") % (loc, kb),
                    lambda: subprocess.Popen(["gnome-session-quit", "--logout", "--force"], **user_subprocess_kwargs()),
                    destructive=False,
                )
        win.run_task(T("lang_full"), _task, _after)

    grp.add(win.row(T("ok"), None, "object-select-symbolic", _apply))
    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=T("lang_full")))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=T("lang_full")))


def build_page_repos(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    g1 = Adw.PreferencesGroup(title=T("sec_repos"))

    def _list_all():
        dnf_out = subprocess.run(["dnf", "repolist", "--all"], capture_output=True, text=True).stdout
        fp_sys = subprocess.run(["flatpak", "remotes", "--system"], capture_output=True, text=True).stdout if shutil.which("flatpak") else "Flatpak absent"
        fp_usr = subprocess.run(["flatpak", "remotes", "--user"], capture_output=True, text=True, **user_subprocess_kwargs()).stdout if shutil.which("flatpak") else ""
        win.show_text_modal(T("repo_list"), f"===== DNF =====\n{dnf_out}\n\n===== Flatpak (system) =====\n{fp_sys}\n\n===== Flatpak (user) =====\n{fp_usr}")

    def _install_rpmfusion_task(emit):
        ok = _ensure_rpmfusion(win, emit)
        return ok, T("done") if ok else T("failed") % 1

    def _install_flathub_task(_emit):
        ok = _ensure_flathub()
        return ok, T("done") if ok else T("failed") % 1

    g1.add(win.row(T("repo_list"), T("repo_list_sub"), "view-list-symbolic", lambda *_: _list_all()))
    g1.add(win.row(T("repo_rpmfusion"), T("repo_rpmfusion_sub"), "system-software-install-symbolic", lambda *_: win.run_task("RPM Fusion", _install_rpmfusion_task)))
    g1.add(win.row(T("repo_flathub"), T("repo_flathub_sub"), "system-software-install-symbolic", lambda *_: win.run_task("Flathub", _install_flathub_task)))
    g1.add(win.row(T("repo_refresh"), T("repo_refresh_sub"), "view-refresh-symbolic", lambda *_: _refresh_repos_task(win)))
    g1.add(
        win.row(
            T("repo_add"),
            None,
            "list-add-symbolic",
            lambda *_: win.show_prompt(
                T("repo_add"), T("repo_add_prompt"), "https://.../example.repo",
                lambda url: win.run_task(T("repo_add"), lambda e: (
                    win.run_cmd_pty(["dnf", "config-manager", "addrepo", f"--from-repofile={url}"] if IS_DNF5 else ["dnf", "config-manager", "--add-repo", url], e) == 0,
                    T("done"),
                )) if url.strip() else None,
            ),
        )
    )
    page.add(g1)

    g2 = Adw.PreferencesGroup()
    g2.add(
        win.row(
            T("repo_disable"), T("repo_disable_sub"), "action-unavailable-symbolic",
            lambda *_: win.show_prompt(
                T("repo_disable"), T("repo_id_prompt"), "rpmfusion-nonfree",
                lambda rid: win.run_task(T("repo_disable"), lambda e: (
                    win.run_cmd_pty(["dnf", "config-manager", "setopt", f"{rid}.enabled=0"] if IS_DNF5 else ["dnf", "config-manager", "--set-disabled", rid], e) == 0,
                    T("done"),
                )) if rid.strip() else None,
            ),
        )
    )
    g2.add(
        win.row(
            T("repo_rm_dnf"), None, "user-trash-symbolic",
            lambda *_: win.show_prompt(
                T("repo_rm_dnf"), T("repo_id_prompt"), "brave-browser",
                lambda rid: _remove_dnf_repo_file(win, rid.strip()),
            ),
        )
    )
    g2.add(
        win.row(
            T("repo_rm_flatpak"), None, "user-trash-symbolic",
            lambda *_: win.show_prompt(
                T("repo_rm_flatpak"), T("repo_fp_prompt"), "flathub",
                lambda rname: win.run_task(T("repo_rm_flatpak"), lambda e: (
                    win.run_cmd_pty(["flatpak", "remote-delete", "--system", rname], e) == 0
                    or win.run_cmd_pty(["flatpak", "remote-delete", "--user", rname], e, as_user=True) == 0,
                    T("done"),
                )) if rname.strip() else None,
            ),
        )
    )
    page.add(g2)


def _refresh_repos_task(win: Ps5ManagerWindow) -> None:
    def _task(emit):
        rc = win.run_cmd_pty(["bash", "-c", "dnf clean all && dnf makecache --refresh"], emit)
        if rc == 0 and shutil.which("flatpak"):
            win.run_cmd_pty(["flatpak", "update", "--appstream", "-y"], emit)
        return rc == 0, T("done") if rc == 0 else T("failed") % rc
    win.run_task(T("repo_refresh"), _task)


def _remove_dnf_repo_file(win: Ps5ManagerWindow, rid: str) -> None:
    if not rid:
        return
    matches = []
    for path in glob.glob("/etc/yum.repos.d/*.repo"):
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                if re.search(rf"^\s*\[{re.escape(rid)}\]", fh.read(), re.MULTILINE):
                    matches.append(path)
        except OSError:
            pass
    if not matches:
        win.show_info(T("repo_rm_dnf"), f"Aucun .repo pour [{rid}]")
        return
    def _do_rm_files():
        for p in matches:
            os.remove(p)
        win.toast(T("done"))

    win.show_confirm(
        T("repo_rm_dnf"),
        "\n".join(matches),
        _do_rm_files,
    )


def build_page_users(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = Adw.PreferencesGroup(title=T("sec_users"))

    def _list_users():
        lines = []
        try:
            with open("/etc/passwd", encoding="utf-8") as fh:
                for ln in fh:
                    parts = ln.strip().split(":")
                    if len(parts) >= 7:
                        uid = int(parts[2])
                        if 1000 <= uid < 65534:
                            lines.append(f"{parts[0]:<18} uid={uid:<6} home={parts[5]:<22} shell={parts[6]}")
        except OSError:
            pass
        win.show_text_modal(T("usr_list"), "\n".join(lines) or T("logs_none"))

    grp.add(win.row(T("usr_list"), T("usr_list_sub"), "system-users-symbolic", lambda *_: _list_users()))
    grp.add(
        win.row(
            T("usr_edit_me") % REAL_USER,
            T("usr_edit_me_sub"),
            "avatar-default-symbolic",
            lambda *_: win.show_prompt(
                T("usr_edit_me") % REAL_USER,
                T("usr_new_pass_prompt"),
                "",
                lambda pw: _set_user_password(win, REAL_USER, pw),
                password=True,
            ),
        )
    )
    grp.add(
        win.row(
            T("usr_add"), None, "list-add-symbolic",
            lambda *_: win.show_prompt(
                T("usr_add"), T("usr_name_prompt"), "nouvel_utilisateur",
                lambda uname: win.show_prompt(
                    uname, T("usr_pass_prompt"), "",
                    lambda pw: _create_user(win, uname.strip(), pw),
                    password=True,
                ) if uname.strip() else None,
            ),
        )
    )
    grp.add(
        win.row(
            T("usr_del"), None, "user-trash-symbolic",
            lambda *_: win.show_prompt(
                T("usr_del"), T("usr_name_prompt"), "",
                lambda uname: _delete_user(win, uname.strip()),
            ),
        )
    )
    grp.add(
        win.row(
            T("usr_root"), None, "dialog-password-symbolic",
            lambda *_: _root_status_dialog(win),
        )
    )
    page.add(grp)


def _set_user_password(win: Ps5ManagerWindow, user: str, pw: str) -> None:
    if not pw:
        return
    res = subprocess.run(["chpasswd"], input=f"{user}:{pw}\n", text=True, capture_output=True)
    if res.returncode == 0:
        win.toast(T("done"))
    else:
        win.show_info(user, res.stderr or T("failed") % res.returncode)


def _create_user(win: Ps5ManagerWindow, uname: str, pw: str) -> None:
    if not uname:
        return
    res = subprocess.run(["useradd", "-m", "-s", "/bin/bash", uname], capture_output=True, text=True)
    if res.returncode == 0:
        if pw:
            subprocess.run(["chpasswd"], input=f"{uname}:{pw}\n", text=True)
        win.toast(f"{uname} — {T('done')}")
    else:
        win.show_info(T("usr_add"), res.stderr or T("failed") % res.returncode)


def _delete_user(win: Ps5ManagerWindow, uname: str) -> None:
    if not uname or uname in ("root", REAL_USER):
        win.show_info(T("usr_del"), f"Refusé pour {uname}")
        return
    win.show_confirm(
        T("usr_del"),
        T("usr_del_confirm") % uname,
        lambda: win.run_task(T("usr_del"), lambda e: (win.run_cmd_pty(["userdel", "-r", uname], e) == 0, T("done"))),
    )


def _root_status_dialog(win: Ps5ManagerWindow) -> None:
    st = subprocess.run(["passwd", "-S", "root"], capture_output=True, text=True).stdout.strip()
    win.show_confirm(
        T("usr_root"),
        f"{st}\n\n{T('usr_new_pass_prompt')}",
        lambda: win.show_prompt(
            "Root", T("usr_pass_prompt"), "", lambda pw: _set_user_password(win, "root", pw), password=True
        ),
        destructive=False,
    )


def build_page_fedora(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = Adw.PreferencesGroup(title=T("sec_fedora"))
    grp.add(
        win.row(
            T("fed_apps"), T("fed_apps_sub"), "system-software-install-symbolic",
            lambda *_: win.run_task(T("fed_apps"), lambda e: (
                win.run_cmd_pty(["dnf", "upgrade", "-y"], e) == 0
                and (not shutil.which("flatpak") or win.run_cmd_pty(["flatpak", "update", "--system", "--noninteractive"], e) == 0),
                T("done"),
            )),
        )
    )
    grp.add(
        win.row(
            T("fed_sys"), T("fed_sys_sub"), "software-update-available-symbolic",
            lambda *_: win.run_task(T("fed_sys"), lambda e: (win.run_cmd_pty(["dnf", "upgrade", "--refresh", "-y"], e) == 0, T("done"))),
        )
    )
    grp.add(
        win.row(
            T("fed_lang"), T("fed_lang_sub"), "preferences-desktop-locale-symbolic",
            lambda *_: win.run_task(T("fed_lang"), lambda e: (win.run_cmd_pty(["dnf", "upgrade", "-y", "langpacks-*", "glibc-langpack-*"], e) == 0, T("done"))),
        )
    )
    grp.add(win.row(T("fed_meta"), T("repo_refresh_sub"), "view-refresh-symbolic", lambda *_: _refresh_repos_task(win)))
    page.add(grp)


def build_page_maint(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    g1 = Adw.PreferencesGroup(title=T("sec_maint"))

    def _clean_all():
        def _task(emit):
            win.run_cmd_pty(["bash", "-c", "dnf clean all && dnf makecache >/dev/null 2>&1 || true; journalctl --vacuum-time=7d || true; rm -rf /tmp/* /var/tmp/* 2>/dev/null || true"], emit)
            thumbs = os.path.join(REAL_HOME, ".cache", "thumbnails")
            if os.path.isdir(thumbs):
                shutil.rmtree(thumbs, ignore_errors=True)
            if shutil.which("flatpak"):
                win.run_cmd_pty(["flatpak", "uninstall", "--system", "--unused", "--noninteractive"], emit)
            return True, T("done")
        win.run_task(T("mnt_all"), _task)

    g1.add(win.row(T("mnt_all"), T("mnt_all_sub"), "edit-clear-all-symbolic", lambda *_: win.show_confirm(T("mnt_all"), T("mnt_all_sub"), _clean_all)))
    g1.add(win.row(T("mnt_cache"), "dnf clean all", "edit-clear-all-symbolic", lambda *_: win.run_task(T("mnt_cache"), lambda e: (win.run_cmd_pty(["dnf", "clean", "all"], e) == 0, T("done")))))
    g1.add(win.row(T("mnt_autoremove"), "dnf autoremove -y", "user-trash-symbolic", lambda *_: win.show_confirm(T("mnt_autoremove"), "dnf autoremove -y", lambda: win.run_task(T("mnt_autoremove"), lambda e: (win.run_cmd_pty(["dnf", "autoremove", "-y"], e) == 0, T("done"))))))
    g1.add(win.row(T("mnt_journal"), "journalctl --vacuum-time=7d", "text-x-generic-symbolic", lambda *_: win.run_task(T("mnt_journal"), lambda e: (win.run_cmd_pty(["journalctl", "--vacuum-time=7d"], e) == 0, T("done")))))
    g1.add(win.row(T("mnt_tmp"), "/tmp & /var/tmp", "folder-symbolic", lambda *_: win.show_confirm(T("mnt_tmp"), "rm -rf /tmp/* /var/tmp/*", lambda: win.run_task(T("mnt_tmp"), lambda e: (win.run_cmd_pty(["bash", "-c", "rm -rf /tmp/* /var/tmp/* 2>/dev/null || true"], e) == 0, T("done"))))))
    def _clean_thumbs():
        shutil.rmtree(os.path.join(REAL_HOME, ".cache", "thumbnails"), ignore_errors=True)
        win.toast(T("done"))

    g1.add(win.row(T("mnt_thumbs"), "~/.cache/thumbnails", "image-x-generic-symbolic", lambda *_: _clean_thumbs()))
    g1.add(win.row(T("mnt_kernels"), None, "drive-harddisk-symbolic", lambda *_: _clean_old_kernels(win)))
    g1.add(win.row(T("mnt_disk"), "df -hT", "drive-harddisk-symbolic", lambda *_: win.show_text_modal(T("mnt_disk"), subprocess.run(["df", "-hT"], capture_output=True, text=True).stdout)))
    page.add(g1)


def _installed_kernel_packages() -> list[tuple[str, str]]:
    """Retourne [(nevra, version), ...] triés du plus récent au plus ancien."""
    res = subprocess.run(
        ["rpm", "-qa", "linux-ps5*", "kernel-core*", "--qf", "%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\t%{VERSION}\n"],
        capture_output=True, text=True,
    )
    items: list[tuple[str, str]] = []
    for line in res.stdout.splitlines():
        if "\t" in line:
            nevra, ver = line.split("\t", 1)
            items.append((nevra.strip(), ver.strip()))

    def _ver_key(ver_str: str) -> tuple:
        return tuple(int(p) if p.isdigit() else p for p in re.split(r"([0-9]+)", ver_str))

    items.sort(key=lambda it: _ver_key(it[1]), reverse=True)
    return items


def _is_protected_kernel(ver: str, cur_k: str, esp_k: str) -> bool:
    if ver == cur_k or cur_k.startswith(ver + "-") or cur_k.startswith(ver + "."):
        return True
    if esp_k and (ver == esp_k or esp_k.startswith(ver + "-") or esp_k.startswith(ver + ".")):
        return True
    return False


def _remove_kernel_package(win: Ps5ManagerWindow, nevra: str, ver: str, emit: Callable[[str], None]) -> bool:
    cur_k = os.uname().release
    esp_k = _esp_kernel_version()
    if _is_protected_kernel(ver, cur_k, esp_k):
        emit(f"REFUS : {nevra} est actif ({cur_k}) ou sur /boot/efi ({esp_k}).")
        return False

    rc = win.run_cmd_pty(["dnf", "remove", "-y", nevra], emit)
    if rc != 0:
        return False

    # Nettoie l'initramfs généré par dracut pour l'ancien noyau supprimé
    for initrd in glob.glob(f"/boot/initrd.img-{ver}*"):
        initrd_k = os.path.basename(initrd)[len("initrd.img-"):]
        if not _is_protected_kernel(initrd_k, cur_k, esp_k):
            try:
                os.remove(initrd)
                emit(f"Supprimé : {initrd}")
            except OSError:
                pass

    # Vérifie que /boot/efi possède toujours un noyau bootable après suppression
    target_k = esp_k if (esp_k and os.path.isfile(f"/boot/vmlinuz-{esp_k}")) else cur_k
    if not (os.path.isfile("/boot/efi/bzImage") and os.path.isfile("/boot/efi/initrd.img")):
        if os.path.isfile("/etc/kernel/postinst.d/zz-update-boot"):
            win.run_cmd_pty(["/etc/kernel/postinst.d/zz-update-boot", target_k, f"/boot/vmlinuz-{target_k}"], emit)
        elif os.path.isfile(f"/boot/vmlinuz-{target_k}") and os.path.isfile(f"/boot/initrd.img-{target_k}"):
            shutil.copy2(f"/boot/vmlinuz-{target_k}", "/boot/efi/bzImage")
            shutil.copy2(f"/boot/initrd.img-{target_k}", "/boot/efi/initrd.img")
            os.sync()
    return True


def _clean_old_kernels(win: Ps5ManagerWindow) -> None:
    pkgs = _installed_kernel_packages()
    if not pkgs:
        win.show_info(T("mnt_kernels"), "Aucun paquet kernel trouvé.")
        return

    cur_k = os.uname().release
    esp_k = _esp_kernel_version()

    # Garde toujours : le noyau démarré, le noyau /boot/efi, et le plus récent
    removable: list[tuple[str, str]] = []
    kept_latest = False
    for nevra, ver in pkgs:
        if _is_protected_kernel(ver, cur_k, esp_k):
            continue
        if not kept_latest:
            kept_latest = True
            continue
        removable.append((nevra, ver))

    if not removable:
        lines = [f"• {n} ({T('krn_protected') if _is_protected_kernel(v, cur_k, esp_k) else T('krn_installed')})" for n, v in pkgs]
        win.show_info(T("mnt_kernels"), "Aucun ancien noyau à supprimer.\n\n" + "\n".join(lines))
        return

    summary = "\n".join(f"• {n}" for n, _v in removable)

    def _do_clean():
        def _task(emit):
            for nevra, ver in removable:
                if not _remove_kernel_package(win, nevra, ver, emit):
                    return False, f"{nevra} : {T('failed') % 1}"
            return True, T("done")
        win.run_task(T("mnt_kernels"), _task)

    win.show_confirm(
        T("mnt_kernels"),
        f"Paquets à supprimer (noyau actif {cur_k} conservé) :\n\n{summary}",
        _do_clean,
    )


def build_page_power(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = Adw.PreferencesGroup(title=T("sec_power"))

    sys_sleep_enabled = (
        subprocess.run(["systemctl", "is-enabled", "sleep.target"], capture_output=True, text=True).stdout.strip()
        != "masked"
    )
    idle_val = subprocess.run(
        ["gsettings", "get", "org.gnome.desktop.session", "idle-delay"],
        capture_output=True, text=True, **user_subprocess_kwargs(),
    ).stdout.strip()
    scr_sleep_enabled = not idle_val.endswith(" 0") and idle_val != "uint32 0"

    sw_sys = Adw.SwitchRow(title=GLib.markup_escape_text(T("pwr_sys")), subtitle=GLib.markup_escape_text(T("pwr_sys_sub")))
    sw_sys.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-power-symbolic"))
    sw_sys.set_active(sys_sleep_enabled)

    def _on_sys_toggle(row, _p):
        act = "unmask" if row.get_active() else "mask"
        rc = subprocess.run(["systemctl", act, "sleep.target", "suspend.target", "hibernate.target", "hybrid-sleep.target", "suspend-then-hibernate.target"]).returncode
        win.toast(T("done") if rc == 0 else T("failed") % rc)

    sw_sys.connect("notify::active", _on_sys_toggle)
    grp.add(sw_sys)

    sw_scr = Adw.SwitchRow(title=GLib.markup_escape_text(T("pwr_scr")), subtitle=GLib.markup_escape_text(T("pwr_scr_sub")))
    sw_scr.add_prefix(Gtk.Image.new_from_icon_name("video-display-symbolic"))
    sw_scr.set_active(scr_sleep_enabled)

    def _on_scr_toggle(row, _p):
        delay = "300" if row.get_active() else "0"
        rc = subprocess.run(["gsettings", "set", "org.gnome.desktop.session", "idle-delay", delay], **user_subprocess_kwargs()).returncode
        win.toast(T("done") if rc == 0 else T("failed") % rc)

    sw_scr.connect("notify::active", _on_scr_toggle)
    grp.add(sw_scr)

    def _set_full(enable: bool):
        act = "unmask" if enable else "mask"
        delay = "300" if enable else "0"
        ac_type = "suspend" if enable else "nothing"
        subprocess.run(["systemctl", act, "sleep.target", "suspend.target", "hibernate.target", "hybrid-sleep.target", "suspend-then-hibernate.target"])
        subprocess.run(["gsettings", "set", "org.gnome.desktop.session", "idle-delay", delay], **user_subprocess_kwargs())
        subprocess.run(["gsettings", "set", "org.gnome.settings-daemon.plugins.power", "sleep-inactive-ac-type", ac_type], **user_subprocess_kwargs())
        win._select_section("power")
        win.toast(T("done"))

    grp.add(win.row(T("pwr_enable_full"), T("pwr_full_sub"), "object-select-symbolic", lambda *_: _set_full(True)))
    grp.add(win.row(T("pwr_disable_full"), T("pwr_full_sub"), "action-unavailable-symbolic", lambda *_: _set_full(False)))
    page.add(grp)


def build_page_fan(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = Adw.PreferencesGroup(title=T("sec_fan"))

    def _svc_active(name: str) -> bool:
        return subprocess.run(["systemctl", "is-active", name], capture_output=True).returncode == 0

    sw_fan = Adw.SwitchRow(title=GLib.markup_escape_text(T("fan_svc")), subtitle=GLib.markup_escape_text(T("fan_svc_sub")))
    sw_fan.add_prefix(Gtk.Image.new_from_icon_name("weather-windy-symbolic"))
    sw_fan.set_active(_svc_active("ps5fan.service"))
    sw_fan.connect(
        "notify::active",
        lambda r, _p: win.toast(
            T("done") if subprocess.run(["systemctl", "enable" if r.get_active() else "disable", "--now", "ps5fan.service"]).returncode == 0
            else T("failed") % 1
        ),
    )
    grp.add(sw_fan)

    sw_boost = Adw.SwitchRow(title=GLib.markup_escape_text(T("fan_boost")), subtitle=GLib.markup_escape_text(T("fan_boost_sub")))
    sw_boost.add_prefix(Gtk.Image.new_from_icon_name("power-profile-performance-symbolic"))
    sw_boost.set_active(_svc_active("ps5boost.service"))
    sw_boost.connect(
        "notify::active",
        lambda r, _p: win.toast(
            T("done") if subprocess.run(["systemctl", "enable" if r.get_active() else "disable", "--now", "ps5boost.service"]).returncode == 0
            else T("failed") % 1
        ),
    )
    grp.add(sw_boost)

    def _show_fan_status():
        s1 = subprocess.run(["systemctl", "status", "ps5fan.service"], capture_output=True, text=True).stdout
        s2 = subprocess.run(["systemctl", "status", "ps5boost.service"], capture_output=True, text=True).stdout
        ctrl = ""
        if os.access("/usr/local/sbin/ps5_control", os.X_OK):
            ctrl = subprocess.run(["/usr/local/sbin/ps5_control", "--status"], capture_output=True, text=True).stdout
        win.show_text_modal(T("fan_status"), f"=== ps5fan.service ===\n{s1}\n\n=== ps5boost.service ===\n{s2}\n\n{ctrl}")

    grp.add(win.row(T("fan_status"), None, "utilities-system-monitor-symbolic", lambda *_: _show_fan_status()))
    grp.add(win.row(T("fan_restart"), None, "view-refresh-symbolic", lambda *_: win.toast(T("done") if subprocess.run(["systemctl", "restart", "ps5fan.service"]).returncode == 0 else T("failed") % 1)))
    grp.add(
        win.row(
            T("fan_tools"), T("fan_tools_sub"), "system-software-install-symbolic",
            lambda *_: win.run_task(T("fan_tools"), lambda e: (
                win.run_cmd_pty(["bash", "-c", f"tmp=$(mktemp -d) && git clone --depth=1 '{TOOLS_REPO}' \"$tmp/tools\" && cd \"$tmp/tools\" && ./install.sh && rm -rf \"$tmp\""], e) == 0,
                T("done"),
            )),
        )
    )
    page.add(grp)


def build_page_hw(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = Adw.PreferencesGroup(title=T("sec_hw"))

    def _hw_nodes():
        hwmon = subprocess.run(["ls", "-l", "/sys/class/hwmon/"], capture_output=True, text=True).stdout
        nodes = [
            "/sys/bus/platform/devices/ps5-fan/target_temp",
            "/sys/class/misc/ps5_buzzer/beep",
            "/sys/class/devfreq/ps5-gpufreq",
            "/sys/class/leds/ps5:rgb:multi_intensity",
        ]
        lines = ["===== /sys/class/hwmon/ =====", hwmon, "===== PS5 nodes ====="]
        for p in nodes:
            lines.append(f"  {'OK    ' if os.path.exists(p) else 'ABSENT'}  {p}")
        win.show_text_modal(T("hw_check"), "\n".join(lines))

    def _hwcon_check():
        local_f = os.path.join(HWCON_PREFIX, "src", "pyproject.toml")
        if not os.path.isfile(local_f):
            win.show_info(T("sec_hw"), T("not_installed"))
            return
        local_ver = ""
        with open(local_f, encoding="utf-8") as fh:
            for ln in fh:
                if ln.strip().startswith("version"):
                    local_ver = ln.split('"')[1]
                    break
        try:
            with urllib.request.urlopen(HWCON_PYPROJECT, timeout=8) as r:
                remote_txt = r.read().decode("utf-8", errors="replace")
            remote_ver = next((ln.split('"')[1] for ln in remote_txt.splitlines() if ln.strip().startswith("version")), "")
        except (urllib.error.URLError, OSError):
            remote_ver = ""
        win.show_info(T("sec_hw"), f"Installée : {local_ver or '?'}\nGitHub : {remote_ver or '?'}")

    grp.add(win.row(T("hw_check"), T("hw_check_sub"), "applications-system-symbolic", lambda *_: _hw_nodes()))
    grp.add(
        win.row(
            T("hw_install"), T("hw_install_sub"), "system-software-install-symbolic",
            lambda *_: win.run_task(T("hw_install"), lambda e: (
                win.run_cmd_pty(["dnf", "install", "-y", "python3-PyQt6"], e) >= 0
                and win.run_cmd_pty(f"curl -fsSL '{HWCON_INSTALL}' | bash", e, as_user=True) == 0,
                T("done"),
            )),
        )
    )
    grp.add(win.row(T("hw_check_upd"), None, "software-update-available-symbolic", lambda *_: _hwcon_check()))
    grp.add(
        win.row(
            T("hw_uninstall"), None, "user-trash-symbolic",
            lambda *_: win.show_confirm(
                T("hw_uninstall"), T("hw_uninstall"),
                lambda: win.run_task(T("hw_uninstall"), lambda e: (
                    win.run_cmd_pty(f"curl -fsSL '{HWCON_INSTALL}' | bash -s -- --uninstall", e, as_user=True) == 0,
                    T("done"),
                )),
            ),
        )
    )
    page.add(grp)


def build_page_mesa(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = Adw.PreferencesGroup(title=T("sec_mesa"))

    def _vulkan_summary(radv_only: bool):
        if not shutil.which("vulkaninfo"):
            win.show_info(T("sec_mesa"), "vulkaninfo absent — installez d'abord vulkan-tools.")
            return
        out = subprocess.run(["vulkaninfo", "--summary"], capture_output=True, text=True).stdout
        if radv_only:
            lines = [ln for ln in out.splitlines() if re.search(r"radv|deviceName|driverName", ln, re.I)]
            out = "\n".join(lines) or "Aucun périphérique RADV détecté."
        win.show_text_modal(T("mesa_radv") if radv_only else T("mesa_summary"), out)

    grp.add(win.row(T("mesa_tools"), T("mesa_tools_sub"), "system-software-install-symbolic", lambda *_: win.run_task(T("mesa_tools"), lambda e: (win.run_cmd_pty(["dnf", "install", "-y", "vulkan-tools", "mesa-demos"], e) == 0, T("done")))))
    grp.add(win.row(T("mesa_upd"), T("mesa_upd_sub"), "software-update-available-symbolic", lambda *_: win.run_task(T("mesa_upd"), lambda e: (win.run_cmd_pty(["dnf", "upgrade", "-y", "mesa*", "vulkan*"], e) == 0, T("done")))))
    grp.add(win.row(T("mesa_radv"), None, "video-display-symbolic", lambda *_: _vulkan_summary(True)))
    grp.add(win.row(T("mesa_summary"), None, "utilities-terminal-symbolic", lambda *_: _vulkan_summary(False)))
    page.add(grp)


def _esp_kernel_version() -> str:
    bz = "/boot/efi/bzImage"
    if not os.path.isfile(bz):
        return ""
    try:
        with open(bz, "rb") as fh:
            data = fh.read()
        m = re.search(rb"Linux version ([^\s]+)", data)
        if m:
            return m.group(1).decode("utf-8", errors="ignore")
    except OSError:
        pass
    return ""


def build_page_kernel(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    cur_k = os.uname().release
    esp_k = _esp_kernel_version() or "—"
    grp = Adw.PreferencesGroup(
        title=T("sec_kernel"),
        description=f"{T('krn_running')}: {cur_k} · {T('krn_esp')}: {esp_k}",
    )

    def _check_latest():
        tag = gh_latest_tag(KERNEL_REPO)
        if not tag or not tag.startswith("kernel-"):
            win.show_info(T("sec_kernel"), "Impossible de contacter GitHub.")
            return
        ver = tag[len("kernel-"):].rsplit("-", 1)[0]
        win.show_info(T("krn_latest"), f"Tag : {tag}\nVersion : {ver}\nActuel : {cur_k}")

    def _install_latest():
        if os.uname().machine != "x86_64":
            win.show_info(T("sec_kernel"), "x86_64 uniquement.")
            return
        tag = gh_latest_tag(KERNEL_REPO)
        if not tag or not tag.startswith("kernel-"):
            win.show_info(T("sec_kernel"), "Release introuvable.")
            return
        ver = tag[len("kernel-"):].rsplit("-", 1)[0]
        rpm_url = f"{KERNEL_BASE}/releases/download/{tag}/linux-ps5-{ver}-1.x86_64.rpm"

        def _do():
            def _task(emit):
                tmp_dir = "/tmp/ps5-kernel"
                os.makedirs(tmp_dir, exist_ok=True)
                local_rpm = os.path.join(tmp_dir, f"linux-ps5-{ver}-1.x86_64.rpm")
                try:
                    rc = win.run_cmd_pty(["curl", "-fL", "--retry", "3", "-o", local_rpm, rpm_url], emit)
                    if rc != 0 or not os.path.isfile(local_rpm):
                        return False, T("failed") % (rc or 1)

                    # Extrait le KVER exact depuis la liste des fichiers du RPM avant installation
                    qlp = subprocess.run(["rpm", "-qlp", local_rpm], capture_output=True, text=True).stdout
                    kver = ""
                    for path in qlp.splitlines():
                        m = re.match(r"^/(?:usr/)?lib/modules/([^/]+)$", path.strip())
                        if m:
                            kver = m.group(1)
                            break

                    # Installation avec --nosignature --replacefiles pour cohabiter avec l'ancien linux-ps5
                    rc = win.run_cmd_pty(["rpm", "-ivh", "--nosignature", "--replacefiles", local_rpm], emit)
                    if rc != 0:
                        return False, T("failed") % rc

                    if not kver and os.path.isdir("/lib/modules"):
                        mod_dirs = sorted(
                            [d for d in os.listdir("/lib/modules") if os.path.isdir(os.path.join("/lib/modules", d)) and ver in d],
                            key=lambda d: os.path.getmtime(os.path.join("/lib/modules", d)),
                            reverse=True,
                        )
                        kver = mod_dirs[0] if mod_dirs else ver
                    kver = kver or ver

                    win.run_cmd_pty(["depmod", "-a", kver], emit)

                    if not os.path.isfile(f"/boot/initrd.img-{kver}") and shutil.which("dracut"):
                        win.run_cmd_pty(["dracut", "--force", "--no-hostonly", f"/boot/initrd.img-{kver}", kver], emit)

                    if os.access("/etc/kernel/postinst.d/zz-update-boot", os.X_OK):
                        win.run_cmd_pty(["/etc/kernel/postinst.d/zz-update-boot", kver, f"/boot/vmlinuz-{kver}"], emit)
                    elif os.path.isdir("/boot/efi") and os.path.isfile(f"/boot/vmlinuz-{kver}"):
                        for dst in ("/boot/efi/bzImage", "/boot/efi/initrd.img"):
                            if os.path.isfile(dst):
                                shutil.copy2(dst, dst + ".old")
                        shutil.copy2(f"/boot/vmlinuz-{kver}", "/boot/efi/bzImage")
                        if os.path.isfile(f"/boot/initrd.img-{kver}"):
                            shutil.copy2(f"/boot/initrd.img-{kver}", "/boot/efi/initrd.img")
                        os.sync()

                    return True, f"Kernel {kver} {T('done')}"
                finally:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
            win.run_task(f"Kernel {ver}", _task, lambda *_: win._select_section("kernel"))

        win.show_confirm(T("krn_install"), f"linux-ps5-{ver}-1.x86_64.rpm\n\n{T('krn_install_sub')}", _do, destructive=False)

    grp.add(win.row(T("krn_latest"), T("krn_latest_sub"), "software-update-available-symbolic", lambda *_: _check_latest()))
    grp.add(win.row(T("krn_install"), T("krn_install_sub"), "system-software-install-symbolic", lambda *_: _install_latest()))
    grp.add(win.row(T("krn_boot"), T("krn_boot_sub"), "media-playback-start-symbolic", lambda *_: _push_boot_kernels(win)))
    grp.add(win.row(T("krn_remove"), T("krn_remove_sub"), "user-trash-symbolic", lambda *_: _push_remove_kernels(win)))
    page.add(grp)


def _push_remove_kernels(win: Ps5ManagerWindow) -> None:
    cur_k = os.uname().release
    esp_k = _esp_kernel_version()
    pkgs = _installed_kernel_packages()

    sub = Adw.PreferencesPage()
    grp = Adw.PreferencesGroup(
        title=T("krn_remove"),
        description=f"{T('krn_running')}: {cur_k} · {T('krn_esp')}: {esp_k or '—'}",
    )
    if not pkgs:
        grp.add(Adw.ActionRow(title="Aucun paquet kernel trouvé."))

    for nevra, ver in pkgs:
        protected = _is_protected_kernel(ver, cur_k, esp_k)
        status = T("krn_protected") if protected else T("krn_installed")
        if protected:
            r = win.row(nevra, status, "security-high-symbolic", None, suffix_icon=None)
        else:
            def _ask_remove(n=nevra, v=ver):
                def _task(emit):
                    ok = _remove_kernel_package(win, n, v, emit)
                    return ok, T("done") if ok else (T("failed") % 1)

                def _refresh(*_):
                    win.nav.pop()
                    _push_remove_kernels(win)

                win.show_confirm(
                    T("krn_remove"),
                    f"dnf remove -y {n}",
                    lambda: win.run_task(n, _task, _refresh),
                )
            r = win.row(nevra, status, "user-trash-symbolic", lambda _r, cb=_ask_remove: cb())
        grp.add(r)

    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=T("krn_remove")))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=T("krn_remove")))


def _push_boot_kernels(win: Ps5ManagerWindow) -> None:
    cur_k = os.uname().release
    esp_k = _esp_kernel_version()
    found = sorted(
        [os.path.basename(p)[len("vmlinuz-"):] for p in glob.glob("/boot/vmlinuz-*") if not os.path.basename(p).startswith("vmlinuz-0-rescue")],
        reverse=True,
    )
    sub = Adw.PreferencesPage()
    grp = Adw.PreferencesGroup(title=T("krn_boot"), description=f"{T('krn_running')}: {cur_k}")
    if not found:
        grp.add(Adw.ActionRow(title="Aucun kernel dans /boot"))
    for kver in found:
        flags = []
        if kver == cur_k:
            flags.append(T("krn_running"))
        if esp_k and kver == esp_k:
            flags.append(T("krn_esp"))
        if not flags:
            flags.append(T("krn_installed"))

        def _copy_kernel(ver: str):
            def _do():
                if not (os.path.isfile(f"/boot/vmlinuz-{ver}") and os.path.isfile(f"/boot/initrd.img-{ver}")):
                    win.show_info(T("sec_kernel"), f"vmlinuz-{ver} ou initrd.img-{ver} absent.")
                    return
                for dst in ("/boot/efi/bzImage", "/boot/efi/initrd.img"):
                    if os.path.isfile(dst):
                        shutil.copy2(dst, dst + ".bak")
                shutil.copy2(f"/boot/vmlinuz-{ver}", "/boot/efi/bzImage")
                shutil.copy2(f"/boot/initrd.img-{ver}", "/boot/efi/initrd.img")
                os.sync()
                win.toast(f"{ver} -> /boot/efi")
                win.nav.pop()
                _push_boot_kernels(win)
            win.show_confirm(T("krn_boot"), f"/boot/vmlinuz-{ver} -> /boot/efi/bzImage\n/boot/initrd.img-{ver} -> /boot/efi/initrd.img", _do, destructive=False)

        grp.add(win.row(kver, " · ".join(flags), "drive-harddisk-symbolic", lambda _r, v=kver: _copy_kernel(v)))
    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=T("krn_boot")))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=T("krn_boot")))


def build_page_ui_lang(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    global UI_LANG
    grp = Adw.PreferencesGroup(title=T("ui_lang_title"), description=T("ui_lang_sub"))

    def _switch(code: str) -> None:
        global UI_LANG
        UI_LANG = code
        write_ui_lang(code)
        win.rebuild_ui_for_language()
        win.toast(T("fr_label") if code == "fr" else T("en_label"))

    for code, lbl_key in (("fr", "fr_label"), ("en", "en_label")):
        r = Adw.ActionRow(title=T(lbl_key), activatable=True)
        r.add_prefix(Gtk.Image.new_from_icon_name("preferences-desktop-locale-symbolic"))
        if code == UI_LANG:
            r.add_suffix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
        r.connect("activated", lambda _r, c=code: _switch(c))
        grp.add(r)
    page.add(grp)

    g_accent = Adw.PreferencesGroup(
        title=T("accent_label"),
        description=f"{T('follow_gnome')} ({win.theme_sync.current_accent})",
    )
    info_row = Adw.ActionRow(
        title=T("follow_gnome"),
        subtitle=f"org.gnome.desktop.interface accent-color → {win.theme_sync.current_accent}",
    )
    info_row.add_prefix(Gtk.Image.new_from_icon_name("preferences-color-symbolic"))
    g_accent.add(info_row)
    page.add(g_accent)


# ------------------------------------------------------------------------------
# Section IA & Développeur (Ollama + Open WebUI + VSCodium + Modèles)
# ------------------------------------------------------------------------------
AI_MODELS_CATALOG: list[tuple[str, str, str]] = [
    ("qwen2.5-coder:3b", "Code léger · recommandé CPU / PS5 (~2 Go)", "Lightweight coding · recommended for CPU / PS5 (~2 GB)"),
    ("qwen2.5-coder:7b", "Code avancé · GPU / 16 Go RAM (~4.7 Go)", "Advanced coding · GPU / 16 GB RAM (~4.7 GB)"),
    ("gemma4:e2b", "Gemma 4 ultra-léger · rapide sur CPU", "Gemma 4 ultra-light · fast on CPU"),
    ("gemma4:e4b", "Gemma 4 compact E4B · polyvalent", "Gemma 4 compact E4B · versatile"),
    ("qwen3.5:4b", "Qwen 3.5 compact 4B · usage général", "Qwen 3.5 compact 4B · general purpose"),
    ("nemotron-3.5-bolt:e4b", "Nemotron 3.5 Bolt E4B · réponses rapides", "Nemotron 3.5 Bolt E4B · fast responses"),
    ("deepseek-r1:8b", "DeepSeek R1 8B · raisonnement avancé", "DeepSeek R1 8B · advanced reasoning"),
    ("eriktonon/deepseek-v4.1-flash-1017:9b", "DeepSeek V4.1 Flash 9B · communautaire", "DeepSeek V4.1 Flash 9B · community"),
    ("mimo-v2.6:9b", "MiMo V2.6 9B · raisonnement & code", "MiMo V2.6 9B · reasoning & coding"),
    ("gemma4:12b", "Gemma 4 12B · modèle lourd (~8+ Go RAM)", "Gemma 4 12B · heavy model (~8+ GB RAM)"),
]

VSCODIUM_GPG = "https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo/-/raw/master/pub.gpg"
VSCODIUM_REPO_FILE = "/etc/yum.repos.d/vscodium.repo"
VSCODIUM_REPO_CONTENT = (
    "[gitlab.com_paulcarroty_vscodium_repo]\n"
    "name=download.vscodium.com\n"
    "baseurl=https://download.vscodium.com/rpms/\n"
    "enabled=1\n"
    "gpgcheck=1\n"
    "repo_gpgcheck=1\n"
    f"gpgkey={VSCODIUM_GPG}\n"
    "metadata_expire=1h\n"
)
OPENWEBUI_IMAGE = "ghcr.io/open-webui/open-webui:main"
OPENWEBUI_ICON_URL = "https://cdn.jsdelivr.net/gh/selfhst/icons/png/open-webui.png"
OPENWEBUI_ICON_PATH = "/usr/share/pixmaps/open-webui.png"
OPENWEBUI_DESKTOP_PATH = "/usr/share/applications/open-webui.desktop"
OPENWEBUI_LAUNCHER_PATH = "/usr/local/bin/open-webui-launch"


def _ollama_bin() -> Optional[str]:
    found = shutil.which("ollama")
    if found and os.access(found, os.X_OK):
        return found
    candidates = [
        "/usr/local/bin/ollama",
        "/usr/bin/ollama",
        "/bin/ollama",
        "/opt/ollama/bin/ollama",
    ]
    if REAL_HOME and REAL_HOME != "/root":
        candidates.extend([
            os.path.join(REAL_HOME, ".local", "bin", "ollama"),
            os.path.join(REAL_HOME, "bin", "ollama"),
        ])
    for cand in candidates:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def _ollama_installed() -> bool:
    return _ollama_bin() is not None


def _ollama_service_exists() -> bool:
    for unit_path in (
        "/etc/systemd/system/ollama.service",
        "/usr/lib/systemd/system/ollama.service",
        "/lib/systemd/system/ollama.service",
    ):
        if os.path.isfile(unit_path):
            return True
    res = subprocess.run(
        ["systemctl", "list-unit-files", "ollama.service"],
        capture_output=True, text=True,
    )
    return "ollama.service" in (res.stdout or "")


def _ollama_version() -> str:
    bin_path = _ollama_bin()
    if not bin_path:
        return ""
    res = subprocess.run([bin_path, "--version"], capture_output=True, text=True)
    out = res.stdout.strip() or res.stderr.strip()
    if "version is" in out:
        return out.splitlines()[-1].strip()
    return out.splitlines()[0].strip() if out else ""


def _ollama_api_reachable(timeout: float = 0.6) -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/version", timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _ollama_service_active() -> bool:
    if subprocess.run(["systemctl", "is-active", "--quiet", "ollama"], capture_output=True).returncode == 0:
        return True
    return _ollama_api_reachable()


def _ollama_service_enabled() -> bool:
    return subprocess.run(["systemctl", "is-enabled", "--quiet", "ollama"], capture_output=True).returncode == 0


def _format_bytes_human(num_bytes: int) -> str:
    if num_bytes <= 0:
        return ""
    gb = num_bytes / (1000 ** 3)
    if gb >= 1.0:
        return f"{gb:.1f} GB"
    mb = num_bytes / (1000 ** 2)
    return f"{mb:.0f} MB"


def _ollama_model_dirs() -> list[str]:
    dirs: list[str] = []
    env_dir = os.environ.get("OLLAMA_MODELS", "").strip()
    if env_dir:
        dirs.append(env_dir)
    for unit_glob in (
        "/etc/systemd/system/ollama.service",
        "/etc/systemd/system/ollama.service.d/*.conf",
    ):
        for p in glob.glob(unit_glob):
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        m = re.search(r"OLLAMA_MODELS=[\"']?([^\"'\s]+)", line)
                        if m:
                            dirs.append(m.group(1))
            except OSError:
                pass
    dirs.extend([
        "/usr/share/ollama/.ollama/models",
        "/var/lib/ollama/.ollama/models",
        "/var/lib/ollama/models",
        os.path.join(REAL_HOME, ".ollama", "models"),
        "/root/.ollama/models",
    ])
    unique: list[str] = []
    for d in dirs:
        if d and d not in unique and os.path.isdir(d):
            unique.append(d)
    return unique


def _scan_ollama_manifests_on_disk() -> dict[str, str]:
    """Scanne les manifests locaux d'Ollama même lorsque ollama.service est arrêté."""
    models: dict[str, str] = {}
    for base_dir in _ollama_model_dirs():
        manifests_root = os.path.join(base_dir, "manifests")
        if not os.path.isdir(manifests_root):
            continue
        for root_dir, _dirs, files in os.walk(manifests_root):
            for fname in files:
                fpath = os.path.join(root_dir, fname)
                rel = os.path.relpath(fpath, manifests_root)
                parts = rel.split(os.sep)
                if len(parts) < 4:
                    continue
                registry, namespace, model = parts[0], parts[1], "/".join(parts[2:-1])
                tag = parts[-1]
                if registry == "registry.ollama.ai" and namespace == "library":
                    model_name = f"{model}:{tag}"
                elif registry == "registry.ollama.ai":
                    model_name = f"{namespace}/{model}:{tag}"
                else:
                    model_name = f"{registry}/{namespace}/{model}:{tag}"
                size_bytes = 0
                try:
                    with open(fpath, encoding="utf-8") as fh:
                        data = json.load(fh)
                    cfg = data.get("config") or {}
                    if isinstance(cfg, dict):
                        size_bytes += int(cfg.get("size") or 0)
                    for layer in data.get("layers") or []:
                        if isinstance(layer, dict):
                            size_bytes += int(layer.get("size") or 0)
                except (OSError, ValueError, TypeError):
                    pass
                models.setdefault(model_name, _format_bytes_human(size_bytes))
    return models


def _ollama_installed_models() -> dict[str, str]:
    """Retourne {nom_modele: taille} via `ollama list` et repli disque si le daemon est arrêté."""
    models: dict[str, str] = {}
    bin_path = _ollama_bin()
    if bin_path:
        env = dict(os.environ)
        env.setdefault("OLLAMA_HOST", "127.0.0.1:11434")
        try:
            res = subprocess.run([bin_path, "list"], capture_output=True, text=True, env=env, timeout=3)
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 4:
                        models[parts[0]] = f"{parts[2]} {parts[3]}"
                    elif parts:
                        models[parts[0]] = ""
        except (OSError, subprocess.SubprocessError):
            pass
    for name, sz in _scan_ollama_manifests_on_disk().items():
        if name not in models:
            models[name] = sz
    return models


def _ollama_running_models() -> set[str]:
    bin_path = _ollama_bin()
    if not bin_path:
        return set()
    try:
        res = subprocess.run([bin_path, "ps"], capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return set()
    if res.returncode != 0:
        return set()
    running: set[str] = set()
    for line in res.stdout.splitlines()[1:]:
        parts = line.split()
        if parts:
            running.add(parts[0])
    return running


def _podman_bin() -> Optional[str]:
    found = shutil.which("podman")
    if found and os.access(found, os.X_OK):
        return found
    for cand in ("/usr/bin/podman", "/usr/local/bin/podman"):
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def _podman_run(args: list[str], owner: str = "user", timeout: int = 12) -> subprocess.CompletedProcess[str]:
    podman = _podman_bin() or "podman"
    kw = user_subprocess_kwargs() if owner == "user" else {}
    return subprocess.run([podman, *args], capture_output=True, text=True, timeout=timeout, **kw)


def _parse_podman_ps_for_openwebui(stdout: str) -> Optional[str]:
    for line in stdout.splitlines():
        parts = line.strip().split("\t", 1)
        if len(parts) < 2:
            continue
        name = parts[0].strip().lstrip("/")
        state = parts[1].strip().lower()
        if name == "open-webui":
            if state.startswith("up"):
                return "running"
            return state
    return None


def _podman_webui_context() -> tuple[str, str]:
    """Retourne (état, propriétaire 'user'|'root')."""
    podman = _podman_bin()
    if not podman:
        return "no_podman", "user"
    contexts = ["user", "root"] if REAL_USER != "root" else ["root"]
    for ctx in contexts:
        try:
            res_ps = _podman_run(["ps", "-a", "--format", "{{.Names}}\t{{.State}}"], owner=ctx, timeout=12)
            if res_ps.returncode == 0:
                st = _parse_podman_ps_for_openwebui(res_ps.stdout)
                if st:
                    return st, ctx
        except (OSError, subprocess.SubprocessError):
            pass
        try:
            res_ins = _podman_run(["inspect", "-f", "{{.State.Status}}", "open-webui"], owner=ctx, timeout=12)
            if res_ins.returncode == 0 and res_ins.stdout.strip():
                return res_ins.stdout.strip().lower(), ctx
        except (OSError, subprocess.SubprocessError):
            pass
    return "missing", "user"


def _podman_webui_state() -> str:
    """Retourne 'running', 'exited'/'stopped', 'missing', ou 'no_podman'."""
    return _podman_webui_context()[0]


def _vscodium_installed() -> bool:
    return subprocess.run(["rpm", "-q", "codium"], capture_output=True).returncode == 0


def _ensure_vscodium_repo(win: Ps5ManagerWindow, emit: Callable[[str], None]) -> bool:
    rc = win.run_cmd_pty(["rpmkeys", "--import", VSCODIUM_GPG], emit)
    if rc != 0:
        return False
    try:
        with open(VSCODIUM_REPO_FILE, "w", encoding="utf-8") as fh:
            fh.write(VSCODIUM_REPO_CONTENT)
        os.chmod(VSCODIUM_REPO_FILE, 0o644)
        os.chown(VSCODIUM_REPO_FILE, 0, 0)
        return True
    except OSError as exc:
        emit(f"Erreur écriture {VSCODIUM_REPO_FILE} : {exc}")
        return False


def _ensure_ollama_ready(win: Ps5ManagerWindow, emit: Callable[[str], None]) -> bool:
    if not _ollama_installed():
        emit("Ollama non détecté — installation avec pciutils…")
        if win.run_cmd_pty(["dnf", "install", "-y", "pciutils"], emit) != 0:
            return False
        if win.run_cmd_pty("curl -fsSL https://ollama.com/install.sh | sh", emit) != 0:
            return False
    if not _ollama_service_active() and _ollama_service_exists():
        win.run_cmd_pty(["systemctl", "start", "ollama"], emit)
    return _ollama_installed()


def _create_openwebui_container(win: Ps5ManagerWindow, emit: Callable[[str], None], owner: str = "user") -> int:
    podman = _podman_bin() or "podman"
    return win.run_cmd_pty(
        [
            podman, "run", "-d", "--network=host",
            "-v", "open-webui:/app/backend/data",
            "-e", "OLLAMA_BASE_URL=http://127.0.0.1:11434",
            "--name", "open-webui",
            "--restart", "always",
            OPENWEBUI_IMAGE,
        ],
        emit,
        as_user=(owner == "user"),
    )


def _run_quick_service_action(
    win: Ps5ManagerWindow,
    title: str,
    fn: Callable[[], tuple[bool, str]],
    on_done: Optional[Callable[[], None]] = None,
) -> None:
    if win.busy:
        win.toast(T("busy"))
        return
    win.busy = True
    win.busy_spinner.start()
    win.logger.write_line(f"──── {title}")

    def _worker() -> None:
        ok = False
        msg = ""
        try:
            ok, msg = fn()
        except Exception as exc:
            ok = False
            msg = str(exc)
        win.logger.write_line(f"──── fin : {title} ({'OK' if ok else 'ERR'}) {msg}")

        def _finish() -> bool:
            win.busy = False
            win.busy_spinner.stop()
            if ok:
                win.toast(f"{title} — {T('done')}")
            else:
                win.show_info(title, msg or T("failed") % 1)
            if on_done:
                on_done()
            return False

        GLib.idle_add(_finish)

    threading.Thread(target=_worker, daemon=True).start()


def build_page_aidev(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    ollama_ok = _ollama_installed()
    ollama_svc = _ollama_service_exists()
    ollama_act = _ollama_service_active() if (ollama_ok or ollama_svc) else False
    ollama_boot = _ollama_service_enabled() if ollama_svc else False
    webui_st, webui_owner = _podman_webui_context()
    codium_ok = _vscodium_installed()
    installed_models = _ollama_installed_models()

    # 1) Outils & Applications IA / Dev
    g_tools = Adw.PreferencesGroup(title=T("aidev_stack"), description=T("aidev_stack_sub"))

    if ollama_ok:
        ver_str = _ollama_version() or "Ollama"
        ollama_sub = f"{ver_str} · {'actif' if ollama_act else 'arrêté'}"
    elif ollama_svc:
        ollama_sub = f"Service détecté · {'actif' if ollama_act else 'arrêté'}"
    else:
        ollama_sub = "pciutils + script officiel ollama.com"
    g_tools.add(
        win.row(
            "Ollama (moteur IA local)",
            ollama_sub,
            "utilities-terminal-symbolic",
            lambda *_: _push_ollama_actions(win),
        )
    )

    owner_tag = "Podman root" if webui_owner == "root" else "Podman"
    webui_labels = {
        "running": f"Actif ({owner_tag}) · http://127.0.0.1:8080",
        "exited": f"Installé (arrêté) · {owner_tag}",
        "stopped": f"Installé (arrêté) · {owner_tag}",
        "created": f"Installé (arrêté) · {owner_tag}",
        "paused": f"En pause · {owner_tag}",
        "missing": "Non installé · Podman ghcr.io/open-webui",
        "no_podman": "Podman absent (sera installé automatiquement)",
    }
    g_tools.add(
        win.row(
            "Open WebUI (interface web IA)",
            webui_labels.get(webui_st, webui_st),
            "web-browser-symbolic",
            lambda *_: _push_webui_actions(win),
        )
    )

    g_tools.add(
        win.row(
            "VSCodium (éditeur de code libre)",
            T("installed_rpm") if codium_ok else f"{T('not_installed')} · dépôt officiel RPM",
            "applications-development-symbolic",
            lambda *_: _push_vscodium_actions(win),
        )
    )
    page.add(g_tools)

    # 2) Contrôle des services IA
    g_srv = Adw.PreferencesGroup(title=T("aidev_services"), description=T("aidev_services_sub"))

    sw_ollama = Adw.SwitchRow(
        title=GLib.markup_escape_text("Service Ollama (ollama.service)"),
        subtitle=GLib.markup_escape_text(
            "Démarrer / arrêter le serveur IA (port 11434)"
            if UI_LANG == "fr"
            else "Start / stop local AI server (port 11434)"
        ),
    )
    sw_ollama.add_prefix(Gtk.Image.new_from_icon_name("system-run-symbolic"))
    sw_ollama.set_active(ollama_act)
    sw_ollama.set_sensitive(ollama_ok or ollama_svc)

    def _toggle_ollama(r, _p):
        act = "start" if r.get_active() else "stop"

        def _do():
            if not _ollama_service_exists():
                return False, "L'unité systemd ollama.service est introuvable. Réinstallez ou mettez à jour Ollama."
            res = subprocess.run(["systemctl", act, "ollama"], capture_output=True, text=True)
            if res.returncode != 0:
                err = (res.stderr or res.stdout or f"code {res.returncode}").strip()
                return False, f"systemctl {act} ollama :\n{err}"
            if act == "start":
                import time
                for _ in range(10):
                    if _ollama_api_reachable(timeout=0.5):
                        break
                    time.sleep(0.4)
            return True, T("done")

        _run_quick_service_action(
            win,
            f"Ollama ({act})",
            _do,
            lambda: win._select_section("aidev"),
        )

    sw_ollama.connect("notify::active", _toggle_ollama)
    g_srv.add(sw_ollama)

    sw_boot = Adw.SwitchRow(
        title=GLib.markup_escape_text(
            "Démarrage automatique Ollama au boot" if UI_LANG == "fr" else "Start Ollama automatically at boot"
        ),
        subtitle=GLib.markup_escape_text("systemctl enable / disable ollama"),
    )
    sw_boot.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-time-symbolic"))
    sw_boot.set_active(ollama_boot)
    sw_boot.set_sensitive(ollama_svc)

    def _toggle_ollama_boot(r, _p):
        act = "enable" if r.get_active() else "disable"

        def _do():
            res = subprocess.run(["systemctl", act, "ollama"], capture_output=True, text=True)
            if res.returncode != 0:
                return False, (res.stderr or res.stdout or f"code {res.returncode}").strip()
            return True, T("done")

        _run_quick_service_action(
            win,
            f"Ollama boot ({act})",
            _do,
            lambda: win._select_section("aidev"),
        )

    sw_boot.connect("notify::active", _toggle_ollama_boot)
    g_srv.add(sw_boot)

    sw_webui = Adw.SwitchRow(
        title=GLib.markup_escape_text("Conteneur Open WebUI (Podman)"),
        subtitle=GLib.markup_escape_text("podman start / stop open-webui"),
    )
    sw_webui.add_prefix(Gtk.Image.new_from_icon_name("network-server-symbolic"))
    sw_webui.set_active(webui_st == "running")
    sw_webui.set_sensitive(webui_st not in ("missing", "no_podman"))

    def _toggle_webui(r, _p):
        act = "start" if r.get_active() else "stop"

        def _do():
            res = _podman_run([act, "open-webui"], owner=webui_owner, timeout=30)
            if res.returncode != 0:
                err = (res.stderr or res.stdout or f"code {res.returncode}").strip()
                return False, f"podman {act} open-webui ({webui_owner}) :\n{err}"
            return True, T("done")

        _run_quick_service_action(
            win,
            f"Open WebUI ({act})",
            _do,
            lambda: win._select_section("aidev"),
        )

    sw_webui.connect("notify::active", _toggle_webui)
    g_srv.add(sw_webui)

    def _start_all():
        def _task(emit):
            did_any = False
            rc1 = 0
            rc2 = 0
            if _ollama_service_exists() or _ollama_installed():
                did_any = True
                rc1 = win.run_cmd_pty(["systemctl", "start", "ollama"], emit)
            else:
                emit("Ollama non détecté sur ce système.")

            st_now, owner_now = _podman_webui_context()
            podman = _podman_bin()
            if st_now not in ("missing", "no_podman") and podman:
                did_any = True
                rc2 = win.run_cmd_pty([podman, "start", "open-webui"], emit, as_user=(owner_now == "user"))
            elif podman:
                # Affiche le diagnostic podman ps -a dans le journal pour transparence
                try:
                    diag = _podman_run(["ps", "-a"], owner="user", timeout=10)
                    emit(f"podman ps -a ({REAL_USER}) rc={diag.returncode}: {(diag.stdout or diag.stderr).strip()}")
                except Exception as exc:
                    emit(f"Erreur podman ps -a : {exc}")
                emit("Conteneur Podman open-webui non détecté.")
            else:
                emit("Podman non installé.")

            if not did_any:
                return False, "Aucun service Ollama ou Open WebUI détecté."
            ok = rc1 == 0 and rc2 == 0
            return ok, T("done") if ok else T("failed") % (rc1 or rc2)
        win.run_task("Démarrer Ollama + Open WebUI", _task, lambda *_: win._select_section("aidev"))

    def _stop_all():
        def _task(emit):
            did_any = False
            st_now, owner_now = _podman_webui_context()
            if st_now == "running":
                did_any = True
                podman = _podman_bin() or "podman"
                win.run_cmd_pty([podman, "stop", "open-webui"], emit, as_user=(owner_now == "user"))
            if _ollama_service_exists() or _ollama_service_active():
                did_any = True
                win.run_cmd_pty(["systemctl", "stop", "ollama"], emit)
            if not did_any:
                return False, "Aucun service actif détecté."
            return True, T("done")
        win.run_task("Arrêter Ollama + Open WebUI", _task, lambda *_: win._select_section("aidev"))

    g_srv.add(
        win.row(
            "Tout démarrer (Ollama + Open WebUI)" if UI_LANG == "fr" else "Start all (Ollama + Open WebUI)",
            "systemctl start ollama && podman start open-webui",
            "media-playback-start-symbolic",
            lambda *_: _start_all(),
        )
    )
    g_srv.add(
        win.row(
            "Tout arrêter (libérer la RAM)" if UI_LANG == "fr" else "Stop all (free RAM)",
            "podman stop open-webui && systemctl stop ollama",
            "media-playback-stop-symbolic",
            lambda *_: _stop_all(),
        )
    )

    def _open_webui_browser():
        if os.access(OPENWEBUI_LAUNCHER_PATH, os.X_OK) and webui_owner == "user":
            subprocess.Popen([OPENWEBUI_LAUNCHER_PATH], **user_subprocess_kwargs())
            return
        st_now, _ = _podman_webui_context()
        if st_now == "running":
            subprocess.Popen(["xdg-open", "http://127.0.0.1:8080"], **user_subprocess_kwargs())
        else:
            win.show_info("Open WebUI", "Démarrez d'abord le conteneur Open WebUI.")

    def _show_podman_ps():
        if not _podman_bin():
            win.show_info("Podman", "Podman n'est pas installé.")
            return
        chunks: list[str] = []
        try:
            r_usr = _podman_run(["ps", "-a"], owner="user", timeout=12)
            txt_usr = "\n".join(p for p in (r_usr.stdout.strip(), r_usr.stderr.strip()) if p) or "(vide)"
            chunks.append(f"=== podman ps -a ({REAL_USER}) [rc={r_usr.returncode}] ===\n{txt_usr}")
        except Exception as exc:
            chunks.append(f"=== podman ps -a ({REAL_USER}) ===\nErreur : {exc}")
        if REAL_USER != "root":
            try:
                r_rt = _podman_run(["ps", "-a"], owner="root", timeout=12)
                txt_rt = "\n".join(p for p in (r_rt.stdout.strip(), r_rt.stderr.strip()) if p)
                if txt_rt:
                    chunks.append(f"\n=== podman ps -a (root) ===\n{txt_rt}")
            except Exception:
                pass
        win.show_text_modal("podman ps -a", "\n".join(chunks))

    def _show_webui_logs():
        if not _podman_bin():
            win.show_info("Open WebUI", "Podman n'est pas installé.")
            return
        st_now, owner_now = _podman_webui_context()
        if st_now in ("missing", "no_podman"):
            try:
                r_diag = _podman_run(["ps", "-a"], owner="user", timeout=10)
                diag = (r_diag.stderr or r_diag.stdout or "").strip()
            except Exception as exc:
                diag = str(exc)
            detail = f"\n\nDiagnostic :\n{diag}" if diag else ""
            win.show_info("Open WebUI", f"Conteneur open-webui introuvable.{detail}")
            return
        podman = _podman_bin() or "podman"
        kw = user_subprocess_kwargs() if owner_now == "user" else {}
        try:
            res = subprocess.run(
                [podman, "logs", "--tail", "30", "open-webui"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=12, **kw,
            )
            out = strip_ansi(res.stdout or "").strip() or "(aucun log)"
            win.show_text_modal("podman logs --tail 30 open-webui", out)
        except Exception as exc:
            win.show_info("podman logs --tail 30 open-webui", f"Erreur : {exc}")

    g_srv.add(
        win.row(
            "Ouvrir Open WebUI dans le navigateur" if UI_LANG == "fr" else "Open Open WebUI in browser",
            "http://127.0.0.1:8080",
            "web-browser-symbolic",
            lambda *_: _open_webui_browser(),
        )
    )
    g_srv.add(
        win.row(
            "État des conteneurs Podman (podman ps -a)" if UI_LANG == "fr" else "Podman containers status (podman ps -a)",
            "Vérifie l'état exact de open-webui",
            "view-list-symbolic",
            lambda *_: _show_podman_ps(),
        )
    )
    g_srv.add(
        win.row(
            "Logs Open WebUI (podman logs --tail 30)" if UI_LANG == "fr" else "Open WebUI logs (podman logs --tail 30)",
            "Affiche les 30 dernières lignes du conteneur open-webui",
            "utilities-terminal-symbolic",
            lambda *_: _show_webui_logs(),
        )
    )
    page.add(g_srv)

    # 3) Modèles IA locaux
    g_mod = Adw.PreferencesGroup(title=T("aidev_models"), description=T("aidev_models_sub"))
    if installed_models:
        preview = ", ".join(list(installed_models.keys())[:4])
        if len(installed_models) > 4:
            preview += f" (+{len(installed_models) - 4})"
        models_sub = f"{len(installed_models)} installé(s) : {preview}"
    else:
        models_sub = "0 installé · qwen2.5-coder, deepseek, gemma4, mimo, nemotron…"
    g_mod.add(
        win.row(
            "Gérer les modèles IA (catalogue & installés)" if UI_LANG == "fr" else "Manage AI models (catalog & installed)",
            models_sub,
            "folder-download-symbolic",
            lambda *_: _push_ai_models(win),
        )
    )

    def _show_ollama_list():
        bin_path = _ollama_bin()
        if not bin_path and not installed_models:
            win.show_info("Ollama", "Ollama n'est pas installé.")
            return
        out = ""
        if bin_path:
            res = subprocess.run([bin_path, "list"], capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                out = res.stdout.strip()
        if not out:
            disk_models = _ollama_installed_models()
            if disk_models:
                lines = ["(Service Ollama arrêté — modèles détectés sur le disque)", "", f"{'NOM':42} {'TAILLE':12}"]
                for m_name, m_size in sorted(disk_models.items()):
                    lines.append(f"{m_name:42} {m_size or '-'}")
                out = "\n".join(lines)
            else:
                out = "(aucun modèle)"
        win.show_text_modal("ollama list", out)

    def _show_ollama_ps():
        bin_path = _ollama_bin()
        if not bin_path:
            win.show_info("Ollama", "Ollama n'est pas installé.")
            return
        res = subprocess.run([bin_path, "ps"], capture_output=True, text=True)
        out = (res.stdout or res.stderr or "").strip() or "(aucun modèle actif)"
        win.show_text_modal("ollama ps", out)

    g_mod.add(
        win.row(
            "Voir les modèles installés (ollama list)" if UI_LANG == "fr" else "List installed models (ollama list)",
            None,
            "view-list-symbolic",
            lambda *_: _show_ollama_list(),
        )
    )
    g_mod.add(
        win.row(
            "Modèles actifs en RAM (ollama ps)" if UI_LANG == "fr" else "Active models in RAM (ollama ps)",
            "Affiche les modèles actuellement chargés en mémoire",
            "utilities-system-monitor-symbolic",
            lambda *_: _show_ollama_ps(),
        )
    )
    page.add(g_mod)

    # 4) Propositions utiles pour PS5 Linux
    g_ext = Adw.PreferencesGroup(title=T("aidev_extras"), description=T("aidev_extras_sub"))

    def _hw_ai_diag():
        cmd = (
            "echo '=== Mémoire RAM / Swap (PS5 unifiée 16 Go) ==='; free -h; "
            "echo ''; echo '=== Processeur ==='; lscpu | grep -E 'Model name|CPU\\(s\\)|Thread'; "
            "echo ''; echo '=== GPU / PCI (pciutils) ==='; lspci | grep -iE 'vga|display|amd' || true; "
            "echo ''; echo '=== Espace disque modèles ==='; df -h / /var /usr/share/ollama 2>/dev/null || df -h /"
        )
        out = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True).stdout
        win.show_text_modal("Diagnostic matériel IA (PS5)", out)

    g_ext.add(
        win.row(
            "Diagnostic RAM / GPU / Disque pour l'IA" if UI_LANG == "fr" else "AI RAM / GPU / Disk diagnostic",
            "Vérifie la mémoire libre avant d'exécuter un modèle 7B / 9B / 12B",
            "applications-system-symbolic",
            lambda *_: _hw_ai_diag(),
        )
    )
    g_ext.add(
        win.row(
            "Nettoyer les anciennes images Podman" if UI_LANG == "fr" else "Prune unused Podman images",
            "podman image prune -f (libère l'espace après mise à jour Open WebUI)",
            "edit-clear-all-symbolic",
            lambda *_: win.run_task(
                "Podman prune",
                lambda e: (win.run_cmd_pty([_podman_bin() or "podman", "image", "prune", "-f"], e, as_user=(webui_owner == "user")) == 0, T("done")),
            ),
        )
    )
    if REAL_USER != "root":
        g_ext.add(
            win.row(
                f"Activer le maintien de session Podman ({REAL_USER})" if UI_LANG == "fr" else f"Enable Podman user linger ({REAL_USER})",
                f"loginctl enable-linger {REAL_USER} · démarre Open WebUI sans terminal",
                "user-available-symbolic",
                lambda *_: win.run_task(
                    "loginctl enable-linger",
                    lambda e: (win.run_cmd_pty(["loginctl", "enable-linger", REAL_USER], e) == 0, T("done")),
                ),
            )
        )
    page.add(g_ext)


def _install_openwebui_desktop_entry(win: Ps5ManagerWindow, emit: Callable[[str], None]) -> bool:
    """Télécharge l'icône Open WebUI localement dans Fedora et crée le lanceur GNOME."""
    rc_icon = win.run_cmd_pty(
        ["curl", "-fL", "--retry", "3", "-o", OPENWEBUI_ICON_PATH, OPENWEBUI_ICON_URL],
        emit,
    )
    if rc_icon == 0 and os.path.isfile(OPENWEBUI_ICON_PATH):
        try:
            os.chmod(OPENWEBUI_ICON_PATH, 0o644)
            os.chown(OPENWEBUI_ICON_PATH, 0, 0)
        except OSError:
            pass
    else:
        emit("Avertissement : impossible de télécharger open-webui.png (icône générique utilisée).")

    launcher_script = """#!/bin/sh
if command -v podman >/dev/null 2>&1 && podman container exists open-webui 2>/dev/null; then
    state=$(podman inspect -f '{{.State.Running}}' open-webui 2>/dev/null || echo false)
    if [ "$state" != "true" ]; then
        podman start open-webui >/dev/null 2>&1 || true
        i=0
        while [ "$i" -lt 15 ]; do
            curl -fsS http://127.0.0.1:8080 >/dev/null 2>&1 && break
            sleep 1
            i=$((i + 1))
        done
    fi
fi
exec xdg-open "http://127.0.0.1:8080"
"""
    desktop_entry = f"""[Desktop Entry]
Name=Open WebUI
Comment=Interface web locale pour Ollama (IA)
Exec={OPENWEBUI_LAUNCHER_PATH}
Icon={OPENWEBUI_ICON_PATH if os.path.isfile(OPENWEBUI_ICON_PATH) else 'web-browser'}
Terminal=false
Type=Application
Categories=Development;Utility;Network;
Keywords=AI;IA;Ollama;OpenWebUI;LLM;Chat;
StartupNotify=true
"""
    try:
        with open(OPENWEBUI_LAUNCHER_PATH, "w", encoding="utf-8") as fh:
            fh.write(launcher_script)
        os.chmod(OPENWEBUI_LAUNCHER_PATH, 0o755)
        os.chown(OPENWEBUI_LAUNCHER_PATH, 0, 0)

        with open(OPENWEBUI_DESKTOP_PATH, "w", encoding="utf-8") as fh:
            fh.write(desktop_entry)
        os.chmod(OPENWEBUI_DESKTOP_PATH, 0o644)
        os.chown(OPENWEBUI_DESKTOP_PATH, 0, 0)
    except OSError as exc:
        emit(f"Erreur création lanceur Open WebUI : {exc}")
        return False

    if shutil.which("restorecon"):
        win.run_cmd_pty(
            ["restorecon", "-RF", OPENWEBUI_ICON_PATH, OPENWEBUI_LAUNCHER_PATH, OPENWEBUI_DESKTOP_PATH],
            emit,
        )
    win.run_cmd_pty(["update-desktop-database", "/usr/share/applications/"], emit)
    emit(f"Raccourci installé : {OPENWEBUI_DESKTOP_PATH} (icône : {OPENWEBUI_ICON_PATH})")
    return True


def _remove_openwebui_desktop_entry(win: Ps5ManagerWindow, emit: Callable[[str], None]) -> None:
    for path in (OPENWEBUI_DESKTOP_PATH, OPENWEBUI_ICON_PATH, OPENWEBUI_LAUNCHER_PATH):
        if os.path.exists(path):
            try:
                os.remove(path)
                emit(f"Supprimé : {path}")
            except OSError:
                pass
    win.run_cmd_pty(["update-desktop-database", "/usr/share/applications/"], emit)


def _push_ollama_actions(win: Ps5ManagerWindow) -> None:
    installed = _ollama_installed()
    sub = Adw.PreferencesPage()
    grp = Adw.PreferencesGroup(
        title="Ollama",
        description=_ollama_version() if installed else "Non installé · pciutils + install.sh",
    )

    def _install_or_update(label: str):
        def _task(emit):
            if win.run_cmd_pty(["dnf", "install", "-y", "pciutils"], emit) != 0:
                return False, T("failed") % 1
            rc = win.run_cmd_pty("curl -fsSL https://ollama.com/install.sh | sh", emit)
            return rc == 0, T("done") if rc == 0 else T("failed") % rc
        win.run_task(label, _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    def _uninstall(purge_models: bool):
        def _task(emit):
            win.run_cmd_pty(["systemctl", "stop", "ollama"], emit)
            win.run_cmd_pty(["systemctl", "disable", "ollama"], emit)
            cmds = [
                "rm -f /etc/systemd/system/ollama.service",
                "systemctl daemon-reload",
                "rm -f /usr/local/bin/ollama /usr/bin/ollama",
                "rm -rf /usr/lib/ollama",
            ]
            if purge_models:
                cmds.append("rm -rf /usr/share/ollama")
            win.run_cmd_pty(["bash", "-c", " && ".join(cmds)], emit)
            return True, T("done")
        win.run_task("Désinstaller Ollama", _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    grp.add(
        win.row(
            T("install"),
            "dnf install -y pciutils && curl -fsSL https://ollama.com/install.sh | sh",
            "system-software-install-symbolic",
            lambda *_: _install_or_update("Installer Ollama"),
        )
    )
    grp.add(
        win.row(
            T("update"),
            "Met à jour Ollama vers la dernière version officielle",
            "software-update-available-symbolic",
            lambda *_: _install_or_update("Mettre à jour Ollama"),
        )
    )
    grp.add(
        win.row(
            T("remove"),
            "Supprime le service et les binaires, conserve /usr/share/ollama",
            "user-trash-symbolic",
            lambda *_: (
                win.show_confirm("Désinstaller Ollama", "Supprimer Ollama tout en conservant les modèles dans /usr/share/ollama ?", lambda: _uninstall(False))
                if _ollama_installed()
                else win.show_info("Ollama", T("not_installed"))
            ),
        )
    )
    if installed:
        grp.add(
            win.row(
                "Désinstaller complètement (+ supprimer tous les modèles)",
                "Supprime aussi /usr/share/ollama",
                "edit-delete-symbolic",
                lambda *_: win.show_confirm("Purger Ollama", "Supprimer définitivement Ollama ET tous les modèles téléchargés (/usr/share/ollama) ?", lambda: _uninstall(True)),
            )
        )
    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title="Ollama"))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title="Ollama"))


def _push_webui_actions(win: Ps5ManagerWindow) -> None:
    st, owner = _podman_webui_context()
    has_desktop = os.path.isfile(OPENWEBUI_DESKTOP_PATH) and os.path.isfile(OPENWEBUI_ICON_PATH)
    sub = Adw.PreferencesPage()
    grp = Adw.PreferencesGroup(
        title="Open WebUI (Podman)",
        description=f"État : {st} ({owner}) · Icône GNOME : {'installée' if has_desktop else 'absente'}",
    )

    def _install():
        def _task(emit):
            if not _podman_bin():
                if win.run_cmd_pty(["dnf", "install", "-y", "podman"], emit) != 0:
                    return False, T("failed") % 1
            cur_st, cur_owner = _podman_webui_context()
            if cur_st in ("missing", "no_podman"):
                rc = _create_openwebui_container(win, emit, owner="user")
                if rc != 0:
                    return False, T("failed") % rc
            _install_openwebui_desktop_entry(win, emit)
            return True, T("done")
        win.run_task("Installer Open WebUI", _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    def _update():
        def _task(emit):
            if not _podman_bin():
                if win.run_cmd_pty(["dnf", "install", "-y", "podman"], emit) != 0:
                    return False, T("failed") % 1
            podman = _podman_bin() or "podman"
            _, cur_owner = _podman_webui_context()
            as_user = cur_owner == "user"
            if win.run_cmd_pty([podman, "pull", OPENWEBUI_IMAGE], emit, as_user=as_user) != 0:
                return False, T("failed") % 1
            win.run_cmd_pty([podman, "stop", "open-webui"], emit, as_user=as_user)
            win.run_cmd_pty([podman, "rm", "open-webui"], emit, as_user=as_user)
            rc = _create_openwebui_container(win, emit, owner=cur_owner)
            if rc != 0:
                return False, T("failed") % rc
            _install_openwebui_desktop_entry(win, emit)
            return True, T("done")
        win.run_task("Mettre à jour Open WebUI", _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    def _install_icon_only():
        def _task(emit):
            ok = _install_openwebui_desktop_entry(win, emit)
            return ok, T("done") if ok else T("failed") % 1
        win.run_task("Icône Open WebUI", _task, lambda *_: (win.nav.pop(), _push_webui_actions(win)))

    def _uninstall(purge_data: bool):
        def _task(emit):
            podman = _podman_bin() or "podman"
            _, cur_owner = _podman_webui_context()
            as_user = cur_owner == "user"
            win.run_cmd_pty([podman, "stop", "open-webui"], emit, as_user=as_user)
            win.run_cmd_pty([podman, "rm", "open-webui"], emit, as_user=as_user)
            if purge_data:
                win.run_cmd_pty([podman, "volume", "rm", "open-webui"], emit, as_user=as_user)
                win.run_cmd_pty([podman, "rmi", OPENWEBUI_IMAGE], emit, as_user=as_user)
            _remove_openwebui_desktop_entry(win, emit)
            return True, T("done")
        win.run_task("Désinstaller Open WebUI", _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    grp.add(
        win.row(
            T("install"),
            "Podman + conteneur open-webui + icône locale dans le menu GNOME",
            "system-software-install-symbolic",
            lambda *_: _install(),
        )
    )
    grp.add(
        win.row(
            T("update"),
            "podman pull + recréation (données conservées) + icône GNOME",
            "software-update-available-symbolic",
            lambda *_: _update(),
        )
    )
    grp.add(
        win.row(
            "Ouvrir dans le navigateur (http://127.0.0.1:8080)",
            "Démarre open-webui si arrêté puis ouvre la page web",
            "web-browser-symbolic",
            lambda *_: subprocess.Popen([OPENWEBUI_LAUNCHER_PATH], **user_subprocess_kwargs())
            if os.access(OPENWEBUI_LAUNCHER_PATH, os.X_OK)
            else subprocess.Popen(["xdg-open", "http://127.0.0.1:8080"], **user_subprocess_kwargs()),
        )
    )
    grp.add(
        win.row(
            "Installer / mettre à jour l'icône GNOME (menu Applications)",
            "Télécharge open-webui.png dans /usr/share/pixmaps/ et crée open-webui.desktop",
            "image-x-generic-symbolic",
            lambda *_: _install_icon_only(),
        )
    )
    grp.add(
        win.row(
            T("remove"),
            "Supprime conteneur + lanceur/icône GNOME (conserve les conversations)",
            "user-trash-symbolic",
            lambda *_: win.show_confirm(
                "Désinstaller Open WebUI",
                "Supprimer le conteneur open-webui et son icône du menu GNOME en conservant vos données ?",
                lambda: _uninstall(False),
            ),
        )
    )
    if st not in ("missing", "no_podman"):
        grp.add(
            win.row(
                "Désinstaller complètement (conteneur + volume + image + icône)",
                "Supprime aussi le volume open-webui et l'image",
                "edit-delete-symbolic",
                lambda *_: win.show_confirm(
                    "Purger Open WebUI",
                    "Supprimer le conteneur, l'icône, l'image ET toutes les conversations (volume open-webui) ?",
                    lambda: _uninstall(True),
                ),
            )
        )
    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title="Open WebUI"))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title="Open WebUI"))


def _push_vscodium_actions(win: Ps5ManagerWindow) -> None:
    installed = _vscodium_installed()
    sub = Adw.PreferencesPage()
    grp = Adw.PreferencesGroup(
        title="VSCodium",
        description=T("installed_rpm") if installed else T("not_installed"),
    )

    def _install():
        def _task(emit):
            if not _ensure_vscodium_repo(win, emit):
                return False, "Erreur configuration dépôt VSCodium"
            rc = win.run_cmd_pty(["dnf", "install", "-y", "codium"], emit)
            return rc == 0, T("done") if rc == 0 else T("failed") % rc
        win.run_task("Installer VSCodium", _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    def _update():
        def _task(emit):
            if not _ensure_vscodium_repo(win, emit):
                return False, "Erreur configuration dépôt VSCodium"
            rc = win.run_cmd_pty(["dnf", "upgrade", "-y", "--refresh", "codium"], emit)
            return rc == 0, T("done") if rc == 0 else T("failed") % rc
        win.run_task("Mettre à jour VSCodium", _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    def _remove():
        def _task(emit):
            rc = win.run_cmd_pty(["dnf", "remove", "-y", "codium"], emit)
            if rc == 0 and os.path.isfile(VSCODIUM_REPO_FILE):
                try:
                    os.remove(VSCODIUM_REPO_FILE)
                except OSError:
                    pass
            return rc == 0, T("done") if rc == 0 else T("failed") % rc
        win.run_task("Désinstaller VSCodium", _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    grp.add(win.row(T("install"), "Clé GPG + vscodium.repo + dnf install codium", "system-software-install-symbolic", lambda *_: _install()))
    grp.add(win.row(T("update"), "dnf upgrade -y --refresh codium", "software-update-available-symbolic", lambda *_: _update()))
    if installed:
        grp.add(win.row("Lancer VSCodium", "Ouvre codium sous votre session utilisateur", "applications-development-symbolic", lambda *_: subprocess.Popen(["codium"], **user_subprocess_kwargs())))
    grp.add(
        win.row(
            T("remove"),
            "dnf remove -y codium + retrait dépôt",
            "user-trash-symbolic",
            lambda *_: (
                win.show_confirm("Désinstaller VSCodium", "Supprimer VSCodium (codium) et son dépôt ?", _remove)
                if _vscodium_installed()
                else win.show_info("VSCodium", T("not_installed"))
            ),
        )
    )

    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title="VSCodium"))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title="VSCodium"))


def _push_ai_models(win: Ps5ManagerWindow) -> None:
    installed = _ollama_installed_models()
    running = _ollama_running_models()
    sub = Adw.PreferencesPage()

    # 1) Modèles déjà installés sur le système (incluant modèles personnalisés)
    g_inst = Adw.PreferencesGroup(
        title="Modèles installés sur le système" if UI_LANG == "fr" else "Installed models on system",
        description=f"{len(installed)} modèle(s) · {len(running)} actif(s) en RAM",
    )
    if not _ollama_installed():
        g_inst.add(Adw.ActionRow(title=GLib.markup_escape_text("Ollama n'est pas installé (sera installé au premier pull).")))
    elif not installed:
        g_inst.add(Adw.ActionRow(title=GLib.markup_escape_text("Aucun modèle installé pour le moment.")))
    else:
        for name, size in installed.items():
            state = "Actif en RAM" if name in running else "Installé"
            sub_lbl = f"{state} · {size}" if size else state
            g_inst.add(
                win.row(
                    name,
                    sub_lbl,
                    "media-playback-start-symbolic" if name in running else "drive-harddisk-symbolic",
                    lambda _r, m=name: _push_model_actions(win, m),
                )
            )
    if running:
        def _stop_all_models():
            def _task(emit):
                ollama = _ollama_bin() or "ollama"
                for m in list(_ollama_running_models()):
                    win.run_cmd_pty([ollama, "stop", m], emit)
                return True, T("done")
            win.run_task("Décharger tous les modèles", _task, lambda *_: (win.nav.pop(), _push_ai_models(win)))

        g_inst.add(
            win.row(
                "Décharger tous les modèles de la RAM" if UI_LANG == "fr" else "Unload all models from RAM",
                "ollama stop sur tous les modèles actifs",
                "media-playback-stop-symbolic",
                lambda *_: _stop_all_models(),
            )
        )
    sub.add(g_inst)

    # 2) Catalogue rapide des modèles demandés
    g_cat = Adw.PreferencesGroup(
        title="Catalogue des modèles recommandés" if UI_LANG == "fr" else "Recommended models catalog",
        description="Cliquez sur un modèle pour le télécharger, mettre à jour, stopper ou supprimer",
    )
    for model_id, desc_fr, desc_en in AI_MODELS_CATALOG:
        desc = desc_fr if UI_LANG == "fr" else desc_en
        if model_id in running:
            badge = "Actif en RAM"
        elif model_id in installed:
            badge = f"Installé ({installed[model_id]})" if installed[model_id] else "Installé"
        else:
            badge = "Non installé"
        g_cat.add(
            win.row(
                model_id,
                f"{desc} · {badge}",
                "folder-download-symbolic",
                lambda _r, m=model_id: _push_model_actions(win, m),
            )
        )

    def _pull_custom():
        win.show_prompt(
            "Télécharger un modèle Ollama",
            "Nom exact du modèle (ex : llama3.2:3b, mistral:7b) :",
            "qwen2.5-coder:3b",
            lambda name: _exec_model_pull(win, name.strip(), refresh_models=True) if name.strip() else None,
        )

    g_cat.add(
        win.row(
            "Télécharger un autre modèle (nom personnalisé)" if UI_LANG == "fr" else "Pull a custom model",
            "ollama pull <nom_du_modele>",
            "list-add-symbolic",
            lambda *_: _pull_custom(),
        )
    )
    sub.add(g_cat)

    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=T("aidev_models")))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=T("aidev_models")))


def _exec_model_pull(win: Ps5ManagerWindow, model_name: str, refresh_models: bool = False) -> None:
    def _task(emit):
        if not _ensure_ollama_ready(win, emit):
            return False, "Échec préparation Ollama"
        ollama = _ollama_bin() or "ollama"
        rc = win.run_cmd_pty([ollama, "pull", model_name], emit)
        return rc == 0, T("done") if rc == 0 else T("failed") % rc

    def _after(*_):
        if refresh_models:
            win.nav.pop()
            _push_ai_models(win)

    win.run_task(f"ollama pull {model_name}", _task, _after)


def _push_model_actions(win: Ps5ManagerWindow, model_name: str) -> None:
    installed = _ollama_installed_models()
    running = _ollama_running_models()
    is_inst = model_name in installed
    is_run = model_name in running
    status = "Actif en RAM" if is_run else (f"Installé ({installed[model_name]})" if is_inst else "Non installé")

    sub = Adw.PreferencesPage()
    grp = Adw.PreferencesGroup(title=model_name, description=status)

    grp.add(
        win.row(
            "Mettre à jour (ollama pull)" if is_inst else "Télécharger (ollama pull)",
            f"ollama pull {model_name}",
            "system-software-install-symbolic",
            lambda *_: _exec_model_pull(win, model_name, refresh_models=False),
        )
    )

    if is_inst:
        grp.add(
            win.row(
                "Décharger de la RAM (ollama stop)",
                f"ollama stop {model_name}",
                "media-playback-stop-symbolic",
                lambda *_: win.run_task(
                    f"ollama stop {model_name}",
                    lambda e: (win.run_cmd_pty([_ollama_bin() or "ollama", "stop", model_name], e) == 0, T("done")),
                ),
            )
        )

        def _show_model_details():
            ollama = _ollama_bin() or "ollama"
            res = subprocess.run([ollama, "show", model_name], capture_output=True, text=True)
            win.show_text_modal(model_name, res.stdout or res.stderr or "(indisponible — démarrez ollama.service)")

        grp.add(
            win.row(
                "Afficher les détails du modèle (ollama show)",
                "Architecture, quantification, paramètres et licence",
                "dialog-information-symbolic",
                lambda *_: _show_model_details(),
            )
        )

        def _do_remove():
            def _task(emit):
                ollama = _ollama_bin() or "ollama"
                if not _ollama_service_active() and _ollama_service_exists():
                    win.run_cmd_pty(["systemctl", "start", "ollama"], emit)
                # Toujours stopper le modèle avant de le supprimer s'il est en RAM
                if model_name in _ollama_running_models():
                    win.run_cmd_pty([ollama, "stop", model_name], emit)
                rc = win.run_cmd_pty([ollama, "rm", model_name], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc

            def _after(*_):
                win.nav.pop()
                win.nav.pop()
                _push_ai_models(win)

            win.run_task(f"ollama rm {model_name}", _task, _after)

        grp.add(
            win.row(
                "Supprimer le modèle (stop auto + ollama rm)",
                f"Stoppe si actif puis exécute ollama rm {model_name}",
                "user-trash-symbolic",
                lambda *_: win.show_confirm(
                    f"Supprimer {model_name}",
                    f"Le modèle sera stoppé s'il est actif puis supprimé (ollama rm {model_name}).",
                    _do_remove,
                ),
            )
        )

    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=model_name))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=model_name))


PAGE_BUILDERS = {
    "logs": build_page_logs,
    "library": build_page_library,
    "aidev": build_page_aidev,
    "update": build_page_update,
    "lang": build_page_lang,
    "repos": build_page_repos,
    "users": build_page_users,
    "fedora": build_page_fedora,
    "maint": build_page_maint,
    "power": build_page_power,
    "fan": build_page_fan,
    "hw": build_page_hw,
    "mesa": build_page_mesa,
    "kernel": build_page_kernel,
    "ui_lang": build_page_ui_lang,
}


# ------------------------------------------------------------------------------
# Application
# ------------------------------------------------------------------------------
class Ps5ManagerApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )
        self.theme_sync: Optional[SystemThemeSync] = None
        self.restart_on_exit: bool = False

    def do_activate(self) -> None:
        if self.theme_sync is None:
            self.theme_sync = SystemThemeSync()
            self.theme_sync.start()
        win = self.props.active_window
        if not win:
            win = Ps5ManagerWindow(self, self.theme_sync)
        win.present()


def main() -> int:
    warnings.simplefilter("ignore", DeprecationWarning)
    # Quitte /root (défini par pkexec) pour éviter tout EACCES lors des sous-processus utilisateur
    try:
        if os.getcwd() == "/root":
            os.chdir(INSTALL_DIR if os.path.isdir(INSTALL_DIR) else "/tmp")
    except OSError:
        pass
    for attr in ("NavigationSplitView", "NavigationView", "PreferencesPage", "ToolbarView"):
        if not hasattr(Adw, attr):
            sys.stderr.write(
                f"Adw.{attr} est absent : libadwaita 1.4+ requis (Fedora 39–45).\n"
            )
            return 1
    app = Ps5ManagerApp()
    rc = app.run(sys.argv)
    if app.restart_on_exit:
        target = (
            "/usr/local/bin/ps5-manager"
            if os.path.isfile("/usr/local/bin/ps5-manager")
            else os.path.abspath(sys.argv[0])
        )
        time.sleep(0.2)
        os.execv(sys.executable, [sys.executable, target, *sys.argv[1:]])
    return rc


if __name__ == "__main__":
    sys.exit(main())
