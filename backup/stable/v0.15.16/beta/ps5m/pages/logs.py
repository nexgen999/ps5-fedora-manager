"""Page Journal : contenu du fichier de log de la bêta."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk  # noqa: E402

from ..i18n import tr  # noqa: E402
from ..ui import text_page  # noqa: E402


def build(win) -> Gtk.Widget:
    page = Adw.PreferencesPage()
    group = Adw.PreferencesGroup()
    group.set_title(tr("logs.title"))

    body = text_page(tr("logs.title"), win.journal.lines())
    body.set_size_request(-1, 420)

    buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    buttons.set_margin_top(8)

    copy = Gtk.Button(label=tr("action.copy"))
    copy.add_css_class("flat")

    def _copy(*_args) -> None:
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(win.journal.text())
        win.toast(tr("logs.copied"))

    copy.connect("clicked", _copy)
    buttons.append(copy)

    clear = Gtk.Button(label=tr("logs.clear"))
    clear.add_css_class("destructive-action")

    def _clear(*_args) -> None:
        win.journal.clear()
        win.toast(tr("logs.cleared"))
        win.go_to("logs")

    clear.connect("clicked", _clear)
    buttons.append(clear)
    group.add(buttons)
    page.add(group)
    page.add(body)
    return page
