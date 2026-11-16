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
#   13 langue de l interface (français / anglais)
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
if [ -n "${PS5_MANAGER_USER:-}" ]; then
    # Relancé via pkexec : on garde l'utilisateur qui a cliqué sur l'icône.
    REAL_USER="$PS5_MANAGER_USER"
elif [ "$(id -u)" -eq 0 ]; then
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
# Droits root
# ------------------------------------------------------------------------------
# Tout ce que fait le gestionnaire (dnf, git dans /opt, systemctl, /boot/efi,
# chpasswd...) exige root. Lancé depuis l'icône du bureau, il n'y a pas de
# terminal : sudo ne peut donc pas demander le mot de passe. On relance le
# script via pkexec (fenêtre polkit), avec sudo en secours si pkexec manque.
if [ "$(id -u)" -ne 0 ] && [ -z "${PS5_MANAGER_ELEVATED:-}" ]; then
    SELF="$(readlink -f "$0" 2>/dev/null || echo "$0")"
    if command -v pkexec >/dev/null 2>&1; then
        pkexec env PS5_MANAGER_ELEVATED=1 PS5_MANAGER_USER="$REAL_USER" \
            DISPLAY="$DISPLAY" XAUTHORITY="${XAUTHORITY:-$REAL_HOME/.Xauthority}" \
            "$SELF" "$@"
        rc=$?
        # 127 = pkexec absent/inutilisable : on tente sudo. Sinon (0 = ok,
        # 126 = annulé) on s'arrête, le travail a été fait ou refusé.
        [ "$rc" -ne 127 ] && exit "$rc"
    fi
    if command -v sudo >/dev/null 2>&1; then
        sudo -E env PS5_MANAGER_ELEVATED=1 PS5_MANAGER_USER="$REAL_USER" "$SELF" "$@"
        exit $?
    fi
    echo "Ce gestionnaire doit être lancé en root (pkexec ou sudo)." >&2
    echo "This manager must run as root (pkexec or sudo)." >&2
    exit 1
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
# Langue de l'interface (fr / en)
# ------------------------------------------------------------------------------
LANG_FILE="/etc/ps5-manager/language"
UI_LANG="fr"

declare -A EN_TR EN_FMT

load_ui_lang() {
    local l
    [ -r "$LANG_FILE" ] || return 0
    l="$(head -n1 "$LANG_FILE" 2>/dev/null)"
    case "$l" in fr|en) UI_LANG="$l" ;; esac
}

save_ui_lang() {
    UI_LANG="$1"
    sudo mkdir -p "$(dirname "$LANG_FILE")" 2>/dev/null
    printf '%s\n' "$UI_LANG" | sudo tee "$LANG_FILE" >/dev/null 2>&1 ||
        printf '%s\n' "$UI_LANG" > "$LANG_FILE" 2>/dev/null || true
}

# Traduit une chaîne exacte (dictionnaire FR -> EN). Inconnue : inchangée.
# %b permet d'afficher les \n des textes multilignes.
tr() {
    local s="$1"
    if [ "$UI_LANG" = "en" ] && [ -n "${EN_TR[$s]:-}" ]; then
        s="${EN_TR[$s]}"
    fi
    printf '%b' "$s"
}

# Traduit une chaîne de format utilisée avec printf.
trf() {
    local f="$1"
    shift
    if [ "$UI_LANG" = "en" ] && [ -n "${EN_FMT[$f]:-}" ]; then
        f="${EN_FMT[$f]}"
    fi
    if [ $# -gt 0 ]; then
        printf "$f" "$@"
    else
        printf '%s' "$f"
    fi
}

# zenity qui traduit automatiquement titres, textes, colonnes et libellés.
Z() {
    if [ "$UI_LANG" != "en" ]; then
        zenity "$@"
        return $?
    fi
    local -a a=()
    local x k v
    for x in "$@"; do
        case "$x" in
            --title=*|--text=*|--column=*|--ok-label=*)
                k="${x%%=*}"
                v="${x#*=}"
                a+=("${k}=$(tr "$v")")
                ;;
            *) a+=("$(tr "$x")") ;;
        esac
    done
    zenity "${a[@]}"
}

choose_language() {
    local pick
    pick="$(Z --list --title="Langue / Language" \
        --text="$(printf 'Choisissez la langue de l interface.\nChoose the interface language.') " \
        --width=480 --height=230 --column="Langue / Language" \
        "Français" "English")"
    case "$pick" in
        "Français") save_ui_lang fr ;;
        "English") save_ui_lang en ;;
        *) return 1 ;;
    esac
}

load_ui_lang

