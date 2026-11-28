#!/usr/bin/env bash
# =============================================================================
#  Diagnostic du mode Gaming (Gamescope) - PS5 Fedora Manager
#
#  LECTURE SEULE : ce script ne modifie rien, il ne fait qu'afficher l'etat du
#  systeme (bureau, gestionnaire de connexion, sessions installees, fichiers du
#  mode Gaming, acces DRM, journaux). Aucun mot de passe, aucune donnee Steam.
#
#  Utilisation (root recommande : /var/log et /var/lib sont en 0700) :
#      cd /opt/ps5-manager
#      sudo bash tools/diagnostic_gaming.sh | tee ~/diagnostic-gaming.txt
#
#  Envoyer ensuite le fichier / le texte affiche : il contient ce qu'il faut
#  pour identifier la session de bureau et la cause du retour au bureau.
# =============================================================================
set -u

TARGET_USER="${SUDO_USER:-${USER:-$(id -un)}}"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --user)   TARGET_USER="${2:-}"; shift 2 || shift ;;
    --user=*) TARGET_USER="${1#*=}"; shift ;;
    *) shift ;;
  esac
done
if [ -z "${TARGET_USER:-}" ] || [ "$TARGET_USER" = "root" ]; then
  TARGET_USER="$(loginctl list-users --no-legend 2>/dev/null | awk '$2 != "root" {print $2; exit}')"
  [ -n "$TARGET_USER" ] || TARGET_USER="$(find /home -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | head -1)"
  [ -n "$TARGET_USER" ] || TARGET_USER="root"
fi
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
[ -n "${TARGET_HOME:-}" ] || TARGET_HOME="/home/$TARGET_USER"

section() { printf '\n===== %s =====\n' "$*"; }
cmd() { printf '\n$ %s\n' "$*"; bash -c "$*" 2>&1 || true; }
have() { command -v "$1" >/dev/null 2>&1 && echo "  oui : $1" || echo "  non : $1"; }

printf 'Diagnostic PS5 Fedora Manager - mode Gaming (Gamescope)\n'
printf 'Date : %s\nUtilisateur analyse : %s (uid %s)\n' \
  "$(date '+%F %T')" "$TARGET_USER" "$(id -u "$TARGET_USER" 2>/dev/null || echo '?')"

section "1. Systeme"
cmd 'grep -E "^(PRETTY_NAME|VERSION_ID)=" /etc/os-release'
cmd 'uname -srm'

section "2. Session graphique de $TARGET_USER"
cmd "loginctl list-sessions --no-legend"
for sid in $(loginctl list-sessions --no-legend 2>/dev/null | awk -v u="$TARGET_USER" '$3 == u {print $1}'); do
  cmd "loginctl show-session $sid -p Id -p Type -p Class -p Desktop -p Active -p Display -p TTY"
done
cmd "for p in /proc/[0-9]*; do [ -r \"\$p/environ\" ] || continue; [ \"\$(stat -c %U \"\$p\" 2>/dev/null)\" = \"$TARGET_USER\" ] || continue; tr '\\0' '\\n' < \"\$p/environ\" 2>/dev/null | grep -E '^(XDG_CURRENT_DESKTOP|XDG_SESSION_TYPE|XDG_SESSION_DESKTOP|DESKTOP_SESSION|WAYLAND_DISPLAY|DISPLAY)=' | sort -u && break; done"

section "3. Gestionnaire de connexion (display-manager.service)"
cmd "systemctl show -p Id --value display-manager.service"
for dm in gdm sddm lightdm; do
  printf '  %-8s actif=%s enabled=%s\n' "$dm" \
    "$(systemctl is-active "$dm.service" 2>/dev/null || true)" \
    "$(systemctl is-enabled "$dm.service" 2>/dev/null || true)"
done
cmd "readlink -f /etc/systemd/system/display-manager.service"

