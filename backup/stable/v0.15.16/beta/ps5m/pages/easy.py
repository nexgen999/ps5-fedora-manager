"""Page Installation facile : profils d'installation et nettoyage."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..i18n import tr  # noqa: E402
from ..runner import check_script, run_script  # noqa: E402
from ..ui import action_row, badge  # noqa: E402
from .addons import _install, _state  # noqa: E402

# Profils : chaque liste est exécutée dans l'ordre, les `needs` étant déjà triés.
PROFILES = (
    ("easy.profile_recommended", (
        "repo-rpmfusion", "repo-flathub", "codecs-av", "ffmpeg-full",
        "gaming-gamescope", "gaming-gamemode", "hw-hwcon-gui",
    )),
    ("easy.profile_gaming", (
        "repo-rpmfusion", "deps-32bit", "codecs-av", "gaming-gamescope",
        "gaming-gamemode", "gaming-mangohud", "app-steam",
    )),
    ("easy.profile_streaming", (
        "repo-rpmfusion", "codecs-av", "ffmpeg-full", "audio-easyeffects",
        "audio-presets-jackhack", "mesa-freeworld",
    )),
    ("easy.profile_office", (
        "repo-flathub", "feature-print", "feature-print-on", "app-btop",
    )),
)

CLEANUP = ("maint-clean", "gaming-uninstall", "hw-uninstall")


def build(win) -> Gtk.Widget:
    page = Adw.PreferencesPage()

    for label_key, chain in PROFILES:
        group = Adw.PreferencesGroup(title=tr(label_key))
        button = Gtk.Button(label=tr("easy.run"))
        button.add_css_class("suggested-action")
        button.set_halign(Gtk.Align.START)
        button.connect("clicked", lambda *_a, c=chain, l=label_key: _run_chain(win, l, c))
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_margin_top(6)
        box.append(button)
        holder = Adw.PreferencesGroup()
        holder.add(box)
        page.add(holder)

        for ident in chain:
            addon = win.addons.get(ident)
            if addon is None:
                continue
            done, total = _state(addon)
            group.add(action_row(
                addon.title(win.language),
                addon.description(win.language),
                addon.icon,
                on_activate=lambda a=addon: win.show_install_confirm(a, _install),
                suffix=badge(done, total, []),
            ))
        page.add(group)

    cleanup = Adw.PreferencesGroup(title=tr("easy.cleanup"))
    for ident in CLEANUP:
        addon = win.addons.get(ident)
        if addon is None:
            continue
        cleanup.add(action_row(
            addon.title(win.language),
            addon.description(win.language),
            addon.icon,
            on_activate=lambda a=addon: win.show_install_confirm(a, _install),
        ))
    page.add(cleanup)
    return page


def _run_chain(win, label_key: str, chain: tuple[str, ...]) -> None:
    def _task(emit) -> tuple[bool, str]:
        for ident in chain:
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

    win.run_task(tr(label_key), _task)