# ==== TABLE DE TRADUCTION FR -> EN ====
# Libellés et titres communs
EN_TR["Choisissez une option :"]="Choose an option:"
EN_TR["Choisissez un logiciel :"]="Choose software:"
EN_TR["Action"]="Action"
EN_TR["Description"]="Description"
EN_TR["Version"]="Version"
EN_TR["Statut"]="Status"
EN_TR["Logiciel"]="Software"
EN_TR["Format"]="Format"
EN_TR["Layout"]="Layout"
EN_TR["Langue installée"]="Installed language"
EN_TR["Langue système"]="System language"
EN_TR["Clavier"]="Keyboard"
EN_TR["Choisissez la disposition du clavier :"]="Choose the keyboard layout:"
EN_TR["Que voulez-vous supprimer ?"]="What do you want to remove?"
EN_TR["Quel format d'installation ?"]="Which installation format?"
EN_TR["Traitement en cours…"]="Working…"
EN_TR["Détail de l'erreur"]="Error details"
EN_TR["Dépendances"]="Dependencies"
EN_TR["Dépôts"]="Repositories"
EN_TR["Kernels"]="Kernels"
EN_TR["Système"]="System"
EN_TR["Maintenance"]="Maintenance"
EN_TR["Utilisateur"]="User"
EN_TR["Mot de passe"]="Password"
EN_TR["Mise à jour"]="Update"
EN_TR["Mises à jour"]="Updates"
EN_TR["Installation"]="Installation"
EN_TR["Désinstallation"]="Uninstallation"
EN_TR["Installer"]="Install"
EN_TR["Désinstaller"]="Uninstall"
EN_TR["Mettre à jour"]="Update"
EN_TR["Vérifier les mises à jour"]="Check for updates"
EN_TR["Langue / Language"]="Language / Langue"
EN_TR["Français"]="Français"
EN_TR["English"]="English"
EN_TR["Root"]="Root"
EN_TR["Flatpak"]="Flatpak"
EN_TR["RPM Fusion"]="RPM Fusion"
EN_TR["Langue"]="Language"
EN_TR["Langue du compte"]="Account language"
EN_TR["Configuration"]="Configuration"
EN_TR["Alimentation"]="Power"
EN_TR["Ventilateur"]="Fan"
EN_TR["Boost"]="Boost"
EN_TR["Kernel"]="Kernel"
EN_TR["Kernel PS5"]="PS5 kernel"
EN_TR["Kernel par défaut"]="Default kernel"
EN_TR["Kernel à démarrer"]="Kernel to boot"
EN_TR["RADV"]="RADV"
EN_TR["Vulkan"]="Vulkan"
EN_TR["Mesa / Vulkan"]="Mesa / Vulkan"
EN_TR["Etcher"]="Etcher"
EN_TR["Opera"]="Opera"
EN_TR["Brave"]="Brave"
EN_TR["Steam"]="Steam"
EN_TR["PS5 Hardware Control"]="PS5 Hardware Control"
EN_TR["PS5 Fan Manager"]="PS5 Fan Manager"
# Menu principal
EN_TR["Mise à jour / Désinstallation"]="Update / Uninstall"
EN_TR["Mettre à jour le manager depuis GitHub (+ dépendances) ou le désinstaller"]="Update the manager from GitHub (and its dependencies), or uninstall it"
EN_TR["Configuration des langues"]="Language configuration"
EN_TR["Langpacks installés, installer une langue, configurer langue + clavier + session"]="Installed language packs, install a language, configure language + keyboard + session"
EN_TR["Gestion des dépôts"]="Repository management"
EN_TR["Voir, installer (RPM/Flatpak), supprimer, mettre à jour ou ajouter un dépôt"]="View, install (RPM/Flatpak), remove, update or add a repository"
EN_TR["Gestion des utilisateurs"]="User management"
EN_TR["Voir, éditer (mot de passe + langue), ajouter/supprimer un compte, root"]="View, edit (password + language), add/remove an account, root"
EN_TR["Mises à jour Fedora"]="Fedora updates"
EN_TR["Applications, système, langpacks, métadonnées des dépôts"]="Applications, system, language packs, repository metadata"
EN_TR["Maintenance & Nettoyage"]="Maintenance & cleanup"
EN_TR["Cache DNF, orphelins, journaux, fichiers temporaires, Flatpak, kernels"]="DNF cache, orphans, logs, temporary files, Flatpak, kernels"
EN_TR["Management de l'alimentation"]="Power management"
EN_TR["Veille complète, système ou écran : activation / désactivation"]="Full, system or screen sleep: enable / disable"
EN_TR["Status, fan on/off, boost on/off, service, restart, mise à jour"]="Status, fan on/off, boost on/off, service, restart, update"
EN_TR["Matériel sysfs, installer, vérifier les mises à jour, désinstaller"]="sysfs hardware, install, check for updates, uninstall"
EN_TR["Mesa / Vulkan & RADV"]="Mesa / Vulkan & RADV"
EN_TR["Outils Vulkan, mesa, résumé Vulkan complet, vérification RADV"]="Vulkan tools, mesa, full Vulkan summary, RADV check"
EN_TR["Mise à jour Kernel"]="Kernel update"
EN_TR["Installer le dernier kernel PS5 (RPM) et choisir le kernel par défaut"]="Install the latest PS5 kernel (RPM) and choose the boot kernel"
EN_TR["Logithèque / Logiciels"]="Software library"
EN_TR["Steam, Heroic, ProtonUp, Decky, Etcher, Opera, Brave, Bazaar..."]="Steam, Heroic, ProtonUp, Decky, Etcher, Opera, Brave, Bazaar..."
EN_TR["Choisir la langue de l'interface : Français ou English"]="Choose the interface language: French or English"
# Menu 1
EN_TR["1. Mise à jour / Désinstallation"]="1. Update / Uninstall"
EN_TR["Mettre à jour le manager + ses dépendances"]="Update the manager and its dependencies"
EN_TR["Désinstaller complètement le manager"]="Completely uninstall the manager"
EN_TR["Supprimer le gestionnaire et ses fichiers ?"]="Remove the manager and its files?"
EN_TR["PS5 Fedora Manager a été désinstallé."]="PS5 Fedora Manager has been uninstalled."
EN_TR["Le gestionnaire a été mis à jour (script + dépendances)."]="The manager has been updated (script + dependencies)."
EN_TR["Installation terminée."]="Installation complete."
EN_TR["Échec du clonage"]="Clone failed"
EN_TR["Échec de la mise à jour"]="Update failed"
# Menu 2
EN_TR["2. Configuration des langues"]="2. Language configuration"
EN_TR["Voir les langpacks installés (système + clavier)"]="Show installed language packs (system + keyboard)"
EN_TR["Installer une langue"]="Install a language"
EN_TR["Configuration intégrale (langue + clavier + compte) et relance session"]="Full configuration (language + keyboard + account) and restart the session"
EN_TR["Langpacks installés"]="Installed language packs"
EN_TR["Code de langue (ex: fr_FR.UTF-8, es_ES.UTF-8) :"]="Language code (e.g. fr_FR.UTF-8, es_ES.UTF-8):"
# Menu 3
EN_TR["3. Gestion des dépôts"]="3. Repository management"
EN_TR["Voir tous les dépôts (RPM + Flatpak système et utilisateur)"]="List all repositories (RPM + Flatpak system and user)"
EN_TR["Installer les dépôts RPM (RPM Fusion free + nonfree)"]="Install the RPM repositories (RPM Fusion free + nonfree)"
EN_TR["Installer le dépôt Flatpak (Flathub)"]="Install the Flatpak repository (Flathub)"
EN_TR["Désinstaller / supprimer un dépôt"]="Uninstall / remove a repository"
EN_TR["Mise à jour des dépôts & nettoyage du cache"]="Update repositories & clean the cache"
EN_TR["Ajouter un dépôt personnalisé (URL .repo)"]="Add a custom repository (.repo URL)"
EN_TR["Dépôts système (RPM + Flatpak)"]="System repositories (RPM + Flatpak)"
EN_TR["Supprimer un dépôt"]="Remove a repository"
EN_TR["Désactiver un dépôt DNF (sans le supprimer)"]="Disable a DNF repository (without removing it)"
EN_TR["Supprimer un dépôt DNF (fichier .repo)"]="Remove a DNF repository (.repo file)"
EN_TR["Supprimer un dépôt Flatpak"]="Remove a Flatpak repository"
EN_TR["Désactiver un dépôt"]="Disable a repository"
EN_TR["ID du dépôt (ex: rpmfusion-nonfree) :"]="Repository ID (e.g. rpmfusion-nonfree):"
EN_TR["ID du dépôt (ex: brave-browser) :"]="Repository ID (e.g. brave-browser):"
EN_TR["Nom du dépôt (ex: flathub) :"]="Repository name (e.g. flathub):"
EN_TR["Dépôt"]="Repository"
EN_TR["Ajouter un dépôt"]="Add a repository"
EN_TR["URL du fichier .repo :"]="URL of the .repo file:"
EN_TR["Dépôt ajouté."]="Repository added."
EN_TR["Installation de RPM Fusion free + nonfree…"]="Installing RPM Fusion free + nonfree…"
EN_TR["RPM Fusion free + nonfree installés."]="RPM Fusion free + nonfree installed."
EN_TR["Dépôt Flathub installé (portée système)."]="Flathub repository installed (system-wide)."
EN_TR["L'ajout de Flathub a échoué."]="Adding Flathub failed."
EN_TR["Cache nettoyé, dépôts et métadonnées rafraîchis."]="Cache cleaned, repositories and metadata refreshed."
EN_TR["Mise à jour des métadonnées Flatpak…"]="Updating Flatpak metadata…"
EN_TR["Formats Flatpak"]="Flatpak formats"
# Menu 4
EN_TR["4. Gestion des utilisateurs"]="4. User management"
EN_TR["Voir la liste des utilisateurs"]="List users"
EN_TR["Ajouter un utilisateur"]="Add a user"
EN_TR["Nom du nouveau compte :"]="New account name:"
EN_TR["Supprimer un compte utilisateur"]="Delete a user account"
EN_TR["Nom du compte à supprimer :"]="Account name to delete:"
EN_TR["Root : état du compte et changement de mot de passe"]="Root: account status and password change"
EN_TR["Compte root"]="Root account"
EN_TR["Nouveau mot de passe pour root :"]="New password for root:"
EN_TR["Mot de passe root"]="Root password"
EN_TR["Mot de passe root modifié."]="Root password changed."
EN_TR["La modification a échoué."]="The change failed."
EN_TR["La modification a échoué (mot de passe contenant « : » ?)."]="The change failed (password containing a colon?)."
EN_TR["Impossible d'appliquer la langue."]="Could not apply the language."
EN_TR["La suppression a échoué (session ouverte ?)."]="Deletion failed (session still open?)."
EN_TR["Utilisateurs du système"]="System users"
# Menu 5
EN_TR["5. Mises à jour Fedora"]="5. Fedora updates"
EN_TR["Mettre à jour les applications (DNF & Flatpak)"]="Update applications (DNF & Flatpak)"
EN_TR["Mettre à jour le système complet"]="Update the whole system"
EN_TR["Mettre à jour les langpacks"]="Update language packs"
EN_TR["Mettre à jour les métadonnées des dépôts"]="Update repository metadata"
EN_TR["Applications mises à jour."]="Applications updated."
EN_TR["Système mis à jour."]="System updated."
EN_TR["Langpacks à jour."]="Language packs updated."
EN_TR["Mise à jour DNF…"]="DNF update…"
EN_TR["Mise à jour Flatpak…"]="Flatpak update…"
EN_TR["Mise à jour complète…"]="Full update…"
EN_TR["Mise à jour des langpacks…"]="Updating language packs…"
EN_TR["Échec de la mise à jour DNF"]="DNF update failed"
EN_TR["Échec de la mise à jour des langpacks"]="Language pack update failed"
# Menu 6
EN_TR["6. Maintenance & Nettoyage"]="6. Maintenance & cleanup"
EN_TR["Nettoyage complet (cache, journaux, temporaires, Flatpak inutilisé)"]="Full cleanup (cache, logs, temporary files, unused Flatpak)"
EN_TR["Nettoyer uniquement le cache DNF"]="Clean the DNF cache only"
EN_TR["Supprimer les paquets orphelins (autoremove)"]="Remove orphaned packages (autoremove)"
EN_TR["Réduire les journaux systemd"]="Shrink the systemd journal"
EN_TR["Nettoyer /tmp et /var/tmp"]="Clean /tmp and /var/tmp"
EN_TR["Nettoyer les caches de l'utilisateur (vignettes)"]="Clean user caches (thumbnails)"
EN_TR["Supprimer les anciens kernels (garder 2)"]="Remove old kernels (keep 2)"
EN_TR["Voir l'espace disque utilisé"]="Show disk usage"
EN_TR["Espace disque"]="Disk space"
EN_TR["Caches DNF, journaux de plus de 7 jours, fichiers temporaires, vignettes et runtimes Flatpak inutilisés nettoyés."]="DNF caches, logs older than 7 days, temporary files, thumbnails and unused Flatpak runtimes cleaned."
EN_TR["Vignettes de l'utilisateur nettoyées."]="User thumbnails cleaned."
EN_TR["/tmp et /var/tmp nettoyés."]="/tmp and /var/tmp cleaned."
EN_TR["Journaux réduits à 7 jours."]="Journal reduced to 7 days."
EN_TR["Paquets orphelins supprimés."]="Orphaned packages removed."
EN_TR["Cache DNF nettoyé et recréé."]="DNF cache cleaned and rebuilt."
EN_TR["Nettoyage complet…"]="Full cleanup…"
EN_TR["Nettoyage du cache DNF…"]="Cleaning the DNF cache…"
EN_TR["Suppression des orphelins…"]="Removing orphans…"
EN_TR["Réduction des journaux…"]="Shrinking logs…"
EN_TR["Nettoyage des temporaires…"]="Cleaning temporary files…"
EN_TR["Suppression des anciens kernels…"]="Removing old kernels…"
EN_TR["Échec du nettoyage"]="Cleanup failed"
EN_TR["Échec de autoremove"]="autoremove failed"
EN_TR["Échec de journalctl"]="journalctl failed"
EN_TR["Échec de la suppression"]="Removal failed"
EN_TR["Anciens kernels supprimés (2 conservés)."]="Old kernels removed (2 kept)."
EN_TR["Aucun paquet kernel trouvé."]="No kernel package found."
EN_TR["package-cleanup est indisponible (paquet dnf-utils absent sur cette version).\nAucune suppression effectuée."]="package-cleanup is unavailable (dnf-utils missing on this release).\nNothing was removed."
# Menu 7
EN_TR["7. Management de l'alimentation"]="7. Power management"
EN_TR["Activer la veille complète (système + écran)"]="Enable full sleep (system + screen)"
EN_TR["Désactiver la veille complète"]="Disable full sleep (system + screen)"
EN_TR["Activer la veille système (suspend/hibernate)"]="Enable system sleep (suspend/hibernate)"
EN_TR["Désactiver la veille système"]="Disable system sleep"
EN_TR["Activer la mise en veille de l'écran (5 min)"]="Enable screen blanking (5 min)"
EN_TR["Désactiver la mise en veille de l'écran"]="Disable screen blanking"
EN_TR["Veille complète activée (système + écran après 5 min)."]="Full sleep enabled (system + screen after 5 min)."
EN_TR["Veille complète désactivée (système + écran)."]="Full sleep disabled (system + screen)."
EN_TR["Échec : la veille complète n a pas pu être activée."]="Failed: full sleep could not be enabled."
EN_TR["Échec : la veille complète n a pas pu être désactivée."]="Failed: full sleep could not be disabled."
EN_TR["Veille système activée."]="System sleep enabled."
EN_TR["Veille système désactivée."]="System sleep disabled."
EN_TR["Veille écran activée (5 min)."]="Screen blanking enabled (5 min)."
EN_TR["Veille écran désactivée."]="Screen blanking disabled."
EN_TR["Impossible de démasquer les cibles de veille."]="Could not unmask the sleep targets."
EN_TR["Impossible de masquer les cibles de veille."]="Could not mask the sleep targets."
EN_TR["gsettings a échoué (session GNOME absente ?)."]="gsettings failed (no GNOME session?)."
# Menu 8
EN_TR["8. PS5 Fan Manager"]="8. PS5 Fan Manager"
EN_TR["Voir le status (services + ps5_control)"]="Show status (services + ps5_control)"
EN_TR["Fan on (activer au démarrage)"]="Fan on (enable at boot)"
EN_TR["Fan off"]="Fan off"
EN_TR["Boost on"]="Boost on"
EN_TR["Boost off"]="Boost off"
EN_TR["Voir l'état des services fan / boost"]="Show fan / boost service status"
EN_TR["Relancer le service"]="Restart the service"
EN_TR["Installer / mettre à jour ps5-linux-tools"]="Install / update ps5-linux-tools"
EN_TR["Status ventilateur"]="Fan status"
EN_TR["Services Fan / Boost"]="Fan / Boost services"
EN_TR["ps5fan.service activé et démarré."]="ps5fan.service enabled and started."
EN_TR["ps5fan.service arrêté et désactivé."]="ps5fan.service stopped and disabled."
EN_TR["ps5fan.service relancé."]="ps5fan.service restarted."
EN_TR["ps5boost.service activé et démarré."]="ps5boost.service enabled and started."
EN_TR["ps5boost.service arrêté et désactivé."]="ps5boost.service stopped and disabled."
EN_TR["Impossible d'activer ps5fan.service (ps5-linux-tools installé ?)."]="Could not enable ps5fan.service (is ps5-linux-tools installed?)."
EN_TR["Impossible de désactiver ps5fan.service."]="Could not disable ps5fan.service."
EN_TR["Impossible d'activer ps5boost.service."]="Could not enable ps5boost.service."
EN_TR["Impossible de désactiver ps5boost.service."]="Could not disable ps5boost.service."
EN_TR["Impossible de relancer ps5fan.service."]="Could not restart ps5fan.service."
EN_TR["Récupération du dépôt…"]="Fetching the repository…"
EN_TR["Compilation et installation…"]="Building and installing…"
EN_TR["Échec de install.sh"]="install.sh failed"
EN_TR["Fan et boost installés / mis à jour.\nServices : ps5fan.service et ps5boost.service."]="Fan and boost installed / updated.\nServices: ps5fan.service and ps5boost.service."
# Menu 9
EN_TR["9. PS5 Hardware Control"]="9. PS5 Hardware Control"
EN_TR["Vérifier la présence du matériel (/sys/class/hwmon et noeuds PS5)"]="Check hardware presence (/sys/class/hwmon and PS5 nodes)"
EN_TR["Installer PS5 Hardware Control"]="Install PS5 Hardware Control"
EN_TR["Mettre à jour PS5 Hardware Control"]="Update PS5 Hardware Control"
EN_TR["Désinstaller PS5 Hardware Control"]="Uninstall PS5 Hardware Control"
EN_TR["Non installé.\nUtilisez l'option Installer."]="Not installed.\nUse the Install option."
EN_TR["Impossible de lire la version disponible sur GitHub."]="Could not read the version available on GitHub."
EN_TR["Matériel PS5"]="PS5 hardware"
EN_TR["L'installateur a échoué.\nLancez-le dans un terminal pour voir le détail."]="The installer failed.\nRun it in a terminal to see the details."
EN_TR["La désinstallation a échoué."]="Uninstall failed."
EN_TR["Installation / mise à jour terminée.\nLancez « ps5-hwcon-gui » (mot de passe demandé)."]="Installation / update complete.\nRun « ps5-hwcon-gui » (password required)."
EN_TR["Désinstallé (vos réglages dans /var/lib/ps5-hwcon sont conservés)."]="Uninstalled (your settings in /var/lib/ps5-hwcon are kept)."
# Menu 10
EN_TR["10. Mesa / Vulkan & RADV"]="10. Mesa / Vulkan & RADV"
EN_TR["Installer les outils Vulkan & Mesa demos"]="Install Vulkan tools & Mesa demos"
EN_TR["Vérifier la prise en charge RADV (GPU AMD PS5)"]="Check RADV support (PS5 AMD GPU)"
EN_TR["Afficher le résumé Vulkan complet"]="Show the full Vulkan summary"
EN_TR["vulkaninfo est absent : utilisez d'abord l'option 1."]="vulkaninfo is missing: use option 1 first."
EN_TR["Mesa et Vulkan mis à jour."]="Mesa and Vulkan updated."
EN_TR["vulkan-tools et mesa-demos installés."]="vulkan-tools and mesa-demos installed."
EN_TR["Vérification RADV"]="RADV check"
EN_TR["Résumé Vulkan"]="Vulkan summary"
# Menu 11
EN_TR["11. Mise à jour Kernel PS5"]="11. PS5 kernel update"
EN_TR["Installer le dernier kernel PS5 (RPM de ps5-linux-patches)"]="Install the latest PS5 kernel (ps5-linux-patches RPM)"
EN_TR["Choisir le kernel à démarrer (copie sur /boot/efi)"]="Choose the boot kernel (copied to /boot/efi)"
EN_TR["Ce kernel n'est publié que pour x86_64."]="This kernel is published for x86_64 only."
EN_TR["Impossible de contacter GitHub pour trouver la dernière release."]="Could not reach GitHub to find the latest release."
EN_TR["Échec du téléchargement du kernel"]="Kernel download failed"
EN_TR["Échec de l'installation du kernel"]="Kernel installation failed"
EN_TR["Aucun kernel trouvé dans /boot."]="No kernel found in /boot."
EN_TR["La copie vers /boot/efi a échoué (ESP en lecture seule ou plein ?)."]="Copy to /boot/efi failed (ESP read-only or full?)."
EN_TR["installé"]="installed"
EN_TR["démarré "]="running "
EN_TR["sur /boot/efi "]="on /boot/efi "
# Menu 12
EN_TR["12. Logithèque PS5"]="12. PS5 software library"
EN_TR["RPM (dépôt officiel)"]="RPM (official repository)"
EN_TR["Flatpak (Flathub)"]="Flatpak (Flathub)"
EN_TR["Vérification impossible (dépôt indisponible ?)."]="Check impossible (repository unavailable?)."
EN_TR["Ajout du dépôt impossible.\n%s"]="Could not add the repository.\n%s"

