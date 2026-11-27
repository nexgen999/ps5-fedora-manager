"""Page Utilisateurs : comptes humains, création et suppression."""
from __future__ import annotations

import grp
import pwd
import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..env import current as current_env  # noqa: E402
from ..i18n import tr  # noqa: E402
from ..runner import run_command  # noqa: E402
from ..ui import action_row, plain_row  # noqa: E402


def _groups(gid: int, name: str) -> list[str]:
    names = {gr.gr_name for gr in grp.getgrall() if name in gr.gr_mem}
    try:
        names.add(grp.getgrgid(gid).gr_name)
    except KeyError:
        pass
    return sorted(names)


def humans() -> list[pwd.struct_passwd]:
    return [p for p in pwd.getpwall() if 1000 <= p.pw_uid < 65000]


def name_dialog(parent, title: str, on_accept) -> Adw.Window:
    """Petite fenêtre pour saisir un nom de compte (fabrique, pas de sous-classe)."""
    window = Adw.Window(transient_for=parent, modal=True, title=title)
    window.set_default_size(420, 180)
    entry = Gtk.Entry(placeholder_text="nom")
    entry.set_margin_top(18)
    entry.set_margin_bottom(6)
    entry.set_margin_start(18)
    entry.set_margin_end(18)

    def _accept() -> None:
        name = entry.get_text().strip()
        if not name:
            return
        window.close()
        on_accept(name)

    create = Gtk.Button(label=tr("users.add"))
    create.add_css_class("suggested-action")
    create.connect("clicked", lambda *_: _accept())
    cancel = Gtk.Button(label=tr("action.cancel"))
    cancel.connect("clicked", lambda *_: window.close())
    buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    buttons.set_halign(Gtk.Align.END)
    buttons.set_margin_start(18)
    buttons.set_margin_end(18)
    buttons.set_margin_bottom(18)
    buttons.append(cancel)
    buttons.append(create)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.append(entry)
    box.append(buttons)

    header = Adw.HeaderBar()
    header.set_title_widget(Adw.WindowTitle(title=title))
    toolbar = Adw.ToolbarView()
    toolbar.add_top_bar(header)
    toolbar.set_content(box)
    window.set_content(toolbar)
    return window


def build(win) -> Adw.PreferencesPage:
    """Construit la page (fonction : `Adw.PreferencesPage` est un type final)."""
    page = Adw.PreferencesPage()
    group = Adw.PreferencesGroup(title=tr("users.title"))
    page.add(group)

    def _do_remove(name: str) -> None:
        def _task(emit) -> tuple[bool, str]:
            emit(f"userdel -r {name}")
            code, out = run_command(["pkexec", "userdel", "-r", name], timeout=120)
            if code != 0:
                emit(out)
                return False, tr("common.failed", code=code)
            return True, tr("common.done")

        win.run_task(tr("users.remove"), _task)

    def _remove(person: pwd.struct_passwd) -> None:
        if person.pw_uid == 1000:
            win.toast(tr("users.keep_primary"))
            return
        win.confirm(
            tr("users.remove"),
            tr("users.confirm_remove", name=person.pw_name),
            lambda: _do_remove(person.pw_name),
        )

    def _create(name: str) -> None:
        def _task(emit) -> tuple[bool, str]:
            emit(f"useradd -m {name}")
            code, out = run_command(["pkexec", "useradd", "-m", name], timeout=120)
            if code != 0:
                emit(out)
                return False, tr("common.failed", code=code)
            # Le mot de passe se définit dans un terminal : `passwd` est interactif.
            try:
                subprocess.Popen(
                    current_env().open_terminal(["pkexec", "passwd", name]),
                    start_new_session=True,
                )
            except OSError as exc:
                emit(str(exc))
            return True, tr("users.created", name=name)

        win.run_task(tr("users.add"), _task)

    def _ask_name() -> None:
        name_dialog(win, tr("users.add"), _create).present()

    actions = Adw.PreferencesGroup()
    add = plain_row(title=tr("users.add"), subtitle=tr("users.add_hint"))
    add.set_activatable(True)
    add.connect("activated", lambda *_: _ask_name())
    actions.add(add)
    page.add(actions)

    people = humans()
    if not people:
        group.add(plain_row(title=tr("users.no_user")))
    else:
        for person in sorted(people, key=lambda p: p.pw_uid):
            row = action_row(
                person.pw_gecos or person.pw_name,
                f"{person.pw_name} · uid {person.pw_uid} · {person.pw_dir}",
                "system-users-symbolic",
                on_activate=lambda p=person: _remove(p),
            )
            row.add_suffix(
                Gtk.Label(label=", ".join(_groups(person.pw_gid, person.pw_name)))
            )
            group.add(row)

    return page
