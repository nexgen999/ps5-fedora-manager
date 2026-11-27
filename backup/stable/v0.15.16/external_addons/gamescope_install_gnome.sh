#!/bin/bash
# =============================================================================
#  Gamescope + session Steam Big Picture  -  script externe PS5 Fedora Manager
#  Bureau : GNOME   (session gnome)
#
#  Utilisation (root) :
#      sudo bash gamescope_install_gnome.sh
#      sudo bash gamescope_install_gnome.sh --user <compte>
#      sudo bash gamescope_install_gnome.sh --no-autologin      (session ajoutee, pas de bascule
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

step "Bureau : $DESKTOP_LABEL (session $DESKTOP_SESSION_DEFAULT) - gestionnaire $DM"
command -v dnf >/dev/null 2>&1 || fail "dnf requis (Fedora)"
command -v loginctl >/dev/null 2>&1 || fail "loginctl requis (systemd)"
command -v python3 >/dev/null 2>&1 || fail "python3 requis"
if ! session_installed "$DESKTOP_SESSION_DEFAULT"; then
  warn "session $DESKTOP_SESSION_DEFAULT absente de /usr/share/{xsessions,wayland-sessions}"
  warn "le paquet du bureau GNOME semble incomplet : le retour au bureau echouera"
fi
command -v gnome-shell >/dev/null 2>&1 || warn "gnome-shell absent : GNOME ne semble pas installe"


step "Dependances : Gamescope et acces DRM"
if ! command -v gamescope >/dev/null 2>&1; then
  dnf install -y gamescope >/dev/null || fail "installation de gamescope impossible"
fi
command -v gamescope >/dev/null 2>&1 || fail "gamescope introuvable apres installation"
# Gamescope ouvre /dev/dri/card* : sans les groupes video/render il echoue.
for g in video render; do
  if getent group "$g" >/dev/null 2>&1; then
    usermod -aG "$g" "$TARGET_USER" >/dev/null 2>&1 || warn "ajout au groupe $g impossible"
  fi
done
if ! command -v steam >/dev/null 2>&1; then
  warn "Steam n'est pas installe : le mode Gaming restera sur un ecran noir."
  warn "Installe Steam avant de redemarrer sur la session Steam."
fi

step "Journaux"
mkdir -p /var/log/ps5-manager
for f in gaming-session.log session-switch.log; do
  touch "/var/log/ps5-manager/$f" 2>/dev/null || true
  chmod 666 "/var/log/ps5-manager/$f" 2>/dev/null || true
done
if [ ! -f "/var/log/ps5-manager/gaming-session.log" ]; then
  warn "/var/log/ps5-manager non inscriptible : les journaux iront dans ~/.cache/ps5-manager"
fi

step "Session Steam pour $TARGET_USER (AccountsService)"
DESKTOP_SESSION="$(resolve_desktop_session)" || \
  warn "session de bureau introuvable : on garde $DESKTOP_SESSION_DEFAULT"
printf '  session de bureau : %s\n' "$DESKTOP_SESSION"
AS="/var/lib/AccountsService/users/$TARGET_USER"
mkdir -p "$(dirname "$AS")"
if [ -f "$AS" ]; then
  sed -i 's/^Session=.*/Session=steam/' "$AS"
  grep -q '^Session=' "$AS" || sed -i '1i Session=steam' "$AS"
else
  printf '[User]\nSession=steam\n' > "$AS"
fi
passwd -u "$TARGET_USER" >/dev/null 2>&1 || true

if [ "$AUTOLOGIN" -eq 1 ]; then
  step "Auto-connexion $DM sur la session Steam"
  write_autologin steam
else
  step "Auto-connexion : desactivee (--no-autologin)"
fi