# ==== CHAÎNES DE FORMAT (utilisées avec trf) ====
EN_FMT["Supprimer ces fichiers ?\n\n%s"]="Remove these files?\n\n%s"
EN_FMT["Kernels installés :\n\n%s\n\nSupprimer les anciens en gardant les 2 plus récents ?"]="Installed kernels:\n\n%s\n\nRemove old kernels, keeping the 2 most recent?"
EN_FMT["À jour.\n\nVersion installée : %s\nVersion GitHub   : %s"]="Up to date.\n\nInstalled version: %s\nGitHub version:    %s"
EN_FMT["Mise à jour disponible.\n\nVersion installée : %s\nVersion GitHub   : %s\n\nUtilisez l option Mettre à jour."]="Update available.\n\nInstalled version: %s\nGitHub version:    %s\n\nUse the Update option."
EN_FMT["Le paquet est introuvable (HTTP %s).\n\n%s"]="Package not found (HTTP %s).\n\n%s"
EN_FMT["Installer le kernel PS5 %s ?\n\nPaquet : linux-ps5-%s-1.x86_64.rpm\n\n- modules dans /usr/lib/modules/%s\n- dracut génère /boot/initrd.img-%s\n- le noyau est copié dans /boot/efi par le paquet, et c est lui qui démarre\n\nUn redémarrage sera nécessaire."]="Install PS5 kernel %s?\n\nPackage: linux-ps5-%s-1.x86_64.rpm\n\n- modules in /usr/lib/modules/%s\n- dracut generates /boot/initrd.img-%s\n- the package copies the kernel to /boot/efi, which is what boots\n\nA reboot will be required."
EN_FMT["Kernel %s installé\n\n"]="Kernel %s installed\n\n"
EN_FMT["  /boot/initrd.img-%s ..... ABSENT (dracut a échoué)\n\n"]="  /boot/initrd.img-%s ..... MISSING (dracut failed)\n\n"
EN_FMT["  /boot/efi/bzImage ....... ABSENT (ESP non monté ?)\n"]="  /boot/efi/bzImage ....... MISSING (ESP not mounted?)\n"
EN_FMT["\nRPM conservé : %s\n"]="\nRPM kept: %s\n"
EN_FMT["\nKernel actuellement démarré : %s"]="\nCurrently running kernel: %s"
EN_FMT["Kernel démarré : %s\nKernel sur /boot/efi : %s\n\nChoisissez le kernel à placer sur /boot/efi (celui qui démarre) :"]="Running kernel: %s\nKernel on /boot/efi: %s\n\nChoose the kernel to place on /boot/efi (the one that boots):"
EN_FMT["Copier le kernel %s sur /boot/efi ?\n\n/boot/vmlinuz-%s      -> /boot/efi/bzImage\n/boot/initrd.img-%s   -> /boot/efi/initrd.img\n\nLes fichiers actuels seront sauvegardés en .bak.\nUn redémarrage sera nécessaire."]="Copy kernel %s to /boot/efi?\n\n/boot/vmlinuz-%s      -> /boot/efi/bzImage\n/boot/initrd.img-%s   -> /boot/efi/initrd.img\n\nCurrent files will be saved as .bak.\nA reboot will be required."
EN_FMT["Kernel %s copié sur /boot/efi.\n\nSauvegarde de l ancien : /boot/efi/bzImage.bak\n\nRedémarrez pour l utiliser."]="Kernel %s copied to /boot/efi.\n\nBackup of the previous one: /boot/efi/bzImage.bak\n\nReboot to use it."
EN_FMT["Ajout du dépôt impossible.\n\n%s"]="Could not add the repository.\n\n%s"
EN_FMT["Mise à jour disponible.\n\nInstallé : %s\nGitHub   : %s"]="Update available.\n\nInstalled: %s\nGitHub:    %s"
EN_FMT["<span size=\"x-large\" weight=\"bold\">PS5 Linux Universal Manager</span>\n\nSystème : %s | Noyau : %s\nChoisissez une action :"]="<span size=\"x-large\" weight=\"bold\">PS5 Linux Universal Manager</span>\n\nSystem: %s | Kernel: %s\nChoose an action:"
EN_FMT["Langue : %s\nClavier : %s\n\nLa session va se fermer pour appliquer les changements.\nContinuer ?"]="Language: %s\nKeyboard: %s\n\nThe session will close to apply the changes.\nContinue?"
EN_FMT["Échec.\n\n%s"]="Failed.\n\n%s"
EN_FMT["État du compte root :\n\n%s\n\nUn mot de passe n est jamais affichable (il est stocké haché).\nVoulez-vous définir un nouveau mot de passe root ?"]="Root account status:\n\n%s\n\nA password can never be displayed (it is stored hashed).\nDo you want to set a new root password?"
# Compléments
EN_FMT["%s supprimé."]="%s removed."
EN_FMT["%s n est pas installé."]="%s is not installed."
EN_FMT["%s est à jour."]="%s is up to date."
EN_FMT["Une mise à jour de %s est disponible."]="An update for %s is available."
EN_FMT["%s est déjà installé."]="%s is already installed."
EN_FMT["%s installé."]="%s installed."
EN_FMT["%s mis à jour."]="%s updated."
EN_FMT["%s est déjà installé (%s)."]="%s is already installed (%s)."
EN_FMT["%s installé via RPM."]="%s installed via RPM."
EN_FMT["%s installé via Flatpak."]="%s installed via Flatpak."
EN_FMT["%s mis à jour (RPM)."]="%s updated (RPM)."
EN_FMT["%s mis à jour (Flatpak)."]="%s updated (Flatpak)."
EN_FMT["%s est à jour (RPM)."]="%s is up to date (RPM)."
EN_FMT["%s est à jour (Flatpak)."]="%s is up to date (Flatpak)."
EN_FMT["Une mise à jour de %s est disponible (RPM)."]="An update for %s is available (RPM)."
EN_FMT["Une mise à jour de %s est disponible (Flatpak)."]="An update for %s is available (Flatpak)."
EN_FMT["Logiciel inconnu : %s"]="Unknown software: %s"
EN_FMT["Dépôt %s désactivé."]="Repository %s disabled."
EN_FMT["Dépôt %s supprimé."]="Repository %s removed."
EN_FMT["Aucun fichier .repo ne définit %s dans /etc/yum.repos.d."]="No .repo file defines %s in /etc/yum.repos.d."
EN_FMT["Suppression de %s impossible."]="Could not remove %s."
EN_FMT["Supprimer le dépôt Flatpak %s ?"]="Remove the Flatpak repository %s?"
EN_FMT["Le RPM téléchargé est vide : %s"]="The downloaded RPM is empty: %s"
EN_FMT["Le fichier /boot/vmlinuz-%s est absent."]="The file /boot/vmlinuz-%s is missing."
EN_FMT["Le fichier /boot/initrd.img-%s est absent : ce kernel ne peut pas démarrer."]="The file /boot/initrd.img-%s is missing: this kernel cannot boot."
EN_FMT["Éditer mon compte (%s) : mot de passe et langue"]="Edit my account (%s): password and language"
EN_FMT["Nouveau mot de passe pour %s (vide = inchangé) :"]="New password for %s (empty = unchanged):"
EN_FMT["Mot de passe de %s mis à jour."]="Password for %s updated."
EN_FMT["Langue du compte %s"]="Language for account %s"
EN_FMT["Langue %s appliquée à %s.\nDéconnectez-vous pour l appliquer."]="Language %s applied to %s.\nLog out to apply it."
EN_FMT["Mot de passe pour %s :"]="Password for %s:"
EN_FMT["Compte %s créé."]="Account %s created."
EN_FMT["La création de %s a échoué."]="Creating %s failed."
EN_FMT["Suppression de %s refusée (compte root ou compte courant)."]="Refusing to delete %s (root or current account)."
EN_FMT["Supprimer le compte %s et son dossier personnel ?"]="Delete account %s and its home directory?"
EN_FMT["Compte %s supprimé."]="Account %s deleted."
EN_FMT["Aucun langpack trouvé pour %s."]="No language pack found for %s."
EN_FMT["Quelle action pour %s ?"]="Which action for %s?"
# ==== Journal / logs ====
EN_TR["14. Journal / Logs"]="14. Logs"
EN_TR["Journal / Logs"]="Logs"
EN_TR["Voir en direct ce que fait le gestionnaire (fenêtre de log, historique, effacement)"]="Watch live what the manager is doing (log window, history, clearing)"
EN_TR["Ouvrir la fenêtre de log en direct"]="Open the live log window"
EN_TR["Voir le journal de cette session"]="View this session's log"
EN_TR["Voir un ancien journal"]="View an older log"
EN_TR["Activer / désactiver la fenêtre automatique"]="Enable / disable the automatic log window"
EN_TR["Effacer les journaux"]="Clear the logs"
EN_TR["Journal"]="Log"
EN_TR["Journaux"]="Logs"
EN_TR["Journal de la session"]="Session log"
EN_TR["Ancien journal"]="Older log"
EN_TR["Choisissez un journal :"]="Choose a log:"
EN_TR["Fichier"]="File"
EN_TR["Aucun journal enregistré pour le moment."]="No log recorded yet."
EN_TR["Aucun terminal graphique détecté (gnome-terminal, kgx, xterm…).\nLe journal est affiché ici à la place."]="No graphical terminal found (gnome-terminal, kgx, xterm…).\nThe log is shown here instead."
EN_TR["Fenêtre de log automatique : activée."]="Automatic log window: enabled."
EN_TR["Fenêtre de log automatique : désactivée."]="Automatic log window: disabled."
EN_TR["Supprimer tous les journaux ?"]="Delete all logs?"
EN_TR["Journaux effacés."]="Logs cleared."
EN_FMT["Ce que fait réellement le gestionnaire, en direct.\nJournal de cette session : %s"]="What the manager is actually doing, live.\nThis session log: %s"

