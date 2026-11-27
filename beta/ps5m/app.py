"""Fenêtre de la bêta : barre latérale, pages et exécution des greffons."""
from __future__ import annotations

import os
import sys
import threading
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from . import __version__, catalog, i18n  # noqa: E402
from .env import current as current_env  # noqa: E402
from .journal import Journal  # noqa: E402
from .pages import ORDER, STATIC, SECTIONS as SECTION_PAGES, build_section  # noqa: E402

APP_ID = "io.github.nexgen999.ps5manager.beta"

# Icône de chaque section ; une section inconnue garde l'icône de dossier.
SECTION_ICONS = {
    "easy": "emblem-ok-symbolic",
    "library": "applications-other-symbolic",
    "aidev": "applications-science-symbolic",
    "dev": "applications-development-symbolic",
    "websrv": "network-server-symbolic",
    "deps": "application-x-addon-symbolic",
    "repos": "folder-download-symbolic",
    "gaming": "applications-games-symbolic",
    "audio": "audio-x-generic-symbolic",
    "video": "video-x-generic-symbolic",
    "hardware": "computer-symbolic",
    "mesa": "video-display-symbolic",
    "kernel": "drive-harddisk-symbolic",
    "power": "preferences-system-power-symbolic",
    "fan": "weather-windy-symbolic",
    "maint": "user-trash-symbolic",
    "update": "software-update-available-symbolic",
    "lang": "preferences-desktop-locale-symbolic",
    "features": "starred-symbolic",
    "fix": "emblem-system-symbolic",
    "services": "system-run-symbolic",
    "ui_lang": "preferences-desktop-locale-symbolic",
    "users": "system-users-symbolic",
    "fedora": "fedora-logo-symbolic",
}


def open_uri(url: str) -> None:
    launcher = getattr(Gtk, "UriLauncher", None)
    if launcher is not None:
        try:
            launcher.new(url).launch(None, None, None)
            return
        except GLib.Error:
            pass
    Gtk.show_uri(None, url, Gdk.CURRENT_TIME)


class LogWindow(Adw.Window):
    """Fenêtre de log en direct pour une installation."""

    def __init__(self, parent: "BetaWindow", title: str) -> None:
        super().__init__(transient_for=parent, modal=True, title=title)
        self.set_default_size(760, 520)
        self.view = Gtk.TextView(editable=False, monospace=True, cursor_visible=False)
        self.view.set_margins(12, 12, 12, 12)
        scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroll.set_child(self.view)

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=title))
        close = Gtk.Button(icon_name="window-close-symbolic")
        close.add_css_class("flat")
        close.connect("clicked", lambda *_: self.close())
        header.pack_end(close)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(scroll)
        self.set_content(toolbar)

    def emit(self, line: str) -> None:
        buffer = self.view.get_buffer()
        buffer.insert(buffer.get_end_iter(), line + "\n")
        mark = buffer.create_mark(None, buffer.get_end_iter(), False)
        self.view.scroll_mark_onscreen(mark)


class BetaWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title=i18n.tr("app.title"))
        self.set_default_size(1040, 760)
        self.journal = Journal()
        self.language = i18n.current()
        self.addons = catalog.load_local()
        self.journal.write(f"bêta {__version__} · bureau {current_env().name} · {self.language}")

        self.split = Adw.NavigationSplitView()
        self.nav = Adw.NavigationView()
        self.sidebar_box = Gtk.ListBox()
        self.sidebar_box.add_css_class("navigation-sidebar")
        self.sidebar_box.connect("row-selected", self._on_row_selected)
        self.lang_dropdown = self._build_language_dropdown()

        self.split.set_sidebar(self._build_sidebar())
        self.split.set_content(self._build_content())
        self.split.set_min_sidebar_width(240)

        self.toasts = Adw.ToastOverlay()
        self.toasts.set_child(self.split)
        self.set_content(self.toasts)

        threading.Thread(target=self._check_addon_updates, daemon=True).start()

    # ---- sections ----
    def section_ids(self) -> list[str]:
        """Sections affichées : page dédiée ou au moins un greffon."""
        known = {ident for ident, _b in SECTION_PAGES}
        return [
            ident for ident in ORDER
            if ident in known or any(a.section == ident for a in self.addons.values())
        ]

    # ---- construction ----
    def _build_sidebar(self) -> Adw.NavigationPage:
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="Bêta", subtitle=f"v{__version__}"))
        header.pack_end(self.lang_dropdown)
        refresh = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh.set_tooltip_text(i18n.tr("action.refresh"))
        refresh.add_css_class("flat")
        refresh.connect("clicked", lambda *_: self.refresh_addons())
        header.pack_start(refresh)

        self._fill_sidebar()

        scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(self.sidebar_box)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(scroll)
        page = Adw.NavigationPage(title="Bêta")
        page.set_child(toolbar)
        return page

    def _fill_sidebar(self) -> None:
        for ident in self.section_ids():
            self.sidebar_box.append(self._sidebar_row(f"section.{ident}", ident))
        for ident, label_key, _builder in STATIC:
            self.sidebar_box.append(self._sidebar_row(label_key, ident))

    def _sidebar_row(self, label_key: str, ident: str) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.ident = ident  # type: ignore[attr-defined]
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        icon = SECTION_ICONS.get(ident, "emblem-documents-symbolic")
        box.append(Gtk.Image.new_from_icon_name(icon))
        label = Gtk.Label(label=i18n.tr(label_key), xalign=0.0, hexpand=True)
        label.set_use_markup(False)
        box.append(label)
        row.set_child(box)
        return row

    def _build_content(self) -> Adw.NavigationPage:
        page = Adw.NavigationPage(title=i18n.tr("app.subtitle"))
        page.set_child(self.nav)
        return page

    def _build_language_dropdown(self) -> Gtk.DropDown:
        languages = i18n.available()
        self._lang_codes = [item["code"] for item in languages]
        labels = [f"{item['name']} ({item['code']})" for item in languages]
        dropdown = Gtk.DropDown.new_from_strings(labels)
        if self.language in self._lang_codes:
            dropdown.set_selected(self._lang_codes.index(self.language))
        dropdown.connect("notify::selected", self._on_language_selected)
        dropdown.set_tooltip_text(i18n.tr("about.language"))
        return dropdown

    # ---- navigation ----
    def _on_row_selected(self, _box, row) -> None:
        if row is None:
            return
        ident = row.ident  # type: ignore[attr-defined]
        builders = dict(SECTION_PAGES)
        if ident in builders:
            widget = builders[ident](self)
            title = i18n.tr(f"section.{ident}")
        elif ident in {i for i, _l, _b in STATIC}:
            builder = next(b for i, _l, b in STATIC if i == ident)
            widget = builder(self)
            title = i18n.tr(next(l for i, l, _b in STATIC if i == ident))
        else:
            widget = build_section(self, ident)
            title = i18n.tr(f"section.{ident}")
        page = Adw.NavigationPage(title=title)
        page.set_child(widget)
        self.nav.push(page)

    def go_to(self, ident: str) -> None:
        """Ouvre une section depuis une autre page (lien interne)."""
        for index, row in enumerate(self.sidebar_box):
            if getattr(row, "ident", None) == ident:
                self.sidebar_box.select_row(row)
                return
        self.toast(i18n.tr(f"section.{ident}"))

    def _on_language_selected(self, dropdown, _pspec) -> None:
        index = dropdown.get_selected()
        if index < 0 or index >= len(self._lang_codes):
            return
        self.set_language(self._lang_codes[index])

    def set_language(self, code: str) -> None:
        if code == self.language:
            return
        i18n.load(code)
        self.language = code
        self.journal.write(f"langue : {code}")
        if code in self._lang_codes:
            self.lang_dropdown.set_selected(self._lang_codes.index(code))
        self.rebuild_ui()

    def rebuild_ui(self) -> None:
        """Reconstruit la barre latérale et les titres après un changement de langue."""
        self.set_title(i18n.tr("app.title"))
        self.sidebar_box.remove_all()
        self._fill_sidebar()
        self.nav = Adw.NavigationView()
        self.split.get_content().set_child(self.nav)

    # ---- actions ----
    def toast(self, message: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=message, timeout=4))

    def open_uri(self, url: str) -> None:
        open_uri(url)

    def show_install_confirm(self, addon: catalog.Addon, install) -> None:
        dialog = Adw.AlertDialog(
            heading=addon.title(self.language),
            body=f"{addon.description(self.language)}\n\n{addon.id} · v{addon.version}",
        )
        dialog.add_response("cancel", i18n.tr("action.cancel"))
        dialog.add_response("install", i18n.tr("action.install"))
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("install")

        def _on_response(_dialog, response: str) -> None:
            if response == "install":
                install(self, addon)

        dialog.connect("response", _on_response)
        dialog.present(self)

    def confirm(self, heading: str, body: str, on_accept) -> None:
        """Confirmation simple pour une action destructive."""
        dialog = Adw.AlertDialog(heading=heading, body=body)
        dialog.add_response("cancel", i18n.tr("action.cancel"))
        dialog.add_response("ok", i18n.tr("action.install"))
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")

        def _on_response(_dialog, response: str) -> None:
            if response == "ok":
                on_accept()

        dialog.connect("response", _on_response)
        dialog.present(self)

    def run_task(self, title: str, task) -> None:
        """Exécute `task(emit) -> (ok, message)` dans un fil, avec log en direct."""
        window = LogWindow(self, title)
        window.present()

        def _emit(line: str) -> None:
            self.journal.write(line)
            GLib.idle_add(window.emit, line)

        def _worker() -> None:
            try:
                ok, message = task(_emit)
            except Exception as exc:  # noqa: BLE001 - une tâche ne doit pas tuer l'app
                ok, message = False, str(exc)
            GLib.idle_add(_finish, ok, message)

        def _finish(_ok: bool, message: str) -> None:
            window.close()
            self.toast(message)
            self.refresh_addons_state()

        threading.Thread(target=_worker, daemon=True).start()

    def run_background(self, task: Callable[[], tuple], done) -> None:
        """Lance une action courte sans fenêtre de log (interrupteurs, services).

        `task` renvoie `(ok, message)` ou `(ok, message, *détails)` : le tuple est
        transmis tel quel à `done`, ce qui laisse une page distinguer une
        annulation d'une vraie erreur (page Services).
        """

        def _worker() -> None:
            try:
                result = task()
            except Exception as exc:  # noqa: BLE001
                result = (False, str(exc))
            GLib.idle_add(done, *result)

        threading.Thread(target=_worker, daemon=True).start()

    def refresh_addons_state(self) -> None:
        """Relit les scripts après une installation (versions et états à jour)."""
        self.addons = catalog.load_local()

    # ---- mises à jour des greffons ----
    def _check_addon_updates(self) -> None:
        try:
            remote = catalog.fetch_index()
        except catalog.CatalogError:
            GLib.idle_add(self.toast, i18n.tr("catalog.offline"))
            return
        outdated, _removed = catalog.pending(self.addons, remote)
        if not outdated:
            return
        GLib.idle_add(self.refresh_hint, len(outdated))

    def refresh_hint(self, count: int) -> None:
        self.toast(f"{i18n.tr('action.refresh')} · {count}")

    def refresh_addons(self) -> None:
        def _task(emit) -> tuple[bool, str]:
            emit(i18n.tr("action.refresh"))
            try:
                report = catalog.refresh()
            except catalog.CatalogError as exc:
                return False, i18n.tr("catalog.failed", error=exc)
            if report["failed"]:
                first = next(iter(report["failed"].items()))
                return False, i18n.tr("catalog.failed", error=f"{first[0]}: {first[1]}")
            if not report["updated"]:
                return True, i18n.tr("catalog.up_to_date", count=report["checked"])
            emit(", ".join(report["updated"]))
            return True, i18n.tr("catalog.updated", count=len(report["updated"]))

        self.run_task(i18n.tr("action.refresh"), _task)


class BetaApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.window: BetaWindow | None = None

    def do_activate(self) -> None:  # noqa: N802 - nom imposé par GObject
        if self.window is None:
            self.window = BetaWindow(self)
        self.window.present()


def main(argv: list[str] | None = None) -> int:
    i18n.load(os.environ.get("PS5M_LANG", "fr"))
    app = BetaApplication()
    return app.run(argv if argv is not None else sys.argv)
