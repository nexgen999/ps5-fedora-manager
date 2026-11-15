#!/bin/bash
# ==============================================================================
# PS5 Fedora Manager - Zenity GUI
# ------------------------------------------------------------------------------
# Couvre les 13 catégories du cahier des charges :
#   1  manager (mise à jour + dépendances, désinstallation)
#   2  langues (langpacks installés, installation, configuration intégrale)
#   3  dépôts (liste, RPM Fusion, Flathub, suppression, mise à jour, ajout)
#   4  utilisateurs (liste, compte + langue, ajout, suppression, root)
#   5  mises à jour Fedora (applications, système, langpacks, dépôts)
#   6  maintenance (cache, orphelins, journaux, temporaires, flatpak, kernels)
#   7  alimentation (veille complète / système / écran, on et off)
#   8  fan manager (status, fan, boost, service, restart, mise à jour)
#   9  hardware control (matériel, installer, vérifier MAJ, désinstaller)
#   10 mesa / vulkan / RADV
#   11 kernel PS5 (RPM de ps5-linux-patches + kernel par défaut)
#   12 logithèque (installer / désinstaller / mettre à jour chaque logiciel)
#   13 presets (gaming, bureautique, développeur)
# ==============================================================================

set -o pipefail

INSTALL_DIR="/opt/ps5-manager"
REPO_URL="${PS5_MANAGER_REPO:-https://github.com/nexgen999/ps5-fedora-manager.git}"
KERNEL_REPO="ps5-linux/ps5-linux-patches"
KERNEL_BASE="https://github.com/${KERNEL_REPO}"
TOOLS_REPO="https://github.com/ps5-linux/ps5-linux-tools"
HWCON_INSTALL="https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-gui/main/install.sh"
HWCON_PYPROJECT="https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-gui/main/pyproject.toml"
HWCON_PREFIX="/opt/ps5-hwcon-gui"
DECKY_INSTALL="https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/install_release.sh"
DECKY_UNINSTALL="https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/uninstall.sh"
FLATHUB_REPO="https://dl.flathub.org/repo/flathub.flatpakrepo"
OPERA_KEY="https://rpm.opera.com/rpmrepo.key"
OPERA_REPO_FILE="/etc/yum.repos.d/opera.repo"
BRAVE_REPO="https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo"
BRAVE_KEY="https://brave-browser-rpm-release.s3.brave.com/brave-core.asc"

# ------------------------------------------------------------------------------
# Utilisateur réel + environnement graphique
# ------------------------------------------------------------------------------
if [ "$(id -u)" -eq 0 ]; then
    if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
        REAL_USER="$SUDO_USER"
    else
        REAL_USER="$(logname 2>/dev/null || echo root)"
    fi
else
    REAL_USER="$(id -un)"
fi
case "$REAL_USER" in
    ""|UNKNOWN) REAL_USER="$(id -un)" ;;
esac
REAL_UID="$(id -u "$REAL_USER" 2>/dev/null || echo 0)"
REAL_HOME="$(getent passwd "$REAL_USER" 2>/dev/null | cut -d: -f6)"
[ -n "$REAL_HOME" ] || REAL_HOME="/root"

# Zenity tourne en root (script lancé via sudo ou .desktop) : il lui faut
# l'autorisation X de l'utilisateur, sinon aucune fenêtre ne s'affiche.
export DISPLAY="${DISPLAY:-:0}"
[ -f "$REAL_HOME/.Xauthority" ] && export XAUTHORITY="$REAL_HOME/.Xauthority"
if [ -d "/run/user/$REAL_UID" ]; then
    export XDG_RUNTIME_DIR="/run/user/$REAL_UID"
    export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$REAL_UID/bus"
fi

# ------------------------------------------------------------------------------
# Zenity : dépendance obligatoire
# ------------------------------------------------------------------------------
if ! command -v zenity >/dev/null 2>&1; then
    dnf install -y zenity || { echo "zenity est requis." >&2; exit 1; }
fi
if ! command -v zenity >/dev/null 2>&1; then
    echo "zenity est introuvable, le gestionnaire ne peut pas démarrer." >&2
    exit 1
fi

# ------------------------------------------------------------------------------
# Interface
# ------------------------------------------------------------------------------
info()     { zenity --info    --title="$1" --text="$2" --width="${3:-440}"; }
warn()     { zenity --warning --title="$1" --text="$2" --width="${3:-440}"; }
error()    { zenity --error   --title="$1" --text="$2" --width="${3:-460}"; }
confirm()  { zenity --question --title="$1" --text="$2" --width="${3:-440}"; }
ask()      { zenity --entry   --title="$1" --text="$2"; }
ask_pass() { zenity --password --title="$1" --text="$2"; }
show_text(){ zenity --text-info --title="$1" --width="${3:-660}" --height="${4:-440}" <<< "$2"; }

LAST_LOG=""
# run_with_progress <titre> <texte> <commande...>
run_with_progress() {
    local title="$1" text="$2"
    shift 2
    local log pid
    log="$(mktemp)"
    LAST_LOG="$log"
    "$@" >"$log" 2>&1 &
    pid=$!
    ( while kill -0 "$pid" 2>/dev/null; do printf '# %s\n' "$text"; sleep 1; done ) |
        zenity --progress --pulse --no-cancel --auto-close --width=460 \
               --title="$title" --text="$text" >/dev/null 2>&1
    wait "$pid"
    return $?
}

show_log() {
    local tail_txt title="Détail de l'erreur"
    [ -n "${1:-}" ] && title="$1"
    tail_txt="$(tail -n 60 "$LAST_LOG" 2>/dev/null)"
    show_text "$title" "${tail_txt:-Aucun message.}" 720 480
}

# Exécute une commande en tant que vrai utilisateur (gsettings, flatpak user,
# gnome-session-quit, installateurs qui refusent root...)
run_as_user() {
    if [ "$(id -u)" -eq 0 ] && [ "$REAL_USER" != "root" ]; then
        sudo -u "$REAL_USER" -H env \
            DISPLAY="${DISPLAY:-:0}" \
            XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-}" \
            DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-}" \
            PATH="/usr/local/bin:/usr/bin:/bin" "$@"
    else
        "$@"
    fi
}

install_pkgs() {
    local title="$1"
    shift
    if ! run_with_progress "$title" "Installation : $*" sudo dnf install -y "$@"; then
        error "$title" "$(printf "Échec de l'installation.\n\n%s" "$(tail -n 15 "$LAST_LOG" 2>/dev/null)")"
        return 1
    fi
}

remove_pkgs() {
    local title="$1"
    shift
    if ! run_with_progress "$title" "Suppression : $*" sudo dnf remove -y "$@"; then
        error "$title" "$(printf 'Échec de la suppression.\n\n%s' "$(tail -n 15 "$LAST_LOG" 2>/dev/null)")"
        return 1
    fi
}

# ------------------------------------------------------------------------------
# Adaptateurs dnf5 / flatpak / GitHub
# ------------------------------------------------------------------------------
DNF5=0
dnf --version 2>/dev/null | head -n1 | grep -qi '^dnf5' && DNF5=1

dnf_add_repo() {
    if [ "$DNF5" = 1 ]; then
        sudo dnf config-manager addrepo --from-repofile="$1"
    else
        sudo dnf config-manager --add-repo "$1"
    fi
}

dnf_disable_repo() {
    if [ "$DNF5" = 1 ]; then
        sudo dnf config-manager setopt "${1}.enabled=0"
    else
        sudo dnf config-manager --set-disabled "$1"
    fi
}

ensure_flathub() {
    command -v flatpak >/dev/null 2>&1 || return 1
    sudo flatpak remote-add --system --if-not-exists flathub "$FLATHUB_REPO" >/dev/null 2>&1
}

flatpak_install() {
    if ! ensure_flathub; then
        error "Flatpak" "Flatpak ou le dépôt Flathub est absent.\nUtilisez l'option 3 (Gestion des dépôts)."
        return 1
    fi
    if ! run_with_progress "Flatpak" "Installation : $*" \
         sudo flatpak install --system --noninteractive flathub "$@"; then
        error "Flatpak" "$(printf "Échec de l'installation.\n\n%s" "$(tail -n 15 "$LAST_LOG" 2>/dev/null)")"
        return 1
    fi
}

flatpak_remove() {
    if ! run_with_progress "Flatpak" "Suppression : $*" \
         sudo flatpak uninstall --system --noninteractive "$@"; then
        error "Flatpak" "$(printf 'Échec de la suppression.\n\n%s' "$(tail -n 15 "$LAST_LOG" 2>/dev/null)")"
        return 1
    fi
}

flatpak_present() {
    flatpak info --system "$1" >/dev/null 2>&1 || flatpak info --user "$1" >/dev/null 2>&1
}