EN_TR["Aucun message."]="No message."
EN_TR["Decky est installé.\\nUtilisez « Mettre à jour » pour passer à la dernière version."]="Decky is installed.\\nUse « Update » to get the latest version."
EN_TR["Decky n est pas installé."]="Decky is not installed."
EN_TR["Etcher est à jour."]="Etcher is up to date."
EN_TR["Etcher installé / mis à jour depuis le RPM GitHub."]="Etcher installed / updated from the GitHub RPM."
EN_TR["Etcher n est pas installé."]="Etcher is not installed."
EN_TR["Impossible de trouver le RPM sur les releases GitHub."]="Could not find the RPM on the GitHub releases."
EN_TR["Langue de l'interface : Français"]="Interface language: French"
EN_TR["Mettre à jour les paquets Mesa & Vulkan"]="Update the Mesa & Vulkan packages"
EN_TR["Supprimer un utilisateur"]="Delete a user"



# ------------------------------------------------------------------------------
# Interface
# ------------------------------------------------------------------------------
info()     { Z --info    --title="$1" --text="$2" --width="${3:-440}"; }
warn()     { Z --warning --title="$1" --text="$2" --width="${3:-440}"; }
error()    { Z --error   --title="$1" --text="$2" --width="${3:-460}"; }
confirm()  { Z --question --title="$1" --text="$2" --width="${3:-440}"; }
ask()      { Z --entry   --title="$1" --text="$2"; }
ask_pass() { Z --password --title="$1" --text="$2"; }
show_text(){
    # Les commandes tournent dans un pty (journal vivant) : on retire les retours
    # chariot et les codes couleur avant de les afficher dans la fenêtre.
    local body
    body="$(printf '%s' "$2" | command tr -d '\r' | command sed -e 's/\x1b\[[0-9;?]*[a-zA-Z]//g')"
    Z --text-info --title="$1" --width="${3:-660}" --height="${4:-440}" <<< "$body"
}

