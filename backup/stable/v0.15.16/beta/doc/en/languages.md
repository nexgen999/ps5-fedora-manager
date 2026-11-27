# Languages

## Principle

The interface has no hard-coded strings: everything goes through
`i18n.tr("key")`. Translations live in `beta/langs/*.json`, one file per
language.

Shipped: `fr`, `en`, `es`, `it`, `de`, `pt` — 81 keys each.

## Adding a language

```bash
cp beta/langs/en.json beta/langs/ja.json
python3 beta/tools/lang_status.py --missing ja   # keys to translate
```

Fill in `_meta`:

```json
"_meta": {"name": "日本語", "english": "Japanese", "direction": "ltr"}
```

`direction` is `ltr` or `rtl`, read by `i18n.direction()`.

The language then appears in the selector and on the "Language & keyboard"
page, with no restart.

## Check

```bash
python3 beta/tools/lang_status.py     # coverage of all languages
python3 beta/tools/check.py           # all languages share the same keys
```

A missing key is not fatal: `tr()` falls back to English.

## System languages

The `lang` section installs `langpacks-*` packages (fr, es, de, it, pt, ja).
These are two different things: the interface (JSON) and system/application
translations (RPM).