flatpak_have_update() {
    flatpak remote-ls --system --updates flathub 2>/dev/null | awk '{print $1}' | grep -qx "$1"
}

# dnf check-update : 0 = à jour, 100 = mise à jour dispo, autre = erreur.
rpm_update_state() {
    dnf check-update -q "$1" >/dev/null 2>&1
    case $? in
        0) printf 'uptodate' ;;
        100) printf 'update' ;;
        *) printf 'unknown' ;;
    esac
}

# Dernier asset d'une release GitHub (sans API : pas de quota).
gh_latest_asset() {
    local repo="$1" pattern="$2" tag
    tag="$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$repo/releases/latest" 2>/dev/null)"
    tag="${tag##*/}"
    [ -n "$tag" ] || return 1
    curl -fsSL "https://github.com/$repo/releases/expanded_assets/$tag" 2>/dev/null |
        grep -o "/$repo/releases/download/[^\"]*" |
        grep -E "$pattern" | head -n1 |
        sed 's|^|https://github.com|'
}

rpm_ensure_rpmfusion() {
    if [ -f /etc/yum.repos.d/rpmfusion-nonfree.repo ]; then
        return 0
    fi
    local fed
    fed="$(rpm -E %fedora)"
    run_with_progress "RPM Fusion" "Installation de RPM Fusion free + nonfree…" \
        sudo dnf install -y \
        "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-${fed}.noarch.rpm" \
        "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-${fed}.noarch.rpm"
}

# ------------------------------------------------------------------------------
# Menu 2 : langues
# ------------------------------------------------------------------------------
installed_locales() {
    localectl list-locales 2>/dev/null | sort -u
}

installed_langpacks() {
    rpm -qa 'langpacks-*' 'glibc-langpack-*' 2>/dev/null | sort
}

keymap_layouts() {
    localectl list-x11-keymap-layouts 2>/dev/null | sort -u
}

# Langue du compte (AccountsService, ce que fait GNOME Paramètres).
set_user_language() {
    local user="$1" loc="$2" uid
    uid="$(id -u "$user" 2>/dev/null)" || return 1
    [ -n "$uid" ] || return 1
    command -v gdbus >/dev/null 2>&1 || return 1
    gdbus call --system --dest org.freedesktop.Accounts \
        --object-path "/org/freedesktop/Accounts/User${uid}" \
        --method org.freedesktop.Accounts.User.SetLanguage "$loc" >/dev/null 2>&1
}

pick_locale() {
    local title="$1" locales=()
    mapfile -t locales < <(installed_locales)
    [ "${#locales[@]}" -gt 0 ] || locales=(fr_FR.UTF-8 en_US.UTF-8)
    zenity --list --title="$title" --width=480 --height=400 \
        --column="Langue installée" "${locales[@]}"
}

apply_language_all() {
    local loc="$1" kb="$2"
    if [ -n "$loc" ]; then
        local code="${loc%%.*}"
        sudo dnf install -y "langpacks-${code}" "glibc-langpack-${code}" >/dev/null 2>&1 ||
            sudo dnf install -y "langpacks-${code%%_*}" "glibc-langpack-${code%%_*}" >/dev/null 2>&1
        sudo localectl set-locale "LANG=${loc}" || true
        set_user_language "$REAL_USER" "$loc" || true
        run_as_user gsettings set org.gnome.system.locale region "$loc" >/dev/null 2>&1 || true
    fi
    if [ -n "$kb" ]; then
        sudo localectl set-keymap "$kb" || true
        sudo localectl set-x11-keymap "$kb" || true
    fi
}

# ------------------------------------------------------------------------------
# Menu 3 : dépôts
# ------------------------------------------------------------------------------
repo_files_for_id() {
    grep -rls "^[[:space:]]*\[$1\]" /etc/yum.repos.d/ 2>/dev/null
}

list_repos() {
    local out
    out="$(printf '===== DNF (RPM) =====\n%s\n' "$(dnf repolist --all 2>&1)")"
    if command -v flatpak >/dev/null 2>&1; then
        out+="$(printf '\n\n===== Flatpak (système) =====\n%s' "$(flatpak remotes --system 2>&1)")"
        out+="$(printf '\n\n===== Flatpak (utilisateur) =====\n%s' "$(run_as_user flatpak remotes --user 2>&1)")"
    else
        out+="$(printf '\n\nFlatpak n est pas installé.')"
    fi
    show_text "Dépôts système (RPM + Flatpak)" "$out" 760 520
}

remove_repo_menu() {
    local sub
    sub="$(zenity --list --title="Supprimer un dépôt" --text="Que voulez-vous supprimer ?" \
        --width=520 --height=270 --column="ID" --column="Action" \
        "1" "Désactiver un dépôt DNF (sans le supprimer)" \
        "2" "Supprimer un dépôt DNF (fichier .repo)" \
        "3" "Supprimer un dépôt Flatpak")"
    case "$sub" in
        1)
            local id out
            id="$(ask "Désactiver un dépôt" "ID du dépôt (ex: rpmfusion-nonfree) :")"
            [ -n "$id" ] || return 0
            if out="$(dnf_disable_repo "$id" 2>&1)"; then
                info "Dépôt" "Dépôt $id désactivé."
            else
                error "Dépôt" "$(printf 'Échec.\n\n%s' "$out")"
            fi
            ;;
        2)
            local id files
            id="$(ask "Supprimer un dépôt" "ID du dépôt (ex: brave-browser) :")"
            [ -n "$id" ] || return 0
            files="$(repo_files_for_id "$id")"
            if [ -z "$files" ]; then
                error "Dépôt" "Aucun fichier .repo ne définit $id dans /etc/yum.repos.d."
                return 1
            fi
            if confirm "Supprimer un dépôt" "$(printf 'Supprimer ces fichiers ?\n\n%s' "$files")"; then
                # shellcheck disable=SC2086
                sudo rm -f $files && info "Dépôt" "Dépôt $id supprimé."
            fi
            ;;
        3)
            local name
            name="$(ask "Supprimer un dépôt Flatpak" "Nom du dépôt (ex: flathub) :")"
            [ -n "$name" ] || return 0
            if confirm "Dépôt Flatpak" "Supprimer le dépôt Flatpak $name ?"; then
                sudo flatpak remote-delete --system "$name" 2>/dev/null ||
                    sudo flatpak remote-delete --user "$name" 2>/dev/null ||
                    {
                        error "Dépôt Flatpak" "Suppression de $name impossible."
                        return 1
                    }
                info "Dépôt Flatpak" "Dépôt $name supprimé."
            fi
            ;;
    esac
}

refresh_repos() {
    if ! run_with_progress "Dépôts" "Nettoyage et rafraîchissement…" \
         sudo bash -c 'dnf clean all && dnf makecache --refresh'; then
        show_log "Échec du rafraîchissement"
        return 1
    fi
    if command -v flatpak >/dev/null 2>&1; then
        run_with_progress "Dépôts" "Mise à jour des métadonnées Flatpak…" \
            sudo flatpak update --appstream -y || true
    fi
    info "Dépôts" "Cache nettoyé, dépôts et métadonnées rafraîchis."
}

