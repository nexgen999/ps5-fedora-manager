"""Catalogue des greffons (.sh) : métadonnées, versions et mises à jour.

Chaque option de l'application est un script autonome dans `addons/`. Son
en-tête `#@ clé: valeur` porte son identifiant, sa version, ses paquets et ses
dépendances ; `index.json` est le catalogue lisible par l'application, régénéré
par `tools/build_catalog.py`.

Mettre à jour une commande = modifier le script, incrémenter `#@ version:`,
relancer `tools/build_catalog.py`. L'application télécharge alors uniquement les
scripts dont la version a changé (`refresh()`), sans toucher aux autres.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ADDONS_DIR = Path(__file__).resolve().parent.parent / "addons"
INDEX_NAME = "index.json"
SCHEMA = 1
REMOTE_BASE = (
    "https://raw.githubusercontent.com/nexgen999/ps5-fedora-manager/main/beta/addons"
)
HEADER_LIMIT = 60  # lignes lues en tête de script


class CatalogError(RuntimeError):
    """Catalogue illisible ou téléchargement impossible."""


def version_key(version: str) -> tuple[int, ...]:
    """« 1.10.2 » → (1, 10, 2) pour comparer les versions sans dépendance."""
    parts: list[int] = []
    for chunk in str(version).replace("-", ".").split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _split(value: str) -> tuple[str, ...]:
    return tuple(part for part in value.replace(",", " ").split() if part)


@dataclass(frozen=True)
class Addon:
    """Une option installable, décrite par son script."""

    id: str
    version: str = "0.0.0"
    file: str = ""
    section: str = "deps"
    icon: str = "application-x-executable-symbolic"
    titles: dict[str, str] = field(default_factory=dict)
    descriptions: dict[str, str] = field(default_factory=dict)
    packages: tuple[str, ...] = ()
    needs: tuple[str, ...] = ()
    check_paths: tuple[str, ...] = ()
    action: bool = False
    root: bool = True
    sha256: str = ""
    path: Path | None = None

    # ---- texte ----
    def title(self, lang: str = "en") -> str:
        return (
            self.titles.get(lang)
            or self.titles.get("en")
            or self.titles.get("fr")
            or self.id
        )

    def description(self, lang: str = "en") -> str:
        return (
            self.descriptions.get(lang)
            or self.descriptions.get("en")
            or self.descriptions.get("fr")
            or ""
        )

    # ---- sérialisation ----
    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "version": self.version,
            "file": self.file,
            "section": self.section,
            "icon": self.icon,
            "titles": self.titles,
            "descriptions": self.descriptions,
            "packages": list(self.packages),
            "needs": list(self.needs),
            "check_paths": list(self.check_paths),
            "action": self.action,
            "root": self.root,
        }
        if self.sha256:
            data["sha256"] = self.sha256
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Addon":
        return cls(
            id=str(data["id"]),
            version=str(data.get("version", "0.0.0")),
            file=str(data.get("file", f"{data['id']}.sh")),
            section=str(data.get("section", "deps")),
            icon=str(data.get("icon", "application-x-executable-symbolic")),
            titles={str(k): str(v) for k, v in (data.get("titles") or {}).items()},
            descriptions={
                str(k): str(v) for k, v in (data.get("descriptions") or {}).items()
            },
            packages=tuple(data.get("packages") or ()),
            needs=tuple(data.get("needs") or ()),
            check_paths=tuple(data.get("check_paths") or ()),
            action=bool(data.get("action", False)),
            root=bool(data.get("root", True)),
            sha256=str(data.get("sha256", "")),
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def parse_script(path: Path) -> Addon:
    """Lit l'en-tête `#@ clé: valeur` d'un script et en fait un `Addon`."""
    meta: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise CatalogError(f"{path.name} : {exc}") from exc
    for line in lines[:HEADER_LIMIT]:
        stripped = line.strip()
        if not stripped.startswith("#@"):
            continue
        key, _, value = stripped[2:].partition(":")
        meta[key.strip().lower()] = value.strip()
    if not meta.get("id"):
        raise CatalogError(f"{path.name} : en-tête « #@ id: » manquant")

    titles: dict[str, str] = {}
    descriptions: dict[str, str] = {}
    for key, value in meta.items():
        if key.startswith("title_"):
            titles[key[6:]] = value
        elif key.startswith("desc_"):
            descriptions[key[5:]] = value
    if meta.get("title"):
        titles.setdefault("en", meta["title"])
    if meta.get("desc"):
        descriptions.setdefault("en", meta["desc"])

    return Addon(
        id=meta["id"],
        version=meta.get("version", "0.0.0"),
        file=path.name,
        section=meta.get("section", "deps"),
        icon=meta.get("icon", "application-x-executable-symbolic"),
        titles=titles,
        descriptions=descriptions,
        packages=_split(meta.get("packages", "")),
        needs=_split(meta.get("needs", "")),
        check_paths=_split(meta.get("check_paths", "")),
        action=meta.get("action", "no").lower() in ("yes", "true", "1"),
        root=meta.get("root", "yes").lower() not in ("no", "false", "0"),
        sha256=_sha256(path),
        path=path,
    )


def load_local(directory: Path = ADDONS_DIR) -> dict[str, Addon]:
    """Tous les scripts présents localement, triés par identifiant."""
    addons: dict[str, Addon] = {}
    for script in sorted(directory.glob("*.sh")):
        addon = parse_script(script)
        addons[addon.id] = addon
    return addons


def build_index(directory: Path = ADDONS_DIR) -> dict[str, Any]:
    """Catalogue complet, à écrire dans `index.json`."""
    return {
        "schema": SCHEMA,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "addons": [a.to_dict() for a in load_local(directory).values()],
    }


def write_index(directory: Path = ADDONS_DIR) -> Path:
    path = directory / INDEX_NAME
    payload = json.dumps(build_index(directory), ensure_ascii=False, indent=2)
    path.write_text(payload + "\n", encoding="utf-8")
    return path


def read_index(path: Path) -> dict[str, Addon]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CatalogError(f"{path.name} : {exc}") from exc
    if int(data.get("schema", 0)) > SCHEMA:
        raise CatalogError(f"{path.name} : schéma {data.get('schema')} plus récent")
    return {
        str(item["id"]): Addon.from_dict(item)
        for item in data.get("addons", [])
        if isinstance(item, dict) and item.get("id")
    }


def fetch_index(base_url: str = REMOTE_BASE, timeout: float = 8.0) -> dict[str, Addon]:
    """Télécharge `index.json` du dépôt (aucune écriture locale)."""
    url = f"{base_url.rstrip('/')}/{INDEX_NAME}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise CatalogError(f"catalogue distant indisponible : {exc}") from exc
    if int(data.get("schema", 0)) > SCHEMA:
        raise CatalogError("le catalogue distant demande une version plus récente")
    return {
        str(item["id"]): Addon.from_dict(item)
        for item in data.get("addons", [])
        if isinstance(item, dict) and item.get("id")
    }


def pending(
    local: dict[str, Addon], remote: dict[str, Addon]
) -> tuple[list[Addon], list[str]]:
    """(scripts à télécharger, identifiants disparus du dépôt)."""
    outdated = [
        addon
        for key, addon in remote.items()
        if key not in local or version_key(addon.version) > version_key(local[key].version)
    ]
    removed = sorted(set(local) - set(remote))
    return outdated, removed


def refresh(
    directory: Path = ADDONS_DIR,
    base_url: str = REMOTE_BASE,
    timeout: float = 8.0,
) -> dict[str, Any]:
    """Met à jour les scripts modifiés depuis le dépôt GitHub.

    Ne touche jamais un script déjà à jour, vérifie le SHA-256 annoncé et écrit
    de façon atomique (fichier temporaire puis remplacement).
    """
    local = load_local(directory)
    remote = fetch_index(base_url, timeout)
    outdated, removed = pending(local, remote)
    updated: list[str] = []
    failed: dict[str, str] = {}
    for addon in outdated:
        url = f"{base_url.rstrip('/')}/{addon.file}"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
                payload = response.read()
        except (OSError, urllib.error.URLError) as exc:
            failed[addon.id] = str(exc)
            continue
        if addon.sha256 and hashlib.sha256(payload).hexdigest() != addon.sha256:
            failed[addon.id] = "empreinte SHA-256 différente"
            continue
        target = directory / addon.file
        tmp = target.with_suffix(".sh.tmp")
        tmp.write_bytes(payload)
        tmp.chmod(0o755)
        tmp.replace(target)
        updated.append(addon.id)
    return {
        "updated": updated,
        "failed": failed,
        "removed": removed,
        "checked": len(remote),
    }


def order(addons: Iterable[Addon]) -> list[Addon]:
    """Trie les greffons pour que chaque `needs` passe avant ses dépendants."""
    remaining = {a.id: a for a in addons}
    ordered: list[Addon] = []
    while remaining:
        ready = [
            a for a in remaining.values() if not (set(a.needs) & set(remaining))
        ]
        if not ready:  # cycle : on garde l'ordre alphabétique
            ready = [remaining[sorted(remaining)[0]]]
        for addon in sorted(ready, key=lambda a: a.id):
            ordered.append(addon)
            remaining.pop(addon.id, None)
    return ordered
