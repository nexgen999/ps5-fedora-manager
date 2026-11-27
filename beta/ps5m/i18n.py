"""Paquets de langue : une langue = un fichier JSON dans `langs/`.

Ajouter une langue = déposer `langs/xx.json` (copie de `en.json` traduite).
Aucun code à modifier : `available()` liste les fichiers présents, `tools/lang_status.py`
indique les clés encore manquantes. Une clé absente retombe sur l'anglais.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LANG_DIR = Path(__file__).resolve().parent.parent / "langs"
FALLBACK = "en"

_state: dict[str, Any] = {"code": FALLBACK, "table": {}, "fallback": {}}


class LanguageError(RuntimeError):
    """Fichier de langue illisible ou inutilisable."""


def _read(code: str) -> dict[str, Any]:
    path = LANG_DIR / f"{code}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LanguageError(f"{path.name} : {exc}") from exc
    if not isinstance(data, dict):
        raise LanguageError(f"{path.name} : un objet JSON est attendu")
    return data


def codes() -> list[str]:
    """Codes présents dans `langs/`, anglais d'abord."""
    found = sorted(p.stem for p in LANG_DIR.glob("*.json") if not p.stem.startswith("_"))
    return [FALLBACK] + [c for c in found if c != FALLBACK]


def available() -> list[dict[str, str]]:
    """Langues proposées dans l'interface, avec leur nom natif."""
    out: list[dict[str, str]] = []
    for code in codes():
        meta: dict[str, Any] = {}
        try:
            meta = _read(code).get("_meta", {}) or {}
        except LanguageError:
            continue
        out.append(
            {
                "code": code,
                "name": str(meta.get("name", code)),
                "english": str(meta.get("english", code)),
                "direction": str(meta.get("direction", "ltr")),
            }
        )
    return out


def load(code: str) -> None:
    """Active une langue (repli anglais si le fichier n'existe pas)."""
    fallback = _read(FALLBACK)
    try:
        table = _read(code)
    except LanguageError:
        code, table = FALLBACK, fallback
    table = {k: v for k, v in table.items() if not k.startswith("_")}
    _state.update({"code": code, "table": table, "fallback": fallback})


def current() -> str:
    return str(_state["code"])


def direction() -> str:
    try:
        return str((_read(current()).get("_meta") or {}).get("direction", "ltr"))
    except LanguageError:
        return "ltr"


def tr(key: str, **fmt: Any) -> str:
    """Traduit `key` ; repli anglais puis clé brute. `{placeholders}` formatés."""
    if not _state["table"]:
        load(FALLBACK)
    text = _state["table"].get(key) or _state["fallback"].get(key) or key
    if not isinstance(text, str):
        return key
    if fmt:
        try:
            return text.format(**fmt)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def coverage(code: str) -> tuple[int, int, list[str]]:
    """(traduites, total, clés absentes) par rapport à l'anglais."""
    try:
        reference = {k for k in _read(FALLBACK) if not k.startswith("_")}
        table = _read(code)
    except LanguageError:
        return 0, 0, []
    translated = {k for k, v in table.items() if not k.startswith("_") and str(v).strip()}
    missing = sorted(reference - translated)
    return len(reference) - len(missing), len(reference), missing