# ------------------------------------------------------------------------------
# Menu 6 : maintenance
# ------------------------------------------------------------------------------
maintenance_clean_all() {
    run_with_progress "Maintenance" "Nettoyage complet…" sudo bash -c '
        dnf clean all
        dnf makecache >/dev/null 2>&1 || true
        journalctl --vacuum-time=7d >/dev/null 2>&1 || true
        rm -rf /tmp/* /var/tmp/* 2>/dev/null || true
    ' || true
    if [ -d "$REAL_HOME/.cache/thumbnails" ]; then
        run_as_user rm -rf "$REAL_HOME/.cache/thumbnails"
    fi
    if command -v flatpak >/dev/null 2>&1; then
        sudo flatpak uninstall --system --unused --noninteractive >/dev/null 2>&1 || true
    fi
    info "Maintenance" "Caches DNF, journaux de plus de 7 jours, fichiers temporaires, vignettes et runtimes Flatpak inutilisés nettoyés."
}

maintenance_old_kernels() {
    local out
    out="$(rpm -qa 'kernel-core*' 'linux-ps5*' --qf '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\n' 2>/dev/null | sort -V)"
    if [ -z "$out" ]; then
        info "Kernels" "Aucun paquet kernel trouvé."
        return 0
    fi
    if ! confirm "Anciens kernels" "$(printf 'Kernels installés :\n\n%s\n\nSupprimer les anciens en gardant les 2 plus récents ?' "$out")" 560; then
        return 0
    fi
    if ! command -v package-cleanup >/dev/null 2>&1; then
        sudo dnf install -y dnf-utils >/dev/null 2>&1 || true
    fi
    if command -v package-cleanup >/dev/null 2>&1; then
        if run_with_progress "Kernels" "Suppression des anciens kernels…" \
             sudo package-cleanup --oldkernels --count=2 -y; then
            info "Kernels" "Anciens kernels supprimés (2 conservés)."
        else
            show_log "Échec de la suppression"
        fi
    else
        error "Kernels" "package-cleanup est indisponible (paquet dnf-utils absent sur cette version).\nAucune suppression effectuée."
    fi
}

# ------------------------------------------------------------------------------
# Menu 7 : alimentation
# ------------------------------------------------------------------------------
suspend_on() {
    sudo systemctl unmask sleep.target suspend.target hibernate.target hybrid-sleep.target
}
suspend_off() {
    sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
}
screen_on() {
    run_as_user gsettings set org.gnome.desktop.session idle-delay 300
}
screen_off() {
    run_as_user gsettings set org.gnome.desktop.session idle-delay 0
}

# ------------------------------------------------------------------------------
# Menu 8 : fan / boost
# ------------------------------------------------------------------------------
fan_status() {
    local out
    out="$(printf '===== ps5fan.service =====\n%s\n\n' "$(systemctl status ps5fan.service 2>&1 || true)")"
    out+="$(printf '===== ps5boost.service =====\n%s\n' "$(systemctl status ps5boost.service 2>&1 || true)")"
    if [ -x /usr/local/sbin/ps5_control ]; then
        out+="$(printf '\n\n===== ps5_control --status =====\n%s' "$(sudo /usr/local/sbin/ps5_control --status 2>&1 || true)")"
    fi
    show_text "Status ventilateur" "$out" 760 520
}

update_tools() {
    local tmp
    tmp="$(mktemp -d)"
    if ! run_with_progress "ps5-linux-tools" "Récupération du dépôt…" \
         git clone --depth=1 "$TOOLS_REPO" "$tmp/tools"; then
        show_log "Échec du clonage"
        rm -rf "$tmp"
        return 1
    fi
    if ! run_with_progress "ps5-linux-tools" "Compilation et installation…" \
         bash -c "cd '$tmp/tools' && ./install.sh"; then
        show_log "Échec de install.sh"
        rm -rf "$tmp"
        return 1
    fi
    rm -rf "$tmp"
    info "ps5-linux-tools" "Fan et boost installés / mis à jour.\nServices : ps5fan.service et ps5boost.service."
}

# ------------------------------------------------------------------------------
# Menu 9 : hardware control
# ------------------------------------------------------------------------------
hwcon_installed_version() {
    local f="$HWCON_PREFIX/src/pyproject.toml"
    [ -f "$f" ] || return 1
    awk -F'"' '/^version[[:space:]]*=/{print $2; exit}' "$f"
}

hwcon_latest_version() {
    curl -fsSL "$HWCON_PYPROJECT" 2>/dev/null |
        awk -F'"' '/^version[[:space:]]*=/{print $2; exit}'
}

hwcon_check_update() {
    local installed latest
    installed="$(hwcon_installed_version)" ||
        {
            info "PS5 Hardware Control" "Non installé.\nUtilisez l'option Installer."
            return 0
        }
    latest="$(hwcon_latest_version)"
    if [ -z "$latest" ]; then
        error "PS5 Hardware Control" "Impossible de lire la version disponible sur GitHub."
        return 1
    fi
    if [ "$installed" = "$latest" ]; then
        info "PS5 Hardware Control" "$(printf 'À jour.\n\nVersion installée : %s\nVersion GitHub   : %s' "$installed" "$latest")"
    else
        info "PS5 Hardware Control" "$(printf 'Mise à jour disponible.\n\nVersion installée : %s\nVersion GitHub   : %s\n\nUtilisez l option Mettre à jour.' "$installed" "$latest")"
    fi
}

hwcon_install() {
    # install.sh exige un utilisateur normal (il refuse root) et installe dans /opt.
    sudo dnf install -y python3-PyQt6 >/dev/null 2>&1 || true
    if run_as_user bash -c "curl -fsSL '$HWCON_INSTALL' | bash"; then
        info "PS5 Hardware Control" "Installation / mise à jour terminée.\nLancez « ps5-hwcon-gui » (mot de passe demandé)."
    else
        error "PS5 Hardware Control" "L'installateur a échoué.\nLancez-le dans un terminal pour voir le détail."
    fi
}

hwcon_uninstall() {
    if run_as_user bash -c "curl -fsSL '$HWCON_INSTALL' | bash -s -- --uninstall"; then
        info "PS5 Hardware Control" "Désinstallé (vos réglages dans /var/lib/ps5-hwcon sont conservés)."
    else
        error "PS5 Hardware Control" "La désinstallation a échoué."
    fi
}

hw_check() {
    local out
    out="$(printf '===== /sys/class/hwmon/ =====\n%s\n\n' "$(ls -l /sys/class/hwmon/ 2>&1)")"
    out+="$(printf '===== noeuds PS5 =====\n')"
    for p in /sys/bus/platform/devices/ps5-fan/target_temp /sys/class/misc/ps5_buzzer/beep \
             /sys/class/devfreq/ps5-gpufreq /sys/class/leds/ps5:rgb:multi_intensity; do
        if [ -e "$p" ]; then out+="$(printf '  OK      %s\n' "$p")"; else out+="$(printf '  ABSENT  %s\n' "$p")"; fi
    done
    show_text "Matériel PS5" "$out" 760 500
}

# ------------------------------------------------------------------------------
# Kernel PS5 (ps5-linux/ps5-linux-patches)
# ------------------------------------------------------------------------------
kernel_latest() {
    local url tag ver
    command -v curl >/dev/null 2>&1 || return 1
    url="$(curl -fsSLI -o /dev/null -w '%{url_effective}' "${KERNEL_BASE}/releases/latest" 2>/dev/null)"
    tag="${url##*/}"
    case "$tag" in kernel-*) ;; *) return 1 ;; esac
    ver="${tag#kernel-}"
    ver="${ver%-*}"
    [ -n "$ver" ] || return 1
    printf '%s\t%s\n' "$tag" "$ver"
}

# Sur PS5 il n'y a pas de GRUB/grubby : le noyau démarre depuis l'ESP.
# Le %post du RPM y copie déjà vmlinuz et initrd (bzImage / initrd.img).
esp_ready() {
    [ -d /boot/efi ] || return 1
    mountpoint -q /boot/efi 2>/dev/null && return 0
    [ -f /boot/efi/bzImage ] && return 0
    return 1
}

# Version du noyau actuellement présent sur l'ESP (celle qui démarre).
esp_kernel_version() {
    [ -f /boot/efi/bzImage ] || return 1
    grep -a -m1 -o 'Linux version [^ ]*' /boot/efi/bzImage 2>/dev/null | awk '{print $3}'
}

kernel_install_latest() {
    local found tag ver rpm_url code report local_dir local_rpm
    if [ "$(uname -m)" != "x86_64" ]; then
        error "Kernel PS5" "Ce kernel n'est publié que pour x86_64."
        return 1
    fi
    command -v curl >/dev/null 2>&1 || { install_pkgs "Kernel PS5" curl || return 1; }

    found="$(kernel_latest)" || {
        error "Kernel PS5" "Impossible de contacter GitHub pour trouver la dernière release."
        return 1
    }
    tag="${found%%$'\t'*}"
    ver="${found##*$'\t'}"
    rpm_url="${KERNEL_BASE}/releases/download/${tag}/linux-ps5-${ver}-1.x86_64.rpm"

    code="$(curl -sIL -o /dev/null -w '%{http_code}' "$rpm_url" 2>/dev/null)"
    if [ "$code" != "200" ]; then
        error "Kernel PS5" "$(printf "Le paquet est introuvable (HTTP %s).\n\n%s" "${code:-?}" "$rpm_url")"
        return 1
    fi

    if ! confirm "Kernel PS5 $ver" "$(printf 'Installer le kernel PS5 %s ?\n\nPaquet : linux-ps5-%s-1.x86_64.rpm\n\n- modules dans /usr/lib/modules/%s\n- dracut génère /boot/initrd.img-%s\n- le noyau est copié dans /boot/efi par le paquet, et c est lui qui démarre\n\nUn redémarrage sera nécessaire.' "$ver" "$ver" "$ver" "$ver")" 540; then
        return 0
    fi

    command -v dracut >/dev/null 2>&1 || install_pkgs "Kernel PS5" dracut || true

    # 1) Téléchargement du RPM de release, 2) installation normale du fichier local.
    local_dir="/var/tmp/ps5-kernel"
    local_rpm="$local_dir/linux-ps5-${ver}-1.x86_64.rpm"
    sudo mkdir -p "$local_dir"
    if ! run_with_progress "Kernel PS5" "Téléchargement de linux-ps5-${ver}-1.x86_64.rpm…" \
         sudo curl -fL --retry 3 -o "$local_rpm" "$rpm_url"; then
        show_log "Échec du téléchargement du kernel"
        return 1
    fi
    if [ ! -s "$local_rpm" ]; then
        error "Kernel PS5" "Le RPM téléchargé est vide : $local_rpm"
        return 1
    fi

    # localpkg_gpgcheck=0 : les RPM de release ne sont pas signés.
    if ! run_with_progress "Kernel PS5" "Installation de linux-ps5 $ver…" \
         sudo dnf install -y --setopt=localpkg_gpgcheck=0 "$local_rpm"; then
        show_log "Échec de l'installation du kernel"
        return 1
    fi

    report="$(printf 'Kernel %s installé\n\n' "$ver")"
    if [ -f "/boot/vmlinuz-$ver" ]; then
        report+="$(printf '  /boot/vmlinuz-%s ......... OK\n' "$ver")"
    else
        report+="$(printf '  /boot/vmlinuz-%s ......... ABSENT\n' "$ver")"
    fi
    if [ -d "/usr/lib/modules/$ver" ]; then
        report+="$(printf '  /usr/lib/modules/%s ....... OK\n' "$ver")"
    else
        report+="$(printf '  /usr/lib/modules/%s ....... ABSENT\n' "$ver")"
    fi
    if [ -f "/boot/initrd.img-$ver" ]; then
        report+="$(printf '  /boot/initrd.img-%s ..... OK\n\n' "$ver")"
    else
        report+="$(printf '  /boot/initrd.img-%s ..... ABSENT (dracut a échoué)\n\n' "$ver")"
    fi
    if [ -f /boot/efi/bzImage ]; then
        report+="$(printf '  /boot/efi/bzImage ....... %s\n' "$(esp_kernel_version || echo présent)")"
        report+="$(printf '  /boot/efi/initrd.img .... %s\n' "$([ -s /boot/efi/initrd.img ] && echo présent || echo ABSENT)")"
    else
        report+="$(printf '  /boot/efi/bzImage ....... ABSENT (ESP non monté ?)\n')"
    fi
    report+="$(printf '\nRPM conservé : %s\n' "$local_rpm")"
    report+="$(printf '\nKernel actuellement démarré : %s' "$(uname -r)")"

    info "Kernel PS5 $ver" "$report" 640
}

