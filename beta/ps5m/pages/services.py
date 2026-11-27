"""Page Services : activer ou couper un service systemd, sans ligne de commande."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..i18n import tr  # noqa: E402
from ..runner import run_command  # noqa: E402
from ..ui import plain_row  # noqa: E402

# (unité, paquet qui la fournit) — l'ordre suit celui de la version stable.
SERVICES = (
    ("sshd.service", "openssh-server"),
    ("bluetooth.service", "bluez"),
    ("cups.service", "cups"),
    ("avahi-daemon.service", "avahi"),
    ("firewalld.service", "firewalld"),
    ("httpd.service", "httpd"),
    ("nginx.service", "nginx"),
    ("mariadb.service", "mariadb-server"),
    ("ollama.service", "ollama"),
    ("tlp.service", "tlp"),
    ("power-profiles-daemon.service", "power-profiles-daemon"),
    ("cockpit.socket", "cockpit"),
    ("ps5fan.service", "ps5 fan control"),
)


def _enabled(unit: str) -> bool:
    code, _ = run_command(["systemctl", "is-enabled", unit], timeout=5)
    return code == 0


def _present(unit: str) -> bool:
    code, _ = run_command(["systemctl", "list-unit-files", unit], timeout=10)
    if code != 0:
        return False
    code, out = run_command(["systemctl", "list-unit-files", unit], timeout=10)
    return unit in out


class _ServiceRow(Adw.SwitchRow):
    def __init__(self, win, unit: str) -> None:
        super().__init__()
        self.win = win
        self.unit = unit
        self._busy = False
        self.set_title(unit.removesuffix(".service"))
        self.set_subtitle(unit)
        self.set_use_markup(False)
        exists = _present(unit)
        self.set_activatable(False)
        if not exists:
            self.set_subtitle(f"{unit} · {tr('services.absent')}")
            self.set_sensitive(False)
            return
        self.set_active(_enabled(unit))
        self.connect("notify::active", self._on_toggle)

    def _on_toggle(self, row, _pspec) -> None:
        if self._busy:
            return
        wanted = row.get_active()
        self._busy = True
        self.set_sensitive(False)
        unit = self.unit

        def _apply() -> tuple[bool, str]:
            action = "enable" if wanted else "disable"
            code, out = run_command(
                ["pkexec", "systemctl", action, "--now", unit], timeout=120
            )
            if code != 0:
                return False, f"{tr('common.failed', code=code)} · {out[:200]}"
            return True, f"{unit} · {tr('services.enable' if wanted else 'services.disable')}"

        def _done(ok: bool, message: str) -> None:
            self._busy = False
            self.set_sensitive(True)
            if not ok:
                self._busy = True
                self.set_active(not wanted)
                self._busy = False
            self.win.toast(message)

        self.win.run_background(_apply, _done)


def build(win) -> Gtk.Widget:
    page = Adw.PreferencesPage()
    group = Adw.PreferencesGroup(title=tr("services.title"))
    for unit, _pkg in SERVICES:
        group.add(_ServiceRow(win, unit))
    hint = plain_row(title=tr("ui_lang.system"), subtitle="systemctl enable/disable --now")
    hint.set_activatable(False)
    group.add(hint)
    page.add(group)
    return page
