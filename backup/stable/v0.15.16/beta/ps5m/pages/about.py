"""Page À propos : versions, bureau détecté, greffons et lien du changelog."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402
from ps5m import __version__, i18n  # noqa: E402
from ps5m.env import current as current_env  # noqa: E402

from ..i18n import tr  # noqa: E402
from ..ui import action_row, plain_row  # noqa: E402

CHANGELOG = "https://github.com/nexgen999/ps5-fedora-manager/blob/main/CHANGELOG.md"


def build(win) -> Gtk.Widget:
    page = Adw.PreferencesPage()
    env = current_env()

    version = Adw.PreferencesGroup()
    version.add(
        action_row(
            "PS5 Fedora Manager — bêta",
            tr("app.subtitle"),
            "applications-system-symbolic",
        )
    )
    version.add(plain_row(title=tr("about.version"), subtitle=__version__))
    version.add(
        plain_row(
            title=tr("about.desktop"),
            subtitle=f"{env.name} ({env.id})",
        )
    )
    languages = i18n.available()
    current_name = next(
        (item["name"] for item in languages if item["code"] == i18n.current()),
        i18n.current(),
    )
    version.add(
        plain_row(
            title=tr("about.language"),
            subtitle=f"{current_name} ({i18n.current()}) · {len(languages)} fichiers",
        )
    )
    version.add(
        plain_row(
            title=tr("about.addons"),
            subtitle=f"{len(win.addons)}",
        )
    )
    version.add(
        action_row(
            tr("about.changelog"),
            CHANGELOG,
            "document-open-recent-symbolic",
            on_activate=lambda: win.open_uri(CHANGELOG),
        )
    )
    page.add(version)
    return page
