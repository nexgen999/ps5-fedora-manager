"""Page Version de Fedora : informations locales et vérification des mises à jour."""
from __future__ import annotations

import platform
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..i18n import tr  # noqa: E402
from ..runner import run_command  # noqa: E402
from ..ui import plain_row  # noqa: E402


def os_release() -> dict[str, str]:
    data: dict[str, str] = {}
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                data[key] = value.strip().strip('"')
    except OSError:
        pass
    return data


def build(win) -> Gtk.Widget:
    page = Adw.PreferencesPage()
    info = Adw.PreferencesGroup(title=tr("fedora.title"))
    release = os_release()
    info.add(plain_row(
        title=tr("fedora.current"),
        subtitle=release.get("PRETTY_NAME", "Fedora"),
    ))
    info.add(plain_row(
        title=tr("fedora.kernel"),
        subtitle=platform.release(),
    ))
    code, dnf = run_command(["dnf", "--version"], timeout=10)
    info.add(plain_row(
        title=tr("fedora.dnf"),
        subtitle=(dnf.splitlines()[0] if code == 0 and dnf else "—"),
    ))
    info.add(plain_row(title="Machine", subtitle=platform.machine()))
    page.add(info)

    actions = Adw.PreferencesGroup()
    check = plain_row(
        title=tr("fedora.check"),
        subtitle="dnf check-update",
    )
    check.set_activatable(True)
    check.connect("activated", lambda *_: win.run_task(
        tr("fedora.check"), _check_updates
    ))
    actions.add(check)
    page.add(actions)
    return page


def _check_updates(emit) -> tuple[bool, str]:
    emit("dnf check-update")
    code, out = run_command(["dnf", "check-update"], timeout=180)
    count = sum(1 for line in out.splitlines() if line and not line.startswith(" "))
    if code == 100:
        emit(out)
        return True, f"{count} mise(s) à jour disponible(s)"
    if code == 0:
        return True, "Système à jour"
    emit(out)
    return False, f"dnf : code {code}"