step "Facteur d'echelle de l'ecran de connexion"
if [ "$DM" = "gdm" ]; then
  mkdir -p /etc/dconf/profile /etc/dconf/db/gdm.d
  printf 'user-db:user\nsystem-db:gdm\n' > /etc/dconf/profile/gdm
  printf '[org/gnome/desktop/interface]\ntext-scaling-factor=1.5\n' > /etc/dconf/db/gdm.d/00-scaling
  dconf update >/dev/null 2>&1 || true
  printf '  GDM : facteur 1.5 applique\n'
else
  printf '  non modifie (%s)\n' "$DM"
fi

step "Outils du guide steam-using-gamescope-guide"
if command -v git >/dev/null 2>&1; then
  rm -rf /tmp/gamescope-guide
  if git clone --depth 1 https://github.com/shahnawazshahin/steam-using-gamescope-guide.git /tmp/gamescope-guide >/dev/null 2>&1; then
    ( cd /tmp/gamescope-guide && bash ./installer.sh ) >/dev/null 2>&1 \
      || warn "installer.sh du guide a echoue : les outils SteamOS sont ignores"
  else
    warn "guide shahnawazshahin inaccessible : les outils SteamOS sont ignores"
  fi
else
  warn "git absent : les outils SteamOS du guide sont ignores"
fi

step "/usr/bin/gamescope-session"
cat > /usr/bin/gamescope-session <<'SH'
#!/bin/bash
# Session Gaming (Gamescope + Steam Big Picture) - PS5 Fedora Manager
# Fermer Steam ramene au bureau : la session n'est plus relancee en boucle.
LOG="/var/log/ps5-manager/gaming-session.log"
if ! { mkdir -p "$(dirname "$LOG")" 2>/dev/null && : >>"$LOG" 2>/dev/null; }; then
  LOG="$HOME/.cache/ps5-manager/gaming-session.log"
  mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
  : >>"$LOG" 2>/dev/null || true
fi
exec >>"$LOG" 2>&1
printf '\n=== %s : session Gaming (%s) ===\n' "$(date '+%F %T')" "GNOME"
printf 'utilisateur %s, groupes : %s\n' "$(id -un)" "$(id -nG)"

NEXT="$HOME/.cache/ps5-manager/next-session"
mkdir -p "$(dirname "$NEXT")" 2>/dev/null || true
rm -f "$NEXT"

switch_to() {
  if [ "$(id -u)" -eq 0 ]; then
    /usr/local/bin/switch-session "$1" || true
  else
    sudo -n /usr/local/bin/switch-session "$1" || true
  fi
}

if ! command -v gamescope >/dev/null 2>&1; then
  echo "gamescope introuvable : retour au bureau"
  switch_to desktop
  exit 1
fi
if ! command -v steam >/dev/null 2>&1; then
  echo "steam introuvable : retour au bureau"
  switch_to desktop
  exit 1
fi
if [ ! -r /dev/dri/card0 ] && [ ! -r /dev/dri/card1 ]; then
  echo "aucun /dev/dri/card* lisible : groupes actuels $(id -nG)"
  echo "ajoute l'utilisateur aux groupes video et render puis redemarre"
fi

# Pas de composition imbriquee : Gamescope pilote directement le DRM.
unset WAYLAND_DISPLAY WAYLAND_SOCKET DISPLAY
export XDG_SESSION_TYPE=wayland
export GAMESCOPE_MODE_SAVE_FILE="$HOME/.config/gamescope/modes.cfg"
mkdir -p "$HOME/.config/gamescope" 2>/dev/null || true

FLAGS=()
if command -v mangoapp >/dev/null 2>&1; then
  FLAGS=(--mangoapp)
else
  echo "mangoapp absent : lancement sans --mangoapp"
fi

gamescope "${FLAGS[@]}" -e -- steam -steamdeck -steamos3
RC=$?
echo "gamescope termine (code $RC)"

REQUEST=""
if [ -f "$NEXT" ]; then
  REQUEST=$(head -n 1 "$NEXT" 2>/dev/null || true)
  rm -f "$NEXT"
fi
if [ "$REQUEST" = "steam" ]; then
  echo "mode Gaming redemande : relance de Gamescope"
  exec /usr/bin/gamescope-session
