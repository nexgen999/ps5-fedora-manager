"""Page Noyau : noyaux installés, noyau par défaut et suppression."""
from __future__ import annotations

import platform
import re
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..i18n import tr  # noqa: E402
from ..runner import run_command  # noqa: E402
from ..ui import action_row, plain_row  # noqa: E402
from .addons import append_section_groups  # noqa: E402

VMLINUZ = re.compile(r"^vmlinuz-(?P<version>.+)$")


def kernels() -> list[str]:
    found: list[str] = []
    boot = Path("/boot")
    if boot.is_dir():
        for entry in sorted(boot.iterdir(), reverse=True):
            match = VMLINUZ.match(entry.name)
            if match:
                found.append(match.group("version"))
    if not found:
        code, out = run_command(["rpm", "-q", "kernel-core"], timeout=10)
        if code == 0:
            found = sorted(
                (line.removeprefix("kernel-core-") for line in out.splitlines() if line),
                reverse=True,
            )
    return found


def build(win) -> Adw.PreferencesPage:
    """Construit la page (fonction : `Adw.PreferencesPage` est un type final)."""
    page = Adw.PreferencesPage()
    group = Adw.PreferencesGroup(title=tr("kernel.group"))
    page.add(group)

    def _set_default(version: str) -> None:
        def _task(emit) -> tuple[bool, str]:
            target = f"/boot/vmlinuz-{version}"
            emit(f"grubby --set-default {target}")
            code, out = run_command(
                ["pkexec", "grubby", "--set-default", target], timeout=60
            )
            if code != 0:
                return False, tr("common.failed", code=code)
            emit(out or target)
            return True, tr("kernel.default_set")

        win.run_task(tr("kernel.set_default"), _task)

    def _do_remove(version: str) -> None:
        def _task(emit) -> tuple[bool, str]:
            emit(f"dnf remove kernel-core-{version}")
            code, out = run_command(
                ["pkexec", "dnf", "remove", "-y", f"kernel-core-{version}"],
                timeout=300,
            )
            if code != 0:
                emit(out)
                return False, tr("common.failed", code=code)
            return True, tr("common.done")

        win.run_task(tr("kernel.remove"), _task)

    def _remove(version: str) -> None:
        win.confirm(
            tr("kernel.remove"),
            tr("kernel.confirm_remove", version=version),
            lambda: _do_remove(version),
        )

    def _remove_button(version: str) -> Gtk.Button:
        button = Gtk.Button(label=tr("kernel.remove"))
        button.add_css_class("destructive-action")
        button.set_valign(Gtk.Align.CENTER)
        button.connect("clicked", lambda *_: _remove(version))
        return button

    running = platform.release()
    group.add(
        plain_row(
            title=tr("kernel.running"),
            subtitle=f"{running} · {platform.machine()}",
        )
    )
    versions = kernels()
    if not versions:
        group.add(plain_row(title="—", subtitle=tr("kernel.empty")))
    else:
        for version in versions:
            row = action_row(
                version,
                running if version == running else "",
                "drive-harddisk-symbolic",
                on_activate=lambda v=version: _set_default(v),
                suffix=Gtk.Image.new_from_icon_name("emblem-default-symbolic")
                if version == running
                else None,
            )
            row.add_suffix(_remove_button(version))
            group.add(row)

    append_section_groups(page, win, "kernel")
    return page
