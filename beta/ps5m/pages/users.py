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


class NameDialog(Adw.Window):
    """Petite fenêtre pour saisir un nom de compte."""

    def __init__(self, parent, title: str, on_accept) -> None:
        super().__init__(transient_for=parent, modal=True, title=title)
        self.set_default_size(420, 180)
        self.entry = Gtk.Entry(placeholder_text="nom")
        self.entry.set_margin_top(18)
        self.entry.set_margin_bottom(6)
        self.entry.set_margin_start(18)
        self.entry.set_margin_end(18)

        create = Gtk.Button(label=tr("users.add"))
        create.add_css_class("suggested-action")
        create.connect("clicked", lambda *_: self._accept(on_accept))
        cancel = Gtk.Button(label=tr("action.cancel"))
        cancel.connect("clicked", lambda *_: self.close())
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        buttons.set_margin_start(18)
        buttons.set_margin_end(18)
        buttons.set_margin_bottom(18)
        buttons.append(cancel)
        buttons.append(create)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(self.entry)
        box.append(buttons)

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=title))
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(box)
        self.set_content(toolbar)

    def _accept(self, on_accept) -> None:
        name = self.entry.get_text().strip()
        if not name:
            return
        self.close()
        on_accept(name)


class UsersPage(Adw.PreferencesPage):
    def __init__(self, win) -> None:
        super().__init__()
        self.win = win
        self.group = Adw.PreferencesGroup(title=tr("users.title"))
        self.add(self.group)

        actions = Adw.PreferencesGroup()
        add = plain_row(title=tr("users.add"), subtitle=tr("users.add_hint"))
        add.set_activatable(True)
        add.connect("activated", lambda *_: self._ask_name())
        actions.add(add)
        self.add(actions)

        self._fill()

    def _fill(self) -> None:
        people = humans()
        if not people:
            self.group.add(plain_row(title=tr("users.no_user")))
            return
        for person in sorted(people, key=lambda p: p.pw_uid):
            row = action_row(
                person.pw_gecos or person.pw_name,
                f"{person.pw_name} · uid {person.pw_uid} · {person.pw_dir}",
                "system-users-symbolic",
                on_activate=lambda p=person: self._remove(p),
            )
            row.add_suffix(Gtk.Label(label=", ".join(_groups(person.pw_gid, person.pw_name))))
            self.group.add(row)

    def _ask_name(self) -> None:
        NameDialog(self.win, tr("users.add"), self._create).present()

    def _create(self, name: str) -> None:
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

        self.win.run_task(tr("users.add"), _task)

    def _remove(self, person: pwd.struct_passwd) -> None:
        if person.pw_uid == 1000:
            self.win.toast(tr("users.keep_primary"))
            return
        self.win.confirm(
            tr("users.remove"),
            tr("users.confirm_remove", name=person.pw_name),
            lambda: self._do_remove(person.pw_name),
        )

    def _do_remove(self, name: str) -> None:
        def _task(emit) -> tuple[bool, str]:
            emit(f"userdel -r {name}")
            code, out = run_command(["pkexec", "userdel", "-r", name], timeout=120)
            if code != 0:
                emit(out)
                return False, tr("common.failed", code=code)
            return True, tr("common.done")

        self.win.run_task(tr("users.remove"), _task)


# La page est une classe : l'alias garde l'interface `build(win)`.
build = UsersPage