# ------------------------------------------------------------------------------
# Journal : un fichier par session + fenêtre de terminal qui le suit en direct
# ------------------------------------------------------------------------------
LOG_DIR="/var/log/ps5-manager"
LOG_WINDOW_FILE="/etc/ps5-manager/log-window"
SESSION_LOG=""
LOG_WIN_OPEN=""

log_line() {
    [ -n "$SESSION_LOG" ] || return 0
    printf '%s  %s\n' "$(date +%H:%M:%S)" "$*" >> "$SESSION_LOG" 2>/dev/null
}

log_setup() {
    mkdir -p "$LOG_DIR" 2>/dev/null && chmod 0755 "$LOG_DIR" 2>/dev/null
    # rotation : on garde 14 jours de journaux
    find "$LOG_DIR" -maxdepth 1 -name 'session-*.log' -mtime +14 -delete 2>/dev/null
    SESSION_LOG="$LOG_DIR/session-$(date +%Y%m%d-%H%M%S)-$$.log"
    if ! : > "$SESSION_LOG" 2>/dev/null; then
        SESSION_LOG="$(mktemp)"
    fi
    chmod 0644 "$SESSION_LOG" 2>/dev/null
    ln -sfn "$SESSION_LOG" "$LOG_DIR/latest.log" 2>/dev/null
    log_line "════ PS5 Manager — $(date '+%F %T') — utilisateur : $REAL_USER — PID $$"
    log_line "système : $(uname -srm)"
}

log_window_enabled() {
    [ "$(head -n1 "$LOG_WINDOW_FILE" 2>/dev/null)" != "off" ]
}

log_window_toggle() {
    mkdir -p "$(dirname "$LOG_WINDOW_FILE")" 2>/dev/null
    if log_window_enabled; then
        echo "off" > "$LOG_WINDOW_FILE" 2>/dev/null
    else
        echo "on" > "$LOG_WINDOW_FILE" 2>/dev/null
    fi
}

# Ouvre une vraie fenêtre de terminal (celle de l'utilisateur, pas de root) qui
# suit le journal avec tail -f : on y voit dnf, flatpak, git, curl défiler.
open_log_window() {
    local logf="${1:-$SESSION_LOG}" term
    [ -n "$logf" ] && [ -r "$logf" ] || return 1
    [ -n "$LOG_WIN_OPEN" ] && return 0
    local -a cmd=()
    for term in ptyxis kgx gnome-terminal konsole xfce4-terminal mate-terminal tilix xterm; do
        command -v "$term" >/dev/null 2>&1 || continue
        case "$term" in
            ptyxis|kgx|gnome-terminal)            cmd=("$term" -- tail -n +1 -f "$logf") ;;
            konsole|xfce4-terminal|mate-terminal) cmd=("$term" -e tail -n +1 -f "$logf") ;;
            tilix)                                cmd=("$term" -e "tail -n +1 -f $logf") ;;
            xterm)                                cmd=("$term" -T "PS5 Manager - journal" \
                                                       -geometry 110x30 -e tail -n +1 -f "$logf") ;;
        esac
        if run_as_user "${cmd[@]}" >/dev/null 2>&1; then
            LOG_WIN_OPEN="$term"
            return 0
        fi
    done
    return 1
}

# Menu 14
log_menu() {
    local c f logf body
    local -a files=()
    log_setup_once
    c="$(Z --list --title="$(tr '14. Journal / Logs')" \
        --text="$(trf 'Ce que fait réellement le gestionnaire, en direct.\nJournal de cette session : %s' "${SESSION_LOG:-—}")" \
        --width=680 --height=380 --column="ID" --column="$(tr 'Action')" \
        "1" "$(tr 'Ouvrir la fenêtre de log en direct')" \
        "2" "$(tr 'Voir le journal de cette session')" \
        "3" "$(tr 'Voir un ancien journal')" \
        "4" "$(tr 'Activer / désactiver la fenêtre automatique')" \
        "5" "$(tr 'Effacer les journaux')")"
    [ -n "$c" ] || return 0
    case "$c" in
        1)
            if ! open_log_window; then
                warn "$(tr 'Journal')" \
                     "$(tr 'Aucun terminal graphique détecté (gnome-terminal, kgx, xterm…).\nLe journal est affiché ici à la place.')"
                show_text "$(tr 'Journal de la session')" \
                    "$(tail -n 800 "$SESSION_LOG" 2>/dev/null)" 900 620
            fi
            ;;
        2)
            body="$(tail -n 1200 "$SESSION_LOG" 2>/dev/null)"
            [ -n "$body" ] || body="$(tr 'Aucun journal enregistré pour le moment.')"
            show_text "$(tr 'Journal de la session')" "$body" 940 640
            ;;
        3)
            while IFS= read -r f; do files+=("$f"); done < <(
                find "$LOG_DIR" -maxdepth 1 -name 'session-*.log' -printf '%T@ %p\n' 2>/dev/null |
                    sort -rn | head -20 | cut -d' ' -f2-)
            if [ "${#files[@]}" -eq 0 ]; then
                info "$(tr 'Journal')" "$(tr 'Aucun journal enregistré pour le moment.')"
                return 0
            fi
            logf="$(Z --list --title="$(tr 'Ancien journal')" --text="$(tr 'Choisissez un journal :')" \
                --width=760 --height=420 --column="$(tr 'Fichier')" "${files[@]}")"
            [ -n "$logf" ] || return 0
            show_text "$logf" "$(tail -n 1200 "$logf" 2>/dev/null)" 940 640
            ;;
        4)
            log_window_toggle
            if log_window_enabled; then
                info "$(tr 'Journal')" "$(tr 'Fenêtre de log automatique : activée.')"
            else
                info "$(tr 'Journal')" "$(tr 'Fenêtre de log automatique : désactivée.')"
            fi
            ;;
        5)
            if confirm "$(tr 'Journaux')" "$(tr 'Supprimer tous les journaux ?')"; then
                rm -f "$LOG_DIR"/session-*.log "$LOG_DIR"/latest.log 2>/dev/null
                log_line "journaux effacés"
                ln -sfn "$SESSION_LOG" "$LOG_DIR/latest.log" 2>/dev/null
                info "$(tr 'Journal')" "$(tr 'Journaux effacés.')"
            fi
            ;;
    esac
}