section "4. Sessions installees (wayland puis X11)"
cmd "ls -1 /usr/share/wayland-sessions 2>/dev/null"
cmd "ls -1 /usr/share/xsessions 2>/dev/null"
cmd "grep -H -E '^(Name|DesktopNames|Exec)=' /usr/share/wayland-sessions/*budgie* /usr/share/xsessions/*budgie* /usr/share/wayland-sessions/steam.desktop 2>/dev/null"

section "5. AccountsService (session enregistree pour $TARGET_USER)"
cmd "grep -n -E '^(Session|XSession)=' /var/lib/AccountsService/users/$TARGET_USER"

section "6. Auto-connexion - SDDM"
cmd "ls -1 /etc/sddm.conf.d 2>/dev/null"
cmd "grep -n . /etc/sddm.conf.d/zz-ps5-manager-autologin.conf 2>/dev/null"
cmd "grep -n -A5 '^\[Autologin\]' /etc/sddm.conf /etc/sddm.conf.d/*.conf 2>/dev/null"

section "7. Auto-connexion - LightDM"
cmd "grep -n 'autologin' /etc/lightdm/lightdm.conf /etc/lightdm/lightdm.conf.d/*.conf 2>/dev/null"

section "8. Auto-connexion - GDM"
cmd "grep -n -E 'AutomaticLogin|DefaultSession' /etc/gdm/custom.conf 2>/dev/null"

section "9. Fichiers du mode Gaming"
cmd "ls -l /usr/local/bin/switch-session /usr/bin/gamescope-session /usr/bin/steamos-session-select /usr/share/wayland-sessions/steam.desktop /etc/sudoers.d/ps5-session 2>&1"
cmd "grep -c resolve_desktop_session /usr/local/bin/switch-session 2>/dev/null"
cmd "grep -n -E 'DESKTOP_SESSION=|SESSION_CANDIDATES|candidats|for c in' /usr/local/bin/switch-session 2>/dev/null | head -20"
cmd "cat /usr/share/wayland-sessions/steam.desktop 2>/dev/null"

section "10. Outils (dont Steam en Flatpak)"
for t in gamescope steam mangoapp flatpak; do have "$t"; done
cmd "rpm -q gamescope steam steam-devices 2>&1 | head -5"
cmd "flatpak list --app --columns=application,version 2>/dev/null | grep -i steam"
cmd "gamescope --version 2>&1 | head -3"
cmd "ls -l /usr/bin/steam $TARGET_HOME/.local/share/Steam/ubuntu12_32/steam 2>&1 | head -5"

section "11. Groupes de $TARGET_USER et acces DRM"
cmd "id $TARGET_USER"
cmd "getent group video render"
cmd "ls -l /dev/dri 2>&1"

section "12. Journaux PS5 Fedora Manager"
for log in /var/log/ps5-manager/gaming-session.log "$TARGET_HOME/.cache/ps5-manager/gaming-session.log" \
           /var/log/ps5-manager/session-switch.log; do
  cmd "echo '--- $log'; tail -n 60 '$log' 2>/dev/null"
done

section "13. Journal systemd (gamescope / steam / gestionnaire de connexion)"
cmd "journalctl -b --no-pager 2>/dev/null | grep -iE 'gamescope|steamos|steam|sddm|lightdm|gdm' | tail -n 60"

section "14. Conclusion rapide"
if [ -f /usr/share/wayland-sessions/steam.desktop ]; then
  echo "  session Gaming installee : oui"
else
  echo "  session Gaming installee : NON (relancer 'Installer Gamescope')"
fi
for t in gamescope steam; do
  if command -v "$t" >/dev/null 2>&1; then
    echo "  $t : $(command -v "$t")"
  else
    echo "  $t : introuvable dans le PATH (Steam en Flatpak ? le script de session ne le trouve pas)"
  fi
done
if ! id -nG "$TARGET_USER" 2>/dev/null | tr ' ' '\n' | grep -qx render; then
  echo "  groupe render : ABSENT -> Gamescope ne peut pas ouvrir le GPU"
fi

printf "\nRien n'a ete modifie.\n"