fi
echo "retour au bureau (GNOME)"
switch_to desktop
exit 0
SH
chmod 755 /usr/bin/gamescope-session

step "/usr/bin/steamos-session-select"
cat > /usr/bin/steamos-session-select <<'SH'
#!/bin/bash
# Appele par Steam (mode Gaming) : choisit la session suivante puis ferme Steam.
NEXT="$HOME/.cache/ps5-manager/next-session"
mkdir -p "$(dirname "$NEXT")" 2>/dev/null || true
case "${1:-desktop}" in
  steam|gamescope|game|gaming) printf 'steam\n' >"$NEXT" ;;
  *) printf 'desktop\n' >"$NEXT" ;;
esac
if command -v steam >/dev/null 2>&1; then
  timeout 10 steam -shutdown >/dev/null 2>&1 || true
fi
exit 0
SH
chmod 755 /usr/bin/steamos-session-select

step "/usr/share/wayland-sessions/steam.desktop"
mkdir -p /usr/share/wayland-sessions
cat > /usr/share/wayland-sessions/steam.desktop <<'DESK'
[Desktop Entry]
Encoding=UTF-8
Name=Steam (Gamescope)
Comment=Run Steam directly in Gamescope
Exec=gamescope-session
Type=Application
Icon=ps5-gaming-mode
DesktopNames=gamescope
DESK
chmod 644 /usr/share/wayland-sessions/steam.desktop

step "Icone de la session Gaming"
ICON_PNG="/usr/share/pixmaps/ps5-gaming-mode.png"
mkdir -p /usr/share/pixmaps /usr/share/icons/hicolor/96x96/apps
base64 -d > "$ICON_PNG" <<'B64'
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
PeX/AaPFWVg+mEd9AAAAAElFTkSuQmCC
B64
install -m 0644 "$ICON_PNG" /usr/share/icons/hicolor/96x96/apps/ps5-gaming-mode.png
if command -v gtk-update-icon-cache >/dev/null; then
  gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi

step "sudoers : bascule de session sans mot de passe"
mkdir -p /etc/sudoers.d
printf '%s ALL=(ALL) NOPASSWD: /usr/local/bin/switch-session, /usr/bin/steamos-session-select, /usr/bin/systemd-run *\n' "$TARGET_USER" \
  > /etc/sudoers.d/ps5-session
chmod 440 /etc/sudoers.d/ps5-session
if command -v visudo >/dev/null; then
  visudo -c -f /etc/sudoers.d/ps5-session >/dev/null || fail "regle sudoers invalide"
fi

step "/usr/local/bin/switch-session"
cat > /usr/local/bin/switch-session <<'SH'
#!/bin/bash
# Bascule de session PS5 Fedora Manager (GNOME).
#   switch-session            bascule bureau <-> Gaming
#   switch-session desktop    revient au bureau (GNOME)
#   switch-session steam      demarre la session Gaming (Gamescope)
# La bascule est deleguee au gestionnaire systeme : elle survit a la fermeture
# de la session en cours.
set -u
SELF="/usr/local/bin/switch-session"
U="@@USER@@"
DESKTOP_SESSION_DEFAULT="gnome"
DESKTOP_SESSION_CANDIDATES="gnome gnome-xorg ubuntu"
DM_FALLBACK="gdm"
LOG="/var/log/ps5-manager/session-switch.log"
USER_ID=$(id -u "$U" 2>/dev/null || true)

log() {
  printf '%s %s\n' "$(date '+%F %T')" "$*" >>"$LOG" 2>/dev/null || \
    printf '%s %s\n' "$(date '+%F %T')" "$*" >&2
}

if [ "${1:-}" != "apply" ]; then
  ARGS="${1:-}"
  if [ "$(id -u)" -eq 0 ]; then
    if [ -n "$ARGS" ]; then
      exec systemd-run --quiet --collect "$SELF" apply "$ARGS"
    fi
    exec systemd-run --quiet --collect "$SELF" apply
  fi
  if [ -n "$ARGS" ]; then
    exec sudo -n systemd-run --quiet --collect "$SELF" apply "$ARGS"
  fi
  exec sudo -n systemd-run --quiet --collect "$SELF" apply
