"""Page Utilisateurs : lecture seule des comptes humains et de leurs groupes."""
from __future__ import annotations

import grp
import pwd

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..i18n import tr  # noqa: E402
from ..ui import plain_row  # noqa: E402


def _groups(gid: int, name: str) -> list[str]:
    names = {gr.gr_name for gr in grp.getgrall() if name in gr.gr_mem}
    try:
        names.add(grp.getgrgid(gid).gr_name)
    except KeyError:
        pass
    return sorted(names)


def build(win) -> Gtk.Widget:
    page = Adw.PreferencesPage()
    group = Adw.PreferencesGroup(title=tr("users.title"))
    humans = [p for p in pwd.getpwall() if 1000 <= p.pw_uid < 65000]
    if not humans:
        row = plain_row(title=tr("users.no_user"))
        group.add(row)
    for person in sorted(humans, key=lambda p: p.pw_uid):
        row = plain_row(
            title=person.pw_gecos or person.pw_name,
            subtitle=f"{person.pw_name} · uid {person.pw_uid} · {person.pw_dir}",
        )
        row.add_suffix(Gtk.Label(label=", ".join(_groups(person.pw_gid, person.pw_name))))
        group.add(row)
    page.add(group)
    return page
