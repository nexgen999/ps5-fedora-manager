"""Petits composants d'interface partagés par les pages."""
from __future__ import annotations

from typing import Callable, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .i18n import tr  # noqa: E402


def plain_row(**kwargs) -> Adw.ActionRow:
    """Ligne dont le titre/sous-titre est du texte littéral (« & » compris)."""
    title = kwargs.pop("title", None)
    subtitle = kwargs.pop("subtitle", None)
    row = Adw.ActionRow(**kwargs)
    if hasattr(row, "set_use_markup"):
        row.set_use_markup(False)
    if title is not None:
        row.set_title(title)
    if subtitle is not None:
        row.set_subtitle(subtitle)
    return row


def badge(done: int, total: int, missing: list[str]) -> Optional[Gtk.Widget]:
    """Pastille ● / ◐ / ○ ; l'infobulle nomme les paquets manquants."""
    if total <= 0:
        return None
    if done >= total:
        text, css, tip = "● " + tr("status.installed"), "success", ""
    elif done:
        text = tr("status.partial", done=done, total=total)
        css = "warning"
        tip = tr("status.missing_hint", names=", ".join(missing))
    else:
        text, css, tip = "○ " + tr("status.missing"), "dim-label", ""
    label = Gtk.Label(label="◐ " + text if done and done < total else text)
    label.add_css_class("caption")
    label.add_css_class(css)
    label.set_valign(Gtk.Align.CENTER)
    if tip:
        label.set_tooltip_text(tip)
    return label


def text_page(title: str, lines: list[str]) -> Gtk.Widget:
    """Bloc de texte monospace défilant (journal, informations)."""
    view = Gtk.TextView(editable=False, monospace=True, cursor_visible=False)
    view.get_buffer().set_text("\n".join(lines) if lines else tr("logs.empty"))
    view.set_margins(12, 12, 12, 12)
    scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
    scroll.set_child(view)
    return scroll


def action_row(
    title: str,
    subtitle: str,
    icon: str,
    on_activate: Optional[Callable] = None,
    suffix: Optional[Gtk.Widget] = None,
) -> Adw.ActionRow:
    row = plain_row(title=title, subtitle=subtitle or None)
    row.add_prefix(Gtk.Image.new_from_icon_name(icon))
    if suffix is not None:
        row.add_suffix(suffix)
    row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
    if on_activate is not None:
        row.set_activatable(True)
        row.connect("activated", lambda *_: on_activate())
    return row
