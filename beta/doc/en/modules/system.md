# `ps5m/system.py`

Read-only system state, no GTK and no root.

| Function | Role |
|---|---|
| `rpm_present(packages)` | `{package: bool}` with a single `rpm -q --qf` call |
| `expand_path(pattern)` | `~`, `$HOME`, `/home/*/x` → existing paths |
| `path_present(patterns)` | `{pattern: bool}` |
| `home()` | home directory |

`rpm_present` is architecture-aware: asking for
`mesa-va-drivers-freeworld` also matches `mesa-va-drivers-freeworld.x86_64`,
while `package.i686` does not match the 64-bit build.

Nothing raises: without `rpm` everything is simply considered missing and the
badge shows `○`.
