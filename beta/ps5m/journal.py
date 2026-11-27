"""Journal de la bêta : écriture horodatée dans un fichier, sans GTK."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

APP_SLUG = "ps5m-beta"


def default_log_path() -> Path:
    state = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state) / APP_SLUG / "manager.log"


class Journal:
    """Journal texte : une ligne par événement, relu par la page « Journal »."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else default_log_path()
        self._lines: list[str] = []
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                self._lines = self.path.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines()[-2000:]
        except OSError:
            self.path = Path(os.devnull)

    def write(self, message: str) -> None:
        stamped = f"{datetime.now().strftime('%H:%M:%S')}  {message}"
        self._lines.append(stamped)
        try:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(stamped + "\n")
        except OSError:
            pass

    def lines(self) -> list[str]:
        return list(self._lines)

    def text(self) -> str:
        return "\n".join(self._lines)

    def clear(self) -> None:
        self._lines.clear()
        try:
            self.path.write_text("", encoding="utf-8")
        except OSError:
            pass