kernel_select_default() {
    local f k cur esp entry args=() kernels=()
    for f in /boot/vmlinuz-*; do
        [ -e "$f" ] || continue
        k="${f##*/vmlinuz-}"
        case "$k" in 0-rescue*) continue ;; esac
        kernels+=("$k")
    done
    if [ "${#kernels[@]}" -eq 0 ]; then
        error "Kernel" "Aucun kernel trouvé dans /boot."
        return 1
    fi
    mapfile -t kernels < <(printf '%s\n' "${kernels[@]}" | sort -Vr)

    cur="$(uname -r)"
    esp="$(esp_kernel_version || true)"

    for k in "${kernels[@]}"; do
        local st=""
        [ "$k" = "$cur" ] && st+="démarré "
        [ -n "$esp" ] && [ "$k" = "$esp" ] && st+="sur /boot/efi "
        [ -z "$st" ] && st="installé"
        args+=("$k" "$st")
    done

    entry="$(zenity --list --title="Kernel à démarrer" \
        --text="$(printf 'Kernel démarré : %s\nKernel sur /boot/efi : %s\n\nChoisissez le kernel à placer sur /boot/efi (celui qui démarre) :' "$cur" "${esp:-inconnu}")" \
        --width=620 --height=420 \
        --column="Version" --column="Statut" "${args[@]}")"
    [ -n "$entry" ] || return 0

    if [ ! -f "/boot/vmlinuz-$entry" ]; then
        error "Kernel" "Le fichier /boot/vmlinuz-$entry est absent."
        return 1
    fi
    if [ ! -f "/boot/initrd.img-$entry" ]; then
        error "Kernel" "Le fichier /boot/initrd.img-$entry est absent : ce kernel ne peut pas démarrer."
        return 1
    fi
    if ! esp_ready; then
        error "Kernel" "L'ESP /boot/efi n'est pas accessible (partition non montée ?).\nImpossible d'y copier le kernel."
        return 1
    fi
    if ! confirm "Kernel à démarrer" "$(printf 'Copier le kernel %s sur /boot/efi ?\n\n/boot/vmlinuz-%s      -> /boot/efi/bzImage\n/boot/initrd.img-%s   -> /boot/efi/initrd.img\n\nLes fichiers actuels seront sauvegardés en .bak.\nUn redémarrage sera nécessaire.' "$entry" "$entry" "$entry")" 560; then
        return 0
    fi

    sudo cp -f /boot/efi/bzImage /boot/efi/bzImage.bak 2>/dev/null || true
    sudo cp -f /boot/efi/initrd.img /boot/efi/initrd.img.bak 2>/dev/null || true
    if sudo cp -f "/boot/vmlinuz-$entry" /boot/efi/bzImage &&
       sudo cp -f "/boot/initrd.img-$entry" /boot/efi/initrd.img &&
       sync; then
        info "Kernel à démarrer" "$(printf 'Kernel %s copié sur /boot/efi.\n\nSauvegarde de l ancien : /boot/efi/bzImage.bak\n\nRedémarrez pour l utiliser.' "$entry")" 560
    else
        error "Kernel" "La copie vers /boot/efi a échoué (ESP en lecture seule ou plein ?)."
        return 1
    fi
}

# ------------------------------------------------------------------------------
# Menu 12 : logithèque (installer / désinstaller / mettre à jour)
# ------------------------------------------------------------------------------
opera_repo_add() {
    sudo rpm --import "$OPERA_KEY" >/dev/null 2>&1 || true
    printf '%s\n' \
        '[opera]' \
        'name=Opera packages' \
        'type=rpm-md' \
        'baseurl=https://rpm.opera.com/rpm' \
        'gpgcheck=1' \
        'gpgkey=https://rpm.opera.com/rpmrepo.key' \
        'enabled=1' | sudo tee "$OPERA_REPO_FILE" >/dev/null
}

brave_repo_add() {
    local out
    if ! out="$(dnf_add_repo "$BRAVE_REPO" 2>&1)"; then
        error "Brave" "$(printf 'Ajout du dépôt impossible.\n\n%s' "$out")"
        return 1
    fi
    sudo rpm --import "$BRAVE_KEY" >/dev/null 2>&1 || true
}

# Détecte le format réellement installé d'un logiciel : rpm, flatpak ou rien.
detect_format() {
    local rpm_name="$1" fp_id="$2"
    if [ -n "$rpm_name" ] && rpm -q "$rpm_name" >/dev/null 2>&1; then
        printf 'rpm'
    elif [ -n "$fp_id" ] && flatpak_present "$fp_id"; then
        printf 'flatpak'
    else
        printf 'none'
    fi
}

