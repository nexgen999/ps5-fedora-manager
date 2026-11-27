#!/bin/bash
# =============================================================================
#  Gamescope + session Steam Big Picture  -  script externe PS5 Fedora Manager
#  Bureau : GNOME   (session gnome)
#
#  Utilisation (root) :
#      sudo bash gamescope_uninstall_gnome.sh
#      sudo bash gamescope_uninstall_gnome.sh --user <compte>
#      sudo bash gamescope_uninstall_gnome.sh --no-autologin      (session ajoutee, pas de bascule
#                                              automatique au demarrage)
#
#  Autonome : n'appelle aucun fichier de PS5 Fedora Manager, peut etre modifie
#  sans toucher au reste de l'application. Desinstallation :
#      sudo bash gamescope_uninstall_gnome.sh
# =============================================================================
set -u

DESKTOP_ID="gnome"
DESKTOP_LABEL="GNOME"
DESKTOP_SESSION_DEFAULT="gnome"
DESKTOP_SESSION_CANDIDATES="gnome gnome-xorg ubuntu"
DISPLAY_MANAGER_FALLBACK="gdm"
AUTOLOGIN=1
TARGET_USER=""

step() { printf '\n==> %s\n' "$*"; }
fail() { printf '  x %s\n' "$*" >&2; exit 1; }
warn() { printf '  ! %s\n' "$*" >&2; }

while [ "$#" -gt 0 ]; do
  case "$1" in
    --user)   [ "$#" -ge 2 ] || fail "--user attend un nom"; TARGET_USER="$2"; shift 2 ;;
    --user=*) TARGET_USER="${1#*=}"; shift ;;
    --no-autologin) AUTOLOGIN=0; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) fail "option inconnue : $1 (voir --help)" ;;
  esac
done

[ "$(id -u)" -eq 0 ] || fail "root requis : sudo bash $0"
if [ -z "$TARGET_USER" ]; then
  if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
    TARGET_USER="$SUDO_USER"
  elif [ -n "${PKEXEC_UID:-}" ]; then
    TARGET_USER="$(getent passwd "$PKEXEC_UID" | cut -d: -f1)"
  fi
fi
[ -n "$TARGET_USER" ] || fail "utilisateur cible inconnu : relance avec --user <compte>"
id "$TARGET_USER" >/dev/null 2>&1 || fail "utilisateur inconnu : $TARGET_USER"
TARGET_UID="$(id -u "$TARGET_USER")"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
[ -n "$TARGET_HOME" ] || TARGET_HOME="/home/$TARGET_USER"

# --- Detection du gestionnaire de connexion (gdm | sddm | lightdm) -----------
detect_dm() {
  local dm d
  dm="$(systemctl show -p Id --value display-manager.service 2>/dev/null | sed 's/\.service$//')"
  case "$dm" in
    gdm*)     printf 'gdm\n'; return 0 ;;
    sddm*)    printf 'sddm\n'; return 0 ;;
    lightdm*) printf 'lightdm\n'; return 0 ;;
  esac
  for d in gdm sddm lightdm; do
    if systemctl is-active --quiet "$d.service" 2>/dev/null; then printf '%s\n' "$d"; return 0; fi
  done
  for d in gdm sddm lightdm; do
    if systemctl is-enabled --quiet "$d.service" 2>/dev/null; then printf '%s\n' "$d"; return 0; fi
  done
  if [ -d /etc/sddm.conf.d ] || [ -f /etc/sddm.conf ]; then printf 'sddm\n'; return 0; fi
  if [ -d /etc/lightdm ]; then printf 'lightdm\n'; return 0; fi
  printf '%s\n' "$DISPLAY_MANAGER_FALLBACK"
}
DM="$(detect_dm)"

# --- Session de bureau installee --------------------------------------------
# Un nom de session absent de /usr/share/{xsessions,wayland-sessions} fait
# retomber le gestionnaire de connexion sur sa session par defaut : la console
# reste alors bloquee sur l'ecran de connexion au lieu de revenir au bureau.
session_installed() {
  [ -f "/usr/share/xsessions/$1.desktop" ] || [ -f "/usr/share/wayland-sessions/$1.desktop" ]
}
resolve_desktop_session() {
  local c saved
  for c in $DESKTOP_SESSION_CANDIDATES; do
    if session_installed "$c"; then printf '%s\n' "$c"; return 0; fi
  done
  saved="$(sed -n 's/^Session=//p' "/var/lib/AccountsService/users/$TARGET_USER" 2>/dev/null | head -n 1)"
  if [ -n "$saved" ] && [ "$saved" != "steam" ] && session_installed "$saved"; then
    printf '%s\n' "$saved"; return 0
  fi
  printf '%s\n' "$DESKTOP_SESSION_DEFAULT"
  return 1
}

# --- Auto-connexion du gestionnaire de connexion -----------------------------
write_autologin() {
  local session="$1" gdm lightdm
  case "$DM" in
    sddm)
      mkdir -p /etc/sddm.conf.d
      printf '[Autologin]\nUser=%s\nSession=%s\nRelogin=false\n' "$TARGET_USER" "$session" \
        > /etc/sddm.conf.d/zz-ps5-manager-autologin.conf
      chmod 644 /etc/sddm.conf.d/zz-ps5-manager-autologin.conf
      ;;
    lightdm)
      mkdir -p /etc/lightdm
      lightdm="/etc/lightdm/lightdm.conf"
      if [ -f "$lightdm" ]; then
        cp -f "$lightdm" "$lightdm.bak-ps5-manager"
      else
        printf '[Seat:*]\n' > "$lightdm"
      fi
      python3 - "$lightdm" "$TARGET_USER" "$session" <<'PY'
