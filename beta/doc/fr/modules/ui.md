# `ps5m/ui.py`

Composants partagés. Point important : tout le texte est passé en littéral
(`set_use_markup(False)`), donc un `&` ou un `<` ne casse jamais l'affichage.

| Composant | Rôle |
|---|---|
| `plain_row(title, subtitle, **kw)` | `Adw.ActionRow` sans markup |
| `badge(done, total, missing)` | pastille `●` / `◐` / `○` avec infobulle |
| `action_row(title, subtitle, icon, on_activate, suffix)` | ligne cliquable complète |
| `text_page(title, lines)` | bloc de texte monospace défilant |

`badge` renvoie `None` si `total == 0` (greffon d'action ou aucun état
déclar) : la ligne affiche alors seulement le chevron.