log_setup_once() {
    [ -n "$SESSION_LOG" ] || log_setup
}

LAST_LOG=""
# run_with_progress <titre> <texte> <commande...>
# La sortie part dans le journal de session (donc dans la fenêtre de log) et un
# terminal (pty) est simulé quand c'est possible, pour que dnf affiche sa vraie
# progression au lieu d'un simple sablier.
PS5_PTY=""
command -v script >/dev/null 2>&1 && script -q -e -c true /dev/null >/dev/null 2>&1 && PS5_PTY=1

run_with_progress() {
    local title="$1" text="$2"
    shift 2
    local log pid label rc cmdline
    log_setup_once
    if [ -n "$SESSION_LOG" ] && [ -w "$SESSION_LOG" ]; then
        log="$SESSION_LOG"
    else
        log="$(mktemp)"
    fi
    LAST_LOG="$log"
    log_line "──── $title : $text"
    log_line "commande : $*"
    log_window_enabled && open_log_window "$log" >/dev/null 2>&1
    if [ -n "$PS5_PTY" ]; then
        cmdline="$(printf '%q ' "$@")"
        script -q -e -c "$cmdline" /dev/null >>"$log" 2>&1 &
    else
        "$@" >>"$log" 2>&1 &
    fi
    pid=$!
    label="$(tr "Traitement en cours…")"
    ( while kill -0 "$pid" 2>/dev/null; do printf '# %s\n' "$label"; sleep 1; done ) |
        Z --progress --pulse --no-cancel --auto-close --width=500 \
          --title="$title" --text="$text" >/dev/null 2>&1
    wait "$pid"
    rc=$?
    log_line "──── fin : $title (code $rc)"
    return $rc
}