fi
shift

[ "$(id -u)" -eq 0 ] || { echo "root requis" >&2; exit 1; }
[ -n "$USER_ID" ] || { echo "utilisateur inconnu : $U" >&2; exit 1; }

session_installed() {
  [ -f "/usr/share/xsessions/$1.desktop" ] || [ -f "/usr/share/wayland-sessions/$1.desktop" ]
}

# Nom de session reellement installe : un Session= inconnu laisse le
# gestionnaire de connexion sur sa session par defaut (ecran de connexion ou
# session en boucle), c'est ce qui bloquait la sortie du mode Gaming.
resolve_desktop_session() {
  local c saved
  for c in $DESKTOP_SESSION_CANDIDATES; do
    if session_installed "$c"; then printf '%s\n' "$c"; return 0; fi
  done
  saved=$(sed -n 's/^Session=//p' "/var/lib/AccountsService/users/$U" 2>/dev/null | head -n 1)
  if [ -n "$saved" ] && [ "$saved" != "steam" ] && session_installed "$saved"; then
    printf '%s\n' "$saved"; return 0
  fi
  return 1
}
DESKTOP_SESSION="$(resolve_desktop_session)" || DESKTOP_SESSION=""

# Gestionnaire de connexion reellement utilise par systemd
DM=$(systemctl show -p Id --value display-manager.service 2>/dev/null | sed 's/\.service$//')
case "$DM" in
  gdm*|sddm*|lightdm*) ;;
  *)
    DM=""
    for d in gdm sddm lightdm; do
      if systemctl is-active --quiet "$d.service" 2>/dev/null; then DM="$d"; break; fi
    done
    [ -n "$DM" ] || DM="$DM_FALLBACK"
    ;;
esac

CURRENT=$(busctl get-property org.freedesktop.Accounts \
  /org/freedesktop/Accounts/User"$USER_ID" \
  org.freedesktop.Accounts.User Session 2>/dev/null | awk -F'"' '{print $2}')

TARGET="${1:-}"
case "$TARGET" in
  desktop|"$DESKTOP_SESSION") TARGET="desktop" ;;
  steam|gamescope|game|gaming) TARGET="steam" ;;
  "")
    if [ "$CURRENT" = "steam" ]; then TARGET="desktop"; else TARGET="steam"; fi
    ;;
  *) echo "session inconnue : $TARGET" >&2; exit 2 ;;
esac

if [ "$TARGET" = "desktop" ]; then
  if [ -z "$DESKTOP_SESSION" ]; then
    log "session GNOME introuvable (aucune de : $DESKTOP_SESSION_CANDIDATES) : bascule annulee"
    echo "session GNOME introuvable : rien n'a ete modifie" >&2
    exit 3
  fi
  NEXT_SESSION="$DESKTOP_SESSION"
else
  NEXT_SESSION="steam"
fi
log "bascule demandee : ${1:-auto} -> $NEXT_SESSION (actuelle : ${CURRENT:-?}, bureau : ${DESKTOP_SESSION:-?}, gestionnaire : $DM)"

# 1. AccountsService : session que le gestionnaire de connexion doit demarrer
busctl call org.freedesktop.Accounts /org/freedesktop/Accounts/User"$USER_ID" \
  org.freedesktop.Accounts.User SetSession s "$NEXT_SESSION" >/dev/null 2>&1 || true
AS="/var/lib/AccountsService/users/$U"
mkdir -p "$(dirname "$AS")" 2>/dev/null || true
if [ -f "$AS" ]; then
  sed -i "s/^Session=.*/Session=$NEXT_SESSION/" "$AS" 2>/dev/null || true
  grep -q '^Session=' "$AS" 2>/dev/null || sed -i "1i Session=$NEXT_SESSION" "$AS" 2>/dev/null || true
