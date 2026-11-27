"""Page Dépôts : activer/couper un dépôt dnf, rafraîchir, ajouter un fichier .repo."""
from __future__ import annotations

import subprocess
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..i18n import tr  # noqa: E402
from ..runner import run_command  # noqa: E402
from ..ui import plain_row  # noqa: E402
from .addons import append_section_groups  # noqa: E402

REPO_DIR = Path("/etc/yum.repos.d")


def repositories() -> list[tuple[str, str, bool]]:
    """[(id, nom, activé)] depuis `dnf repolist --all`."""
    try:
        result = subprocess.run(
            ["dnf", "repolist", "--all", "--quiet"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    repos: list[tuple[str, str, bool]] = []
    for line in (result.stdout or "").splitlines():
        parts = line.split(None, 2)
        if len(parts) < 2 or parts[0].startswith("repo"):
            continue
        repo_id, name = parts[0], parts[1]
        status = parts[2].lower() if len(parts) > 2 else ""
        enabled = status.startswith("enabled") or status == ""
        if repo_id.endswith(".repo") or not repo_id:
            continue
        repos.append((repo_id, name, enabled))
    return repos


class ReposPage(Adw.PreferencesPage):
    def __init__(self, win) -> None:
        super().__init__()
        self.win = win
        self.group = Adw.PreferencesGroup(title=tr("repos.group"))
        self.add(self.group)

        actions = Adw.PreferencesGroup()
        refresh = plain_row(title=tr("repos.refresh"), subtitle="dnf makecache")
        refresh.set_activatable(True)
        refresh.connect("activated", lambda *_: self._refresh())
        actions.add(refresh)

        add = plain_row(title=tr("repos.add"), subtitle=f"{REPO_DIR}/*.repo")
        add.set_activatable(True)
        add.connect("activated", lambda *_: self._choose())
        actions.add(add)
        self.add(actions)

        self._fill()
        append_section_groups(self, win, "repos")

    def _fill(self) -> None:
        repos = repositories()
        if not repos:
            self.group.add(plain_row(title=tr("repos.empty")))
            return
        for repo_id, name, enabled in repos:
            row = Adw.SwitchRow()
            row.set_title(repo_id)
            row.set_subtitle(name)
            row.set_use_markup(False)
            row.set_active(enabled)
            row.connect("notify::active", self._on_toggle, repo_id)
            self.group.add(row)

    def _on_toggle(self, row, _pspec, repo_id: str) -> None:
        wanted = "1" if row.get_active() else "0"
        row.set_sensitive(False)

        def _task(emit) -> tuple[bool, str]:
            command = [
                "pkexec", "dnf", "config-manager",
                "setopt", f"{repo_id}.enabled={wanted}",
            ]
            emit(" ".join(command))
            code, out = run_command(command, timeout=120)
            if code != 0:
                emit(out)
                return False, tr("common.failed", code=code)
            return True, tr("common.done")

        self.win.run_background(_task, lambda ok, msg: row.set_sensitive(True))

    def _refresh(self) -> None:
        def _task(emit) -> tuple[bool, str]:
            emit("dnf makecache")
            code, out = run_command(
                ["pkexec", "dnf", "makecache"], timeout=300
            )
            if code != 0:
                emit(out)
                return False, tr("common.failed", code=code)
            return True, tr("common.done")

        self.win.run_task(tr("repos.refresh"), _task)

    def _choose(self) -> None:
        dialog = Gtk.FileChooserNative(
            title=tr("repos.add"),
            transient_for=self.win,
            action=Gtk.FileChooserAction.OPEN,
        )
        filter_repo = Gtk.FileFilter()
        filter_repo.set_name(".repo")
        filter_repo.add_pattern("*.repo")
        dialog.add_filter(filter_repo)

        def _on_response(native, response) -> None:
            if response != Gtk.ResponseType.ACCEPT:
                return
            selected = native.get_file()
            path = Path(selected.get_path() or "") if selected else None
            if path is None or not path.is_file():
                self.win.toast(tr("repos.failed"))
                return
            self._add(path)

        dialog.connect("response", _on_response)
        dialog.show()

    def _add(self, source: Path) -> None:
        def _task(emit) -> tuple[bool, str]:
            target = REPO_DIR / source.name
            emit(f"{source} → {target}")
            code, out = run_command(
                ["pkexec", "install", "-m", "0644", str(source), str(target)],
                timeout=60,
            )
            if code != 0:
                emit(out)
                return False, tr("common.failed", code=code)
            return True, tr("common.done")

        self.win.run_task(tr("repos.add"), _task)