show_log() {
    local tail_txt title="Détail de l'erreur"
    [ -n "${1:-}" ] && title="$1"
    tail_txt="$(tail -n 60 "$LAST_LOG" 2>/dev/null)"
    show_text "$title" "${tail_txt:-$(tr 'Aucun message.')}" 720 480
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
    Z --list --title="$title" --width=480 --height=400 \
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
    sub="$(Z --list --title="Supprimer un dépôt" --text="Que voulez-vous supprimer ?" \
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
                info "Dépôt" "$(trf 'Dépôt %s désactivé.' "$id")"
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
                error "Dépôt" "$(trf 'Aucun fichier .repo ne définit %s dans /etc/yum.repos.d.' "$id")"
                return 1
            fi
            if confirm "Supprimer un dépôt" "$(trf 'Supprimer ces fichiers ?\n\n%s' "$files")"; then
                # shellcheck disable=SC2086
                sudo rm -f $files && info "Dépôt" "$(trf 'Dépôt %s supprimé.' "$id")"
            fi
            ;;
        3)
            local name
            name="$(ask "Supprimer un dépôt Flatpak" "Nom du dépôt (ex: flathub) :")"
            [ -n "$name" ] || return 0
            if confirm "Dépôt Flatpak" "$(trf 'Supprimer le dépôt Flatpak %s ?' "$name")"; then
                sudo flatpak remote-delete --system "$name" 2>/dev/null ||
                    sudo flatpak remote-delete --user "$name" 2>/dev/null ||
                    {
                        error "Dépôt Flatpak" "$(trf 'Suppression de %s impossible.' "$name")"
                        return 1
                    }
                info "Dépôt Flatpak" "$(trf 'Dépôt %s supprimé.' "$name")"
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
    if ! confirm "Anciens kernels" "$(trf 'Kernels installés :\n\n%s\n\nSupprimer les anciens en gardant les 2 plus récents ?' "$out")" 560; then
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
# Menu 7 : alimentation (6 opérations : système, écran, complète)
# ------------------------------------------------------------------------------
# gsettings doit tourner en tant qu'utilisateur : en root il écrit dans la
# base dconf de root et rien ne change pour la session.
pw_system_off() {
    sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
}
pw_system_on() {
    sudo systemctl unmask sleep.target suspend.target hibernate.target hybrid-sleep.target
}
pw_screen_off() {
    run_as_user gsettings set org.gnome.desktop.session idle-delay 0
}
pw_screen_on() {
    run_as_user gsettings set org.gnome.desktop.session idle-delay 300
}
pw_full_off() {
    sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target &&
        run_as_user gsettings set org.gnome.desktop.session idle-delay 0 &&
        run_as_user gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
}
pw_full_on() {
    sudo systemctl unmask sleep.target suspend.target hibernate.target hybrid-sleep.target &&
        run_as_user gsettings set org.gnome.desktop.session idle-delay 300 &&
        run_as_user gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'suspend'
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
        info "PS5 Hardware Control" "$(trf 'À jour.\n\nVersion installée : %s\nVersion GitHub   : %s' "$installed" "$latest")"
    else
        info "PS5 Hardware Control" "$(trf 'Mise à jour disponible.\n\nVersion installée : %s\nVersion GitHub   : %s\n\nUtilisez l option Mettre à jour.' "$installed" "$latest")"
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
        error "Kernel PS5" "$(trf 'Le paquet est introuvable (HTTP %s).\n\n%s' "${code:-?}" "$rpm_url")"
        return 1
    fi

    if ! confirm "Kernel PS5 $ver" "$(trf 'Installer le kernel PS5 %s ?\n\nPaquet : linux-ps5-%s-1.x86_64.rpm\n\n- modules dans /usr/lib/modules/%s\n- dracut génère /boot/initrd.img-%s\n- le noyau est copié dans /boot/efi par le paquet, et c est lui qui démarre\n\nUn redémarrage sera nécessaire.' "$ver" "$ver" "$ver" "$ver")" 540; then
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
        error "Kernel PS5" "$(trf 'Le RPM téléchargé est vide : %s' "$local_rpm")"
        return 1
    fi

    # localpkg_gpgcheck=0 : les RPM de release ne sont pas signés.
    if ! run_with_progress "Kernel PS5" "Installation de linux-ps5 $ver…" \
         sudo dnf install -y --setopt=localpkg_gpgcheck=0 "$local_rpm"; then
        show_log "Échec de l'installation du kernel"
        return 1
    fi

    report="$(trf 'Kernel %s installé\n\n' "$ver")"
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
        report+="$(trf '  /boot/initrd.img-%s ..... ABSENT (dracut a échoué)\n\n' "$ver")"
    fi
    if [ -f /boot/efi/bzImage ]; then
        report+="$(printf '  /boot/efi/bzImage ....... %s\n' "$(esp_kernel_version || echo présent)")"
        report+="$(printf '  /boot/efi/initrd.img .... %s\n' "$([ -s /boot/efi/initrd.img ] && echo présent || echo ABSENT)")"
    else
        report+="$(trf '  /boot/efi/bzImage ....... ABSENT (ESP non monté ?)\n')"
    fi
            report+="$(trf '\nRPM conservé : %s\n' "$local_rpm")"
    report+="$(trf '\nKernel actuellement démarré : %s' "$(uname -r)")"

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

    entry="$(Z --list --title="Kernel à démarrer" \
        --text="$(trf 'Kernel démarré : %s\nKernel sur /boot/efi : %s\n\nChoisissez le kernel à placer sur /boot/efi (celui qui démarre) :' "$cur" "${esp:-inconnu}")" \
        --width=620 --height=420 \
        --column="Version" --column="Statut" "${args[@]}")"
    [ -n "$entry" ] || return 0

    if [ ! -f "/boot/vmlinuz-$entry" ]; then
        error "Kernel" "$(trf 'Le fichier /boot/vmlinuz-%s est absent.' "$entry")"
        return 1
    fi
    if [ ! -f "/boot/initrd.img-$entry" ]; then
        error "Kernel" "$(trf 'Le fichier /boot/initrd.img-%s est absent : ce kernel ne peut pas démarrer.' "$entry")"
        return 1
    fi
    if ! esp_ready; then
        error "Kernel" "L'ESP /boot/efi n'est pas accessible (partition non montée ?).\nImpossible d'y copier le kernel."
        return 1
    fi
    if ! confirm "Kernel à démarrer" "$(trf 'Copier le kernel %s sur /boot/efi ?\n\n/boot/vmlinuz-%s      -> /boot/efi/bzImage\n/boot/initrd.img-%s   -> /boot/efi/initrd.img\n\nLes fichiers actuels seront sauvegardés en .bak.\nUn redémarrage sera nécessaire.' "$entry" "$entry" "$entry")" 560; then
        return 0
    fi

    sudo cp -f /boot/efi/bzImage /boot/efi/bzImage.bak 2>/dev/null || true
    sudo cp -f /boot/efi/initrd.img /boot/efi/initrd.img.bak 2>/dev/null || true
    if sudo cp -f "/boot/vmlinuz-$entry" /boot/efi/bzImage &&
       sudo cp -f "/boot/initrd.img-$entry" /boot/efi/initrd.img &&
       sync; then
        info "Kernel à démarrer" "$(trf 'Kernel %s copié sur /boot/efi.\n\nSauvegarde de l ancien : /boot/efi/bzImage.bak\n\nRedémarrez pour l utiliser.' "$entry")" 560
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
        error "Brave" "$(trf 'Ajout du dépôt impossible.\n\n%s' "$out")"
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
            error "Logithèque" "$(trf 'Logiciel inconnu : %s' "$sw")"
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
                        info "$sw" "$(trf '%s supprimé.' "$sw")"
                    fi
                    ;;
                check)
                    if ! rpm -q "$rpm_name" >/dev/null 2>&1; then
                        info "$sw" "$(trf '%s n est pas installé.' "$sw")"
                    else
                        case "$(rpm_update_state "$rpm_name")" in
                            uptodate) info "$sw" "$(trf '%s est à jour.' "$sw")" ;;
                            update) info "$sw" "$(trf 'Une mise à jour de %s est disponible.' "$sw")" ;;
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
                        info "$sw" "$(trf '%s est déjà installé.' "$sw")"
                    elif flatpak_install "$fp_id"; then
                        info "$sw" "$(trf '%s installé.' "$sw")"
                    fi
                    ;;
                update)
                    if ! flatpak_present "$fp_id"; then
                        info "$sw" "$(trf '%s n est pas installé.' "$sw")"
                    elif run_with_progress "$sw" "Mise à jour de $sw…" \
                         sudo flatpak update --system --noninteractive "$fp_id"; then
                        info "$sw" "$(trf '%s mis à jour.' "$sw")"
                    else
                        show_log "Échec de la mise à jour"
                    fi
                    ;;
                remove|uninstall)
                    if ! flatpak_present "$fp_id"; then
                        info "$sw" "$(trf '%s n est pas installé.' "$sw")"
                    elif flatpak_remove "$fp_id"; then
                        info "$sw" "$(trf '%s supprimé.' "$sw")"
                    fi
                    ;;
                check)
                    if ! flatpak_present "$fp_id"; then
                        info "$sw" "$(trf '%s n est pas installé.' "$sw")"
                    elif flatpak_have_update "$fp_id"; then
                        info "$sw" "$(trf 'Une mise à jour de %s est disponible.' "$sw")"
                    else
                        info "$sw" "$(trf '%s est à jour.' "$sw")"
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
                        info "Etcher" "$(trf 'Mise à jour disponible.\n\nInstallé : %s\nGitHub   : %s' "$inst" "$latest")"
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
                        info "$sw" "$(trf '%s est déjà installé (%s).' "$sw" "$fmt")"
                        return 0
                    fi
                    local how
                    how="$(Z --list --title="$sw" --text="Quel format d'installation ?" \
                        --width=460 --height=250 --column="ID" --column="Format" \
                        "1" "RPM (dépôt officiel)" \
                        "2" "Flatpak (Flathub)")"
                    [ -n "$how" ] || return 0
                    if [ "$how" = "1" ]; then
                        if [ "$sw" = "Opera" ]; then
                            opera_repo_add
                        else
                            brave_repo_add || return 1
                        fi
                        if install_pkgs "$sw" "$rpm_name"; then
                            info "$sw" "$(trf '%s installé via RPM.' "$sw")"
                        fi
                    elif flatpak_install "$fp_id"; then
                        info "$sw" "$(trf '%s installé via Flatpak.' "$sw")"
                    fi
                    ;;
                update)
                    case "$fmt" in
                        rpm)
                            if run_with_progress "$sw" "Mise à jour de $sw…" \
                                 sudo dnf upgrade -y "$rpm_name"; then
                                info "$sw" "$(trf '%s mis à jour (RPM).' "$sw")"
                            else
                                show_log "Échec de la mise à jour"
                            fi
                            ;;
                        flatpak)
                            if run_with_progress "$sw" "Mise à jour de $sw…" \
                                 sudo flatpak update --system --noninteractive "$fp_id"; then
                                info "$sw" "$(trf '%s mis à jour (Flatpak).' "$sw")"
                            else
                                show_log "Échec de la mise à jour"
                            fi
                            ;;
                        *)
                            info "$sw" "$(trf '%s n est pas installé.' "$sw")"
                            ;;
                    esac
                    ;;
                remove|uninstall)
                    case "$fmt" in
                        rpm)
                            remove_pkgs "$sw" "$rpm_name" && info "$sw" "$(trf '%s supprimé.' "$sw")"
                            ;;
                        flatpak)
                            flatpak_remove "$fp_id" && info "$sw" "$(trf '%s supprimé.' "$sw")"
                            ;;
                        *)
                            info "$sw" "$(trf '%s n est pas installé.' "$sw")"
                            ;;
                    esac
                    ;;
                check)
                    case "$fmt" in
                        rpm)
                            case "$(rpm_update_state "$rpm_name")" in
                                uptodate) info "$sw" "$(trf '%s est à jour (RPM).' "$sw")" ;;
                                update) info "$sw" "$(trf 'Une mise à jour de %s est disponible (RPM).' "$sw")" ;;
                                *) info "$sw" "Vérification impossible (dépôt indisponible ?)." ;;
                            esac
                            ;;
                        flatpak)
                            if flatpak_have_update "$fp_id"; then
                                info "$sw" "$(trf 'Une mise à jour de %s est disponible (Flatpak).' "$sw")"
                            else
                                info "$sw" "$(trf '%s est à jour (Flatpak).' "$sw")"
                            fi
                            ;;
                        *)
                            info "$sw" "$(trf '%s n est pas installé.' "$sw")"
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

# Journal de la session (créé au démarrage, avant toute action)
log_setup

