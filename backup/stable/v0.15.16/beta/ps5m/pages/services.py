"""Page Services : activer ou couper un service systemd, sans ligne de commande.

Un seul appel `systemctl show` par service donne à la fois sa présence et son
état d'activation. L'activation passe par `pkexec` : si l'utilisateur annule la
demande polkit (code 126), l'interrupteur revient à sa position et rien n'est
signalé comme une erreur.
"""
from __future__ import annotations

from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..i18n import tr  # noqa: E402
from ..runner import run_command  # noqa: E402
from ..ui import plain_row  # noqa: E402
from .addons import append_section_groups  # noqa: E402

# Code de sortie de pkexec quand la boîte d'authentification est fermée.
POLKIT_DISMISSED = 126
POLKIT_NOT_AUTHORIZED = 127

# Services proposés, dans l'ordre de la version stable.
SERVICES = (
    "sshd.service",
    "bluetooth.service",
    "cups.service",
    "avahi-daemon.service",
    "firewalld.service",
    "httpd.service",
    "nginx.service",
    "mariadb.service",
    "ollama.service",
    "tlp.service",
    "power-profiles-daemon.service",
    "cockpit.socket",
    "ps5fan.service",
)

# États d'UnitFileState qui ne se pilotent pas avec enable/disable.
STATIC_STATES = {"static", "indirect", "alias", "generated", "transient"}


class ServiceState:
    """Présence et état d'un service, lus en un seul appel systemctl."""

    __slots__ = ("present", "enabled", "static", "detail")

    def __init__(self, present: bool, enabled: bool, static: bool, detail: str) -> None:
        self.present = present
        self.enabled = enabled
        self.static = static
        self.detail = detail


def read_state(unit: str) -> ServiceState:
    code, out = run_command(
        ["systemctl", "show", "-p", "LoadState", "-p", "UnitFileState", unit],
        timeout=5,
    )
    fields: dict[str, str] = {}
    for line in out.splitlines():
        key, _, value = line.partition("=")
        if value:
            fields[key.strip()] = value.strip()
    load_state = fields.get("LoadState", "")
    unit_state = fields.get("UnitFileState", "")
    present = bool(load_state) and load_state != "not-found"
    enabled = unit_state == "enabled" or unit_state.startswith("enabled")
    static = unit_state in STATIC_STATES
    detail = unit_state or load_state or f"systemctl {code}"
    return ServiceState(present, enabled, static, detail)


def service_row(win, unit: str) -> Adw.SwitchRow:
    """Ligne d'interrupteur systemd.

    `Adw.SwitchRow` est un type final : on compose une ligne au lieu d'en
    dériver une classe (PyGObject refuse la sous-classe depuis GTK 4.22).
    """
    row = Adw.SwitchRow()
    row.set_title(unit.removesuffix(".service").removesuffix(".socket"))
    row.set_use_markup(False)
    row.set_activatable(False)

    state = read_state(unit)
    if not state.present:
        row.set_subtitle(f"{unit} · {tr('services.absent')}")
        row.set_sensitive(False)
        return row
    if state.static:
        row.set_subtitle(f"{unit} · {tr('services.static')}")
        row.set_sensitive(False)
        row.set_active(state.enabled)
        return row

    row.set_subtitle(f"{unit} · {state.detail}")
    row.set_active(state.enabled)
    busy = {"value": False}

    def _on_toggle(_row, _pspec) -> None:
        if busy["value"]:
            return
        wanted = row.get_active()
        busy["value"] = True
        row.set_sensitive(False)
        row.set_subtitle(f"{unit} · …")

        def _apply() -> tuple[bool, str, bool]:
            action = "enable" if wanted else "disable"
            code, out = run_command(
                ["pkexec", "systemctl", action, "--now", unit], timeout=180
            )
            if code == 0:
                return True, unit, True
            if code == POLKIT_DISMISSED:
                return False, tr("services.cancelled"), True
            return False, f"{tr('common.failed', code=code)} · {out[:200]}", False

        def _done(ok: bool, message: str, cancelled: bool) -> None:
            row.set_sensitive(True)
            busy["value"] = False
            if not ok:
                # Annulation polkit : on remet l'interrupteur sans rien signaler.
                busy["value"] = True
                row.set_active(not wanted)
                busy["value"] = False
                fresh = read_state(unit)
                row.set_subtitle(f"{unit} · {fresh.detail}")
                if not cancelled:
                    win.toast(message)
                return
            fresh = read_state(unit)
            row.set_subtitle(f"{unit} · {fresh.detail}")
            win.toast(
                f"{unit} · "
                + tr("services.enable" if fresh.enabled else "services.disable")
            )

        win.run_background(_apply, _done)

    row.connect("notify::active", _on_toggle)
    return row


def build(win) -> Gtk.Widget:
    page = Adw.PreferencesPage()
    group = Adw.PreferencesGroup(
        title=tr("services.title"), description=tr("services.subtitle")
    )
    for unit in SERVICES:
        group.add(service_row(win, unit))
    note: Optional[Adw.ActionRow] = plain_row(
        title="systemctl enable/disable --now",
        subtitle=tr("services.subtitle"),
    )
    note.set_activatable(False)
    group.add(note)
    page.add(group)
    append_section_groups(page, win, "services")
    return page
