"""Page générique d'une section : une ligne par greffon de `addons/`."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402
from ps5m import catalog, system  # noqa: E402

from ..i18n import tr  # noqa: E402
from ..runner import check_script, run_script  # noqa: E402
from ..ui import action_row, badge  # noqa: E402


def _state(addon: catalog.Addon) -> tuple[int, int]:
    """(installés, total) en combinant paquets RPM et chemins déclarés."""
    done = total = 0
    if addon.packages:
        present = system.rpm_present(addon.packages)
        done += sum(1 for ok in present.values() if ok)
        total += len(present)
    if addon.check_paths:
        present = system.path_present(addon.check_paths)
        done += sum(1 for ok in present.values() if ok)
        total += len(present)
    return done, total


def _missing(addon: catalog.Addon) -> list[str]:
    names: list[str] = []
    if addon.packages:
        names += [p for p, ok in system.rpm_present(addon.packages).items() if not ok]
    if addon.check_paths:
        names += [p for p, ok in system.path_present(addon.check_paths).items() if not ok]
    return names


def _install(win, addon: catalog.Addon) -> None:
    def _task(emit) -> tuple[bool, str]:
        if addon.path is None:
            return False, tr("catalog.failed", error=addon.id)
        if check_script(addon.path):
            emit(tr("status.installed"))
            return True, tr("common.done")
        code = run_script(addon.path, emit)
        return code == 0, tr("common.done") if code == 0 else tr("common.failed", code=code)

    win.run_task(f"{addon.title(win.language)} {addon.version}", _task)


def build_section(win, section: str) -> Gtk.Widget:
    page = Adw.PreferencesPage()
    group = Adw.PreferencesGroup()
    group.set_title(tr(f"section.{section}"))
    group.set_description(tr("catalog.subtitle"))

    addons = [a for a in win.addons.values() if a.section == section]
    for addon in catalog.order(addons):
        done, total = _state(addon)
        row = action_row(
            addon.title(win.language),
            addon.description(win.language),
            addon.icon,
            on_activate=lambda a=addon: win.show_install_confirm(a, _install),
            suffix=badge(done, total, _missing(addon)),
        )
        row.set_tooltip_text(f"{addon.id} · v{addon.version}")
        group.add(row)

    page.add(group)
    return page
