# Coverage of 0.15.11

Status: **every option of the stable release has an equivalent in the beta**.

Measured by `tools/compare_stable.py`: static reading of `ps5_manager.py`
(149 options across 24 sections, `DEV_CATALOG` / `WEB_CATALOG` included) then
matched against the **107 addons** and the dedicated pages.
Full per-option tables: [comparison-0.15.11.md](comparison-0.15.11.md).

| Metric | Value |
|---|---|
| options read from the stable | 149 |
| beta addons | 107 |
| dedicated pages | 10 (journal, about, easy setup, applications, services, language, accounts, Fedora release, kernels, repositories) |
| stable packages without an addon | 1 (`xhost`, unnecessary here) |

## The only package not installed

`xhost` let root display the GTK interface when the stable elevated the whole
app. The beta never elevates the interface: it calls `pkexec` only for a
`root: yes` addon script. Root's X11 authorisation has no use.

## Notable equivalences

| Stable option | Beta equivalent |
|---|---|
| accounts: list, add, delete | Users page (`useradd -m`, `userdel -r`, `passwd` in a terminal, primary account protected) |
| kernels: pick, boot into, remove | Kernel page (`grubby --set-default`, `dnf remove kernel-core-<v>`, confirmation) |
| repositories: list, enable/disable, add, refresh | Repositories page (`dnf config-manager setopt`, `dnf makecache`, `.repo` import) |
| AppImage: install, list, uninstall | Applications page (copy to `~/Applications`, menu entry, removal) |
| easy setup: profiles | Easy setup page: recommended, gaming, streaming, office + cleanup |
| maintenance: 10 actions | 11 action addons (`maint-*`) |
| AI: Open WebUI, start/stop, logs, diagnostics | 8 `ai-*` addons |
| printers, phone sharing | `feature-print*`, `feature-mobile` |
| gaming: uninstall, log | `gaming-uninstall`, `gaming-log` |
| Steam repair | `fix-steam` |
| repositories: OpenH264, refresh | `repos-openh264`, `repos-refresh` |
| system: update, uninstall the manager | `update-system`, `update-beta`, `update-uninstall` |
| languages: install all | `lang-all` |

## Deliberate differences

- **Root model**: the stable elevates the whole app; the beta stays as the user
  and elevates one addon at a time (`pkexec`). Safer, and it is why `xhost` is
  unnecessary.
- **Account removal**: `userdel -r` is offered, but uid 1000 is refused so the
  session cannot be broken.
- **Kernels**: removal is offered one kernel at a time with confirmation; the
  running kernel is never cleaned automatically.
- **Action addons**: stateless operations (cleanup, restart, diagnostics) show
  no badge and ask for confirmation.

## What a development machine cannot prove

- GTK4/Libadwaita rendering and polkit dialogs are validated on the PS5
  (`python3 beta/run.py`), not here.
- es/it/de/pt translations deserve a native review.