else
  printf '[User]\nSession=%s\n' "$NEXT_SESSION" >"$AS" 2>/dev/null || true
fi

# 2. Auto-connexion : elle doit viser la nouvelle session, sinon le
#    gestionnaire de connexion relance indefiniment l'ancienne.
case "$DM" in
  sddm)
    mkdir -p /etc/sddm.conf.d
    printf '[Autologin]\nUser=%s\nSession=%s\nRelogin=false\n' "$U" "$NEXT_SESSION" \
      > /etc/sddm.conf.d/zz-ps5-manager-autologin.conf
    ;;
  lightdm)
    mkdir -p /etc/lightdm
    LCONF="/etc/lightdm/lightdm.conf"
    [ -f "$LCONF" ] || printf '[Seat:*]\n' > "$LCONF"
    python3 - "$LCONF" "$U" "$NEXT_SESSION" <<'PY'
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
    GDM="/etc/gdm/custom.conf"
    if [ -f "$GDM" ]; then
      cp -f "$GDM" "$GDM.ps5-manager.bak" 2>/dev/null || true
    else
      printf '[daemon]\n' > "$GDM"
    fi
    grep -q '^\[daemon\]' "$GDM" || printf '\n[daemon]\n' >> "$GDM"
    python3 - "$GDM" "$U" <<'PY'
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

# 3. Fermeture de la session courante (laisse le DRM libre pour Gamescope)
loginctl terminate-user "$U" >/dev/null 2>&1 || true
i=0
while [ "$i" -lt 20 ]; do
  if ! loginctl list-sessions --no-legend 2>/dev/null | awk '{print $3}' | grep -qx "$U"; then
    break
  fi
  sleep 0.5
  i=$((i + 1))
done
sleep 1

# 4. Redemarrage du gestionnaire de connexion sur la nouvelle session
if ! systemctl restart "$DM" >/dev/null 2>&1; then
  systemctl start "$DM" >/dev/null 2>&1 || true
fi
log "session $NEXT_SESSION demandee (bureau ${DESKTOP_SESSION:-inconnu}, gestionnaire $DM)"
exit 0
SH
sed -i \
  -e "s|@@USER@@|$TARGET_USER|g" \
  -e "s|gnome|$DESKTOP_SESSION|g" \
  /usr/local/bin/switch-session
chmod 755 /usr/local/bin/switch-session
sed -i -e "s|GNOME|$DESKTOP_LABEL|g" \
  -e "s|gnome gnome-xorg ubuntu|$DESKTOP_SESSION_CANDIDATES|g" \
  -e "s|gdm|$DISPLAY_MANAGER_FALLBACK|g" \
  /usr/local/bin/switch-session /usr/bin/gamescope-session

step "Raccourcis (menu des applications + bureau)"
APP_DIR="$TARGET_HOME/.local/share/applications"
mkdir -p "$APP_DIR"
cat > "$APP_DIR/switch-session.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Bascule Session ($DESKTOP_LABEL)
Comment=$DESKTOP_LABEL / Steam Big Picture
Exec=/usr/local/bin/switch-session steam
Icon=ps5-gaming-mode
Terminal=false
Categories=Game;Utility;
DESK
chmod 755 "$APP_DIR/switch-session.desktop"
for d in Bureau Desktop; do
  if [ -d "$TARGET_HOME/$d" ]; then
    cp -f "$APP_DIR/switch-session.desktop" "$TARGET_HOME/$d/"
    chown "$TARGET_USER": "$TARGET_HOME/$d/switch-session.desktop" 2>/dev/null || true
  fi
done
chown -R "$TARGET_USER": "$APP_DIR" 2>/dev/null || true
if command -v update-desktop-database >/dev/null; then
  update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

printf '\nTermine. Journaux : /var/log/ps5-manager/gaming-session.log et session-switch.log\n'
printf 'Redemarre la console pour arriver sur la session Steam (Gamescope).\n'
