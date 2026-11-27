# `ps5m/ui.py`

Shared components. Key point: all text is set as literal
(`set_use_markup(False)`), so `&` or `<` can never break rendering.

| Component | Role |
|---|---|
| `plain_row(title, subtitle, **kw)` | `Adw.ActionRow` without markup |
| `badge(done, total, missing)` | `●` / `◐` / `○` badge with tooltip |
| `action_row(title, subtitle, icon, on_activate, suffix)` | full clickable row |
| `text_page(title, lines)` | scrolling monospace text block |

`badge` returns `None` when `total == 0` (action addon or no declared state):
the row then only shows the chevron.