software_action() {
    local sw="$1" action="$2" kind="" rpm_name="" fp_id="" url="" fmt="" out=""
    case "$sw" in
        "Steam")
            kind="rpm"; rpm_name="steam"
            ;;
        "Heroic Games Launcher")
            kind="flatpak"; fp_id="com.heroicgameslauncher.hgl"
            ;;
        "ProtonUp-Qt")
            kind="flatpak"; fp_id="net.davidotek.pupgui2"
            ;;
        "Decky Loader")
            kind="decky"
            ;;
        "Etcher")
            kind="ghrpm"; rpm_name="balena-etcher"
            ;;
        "Opera")
            kind="dual"; rpm_name="opera-stable"; fp_id="com.opera.Opera"
            ;;
        "Brave")
            kind="dual"; rpm_name="brave-browser"; fp_id="com.brave.Browser"
            ;;
        "Bazaar")
            kind="flatpak"; fp_id="io.github.kolunmi.Bazaar"
            ;;
        "GNOME Extension Manager")
            kind="flatpak"; fp_id="com.mattjakeman.ExtensionManager"
            ;;
        *)
            error "Logithèque" "Logiciel inconnu : $sw"
            return 1
            ;;
    esac

    case "$kind" in
        rpm)
            case "$action" in
                install|update)
                    if [ "$rpm_name" = "steam" ]; then
                        rpm_ensure_rpmfusion || true
                    fi
                    if install_pkgs "$sw" "$rpm_name"; then
                        info "$sw" "$(printf '%s installé / mis à jour.' "$sw")"
                    fi
                    ;;
                remove|uninstall)
                    if remove_pkgs "$sw" "$rpm_name"; then
                        info "$sw" "$sw supprimé."
                    fi
                    ;;
                check)
                    if ! rpm -q "$rpm_name" >/dev/null 2>&1; then
                        info "$sw" "$sw n est pas installé."
                    else
                        case "$(rpm_update_state "$rpm_name")" in
                            uptodate) info "$sw" "$sw est à jour." ;;
                            update) info "$sw" "Une mise à jour de $sw est disponible." ;;
                            *) info "$sw" "Vérification impossible (dépôt indisponible ?)." ;;
                        esac
                    fi
                    ;;
            esac
            ;;
        flatpak)
            case "$action" in
                install)
                    if flatpak_present "$fp_id"; then
                        info "$sw" "$sw est déjà installé."
                    elif flatpak_install "$fp_id"; then
                        info "$sw" "$sw installé."
                    fi
                    ;;
                update)
                    if ! flatpak_present "$fp_id"; then
                        info "$sw" "$sw n est pas installé."
                    elif run_with_progress "$sw" "Mise à jour de $sw…" \
                         sudo flatpak update --system --noninteractive "$fp_id"; then
                        info "$sw" "$sw mis à jour."
                    else
                        show_log "Échec de la mise à jour"
                    fi
                    ;;
                remove|uninstall)
                    if ! flatpak_present "$fp_id"; then
                        info "$sw" "$sw n est pas installé."
                    elif flatpak_remove "$fp_id"; then
                        info "$sw" "$sw supprimé."
                    fi
                    ;;
                check)
                    if ! flatpak_present "$fp_id"; then
                        info "$sw" "$sw n est pas installé."
                    elif flatpak_have_update "$fp_id"; then
                        info "$sw" "Une mise à jour de $sw est disponible."
                    else
                        info "$sw" "$sw est à jour."
                    fi
                    ;;
            esac
            ;;
        decky)
            case "$action" in
                install|update)
                    if run_as_user bash -c "curl -fsSL '$DECKY_INSTALL' | bash"; then
                        info "Decky Loader" "Decky installé / mis à jour."
                    else
                        error "Decky Loader" "L'installateur Decky a échoué (Steam est-il installé ?)."
                    fi
                    ;;
                remove|uninstall)
                    if run_as_user bash -c "curl -fsSL '$DECKY_UNINSTALL' | bash"; then
                        info "Decky Loader" "Decky désinstallé."
                    else
                        error "Decky Loader" "La désinstallation a échoué."
                    fi
                    ;;
                check)
                    if [ -d "$REAL_HOME/homebrew" ]; then
                        info "Decky Loader" "Decky est installé.\nUtilisez « Mettre à jour » pour passer à la dernière version."
                    else
                        info "Decky Loader" "Decky n est pas installé."
                    fi
                    ;;
            esac
            ;;
        ghrpm)
            case "$action" in
                install|update)
                    url="$(gh_latest_asset "balena-io/etcher" 'x86_64\.rpm$')"
                    if [ -z "$url" ]; then
                        error "Etcher" "Impossible de trouver le RPM sur les releases GitHub."
                        return 1
                    fi
                    if run_with_progress "Etcher" "Installation du RPM de release…" \
                         sudo dnf install -y --setopt=localpkg_gpgcheck=0 "$url"; then
                        info "Etcher" "Etcher installé / mis à jour depuis le RPM GitHub."
                    else
                        show_log "Échec de l'installation d'Etcher"
                        return 1
                    fi
                    ;;
                remove|uninstall)
                    if rpm -q "$rpm_name" >/dev/null 2>&1; then
                        remove_pkgs "Etcher" "$rpm_name" && info "Etcher" "Etcher supprimé."
                    else
                        info "Etcher" "Etcher n est pas installé."
                    fi
                    ;;
                check)
                    local inst latest
                    inst="$(rpm -q --qf '%{VERSION}' "$rpm_name" 2>/dev/null)"
                    latest="$(gh_latest_asset "balena-io/etcher" 'x86_64\.rpm$')"
                    latest="${latest##*/balena-etcher-}"
                    latest="${latest%%-*}"
                    if [ -z "$inst" ]; then
                        info "Etcher" "Etcher n est pas installé."
                    elif [ -n "$latest" ] && [ "$inst" != "$latest" ]; then
                        info "Etcher" "$(printf 'Mise à jour disponible.\n\nInstallé : %s\nGitHub   : %s' "$inst" "$latest")"
                    else
                        info "Etcher" "Etcher est à jour."
                    fi
                    ;;
            esac
            ;;
        dual)
            fmt="$(detect_format "$rpm_name" "$fp_id")"
            case "$action" in
                install)
                    if [ "$fmt" != "none" ]; then
                        info "$sw" "$sw est déjà installé ($fmt)."
                        return 0
                    fi
                    local how
                    how="$(zenity --list --title="$sw" --text="Quel format d'installation ?" \
                        --width=430 --height=230 --column="Format" \
                        "RPM (dépôt officiel)" "Flatpak (Flathub)")"
                    [ -n "$how" ] || return 0
                    if [ "$how" = "RPM (dépôt officiel)" ]; then
                        if [ "$sw" = "Opera" ]; then
                            opera_repo_add
                        else
                            brave_repo_add || return 1
                        fi
                        if install_pkgs "$sw" "$rpm_name"; then
                            info "$sw" "$sw installé via RPM."
                        fi
                    elif flatpak_install "$fp_id"; then
                        info "$sw" "$sw installé via Flatpak."
                    fi
                    ;;
                update)
                    case "$fmt" in
                        rpm)
                            if run_with_progress "$sw" "Mise à jour de $sw…" \
                                 sudo dnf upgrade -y "$rpm_name"; then
                                info "$sw" "$sw mis à jour (RPM)."
                            else
                                show_log "Échec de la mise à jour"
                            fi
                            ;;
                        flatpak)
                            if run_with_progress "$sw" "Mise à jour de $sw…" \
                                 sudo flatpak update --system --noninteractive "$fp_id"; then
                                info "$sw" "$sw mis à jour (Flatpak)."
                            else
                                show_log "Échec de la mise à jour"
                            fi
                            ;;
                        *)
                            info "$sw" "$sw n est pas installé."
                            ;;
                    esac
                    ;;
                remove|uninstall)
                    case "$fmt" in
                        rpm)
                            remove_pkgs "$sw" "$rpm_name" && info "$sw" "$sw supprimé."
                            ;;
                        flatpak)
                            flatpak_remove "$fp_id" && info "$sw" "$sw supprimé."
                            ;;
                        *)
                            info "$sw" "$sw n est pas installé."
                            ;;
                    esac
                    ;;
                check)
                    case "$fmt" in
                        rpm)
                            case "$(rpm_update_state "$rpm_name")" in
                                uptodate) info "$sw" "$sw est à jour (RPM)." ;;
                                update) info "$sw" "Une mise à jour de $sw est disponible (RPM)." ;;
                                *) info "$sw" "Vérification impossible (dépôt indisponible ?)." ;;
                            esac
                            ;;
                        flatpak)
                            if flatpak_have_update "$fp_id"; then
                                info "$sw" "Une mise à jour de $sw est disponible (Flatpak)."
                            else
                                info "$sw" "$sw est à jour (Flatpak)."
                            fi
                            ;;
                        *)
                            info "$sw" "$sw n est pas installé."
                            ;;
                    esac
                    ;;
            esac
            ;;
    esac
}

# ------------------------------------------------------------------------------
# Menu 1 : manager
# ------------------------------------------------------------------------------
ensure_deps() {
    local p missing=()
    for p in curl git zenity; do
        command -v "$p" >/dev/null 2>&1 || missing+=("$p")
    done
    if [ "${#missing[@]}" -gt 0 ]; then
        run_with_progress "Dépendances" "Installation : ${missing[*]}" \
            sudo dnf install -y "${missing[@]}"
    fi
}

install_files() {
    local src="$INSTALL_DIR"
    if [ ! -f "$src/ps5-manager.sh" ]; then
        error "Installation" "ps5-manager.sh est absent de $src."
        return 1
    fi
    sudo install -m 0755 "$src/ps5-manager.sh" /usr/local/bin/ps5-manager || return 1
    [ -f "$src/ps5-manager.desktop" ] &&
        sudo install -m 0644 "$src/ps5-manager.desktop" /usr/share/applications/ps5-manager.desktop
    [ -f "$src/icon.png" ] &&
        sudo install -m 0644 "$src/icon.png" /usr/share/pixmaps/ps5-manager.png
    sudo update-desktop-database /usr/share/applications/ >/dev/null 2>&1 || true
}

update_manager() {
    ensure_deps
    if [ -d "$INSTALL_DIR/.git" ]; then
        if ! run_with_progress "Mise à jour" "Récupération depuis GitHub…" \
             sudo git -C "$INSTALL_DIR" fetch --all --prune; then
            show_log "Échec de la mise à jour"
            return 1
        fi
        if ! sudo git -C "$INSTALL_DIR" reset --hard origin/main >/dev/null 2>&1; then
            error "Mise à jour" "git reset a échoué dans $INSTALL_DIR."
            return 1
        fi
        install_files || return 1
        info "Mise à jour" "Le gestionnaire a été mis à jour (script + dépendances)."
    else
        if [ -e "$INSTALL_DIR" ]; then
            error "Installation" "$INSTALL_DIR existe mais n'est pas un dépôt git.\nSupprimez-le puis relancez."
            return 1
        fi
        if ! run_with_progress "Installation" "Clonage du dépôt…" \
             sudo git clone "$REPO_URL" "$INSTALL_DIR"; then
            show_log "Échec du clonage"
            return 1
        fi
        install_files || return 1
        info "Installation" "Installation terminée."
    fi
}

