"""Page Logithèque : gestion des AppImage + greffons de la section."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..i18n import tr  # noqa: E402
from ..ui import action_row, plain_row  # noqa: E402
from .addons import append_section_groups  # noqa: E402

APPS_DIR = Path(os.path.expanduser("~/Applications"))
DESKTOP_DIR = Path(os.path.expanduser("~/.local/share/applications"))


def installed() -> list[Path]:
    if not APPS_DIR.is_dir():
        return []
    return sorted(p for p in APPS_DIR.glob("*.AppImage") if p.is_file())


def _desktop_file(appimage: Path) -> Path:
    return DESKTOP_DIR / f"{appimage.stem}.desktop"


def install_file(source: Path) -> str:
    """Copie une AppImage, la rend exécutable et crée son entrée de menu."""
    APPS_DIR.mkdir(parents=True, exist_ok=True)
    target = APPS_DIR / source.name
    shutil.copy2(source, target)
    target.chmod(0o755)
    DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
    _desktop_file(target).write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={target.stem}\n"
        f"Exec={target}\n"
        "Terminal=false\n"
        "Categories=Utility;\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["update-desktop-database", str(DESKTOP_DIR)], capture_output=True, check=False
    )
    return str(target)


def remove_file(appimage: Path) -> None:
    _desktop_file(appimage).unlink(missing_ok=True)
    appimage.unlink(missing_ok=True)


class LibraryPage(Adw.PreferencesPage):
    def __init__(self, win) -> None:
        super().__init__()
        self.win = win
        self.group = Adw.PreferencesGroup(
            title=tr("library.appimage_group"),
            description=tr("library.appimage_hint"),
        )
        self.add(self.group)

        button = Gtk.Button(label=tr("library.appimage_install"))
        button.add_css_class("suggested-action")
        button.set_halign(Gtk.Align.START)
        button.connect("clicked", lambda *_: self._choose())
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_margin_top(6)
        box.append(button)
        holder = Adw.PreferencesGroup()
        holder.add(box)
        self.add(holder)

        self._fill()
        append_section_groups(self, win, "library")

    def _fill(self) -> None:
        apps = installed()
        if not apps:
            self.group.add(plain_row(title=tr("library.appimage_empty")))
            return
        for appimage in apps:
            row = action_row(
                appimage.stem,
                str(appimage),
                "application-x-executable-symbolic",
                on_activate=lambda a=appimage: self.win.confirm(
                    tr("library.appimage_remove"),
                    a.name,
                    lambda: self._remove(a),
                ),
            )
            self.group.add(row)

    def _remove(self, appimage: Path) -> None:
        def _task(emit) -> tuple[bool, str]:
            emit(str(appimage))
            remove_file(appimage)
            return True, tr("common.done")

        self.win.run_task(tr("library.appimage_remove"), _task)

    def _choose(self) -> None:
        dialog = Gtk.FileChooserNative(
            title=tr("library.appimage_install"),
            transient_for=self.win,
            action=Gtk.FileChooserAction.OPEN,
        )
        filter_appimage = Gtk.FileFilter()
        filter_appimage.set_name("AppImage")
        filter_appimage.add_pattern("*.AppImage")
        filter_appimage.add_pattern("*.appimage")
        dialog.add_filter(filter_appimage)

        def _on_response(native, response) -> None:
            if response != Gtk.ResponseType.ACCEPT:
                return
            selected = native.get_file()
            if selected is None:
                return
            path = Path(selected.get_path() or "")
            if not path.is_file():
                self.win.toast(tr("library.appimage_failed"))
                return
            self._install(path)

        dialog.connect("response", _on_response)
        dialog.show()

    def _install(self, source: Path) -> None:
        def _task(emit) -> tuple[bool, str]:
            emit(f"{source} → {APPS_DIR}")
            target = install_file(source)
            emit(target)
            return True, tr("common.done")

        self.win.run_task(tr("library.appimage_install"), _task)

    def reload(self) -> None:
        self.group.remove_all()
        self._fill()
