# `ps5m/pages/`

Une page = un module avec `build(win) -> Gtk.Widget`. Deux familles :

- **générique** (`addons.py`) : une ligne par greffon de la section, pastille,
  confirmation, installation. C'est le cas par défaut.
- **dédiée** : quand il faut une vraie interface (interrupteurs, comptes,
  sélection de langue, enchaînement d'installations).

## Enregistrement

`pages/__init__.py` expose trois choses :

| Nom | Rôle |
|---|---|
| `STATIC` | pages fixes : journal, à propos |
| `SECTIONS` | sections avec page dédiée (`easy`, `services`, `ui_lang`, `users`, `fedora`) |
| `ORDER` | ordre de la barre latérale |

`app.section_ids()` n'affiche que les sections présentes dans `ORDER` et
auxquelles correspondent une page dédiée ou au moins un greffon.

## Pages livrées

| Page | Rôle |
|---|---|
| `addons.py` | section générique depuis le catalogue |
| `easy.py` | enchaînement recommandé (dépôts → codecs → jeu) |
| `services.py` | `systemctl enable/disable --now` via `pkexec` |
| `ui_lang.py` | changement de langue + couverture des traductions |
| `users.py` | comptes humains et groupes (lecture seule) |
| `fedora.py` | version installée, noyau, `dnf check-update` |
| `logs.py` | journal |
| `about.py` | à propos, liens, crédits |

## Ajouter une page

1. Créer `pages/ma_page.py` avec `build(win)`.
2. L'ajouter à `STATIC` (page fixe) ou à `SECTIONS` (section).
3. Si c'est une section, l'ajouter aussi à `ORDER` et, au besoin, à
   `SECTION_ICONS` dans `app.py`.
4. Ajouter les clés `section.<id>` et le texte de la page dans les 6 langues.
