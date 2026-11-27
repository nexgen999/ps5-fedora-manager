# `ps5m/app.py`

Fenêtre principale et orchestration. C'est le seul module qui connaît à la fois
les pages, le catalogue et le journal.

## Classes

### `BetaWindow`

| Élément | Rôle |
|---|---|
| `self.addons` | catalogue local, relu par `refresh_addons_state()` |
| `self.language` | code de la langue active |
| `self.journal` | `Journal` partagé par toute la session |
| `section_ids()` | sections affichées (page dédiée ou au moins un greffon) |
| `go_to(ident)` | ouvre une section depuis un lien interne |
| `set_language(code)` | change la langue, reconstruit la barre latérale |
| `show_install_confirm(addon, fn)` | dialogue Confirmer/Annuler |
| `run_task(title, task)` | tâche longue avec fenêtre de log |
| `run_background(task, done)` | action courte (interrupteur de service) |
| `refresh_addons()` | télécharge les greffons plus récents |

`task` a la forme `task(emit) -> (ok: bool, message: str)`. `emit` écrit dans le
journal et dans la fenêtre de log ; la tâche tourne dans un fil, l'interface ne
se bloque pas.

### `LogWindow`

Fenêtre modale avec un `Gtk.TextView` monospace. `emit(line)` ajoute une ligne et
fait défiler jusqu'en bas.

## Règles à respecter

- Ne jamais écrire de markup Pango avec du texte utilisateur : `&` casse le
  rendu (« FX Sound & Vidéo »). Utiliser `ui.plain_row`.
- Ne jamais bloquer le fil GTK : toute commande passe par `run_task` ou
  `run_background`.
- Toute nouvelle section doit être ajoutée à `pages.ORDER` et, si elle a une
  icône propre, à `SECTION_ICONS`.