import io, re, sys
path, user, session = sys.argv[1], sys.argv[2], sys.argv[3]
lines = [l for l in io.open(path, encoding="utf-8").read().splitlines()
         if not re.match(r"\s*autologin-(user|session)\s*=", l)]
try:
    i = next(n for n, l in enumerate(lines) if l.strip() == "[Seat:*]")
except StopIteration:
    lines.insert(0, "[Seat:*]")
    i = 0
lines[i + 1:i + 1] = ["autologin-user=" + user, "autologin-session=" + session]
io.open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
PY
      ;;
    *)
      mkdir -p /etc/gdm
      gdm="/etc/gdm/custom.conf"
      if [ -f "$gdm" ]; then
        cp -f "$gdm" "$gdm.bak-ps5-manager"
      else
        printf '# GDM configuration storage\n\n[daemon]\n\n[security]\n\n[xdmcp]\n\n[chooser]\n\n[debug]\n#Enable=true\n' > "$gdm"
      fi
      python3 - "$gdm" "$TARGET_USER" <<'PY'
import io, re, sys
path, user = sys.argv[1], sys.argv[2]
lines = [l for l in io.open(path, encoding="utf-8").read().splitlines()
         if not re.match(r"\s*AutomaticLogin(Enable)?\s*=", l)]
try:
    i = next(n for n, l in enumerate(lines) if l.strip() == "[daemon]")
except StopIteration:
    lines.insert(0, "[daemon]")
    i = 0
lines[i + 1:i + 1] = ["AutomaticLoginEnable=True", "AutomaticLogin=" + user]
io.open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
PY
      ;;
  esac
}

step "Scripts de session Gamescope / Steam"
rm -f /usr/local/bin/switch-session /usr/bin/steamos-session-select \
      /usr/bin/gamescope-session /usr/bin/jupiter-biosupdate \
      /usr/bin/steamos-select-branch /usr/bin/steamos-update
rm -f /usr/bin/steamos-polkit-helpers/jupiter-biosupdate \
      /usr/bin/steamos-polkit-helpers/steamos-update \
      /usr/bin/steamos-polkit-helpers/steamos-set-timezone
rmdir /usr/bin/steamos-polkit-helpers 2>/dev/null || true
rm -f /usr/share/wayland-sessions/steam.desktop
rm -f /usr/share/pixmaps/ps5-gaming-mode.png \
      /usr/share/icons/hicolor/96x96/apps/ps5-gaming-mode.png
if command -v gtk-update-icon-cache >/dev/null; then
  gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi

step "Regle sudoers"
rm -f /etc/sudoers.d/ps5-session

step "Raccourcis"
rm -f "$TARGET_HOME/.local/share/applications/switch-session.desktop" \
      "$TARGET_HOME/Bureau/switch-session.desktop" \
      "$TARGET_HOME/Desktop/switch-session.desktop" \
      "$TARGET_HOME/.local/share/applications/mode-gaming.desktop"
rm -f "$TARGET_HOME/.cache/ps5-manager/next-session"
if command -v update-desktop-database >/dev/null; then
  update-desktop-database "$TARGET_HOME/.local/share/applications" >/dev/null 2>&1 || true
fi

step "Session GNOME par defaut"
if [ -n "$TARGET_UID" ] && command -v busctl >/dev/null 2>&1; then
  busctl call org.freedesktop.Accounts /org/freedesktop/Accounts/User"$TARGET_UID" \
    org.freedesktop.Accounts.User SetSession s "gnome" >/dev/null 2>&1 || true
fi
AS="/var/lib/AccountsService/users/$TARGET_USER"
if [ -f "$AS" ]; then
  sed -i 's/^Session=.*/Session=gnome/' "$AS"
  grep -q '^Session=' "$AS" || sed -i '1i Session=gnome' "$AS"
fi

step "Gestionnaire de connexion : retrait de l'auto-connexion"
rm -f /etc/sddm.conf.d/zz-ps5-manager-autologin.conf
if [ -f /etc/gdm/custom.conf ]; then
  cp -f /etc/gdm/custom.conf /etc/gdm/custom.conf.ps5-manager-uninstall.bak 2>/dev/null || true
  sed -i '/^AutomaticLoginEnable=/d;/^AutomaticLogin=/d' /etc/gdm/custom.conf
fi
if [ -f /etc/lightdm/lightdm.conf ]; then
  cp -f /etc/lightdm/lightdm.conf /etc/lightdm/lightdm.conf.ps5-manager-uninstall.bak 2>/dev/null || true
  sed -i '/^[[:space:]]*autologin-user[[:space:]]*=/d;/^[[:space:]]*autologin-session[[:space:]]*=/d' /etc/lightdm/lightdm.conf
fi
rm -rf /tmp/gamescope-guide

printf '\nDesinstallation terminee : la session GNOME (gnome) redevient celle par defaut.\n'
printf 'Redemarre la console (ou relance le gestionnaire de connexion) pour revenir au bureau.\n'
