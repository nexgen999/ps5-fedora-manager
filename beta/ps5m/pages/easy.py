"""Page Installation facile : enchaîne les greffons essentiels dans l'ordre."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .. import catalog  # noqa: E402
from ..i18n import tr  # noqa: E402
from ..runner import check_script, run_script  # noqa: E402
from ..ui import action_row, badge  # noqa: E402

# Ordre volontairement explicite : dépôts → codecs → greffons de jeu.
CHAIN = (
    "repo-rpmfusion",
    "repo-flathub",
    "codecs-av",
    "ffmpeg-full",
    "gaming-gamescope",
    "gaming-gamemode",
    "hw-hwcon-gui",
)


def _state(addon) -> tuple[int, int]:
    from .addons import _state as state

    return state(addon)


def build(win) -> Gtk.Widget:
    page = Adw.PreferencesPage()
    group = Adw.PreferencesGroup(
        title=tr("easy.title"), description=tr("easy.subtitle")
    )

    button = Gtk.Button(label=tr("easy.run"))
    button.add_css_class("suggested-action")
    button.set_halign(Gtk.Align.START)
    button.connect("clicked", lambda *_: _run_chain(win))
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    box.set_margin_top(6)
    box.append(button)

    for ident in CHAIN:
        addon = win.addons.get(ident)
        if addon is None:
            continue
        done, total = _state(addon)
        row = action_row(
            addon.title(win.language),
            addon.description(win.language),
            addon.icon,
            on_activate=lambda a=addon: win.show_install_confirm(a, _install_one),
            suffix=badge(done, total, []),
        )
        group.add(row)

    holder = Adw.PreferencesGroup()
    holder.add(box)
    page.add(holder)
    page.add(group)
    return page


def _install_one(win, addon: catalog.Addon) -> None:
    from .addons import _install

    _install(win, addon)


def _run_chain(win) -> None:
    def _task(emit) -> tuple[bool, str]:
        for ident in CHAIN:
            addon = win.addons.get(ident)
            if addon is None or addon.path is None:
                continue
            emit(f"— {ident} v{addon.version}")
            if check_script(addon.path):
                emit(f"{ident} : déjà installé")
                continue
            code = run_script(addon.path, emit, root=addon.root)
            if code != 0:
                return False, tr("common.failed", code=code)
        return True, tr("easy.chain_done")

    win.run_task(tr("easy.title"), _task)