# ------------------------------------------------------------------------------
# Boucle principale
# ------------------------------------------------------------------------------
while true; do
    if ! CHOICE="$(Z --list \
        --title="PS5 Linux Universal Manager (nexgen999)" \
        --text="$(trf '<span size="x-large" weight="bold">PS5 Linux Universal Manager</span>\n\nSystème : %s | Noyau : %s\nChoisissez une action :' "$OS_VER" "$K_VER")" \
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
        "13" "Langue / Language"            "Choisir la langue de l'interface : Français ou English" \
        "14" "Journal / Logs"               "Voir en direct ce que fait le gestionnaire (fenêtre de log, historique, effacement)")" ; then
        exit 0
    fi
    [ -n "$CHOICE" ] || exit 0

    case "$CHOICE" in
        1)
            SUB="$(Z --list --title="1. Mise à jour / Désinstallation" --text="Choisissez une option :" \
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
            SUB="$(Z --list --title="2. Configuration des langues" --text="Choisissez une option :" \
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
                        error "Langue" "$(trf 'Aucun langpack trouvé pour %s.' "$LANG_IN")"
                    fi
                    ;;
                3)
                    SELECTED_LANG="$(pick_locale "Langue système")"
                    [ -n "$SELECTED_LANG" ] || continue
                    KB_LIST=()
                    mapfile -t KB_LIST < <(keymap_layouts | head -n 60)
                    [ "${#KB_LIST[@]}" -gt 0 ] || KB_LIST=(fr us de es)
                    SELECTED_KB="$(Z --list --title="Clavier" \
                        --text="Choisissez la disposition du clavier :" --width=460 --height=340 \
                        --column="Layout" "${KB_LIST[@]}")"
                    [ -n "$SELECTED_KB" ] || SELECTED_KB="fr"
                    apply_language_all "$SELECTED_LANG" "$SELECTED_KB"
                    if confirm "Configuration" "$(trf 'Langue : %s\nClavier : %s\n\nLa session va se fermer pour appliquer les changements.\nContinuer ?' "$SELECTED_LANG" "$SELECTED_KB")"; then
                        run_as_user gnome-session-quit --logout --force
                    fi
                    ;;
            esac
            ;;
        3)
            SUB="$(Z --list --title="3. Gestion des dépôts" --text="Choisissez une option :" \
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
                            error "Dépôt" "$(trf 'Échec.\n\n%s' "$OUT")"
                        fi
                    fi
                    ;;
            esac
            ;;
        4)
            SUB="$(Z --list --title="4. Gestion des utilisateurs" --text="Choisissez une option :" \
                --width=560 --height=310 --column="ID" --column="Action" \
                "1" "Voir la liste des utilisateurs" \
                "2" "$(trf 'Éditer mon compte (%s) : mot de passe et langue' "$REAL_USER")" \
                "3" "Ajouter un utilisateur" \
                "4" "Supprimer un compte utilisateur" \
                "5" "Root : état du compte et changement de mot de passe")"
            case "$SUB" in
                1)
                    show_text "Utilisateurs du système" "$(awk -F: '$3>=1000 && $3<65534 {printf "%-20s uid=%-6s home=%-22s shell=%s\n", $1, $3, $6, $7}' /etc/passwd)"
                    ;;
                2)
                    NEW_PASS="$(ask_pass "Mot de passe" "$(trf 'Nouveau mot de passe pour %s (vide = inchangé) :' "$REAL_USER")")"
                    if [ -n "$NEW_PASS" ]; then
                        if printf '%s:%s\n' "$REAL_USER" "$NEW_PASS" | sudo chpasswd; then
                            info "Mot de passe" "$(trf 'Mot de passe de %s mis à jour.' "$REAL_USER")"
                        else
                            error "Mot de passe" "La modification a échoué (mot de passe contenant « : » ?)."
                        fi
                    fi
                    USER_LANG="$(pick_locale "$(trf 'Langue du compte %s' "$REAL_USER")")"
                    if [ -n "$USER_LANG" ]; then
                        applied="0"
                        set_user_language "$REAL_USER" "$USER_LANG" && applied="1"
                        run_as_user gsettings set org.gnome.system.locale region "$USER_LANG" >/dev/null 2>&1 && applied="1"
                        if [ "$applied" = "1" ]; then
                            info "Langue du compte" "$(trf 'Langue %s appliquée à %s.\nDéconnectez-vous pour l appliquer.' "$USER_LANG" "$REAL_USER")"
                        else
                            error "Langue du compte" "Impossible d'appliquer la langue."
                        fi
                    fi
                    ;;
                3)
                    NEW_USER="$(ask "Ajouter un utilisateur" "Nom du nouveau compte :")"
                    [ -n "$NEW_USER" ] || continue
                    NEW_UPASS="$(ask_pass "Mot de passe" "$(trf 'Mot de passe pour %s :' "$NEW_USER")")"
                    if sudo useradd -m -s /bin/bash "$NEW_USER" &&
                       printf '%s:%s\n' "$NEW_USER" "$NEW_UPASS" | sudo chpasswd; then
                        info "Utilisateur" "$(trf 'Compte %s créé.' "$NEW_USER")"
                    else
                        error "Utilisateur" "$(trf 'La création de %s a échoué.' "$NEW_USER")"
                    fi
                    ;;
                4)
                    DEL_USER="$(ask "Supprimer un utilisateur" "Nom du compte à supprimer :")"
                    [ -n "$DEL_USER" ] || continue
                    if [ "$DEL_USER" = "root" ] || [ "$DEL_USER" = "$REAL_USER" ]; then
                        error "Utilisateur" "$(trf 'Suppression de %s refusée (compte root ou compte courant).' "$DEL_USER")"
                    elif confirm "Supprimer $DEL_USER" "$(trf 'Supprimer le compte %s et son dossier personnel ?' "$DEL_USER")"; then
                        if sudo userdel -r "$DEL_USER"; then
                            info "Utilisateur" "$(trf 'Compte %s supprimé.' "$DEL_USER")"
                        else
                            error "Utilisateur" "La suppression a échoué (session ouverte ?)."
                        fi
                    fi
                    ;;
                5)
                    ROOT_STATE="$(sudo passwd -S root 2>&1)"
                    if confirm "Compte root" "$(trf 'État du compte root :\n\n%s\n\nUn mot de passe n est jamais affichable (il est stocké haché).\nVoulez-vous définir un nouveau mot de passe root ?' "$ROOT_STATE")" 520; then
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
            SUB="$(Z --list --title="5. Mises à jour Fedora" --text="Choisissez une option :" \
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
            SUB="$(Z --list --title="6. Maintenance & Nettoyage" --text="Choisissez une option :" \
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
            SUB="$(Z --list --title="7. Management de l'alimentation" --text="Choisissez une option :" \
                --width=580 --height=310 --column="ID" --column="Action" \
                "1" "Activer la veille complète (système + écran)" \
                "2" "Désactiver la veille complète" \
                "3" "Activer la veille système (suspend/hibernate)" \
                "4" "Désactiver la veille système" \
                "5" "Activer la mise en veille de l'écran (5 min)" \
                "6" "Désactiver la mise en veille de l'écran")"
            case "$SUB" in
                1)
                    if pw_full_on; then
                        info "Alimentation" "Veille complète activée (système + écran après 5 min)."
                    else
                        error "Alimentation" "Échec : la veille complète n a pas pu être activée."
                    fi
                    ;;
                2)
                    if pw_full_off; then
                        info "Alimentation" "Veille complète désactivée (système + écran)."
                    else
                        error "Alimentation" "Échec : la veille complète n a pas pu être désactivée."
                    fi
                    ;;
                3)
                    if pw_system_on; then
                        info "Alimentation" "Veille système activée."
                    else
                        error "Alimentation" "Impossible de démasquer les cibles de veille."
                    fi
                    ;;
                4)
                    if pw_system_off; then
                        info "Alimentation" "Veille système désactivée."
                    else
                        error "Alimentation" "Impossible de masquer les cibles de veille."
                    fi
                    ;;
                5)
                    if pw_screen_on; then
                        info "Alimentation" "Veille écran activée (5 min)."
                    else
                        error "Alimentation" "gsettings a échoué (session GNOME absente ?)."
                    fi
                    ;;
                6)
                    if pw_screen_off; then
                        info "Alimentation" "Veille écran désactivée."
                    else
                        error "Alimentation" "gsettings a échoué (session GNOME absente ?)."
                    fi
                    ;;
            esac
            ;;
        8)
            SUB="$(Z --list --title="8. PS5 Fan Manager" --text="Choisissez une option :" \
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
            SUB="$(Z --list --title="9. PS5 Hardware Control" --text="Choisissez une option :" \
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
            SUB="$(Z --list --title="10. Mesa / Vulkan & RADV" --text="Choisissez une option :" \
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
            SUB="$(Z --list --title="11. Mise à jour Kernel PS5" --text="Choisissez une option :" \
                --width=580 --height=250 --column="ID" --column="Action" \
                "1" "Installer le dernier kernel PS5 (RPM de ps5-linux-patches)" \
                "2" "Choisir le kernel à démarrer (copie sur /boot/efi)")"
            case "$SUB" in
                1) kernel_install_latest ;;
                2) kernel_select_default ;;
            esac
            ;;
        12)
            SUB="$(Z --list --title="12. Logithèque PS5" --text="Choisissez un logiciel :" \
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
            ACT="$(Z --list --title="$SUB" --text="$(trf 'Quelle action pour %s ?' "$SUB")" \
                --width=500 --height=310 --column="ID" --column="Action" \
                "1" "Installer" \
                "2" "Désinstaller" \
                "3" "Mettre à jour" \
                "4" "Vérifier les mises à jour")"
            [ -n "$ACT" ] || continue
            # On teste l'identifiant, pas le libellé : le libellé change avec la langue.
            case "$ACT" in
                1) software_action "$SUB" install ;;
                2) software_action "$SUB" remove ;;
                3) software_action "$SUB" update ;;
                4) software_action "$SUB" check ;;
            esac
            ;;
        13)
            if choose_language; then
                if [ "$UI_LANG" = "en" ]; then
                    info "Langue / Language" "Interface language: English"
                else
                    info "Langue / Language" "Langue de l'interface : Français"
                fi
            fi
            ;;
        14)
            log_menu
            ;;
    esac
done