# ------------------------------------------------------------------------------
# Infos système
# ------------------------------------------------------------------------------
OS_VER="$(. /etc/os-release 2>/dev/null && printf '%s' "${PRETTY_NAME% (*}")"
K_VER="$(uname -r)"

# ------------------------------------------------------------------------------
# Boucle principale
# ------------------------------------------------------------------------------
while true; do
    if ! CHOICE="$(zenity --list \
        --title="PS5 Linux Universal Manager (nexgen999)" \
        --text="$(printf '<span size="x-large" weight="bold">PS5 Linux Universal Manager</span>\n\nSystème : %s | Noyau : %s\nChoisissez une action :' "$OS_VER" "$K_VER")" \
        --width=880 --height=640 \
        --column="Opt" --column="Action" --column="Description" \
        "1"  "Mise à jour / Désinstallation" "Mettre à jour le manager depuis GitHub (+ dépendances) ou le désinstaller" \
        "2"  "Configuration des langues"    "Langpacks installés, installer une langue, configurer langue + clavier + session" \
        "3"  "Gestion des dépôts"           "Voir, installer (RPM/Flatpak), supprimer, mettre à jour ou ajouter un dépôt" \
        "4"  "Gestion des utilisateurs"     "Voir, éditer (mot de passe + langue), ajouter/supprimer un compte, root" \
        "5"  "Mises à jour Fedora"          "Applications, système, langpacks, métadonnées des dépôts" \
        "6"  "Maintenance & Nettoyage"      "Cache DNF, orphelins, journaux, fichiers temporaires, Flatpak, kernels" \
        "7"  "Management de l'alimentation" "Veille complète, système ou écran : activation / désactivation" \
        "8"  "PS5 Fan Manager"              "Status, fan on/off, boost on/off, service, restart, mise à jour" \
        "9"  "PS5 Hardware Control"         "Matériel sysfs, installer, vérifier les mises à jour, désinstaller" \
        "10" "Mesa / Vulkan & RADV"         "Outils Vulkan, mesa, résumé Vulkan complet, vérification RADV" \
        "11" "Mise à jour Kernel"           "Installer le dernier kernel PS5 (RPM) et choisir le kernel par défaut" \
        "12" "Logithèque / Logiciels"       "Steam, Heroic, ProtonUp, Decky, Etcher, Opera, Brave, Bazaar..." \
        "13" "Software Presets"             "Installation groupée : Gaming, Bureautique ou Développeur")"; then
        exit 0
    fi
    [ -n "$CHOICE" ] || exit 0

    case "$CHOICE" in
        1)
            SUB="$(zenity --list --title="1. Mise à jour / Désinstallation" --text="Choisissez une option :" \
                --width=500 --height=250 --column="ID" --column="Action" \
                "1" "Mettre à jour le manager + ses dépendances" \
                "2" "Désinstaller complètement le manager")"
            case "$SUB" in
                1) update_manager ;;
                2)
                    if confirm "Désinstallation" "Supprimer le gestionnaire et ses fichiers ?"; then
                        sudo rm -rf "$INSTALL_DIR" /usr/local/bin/ps5-manager \
                            /usr/share/applications/ps5-manager.desktop \
                            /usr/share/pixmaps/ps5-manager.png
                        info "Désinstallation" "PS5 Fedora Manager a été désinstallé."
                        exit 0
                    fi
                    ;;
            esac
            ;;
        2)
            SUB="$(zenity --list --title="2. Configuration des langues" --text="Choisissez une option :" \
                --width=560 --height=290 --column="ID" --column="Action" \
                "1" "Voir les langpacks installés (système + clavier)" \
                "2" "Installer une langue" \
                "3" "Configuration intégrale (langue + clavier + compte) et relance session")"
            case "$SUB" in
                1)
                    show_text "Langpacks installés" "$(printf '===== Langpacks =====\n%s\n\n===== localectl (système + clavier) =====\n%s' \
                        "$(installed_langpacks)" "$(localectl status 2>&1)")" 700 500
                    ;;
                2)
                    LANG_IN="$(ask "Installer une langue" "Code de langue (ex: fr_FR.UTF-8, es_ES.UTF-8) :")"
                    [ -n "$LANG_IN" ] || continue
                    # langpacks-fr, langpacks-pt_BR... jamais langpacks-fr_FR.UTF-8
                    LANG_CODE="${LANG_IN%%.*}"
                    if sudo dnf install -y "langpacks-${LANG_CODE}" "glibc-langpack-${LANG_CODE}" >/dev/null 2>&1; then
                        info "Langue" "Installé : langpacks-${LANG_CODE} + glibc-langpack-${LANG_CODE}"
                    elif sudo dnf install -y "langpacks-${LANG_CODE%%_*}" "glibc-langpack-${LANG_CODE%%_*}" >/dev/null 2>&1; then
                        info "Langue" "Installé : langpacks-${LANG_CODE%%_*} + glibc-langpack-${LANG_CODE%%_*}"
                    else
                        error "Langue" "Aucun langpack trouvé pour $LANG_IN."
                    fi
                    ;;
                3)
                    SELECTED_LANG="$(pick_locale "Langue système")"
                    [ -n "$SELECTED_LANG" ] || continue
                    KB_LIST=()
                    mapfile -t KB_LIST < <(keymap_layouts | head -n 60)
                    [ "${#KB_LIST[@]}" -gt 0 ] || KB_LIST=(fr us de es)
                    SELECTED_KB="$(zenity --list --title="Clavier" \
                        --text="Choisissez la disposition du clavier :" --width=460 --height=340 \
                        --column="Layout" "${KB_LIST[@]}")"
                    [ -n "$SELECTED_KB" ] || SELECTED_KB="fr"
                    apply_language_all "$SELECTED_LANG" "$SELECTED_KB"
                    if confirm "Configuration" "$(printf 'Langue : %s\nClavier : %s\n\nLa session va se fermer pour appliquer les changements.\nContinuer ?' "$SELECTED_LANG" "$SELECTED_KB")"; then
                        run_as_user gnome-session-quit --logout --force
                    fi
                    ;;
            esac
            ;;
        3)
            SUB="$(zenity --list --title="3. Gestion des dépôts" --text="Choisissez une option :" \
                --width=580 --height=330 --column="ID" --column="Action" \
                "1" "Voir tous les dépôts (RPM + Flatpak système et utilisateur)" \
                "2" "Installer les dépôts RPM (RPM Fusion free + nonfree)" \
                "3" "Installer le dépôt Flatpak (Flathub)" \
                "4" "Désinstaller / supprimer un dépôt" \
                "5" "Mise à jour des dépôts & nettoyage du cache" \
                "6" "Ajouter un dépôt personnalisé (URL .repo)")"
            case "$SUB" in
                1) list_repos ;;
                2)
                    if rpm_ensure_rpmfusion; then
                        info "Dépôts RPM" "RPM Fusion free + nonfree installés."
                    else
                        show_log "Échec de l'installation de RPM Fusion"
                    fi
                    ;;
                3)
                    command -v flatpak >/dev/null 2>&1 || install_pkgs "Flatpak" flatpak || continue
                    if ensure_flathub; then
                        info "Flathub" "Dépôt Flathub installé (portée système)."
                    else
                        error "Flathub" "L'ajout de Flathub a échoué."
                    fi
                    ;;
                4) remove_repo_menu ;;
                5) refresh_repos ;;
                6)
                    REPO_URL_ADD="$(ask "Ajouter un dépôt" "URL du fichier .repo :")"
                    if [ -n "$REPO_URL_ADD" ]; then
                        if OUT="$(dnf_add_repo "$REPO_URL_ADD" 2>&1)"; then
                            info "Dépôt" "Dépôt ajouté."
                        else
                            error "Dépôt" "$(printf 'Échec.\n\n%s' "$OUT")"
                        fi
                    fi
                    ;;
            esac
            ;;
        4)
            SUB="$(zenity --list --title="4. Gestion des utilisateurs" --text="Choisissez une option :" \
                --width=560 --height=310 --column="ID" --column="Action" \
                "1" "Voir la liste des utilisateurs" \
                "2" "Éditer mon compte ($REAL_USER) : mot de passe et langue" \
                "3" "Ajouter un utilisateur" \
                "4" "Supprimer un compte utilisateur" \
                "5" "Root : état du compte et changement de mot de passe")"
            case "$SUB" in
                1)
                    show_text "Utilisateurs du système" "$(awk -F: '$3>=1000 && $3<65534 {printf "%-20s uid=%-6s home=%-22s shell=%s\n", $1, $3, $6, $7}' /etc/passwd)"
                    ;;
                2)
                    NEW_PASS="$(ask_pass "Mot de passe" "Nouveau mot de passe pour $REAL_USER (vide = inchangé) :")"
                    if [ -n "$NEW_PASS" ]; then
                        if printf '%s:%s\n' "$REAL_USER" "$NEW_PASS" | sudo chpasswd; then
                            info "Mot de passe" "Mot de passe de $REAL_USER mis à jour."
                        else
                            error "Mot de passe" "La modification a échoué (mot de passe contenant « : » ?)."
                        fi
                    fi
                    USER_LANG="$(pick_locale "Langue du compte $REAL_USER")"
                    if [ -n "$USER_LANG" ]; then
                        applied="0"
                        set_user_language "$REAL_USER" "$USER_LANG" && applied="1"
                        run_as_user gsettings set org.gnome.system.locale region "$USER_LANG" >/dev/null 2>&1 && applied="1"
                        if [ "$applied" = "1" ]; then
                            info "Langue du compte" "Langue $USER_LANG appliquée à $REAL_USER.\nDéconnectez-vous pour l'appliquer."
                        else
                            error "Langue du compte" "Impossible d'appliquer la langue."
                        fi
                    fi
                    ;;
                3)
                    NEW_USER="$(ask "Ajouter un utilisateur" "Nom du nouveau compte :")"
                    [ -n "$NEW_USER" ] || continue
                    NEW_UPASS="$(ask_pass "Mot de passe" "Mot de passe pour $NEW_USER :")"
                    if sudo useradd -m -s /bin/bash "$NEW_USER" &&
                       printf '%s:%s\n' "$NEW_USER" "$NEW_UPASS" | sudo chpasswd; then
                        info "Utilisateur" "Compte $NEW_USER créé."
                    else
                        error "Utilisateur" "La création de $NEW_USER a échoué."
                    fi
                    ;;
                4)
                    DEL_USER="$(ask "Supprimer un utilisateur" "Nom du compte à supprimer :")"
                    [ -n "$DEL_USER" ] || continue
                    if [ "$DEL_USER" = "root" ] || [ "$DEL_USER" = "$REAL_USER" ]; then
                        error "Utilisateur" "Suppression de $DEL_USER refusée (compte root ou compte courant)."
                    elif confirm "Supprimer $DEL_USER" "Supprimer le compte $DEL_USER et son dossier personnel ?"; then
                        if sudo userdel -r "$DEL_USER"; then
                            info "Utilisateur" "Compte $DEL_USER supprimé."
                        else
                            error "Utilisateur" "La suppression a échoué (session ouverte ?)."
                        fi
                    fi
                    ;;
                5)
                    ROOT_STATE="$(sudo passwd -S root 2>&1)"
                    if confirm "Compte root" "$(printf 'État du compte root :\n\n%s\n\nUn mot de passe n est jamais affichable (il est stocké haché).\nVoulez-vous définir un nouveau mot de passe root ?' "$ROOT_STATE")" 520; then
                        ROOT_PASS="$(ask_pass "Mot de passe root" "Nouveau mot de passe pour root :")"
                        if [ -n "$ROOT_PASS" ]; then
                            if printf 'root:%s\n' "$ROOT_PASS" | sudo chpasswd; then
                                info "Root" "Mot de passe root modifié."
                            else
                                error "Root" "La modification a échoué."
                            fi
                        fi
                    fi
                    ;;
            esac
            ;;
        5)
            SUB="$(zenity --list --title="5. Mises à jour Fedora" --text="Choisissez une option :" \
                --width=480 --height=280 --column="ID" --column="Action" \
                "1" "Mettre à jour les applications (DNF & Flatpak)" \
                "2" "Mettre à jour le système complet" \
                "3" "Mettre à jour les langpacks" \
                "4" "Mettre à jour les métadonnées des dépôts")"
            case "$SUB" in
                1)
                    if run_with_progress "Mises à jour" "Mise à jour DNF…" sudo dnf upgrade -y; then
                        if command -v flatpak >/dev/null 2>&1; then
                            run_with_progress "Mises à jour" "Mise à jour Flatpak…" \
                                sudo flatpak update --system --noninteractive || true
                        fi
                        info "Mises à jour" "Applications mises à jour."
                    else
                        show_log "Échec de la mise à jour DNF"
                    fi
                    ;;
                2)
                    if run_with_progress "Système" "Mise à jour complète…" sudo dnf upgrade --refresh -y; then
                        info "Système" "Système mis à jour."
                    else
                        show_log "Échec de la mise à jour"
                    fi
                    ;;
                3)
                    if run_with_progress "Langpacks" "Mise à jour des langpacks…" \
                         sudo dnf upgrade -y 'langpacks-*' 'glibc-langpack-*'; then
                        info "Langpacks" "Langpacks à jour."
                    else
                        show_log "Échec de la mise à jour des langpacks"
                    fi
                    ;;
                4) refresh_repos ;;
            esac
            ;;
        6)
            SUB="$(zenity --list --title="6. Maintenance & Nettoyage" --text="Choisissez une option :" \
                --width=580 --height=360 --column="ID" --column="Action" \
                "1" "Nettoyage complet (cache, journaux, temporaires, Flatpak inutilisé)" \
                "2" "Nettoyer uniquement le cache DNF" \
                "3" "Supprimer les paquets orphelins (autoremove)" \
                "4" "Réduire les journaux systemd" \
                "5" "Nettoyer /tmp et /var/tmp" \
                "6" "Nettoyer les caches de l'utilisateur (vignettes)" \
                "7" "Supprimer les anciens kernels (garder 2)" \
                "8" "Voir l'espace disque utilisé")"
            case "$SUB" in
                1) maintenance_clean_all ;;
                2)
                    if run_with_progress "Maintenance" "Nettoyage du cache DNF…" sudo dnf clean all; then
                        sudo dnf makecache >/dev/null 2>&1 || true
                        info "Maintenance" "Cache DNF nettoyé et recréé."
                    else
                        show_log "Échec du nettoyage"
                    fi
                    ;;
                3)
                    if run_with_progress "Maintenance" "Suppression des orphelins…" sudo dnf autoremove -y; then
                        info "Maintenance" "Paquets orphelins supprimés."
                    else
                        show_log "Échec de autoremove"
                    fi
                    ;;
                4)
                    if run_with_progress "Maintenance" "Réduction des journaux…" \
                         sudo journalctl --vacuum-time=7d; then
                        info "Maintenance" "Journaux réduits à 7 jours."
                    else
                        show_log "Échec de journalctl"
                    fi
                    ;;
                5)
                    if run_with_progress "Maintenance" "Nettoyage des temporaires…" \
                         sudo bash -c 'rm -rf /tmp/* /var/tmp/* 2>/dev/null || true'; then
                        info "Maintenance" "/tmp et /var/tmp nettoyés."
                    else
                        show_log "Échec du nettoyage"
                    fi
                    ;;
                6)
                    if [ -d "$REAL_HOME/.cache/thumbnails" ]; then
                        run_as_user rm -rf "$REAL_HOME/.cache/thumbnails"
                    fi
                    info "Maintenance" "Vignettes de l'utilisateur nettoyées."
                    ;;
                7) maintenance_old_kernels ;;
                8) show_text "Espace disque" "$(df -h 2>&1)" 640 420 ;;
            esac
            ;;
        7)
            SUB="$(zenity --list --title="7. Management de l'alimentation" --text="Choisissez une option :" \
                --width=580 --height=310 --column="ID" --column="Action" \
                "1" "Activer la veille complète (système + écran)" \
                "2" "Désactiver la veille complète" \
                "3" "Activer la veille système (suspend/hibernate)" \
                "4" "Désactiver la veille système" \
                "5" "Activer la mise en veille de l'écran (5 min)" \
                "6" "Désactiver la mise en veille de l'écran")"
            case "$SUB" in
                1)
                    suspend_on >/dev/null 2>&1
                    screen_on >/dev/null 2>&1
                    info "Alimentation" "Veille complète activée (système + écran après 5 min)."
                    ;;
                2)
                    suspend_off >/dev/null 2>&1
                    screen_off >/dev/null 2>&1
                    info "Alimentation" "Veille complète désactivée."
                    ;;
                3)
                    if suspend_on; then
                        info "Alimentation" "Veille système activée."
                    else
                        error "Alimentation" "Impossible de démasquer les cibles de veille."
                    fi
                    ;;
                4)
                    if suspend_off; then
                        info "Alimentation" "Veille système désactivée."
                    else
                        error "Alimentation" "Impossible de masquer les cibles de veille."
                    fi
                    ;;
                5)
                    if screen_on; then
                        info "Alimentation" "Veille écran activée (5 min)."
                    else
                        error "Alimentation" "gsettings a échoué (session GNOME absente ?)."
                    fi
                    ;;
                6)
                    if screen_off; then
                        info "Alimentation" "Veille écran désactivée."
                    else
                        error "Alimentation" "gsettings a échoué (session GNOME absente ?)."
                    fi
                    ;;
            esac
            ;;
        8)
            SUB="$(zenity --list --title="8. PS5 Fan Manager" --text="Choisissez une option :" \
                --width=520 --height=380 --column="ID" --column="Action" \
                "1" "Voir le status (services + ps5_control)" \
                "2" "Fan on (activer au démarrage)" \
                "3" "Fan off" \
                "4" "Boost on" \
                "5" "Boost off" \
                "6" "Voir l'état des services fan / boost" \
                "7" "Relancer le service" \
                "8" "Installer / mettre à jour ps5-linux-tools")"
            case "$SUB" in
                1) fan_status ;;
                2)
                    if sudo systemctl enable --now ps5fan.service; then
                        info "Ventilateur" "ps5fan.service activé et démarré."
                    else
                        error "Ventilateur" "Impossible d'activer ps5fan.service (ps5-linux-tools installé ?)."
                    fi
                    ;;
                3)
                    if sudo systemctl disable --now ps5fan.service; then
                        info "Ventilateur" "ps5fan.service arrêté et désactivé."
                    else
                        error "Ventilateur" "Impossible de désactiver ps5fan.service."
                    fi
                    ;;
                4)
                    if sudo systemctl enable --now ps5boost.service; then
                        info "Boost" "ps5boost.service activé et démarré."
                    else
                        error "Boost" "Impossible d'activer ps5boost.service."
                    fi
                    ;;
                5)
                    if sudo systemctl disable --now ps5boost.service; then
                        info "Boost" "ps5boost.service arrêté et désactivé."
                    else
                        error "Boost" "Impossible de désactiver ps5boost.service."
                    fi
                    ;;
                6)
                    show_text "Services Fan / Boost" "$(printf '%s\n' \
                        "ps5fan   : $(systemctl is-active ps5fan.service 2>/dev/null || echo inconnu) / $(systemctl is-enabled ps5fan.service 2>/dev/null || echo inconnu)" \
                        "ps5boost : $(systemctl is-active ps5boost.service 2>/dev/null || echo inconnu) / $(systemctl is-enabled ps5boost.service 2>/dev/null || echo inconnu)")"
                    ;;
                7)
                    if sudo systemctl restart ps5fan.service; then
                        info "Ventilateur" "ps5fan.service relancé."
                    else
                        error "Ventilateur" "Impossible de relancer ps5fan.service."
                    fi
                    ;;
                8) update_tools ;;
            esac
            ;;
        9)
            SUB="$(zenity --list --title="9. PS5 Hardware Control" --text="Choisissez une option :" \
                --width=560 --height=320 --column="ID" --column="Action" \
                "1" "Vérifier la présence du matériel (/sys/class/hwmon et noeuds PS5)" \
                "2" "Installer PS5 Hardware Control" \
                "3" "Vérifier les mises à jour" \
                "4" "Mettre à jour PS5 Hardware Control" \
                "5" "Désinstaller PS5 Hardware Control")"
            case "$SUB" in
                1) hw_check ;;
                2) hwcon_install ;;
                3) hwcon_check_update ;;
                4) hwcon_install ;;
                5) hwcon_uninstall ;;
            esac
            ;;
        10)
            SUB="$(zenity --list --title="10. Mesa / Vulkan & RADV" --text="Choisissez une option :" \
                --width=560 --height=290 --column="ID" --column="Action" \
                "1" "Installer les outils Vulkan & Mesa demos" \
                "2" "Mettre à jour les paquets Mesa & Vulkan" \
                "3" "Vérifier la prise en charge RADV (GPU AMD PS5)" \
                "4" "Afficher le résumé Vulkan complet")"
            case "$SUB" in
                1)
                    if install_pkgs "Vulkan" vulkan-tools mesa-demos; then
                        info "Vulkan" "vulkan-tools et mesa-demos installés."
                    fi
                    ;;
                2)
                    if run_with_progress "Mesa / Vulkan" "Mise à jour…" \
                         sudo dnf upgrade -y 'mesa*' 'vulkan*'; then
                        info "Mesa / Vulkan" "Mesa et Vulkan mis à jour."
                    else
                        show_log "Échec de la mise à jour"
                    fi
                    ;;
                3)
                    if ! command -v vulkaninfo >/dev/null 2>&1; then
                        error "RADV" "vulkaninfo est absent : utilisez d'abord l'option 1."
                    else
                        RADV_INFO="$(vulkaninfo --summary 2>&1 | grep -i 'radv\|deviceName\|driverName' ||
                                     echo 'Aucun périphérique RADV détecté.')"
                        show_text "Vérification RADV" "$RADV_INFO" 620 380
                    fi
                    ;;
                4)
                    if command -v vulkaninfo >/dev/null 2>&1; then
                        show_text "Résumé Vulkan" "$(vulkaninfo --summary 2>&1)" 720 500
                    else
                        error "Vulkan" "vulkaninfo est absent : utilisez d'abord l'option 1."
                    fi
                    ;;
            esac
            ;;
        11)
            SUB="$(zenity --list --title="11. Mise à jour Kernel PS5" --text="Choisissez une option :" \
                --width=580 --height=250 --column="ID" --column="Action" \
                "1" "Installer le dernier kernel PS5 (RPM de ps5-linux-patches)" \
                "2" "Choisir le kernel à démarrer (copie sur /boot/efi)")"
            case "$SUB" in
                1) kernel_install_latest ;;
                2) kernel_select_default ;;
            esac
            ;;
        12)
            SUB="$(zenity --list --title="12. Logithèque PS5" --text="Choisissez un logiciel :" \
                --width=560 --height=430 --column="Logiciel" \
                "Steam" \
                "Heroic Games Launcher" \
                "ProtonUp-Qt" \
                "Decky Loader" \
                "Etcher" \
                "Opera" \
                "Brave" \
                "Bazaar" \
                "GNOME Extension Manager")"
            [ -n "$SUB" ] || continue
            ACT="$(zenity --list --title="$SUB" --text="Quelle action pour $SUB ?" \
                --width=460 --height=280 --column="Action" \
                "Installer" \
                "Désinstaller" \
                "Mettre à jour" \
                "Vérifier les mises à jour")"
            [ -n "$ACT" ] || continue
            case "$ACT" in
                "Installer") software_action "$SUB" install ;;
                "Désinstaller") software_action "$SUB" remove ;;
                "Mettre à jour") software_action "$SUB" update ;;
                "Vérifier les mises à jour") software_action "$SUB" check ;;
            esac
            ;;
        13)
            PRESET="$(zenity --list --title="13. Software Presets" --text="Choisissez un pack complet à déployer :" \
                --width=500 --height=270 --column="Preset" --column="Description" \
                "Gaming" "Steam, Heroic, ProtonUp-Qt, Decky Loader" \
                "Bureautique" "Brave, Opera, Bazaar, Extension Manager" \
                "Développeur" "Outils de build, git, python3-devel, curl, wget")"
            case "$PRESET" in
                "Gaming")
                    rpm_ensure_rpmfusion || true
                    install_pkgs "Preset Gaming" steam || true
                    flatpak_install com.heroicgameslauncher.hgl net.davidotek.pupgui2 || true
                    run_as_user bash -c "curl -fsSL '$DECKY_INSTALL' | bash" || true
                    info "Preset Gaming" "Preset Gaming déployé (Steam, Heroic, ProtonUp-Qt, Decky)."
                    ;;
                "Bureautique")
                    if ! flatpak_present com.brave.Browser; then
                        flatpak_install com.brave.Browser || true
                    fi
                    if ! flatpak_present com.opera.Opera; then
                        flatpak_install com.opera.Opera || true
                    fi
                    flatpak_install io.github.kolunmi.Bazaar com.mattjakeman.ExtensionManager &&
                        info "Preset Bureautique" "Preset Bureautique déployé."
                    ;;
                "Développeur")
                    # dnf5 a supprimé l'alias groupinstall.
                    GRP=(dnf group install -y development-tools)
                    [ "$DNF5" = 1 ] || GRP=(dnf groupinstall -y development-tools)
                    if run_with_progress "Preset Développeur" "Installation du groupe de build…" \
                         sudo "${GRP[@]}"; then
                        sudo dnf install -y python3-devel git curl wget >/dev/null 2>&1 || true
                        info "Preset Développeur" "Preset Développeur déployé."
                    else
                        show_log "Échec du preset Développeur"
                    fi
                    ;;
            esac
            ;;
    esac
done
