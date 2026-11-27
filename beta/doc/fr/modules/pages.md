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
| `easy.py` | quatre profils (recommandé, gaming, streaming, bureautique) + nettoyage |
| `appimage.py` | AppImage : installer, lister, désinstaller (+ greffons de la section) |
| `repos.py` | dépôts : activer/couper, rafraîchir, ajouter un `.repo` |
| `kernel.py` | noyaux installés, noyau par défaut, suppression |
| `services.py` | un appel `systemctl show` par service (présence + état), bascule via `pkexec`, annulation polkit (code 126) sans erreur |
| `ui_lang.py` | changement de langue + couverture des traductions |
| `users.py` | comptes humains, création (`useradd -m`) et suppression (`userdel -r`) |
| `fedora.py` | version installée, noyau, `dnf check-update` |
| `logs.py` | journal |
| `about.py` | à propos, liens, crédits |

## Règle : pas de sous-classe de widget

Les pages sont des **fonctions** `build(win)` et les lignes réutilisables des
**fabriques** (`service_row(win, unit)`, `name_dialog(parent, titre, cb)`).
Depuis GTK 4.22 / PyGObject 3.54, de nombreux widgets Adwaita sont `final`
(`Adw.SwitchRow`, `Adw.PreferencesPage`) : en dériver une classe Python lève
`RuntimeError: could not create new GType`. `tools/check.py` (groupe `gtypes`)
refuse toute sous-classe de `Adw.*`/`Gtk.*` hors `Adw.Application`,
`Adw.ApplicationWindow` et `Adw.Window`.

## Ajouter une page

1. Créer `pages/ma_page.py` avec `build(win)`.
2. L'ajouter à `STATIC` (page fixe) ou à `SECTIONS` (section).
3. Si c'est une section, l'ajouter aussi à `ORDER` et, au besoin, à
   `SECTION_ICONS` dans `app.py`.
4. Ajouter les clés `section.<id>` et le texte de la page dans les 6 langues.
