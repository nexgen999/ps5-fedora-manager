"""Page Langue : choisir la langue de l'interface (un fichier JSON par langue)."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .. import i18n  # noqa: E402
from ..ui import plain_row  # noqa: E402


def build(win) -> Gtk.Widget:
    page = Adw.PreferencesPage()
    group = Adw.PreferencesGroup(
        title=i18n.tr("ui_lang.title"), description=i18n.tr("ui_lang.subtitle")
    )
    for item in i18n.available():
        done, total, missing = i18n.coverage(item["code"])
        row = plain_row(
            title=f"{item['name']} ({item['code']})",
            subtitle=f"{done}/{total}" + (f" · {len(missing)} clés manquantes" if missing else ""),
        )
        row.set_activatable(True)
        if item["code"] == i18n.current():
            row.add_suffix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
        row.connect("activated", lambda _r, c=item["code"]: win.set_language(c))
        group.add(row)
    page.add(group)

    system = Adw.PreferencesGroup(title=i18n.tr("ui_lang.system"))
    link = plain_row(
        title=i18n.tr("section.lang"),
        subtitle=i18n.tr("section.lang") + " · langpacks",
    )
    link.set_activatable(True)
    link.connect("activated", lambda *_: win.go_to("lang"))
    system.add(link)
    page.add(system)
    return page
