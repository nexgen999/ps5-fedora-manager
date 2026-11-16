#!/usr/bin/env python3
# ==============================================================================
# PS5 Manager — interface GTK4 / libadwaita (style Paramètres GNOME)
# ------------------------------------------------------------------------------
# L'interface ne fait qu'afficher : tout le travail système reste dans
# ps5-manager.sh, appelé en mode « --cli » (sortie texte, sans zenity).
#
# Prérequis Fedora : python3-gobject, gtk4, libadwaita
#   sudo dnf install python3-gobject gtk4 libadwaita
#
# Lancement : ps5-manager-gui   (demande les droits root via pkexec)
# ==============================================================================

import os
import pwd
import shutil
import subprocess
import sys
import threading

APP_ID = "io.github.nexgen999.Ps5Manager"
LANG_FILE = "/etc/ps5-manager/language"
LOG_WINDOW_FILE = "/etc/ps5-manager/log-window"

SCRIPT_CANDIDATES = [
    "/usr/local/bin/ps5-manager",
    "/opt/ps5-manager/ps5-manager.sh",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ps5-manager.sh"),
]


def find_script():
    for path in SCRIPT_CANDIDATES:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return SCRIPT_CANDIDATES[0]


SCRIPT = find_script()


# ------------------------------------------------------------------------------
# Droits root : le moteur a besoin de root (dnf, /boot/efi, systemctl…).
# On relance l'interface via pkexec, avec sudo en secours.
# ------------------------------------------------------------------------------
def elevate_if_needed():
    if os.geteuid() == 0 or os.environ.get("PS5_MANAGER_ELEVATED"):
        return
    try:
        user = pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        user = os.environ.get("USER", "root")
    display = os.environ.get("DISPLAY", ":0")
    xauth = os.environ.get("XAUTHORITY", os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".Xauthority"))
    self_path = os.path.abspath(sys.argv[0])
    common = [
        "PS5_MANAGER_ELEVATED=1", f"PS5_MANAGER_USER={user}",
        f"DISPLAY={display}", f"XAUTHORITY={xauth}",
        # GTK en root ne peut pas utiliser le socket Wayland de l'utilisateur :
        # on passe par Xwayland avec son autorisation X.
        "GDK_BACKEND=x11",
    ]
    if elev := shutil.which("pkexec"):
        os.execv(elev, [elev, "env", *common, sys.executable, self_path, *sys.argv[1:]])
    if elev := shutil.which("sudo"):
        os.execvp(elev, [elev, "-E", "env", *common, sys.executable, self_path, *sys.argv[1:]])
    sys.stderr.write("Ce gestionnaire doit être lancé en root (pkexec ou sudo).\n")
    raise SystemExit(1)


elevate_if_needed()
os.environ["PS5_MANAGER_ELEVATED"] = "1"
if os.geteuid() == 0:
    os.environ.setdefault("GDK_BACKEND", "x11")

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402


# ------------------------------------------------------------------------------
# Traductions (l'interface suit la langue choisie dans le gestionnaire)
# ------------------------------------------------------------------------------
FR = {
    "app": "PS5 Manager",
    "logs": "Journal / Logs",
    "library": "Logithèque",
    "update": "Mise à jour du manager",
    "lang": "Langues & clavier",
    "repos": "Dépôts",
    "users": "Utilisateurs",
    "fedora": "Mises à jour Fedora",
    "maint": "Maintenance",
    "power": "Alimentation",
    "fan": "Ventilateur",
    "hw": "Hardware Control",
    "mesa": "Mesa / Vulkan",
    "kernel": "Kernel PS5",
    "ui_lang": "Langue de l'interface",
    "live": "Fenêtre de log en direct",
    "live_sub": "Suivre en direct ce que fait le gestionnaire",
    "session": "Journal de cette session",
    "session_sub": "session courante, mise à jour en direct",
    "old": "Anciens journaux",
    "old_sub": "14 derniers jours, consultables un par un",
    "auto": "Ouverture automatique",
    "auto_sub": "Ouvrir la fenêtre au premier travail long",
    "clear": "Effacer les journaux",
    "clear_sub": "Supprime les fichiers de /var/log/ps5-manager",
    "install": "Installer",
    "remove": "Désinstaller",
    "upd": "Mettre à jour",
    "check": "Vérifier",
    "choose_action": "Que faire de %s ?",
    "cache": "Nettoyer le cache DNF",
    "cache_sub": "dnf clean all",
    "autoremove": "Supprimer les orphelins",
    "autoremove_sub": "dnf autoremove",
    "journals": "Réduire les journaux systemd",
    "journals_sub": "journalctl --vacuum-time=7d",
    "tmp": "Nettoyer /tmp et /var/tmp",
    "tmp_sub": "fichiers temporaires",
    "thumbs": "Nettoyer les vignettes",
    "thumbs_sub": "caches de l'utilisateur",
    "disk": "Voir l'espace disque",
    "disk_sub": "df -hT",
    "latest_kernel": "Dernier kernel disponible",
    "latest_kernel_sub": "depuis ps5-linux/ps5-linux-patches",
    "install_kernel": "Installer le dernier kernel",
    "install_kernel_sub": "RPM linux-ps5 puis copie sur /boot/efi",
    "boot_kernel": "Kernel à démarrer",
    "boot_kernel_sub": "choisir le kernel copié sur /boot/efi",
    "list_kernel": "Kernels installés",
    "list_kernel_sub": "versions présentes dans /boot",
    "pending": "Portage en cours",
    "pending_sub": "cette page arrive dans la prochaine version de l'interface",
    "classic": "Ouvrir l'interface classique",
    "classic_sub": "la version zenity, complète dès maintenant",
    "confirm": "Confirmer",
    "cancel": "Annuler",
    "running": "Action en cours…",
    "busy": "Une action est déjà en cours.",
    "done": "Terminé.",
    "failed": "Échec (code %s)",
    "no_log": "Aucun journal pour le moment.",
    "log": "Journal",
    "language": "Langue de l'interface",
    "fr": "Français",
    "en": "English",
    "restart_hint": "La langue sera appliquée au prochain lancement.",
}

EN = {
    "app": "PS5 Manager",
    "logs": "Logs",
    "library": "Software library",
    "update": "Manager update",
    "lang": "Languages & keyboard",
    "repos": "Repositories",
    "users": "Users",
    "fedora": "Fedora updates",
    "maint": "Maintenance",
    "power": "Power",
    "fan": "Fan",
    "hw": "Hardware Control",
    "mesa": "Mesa / Vulkan",
    "kernel": "PS5 kernel",
    "ui_lang": "Interface language",
    "live": "Live log window",
    "live_sub": "Watch what the manager is doing, live",
    "session": "This session's log",
    "session_sub": "current session, updated live",
    "old": "Older logs",
    "old_sub": "last 14 days, one by one",
    "auto": "Open automatically",
    "auto_sub": "Open the window on the first long task",
    "clear": "Clear the logs",
    "clear_sub": "Delete the files in /var/log/ps5-manager",
    "install": "Install",
    "remove": "Uninstall",
    "upd": "Update",
    "check": "Check",
    "choose_action": "What should we do with %s?",
    "cache": "Clean the DNF cache",
    "cache_sub": "dnf clean all",
    "autoremove": "Remove orphaned packages",
    "autoremove_sub": "dnf autoremove",
    "journals": "Shrink the systemd journal",
    "journals_sub": "journalctl --vacuum-time=7d",
    "tmp": "Clean /tmp and /var/tmp",
    "tmp_sub": "temporary files",
    "thumbs": "Clean thumbnails",
    "thumbs_sub": "user caches",
    "disk": "Show disk usage",
    "disk_sub": "df -hT",
    "latest_kernel": "Latest available kernel",
    "latest_kernel_sub": "from ps5-linux/ps5-linux-patches",
    "install_kernel": "Install the latest kernel",
    "install_kernel_sub": "linux-ps5 RPM, then copy to /boot/efi",
    "boot_kernel": "Kernel to boot",
    "boot_kernel_sub": "choose the kernel copied to /boot/efi",
    "list_kernel": "Installed kernels",
    "list_kernel_sub": "versions found in /boot",
    "pending": "Port in progress",
    "pending_sub": "this page arrives in the next version of the interface",
    "classic": "Open the classic interface",
    "classic_sub": "the zenity version, already complete",
    "confirm": "Confirm",
    "cancel": "Cancel",
    "running": "Running…",
    "busy": "An action is already running.",
    "done": "Done.",
    "failed": "Failed (code %s)",
    "no_log": "No log yet.",
    "log": "Log",
    "language": "Interface language",
    "fr": "Français",
    "en": "English",
    "restart_hint": "The language will apply on next launch.",
}


def read_lang():
    try:
        with open(LANG_FILE, encoding="utf-8") as fh:
            value = fh.readline().strip()
        return value if value in ("fr", "en") else "fr"
    except OSError:
        return "fr"


LANG = read_lang()


def T(key):
    return (FR if LANG == "fr" else EN).get(key, key)


# ------------------------------------------------------------------------------
# Fenêtre de journal
# ------------------------------------------------------------------------------
class LogWindow(Adw.Window):
    def __init__(self, parent, title):
        super().__init__(transient_for=parent, title=title, default_width=920, default_height=580)
        self._path = None
        self._offset = 0
        self._timer = None

        self.view = Gtk.TextView(editable=False, monospace=True, cursor_visible=False)
        self.view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.view.set_left_margin(12)
        self.view.set_top_margin(8)
        self.buf = self.view.get_buffer()

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=title))
        clear_btn = Gtk.Button(icon_name="edit-clear-all-symbolic")
        clear_btn.set_tooltip_text(T("clear"))
        clear_btn.connect("clicked", lambda *_: self.buf.set_text(""))
        header.pack_end(clear_btn)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(Gtk.ScrolledWindow(child=self.view, hexpand=True, vexpand=True))
        self.set_content(toolbar)

    def append(self, text):
        if not text:
            return
        if not self.buf.get_text(self.buf.get_start_iter(), self.buf.get_end_iter(), False).endswith("\n"):
            self.buf.insert(self.buf.get_end_iter(), "\n")
        self.buf.insert(self.buf.get_end_iter(), text + "\n")
        self.buf.place_cursor(self.buf.get_end_iter())
        self.view.scroll_to_iter(self.buf.get_end_iter(), 0.0, False, 0.0, 0.0)

    def load_text(self, text):
        self.buf.set_text(text)
        self.view.scroll_to_iter(self.buf.get_end_iter(), 0.0, False, 0.0, 0.0)

    def _tick(self):
        if not self._path:
            return False
        try:
            with open(self._path, encoding="utf-8", errors="replace") as fh:
                fh.seek(self._offset)
                chunk = fh.read()
                self._offset = fh.tell()
        except OSError:
            return True
        if chunk:
            self.append(chunk.rstrip("\n"))
        return True

    def follow(self, path):
        self._path = path
        self._offset = 0
        self._tick()
        if self._timer is None:
            self._timer = GLib.timeout_add(700, self._tick)


# ------------------------------------------------------------------------------
# Fenêtre principale
# ------------------------------------------------------------------------------
class Ps5Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="PS5 Manager", default_width=1180, default_height=760)
        self.busy = False
        self.log_window = None
        self.pages = []
        self.busy_spinner = Gtk.Spinner()

        self.overlay = Adw.ToastOverlay()
        self.split = Adw.NavigationSplitView()
        self.split.set_min_sidebar_width(260)
        self.split.set_max_sidebar_width(340)
        self.split.set_sidebar(self._build_sidebar())
        self.split.set_content(self._build_content())
        self.overlay.set_child(self.split)
        self.set_content(self.overlay)

    # ---- construction ----
    def _build_sidebar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_title_widget(Gtk.Label(label="PS5 Manager"))
        box.append(header)

        listbox = Gtk.ListBox()
        listbox.add_css_class("navigation-sidebar")
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        for index, (key, icon) in enumerate(SECTIONS):
            row = Adw.ActionRow(title=T(key), activatable=True)
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            row.set_activatable_widget(None)
            row.section_index = index
            listbox.append(row)
        listbox.connect("row-activated", self._on_sidebar_row)
        self.sidebar_list = listbox
        box.append(Gtk.ScrolledWindow(child=listbox, hexpand=True, vexpand=True))
        return Adw.NavigationPage(child=box, title="PS5 Manager")

    def _build_content(self):
        self.nav = Adw.NavigationView()
        for key, _icon in SECTIONS:
            self.pages.append(self._make_page(key))
        self.nav.add(self.pages[0])
        self.nav.connect("popped", self._on_popped)
        return Adw.NavigationPage(child=self.nav, title=T("app"))

    def _on_sidebar_row(self, _lb, row):
        target = self.pages[row.section_index]
        while self.nav.get_navigation_stack().get_n_items() > 1:
            self.nav.pop()
        if self.nav.get_visible_page() is not target:
            self.nav.push(target)

    def _on_popped(self, _nav, _page):
        pass

    def _make_page(self, key):
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=T(key)))
        header.pack_end(self.busy_spinner)
        log_btn = Gtk.Button(icon_name="utilities-terminal-symbolic")
        log_btn.set_tooltip_text(T("log"))
        log_btn.connect("clicked", lambda *_: self.open_log(follow=True))
        header.pack_end(log_btn)
        toolbar.add_top_bar(header)

        page = Adw.PreferencesPage()
        builder = PAGE_BUILDERS.get(key)
        if builder:
            builder(self, page)
        else:
            group = Adw.PreferencesGroup(title=T(key))
            group.add(self._row(T("pending"), T("pending_sub"), "dialog-information-symbolic", None))
            group.add(self._row(T("classic"), T("classic_sub"), "utilities-terminal-symbolic",
                                lambda *_: self.open_classic()))
            page.add(group)
        toolbar.set_content(page)
        return Adw.NavigationPage(child=toolbar, title=T(key))

    def _row(self, title, subtitle, icon, callback, suffix="go-next-symbolic"):
        row = Adw.ActionRow(title=title, subtitle=subtitle, activatable=callback is not None)
        if icon:
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
        if suffix:
            row.add_suffix(Gtk.Image.new_from_icon_name(suffix))
        if callback:
            row.connect("activated", callback)
        return row

    # ---- exécution du moteur bash ----
    def run(self, args, title, confirm_text=None):
        if self.busy:
            self.toast(T("busy"))
            return
        if confirm_text:
            self.confirm(title, confirm_text, lambda: self._start(args, title))
        else:
            self._start(args, title)

    def _start(self, args, title):
        self.busy = True
        self.busy_spinner.start()
        self.open_log(follow=False)
        self.log_window.append(f"▶ {title}")
        env = dict(os.environ, PS5_MANAGER_ELEVATED="1")
        try:
            proc = subprocess.Popen(
                [SCRIPT, "--cli", *args],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, env=env,
            )
        except OSError as exc:
            self._finish(127, title, str(exc))
            return
        threading.Thread(target=self._read, args=(proc, title), daemon=True).start()

    def _read(self, proc, title):
        for line in proc.stdout:
            GLib.idle_add(self._on_line, line.rstrip("\n"))
        GLib.idle_add(self._finish, proc.wait(), title, None)

    def _on_line(self, line):
        if self.log_window:
            self.log_window.append(line)
        return False

    def _finish(self, code, title, error):
        self.busy = False
        self.busy_spinner.stop()
        if error:
            self.toast(error)
        elif code == 0:
            self.toast(f"{title} — {T('done')}")
        else:
            self.toast(T("failed") % code)
        return False

    def toast(self, text):
        self.overlay.add_toast(Adw.Toast(title=text, timeout=4))

    # ---- fenêtre de log ----
    def open_log(self, follow):
        if self.log_window is None:
            self.log_window = LogWindow(self, T("log"))
        self.log_window.present()
        if follow is True:
            path = self._session_log_path()
            if path:
                self.log_window.follow(path)
        elif follow is False and not self.log_window._path:
            path = self._session_log_path()
            if path:
                try:
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        self.log_window.load_text(fh.read())
                except OSError:
                    pass

    def _session_log_path(self):
        try:
            out = subprocess.run([SCRIPT, "--cli", "log", "path"], capture_output=True, text=True,
                                 timeout=20, env=dict(os.environ, PS5_MANAGER_ELEVATED="1"))
            return out.stdout.strip() or None
        except (OSError, subprocess.SubprocessError):
            return None

    def open_classic(self):
        env = dict(os.environ, PS5_MANAGER_ELEVATED="1")
        try:
            subprocess.Popen([SCRIPT], env=env, start_new_session=True)
            self.toast(T("classic"))
        except OSError as exc:
            self.toast(str(exc))

    # ---- confirmation ----
    def confirm(self, heading, body, on_ok):
        if hasattr(Adw, "AlertDialog"):
            dialog = Adw.AlertDialog(heading=heading, body=body)
            dialog.add_response("cancel", T("cancel"))
            dialog.add_response("ok", T("confirm"))
            dialog.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")

            def _response(_d, response):
                if response == "ok":
                    on_ok()

            dialog.connect("response", _response)
            dialog.present(self)
        else:  # libadwaita < 1.5
            dialog = Adw.MessageDialog(transient_for=self, heading=heading, body=body)
            dialog.add_response("cancel", T("cancel"))
            dialog.add_response("ok", T("confirm"))
            dialog.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)

            def _response(_d, response):
                if response == "ok":
                    on_ok()

            dialog.connect("response", _response)
            dialog.present()


# ------------------------------------------------------------------------------
# Pages
# ------------------------------------------------------------------------------
SECTIONS = [
    ("logs", "utilities-terminal-symbolic"),
    ("library", "system-software-install-symbolic"),
    ("update", "software-update-available-symbolic"),
    ("lang", "preferences-desktop-locale-symbolic"),
    ("repos", "network-server-symbolic"),
    ("users", "system-users-symbolic"),
    ("fedora", "software-update-available-symbolic"),
    ("maint", "applications-engineering-symbolic"),
    ("power", "preferences-system-power-symbolic"),
    ("fan", "temperature-symbolic"),
    ("hw", "applications-system-symbolic"),
    ("mesa", "video-display-symbolic"),
    ("kernel", "application-x-executable-symbolic"),
    ("ui_lang", "font-select-symbolic"),
]

SOFTWARE = [
    "Steam", "Heroic Games Launcher", "ProtonUp-Qt", "Decky Loader",
    "Etcher", "Opera", "Brave", "Bazaar", "GNOME Extension Manager",
]


def page_logs(win, page):
    group = Adw.PreferencesGroup(title=T("logs"))
    group.add(win._row(T("live"), T("live_sub"), "utilities-terminal-symbolic",
                       lambda *_: win.open_log(follow=True)))
    group.add(win._row(T("session"), T("session_sub"), "text-x-generic-symbolic",
                       lambda *_: win.open_log(follow=True)))
    group.add(win._row(T("old"), T("old_sub"), "folder-documents-symbolic",
                       lambda *_: show_old_logs(win)))
    page.add(group)

    group2 = Adw.PreferencesGroup()
    switch = Adw.SwitchRow(title=T("auto"), subtitle=T("auto_sub"))
    switch.set_active(log_window_enabled())
    switch.connect("notify::active", lambda row, _p: set_log_window(row.get_active()))
    group2.add(switch)
    group2.add(win._row(T("clear"), T("clear_sub"), "user-trash-symbolic",
                        lambda *_: win.run(["log", "clear"], T("clear"),
                                           confirm_text=T("clear_sub"))))
    page.add(group2)


def log_window_enabled():
    try:
        with open(LOG_WINDOW_FILE, encoding="utf-8") as fh:
            return fh.readline().strip() != "off"
    except OSError:
        return True


def set_log_window(enabled):
    try:
        os.makedirs(os.path.dirname(LOG_WINDOW_FILE), exist_ok=True)
        with open(LOG_WINDOW_FILE, "w", encoding="utf-8") as fh:
            fh.write("on\n" if enabled else "off\n")
    except OSError:
        pass


def show_old_logs(win):
    try:
        out = subprocess.run([SCRIPT, "--cli", "log", "list"], capture_output=True, text=True, timeout=20,
                             env=dict(os.environ, PS5_MANAGER_ELEVATED="1"))
        files = [line for line in out.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.SubprocessError):
        files = []
    page = Adw.PreferencesPage()
    group = Adw.PreferencesGroup(title=T("old"))
    if not files:
        group.add(Adw.ActionRow(title=T("no_log")))
    for name in files[:20]:
        group.add(win._row(name, None, "text-x-generic-symbolic",
                           lambda _r, _n=name: show_log_file(win, _n)))
    page.add(group)
    toolbar = Adw.ToolbarView()
    header = Adw.HeaderBar()
    header.set_title_widget(Adw.WindowTitle(title=T("old")))
    toolbar.add_top_bar(header)
    toolbar.set_content(page)
    win.nav.push(Adw.NavigationPage(child=toolbar, title=T("old")))


def log_dir():
    for candidate in ("/var/log/ps5-manager", "/tmp/ps5-manager-logs"):
        if os.path.isdir(candidate):
            return candidate
    return "/var/log/ps5-manager"


def show_log_file(win, name):
    path = name if os.path.isabs(name) else os.path.join(log_dir(), name)
    preview = LogWindow(win, name)
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            preview.load_text(fh.read())
    except OSError as exc:
        preview.load_text(str(exc))
    preview.present()


def page_library(win, page):
    group = Adw.PreferencesGroup(title=T("library"))
    for app_name in SOFTWARE:
        group.add(win._row(app_name, None, "application-x-executable-symbolic",
                           lambda _r, _n=app_name: show_app_actions(win, _n)))
    page.add(group)


def show_app_actions(win, app_name):
    page = Adw.PreferencesPage()
    group = Adw.PreferencesGroup(title=T("choose_action") % app_name)
    actions = [("install", T("install"), "system-software-install-symbolic"),
               ("remove", T("remove"), "user-trash-symbolic"),
               ("update", T("upd"), "software-update-available-symbolic"),
               ("check", T("check"), "dialog-question-symbolic")]
    for action, label, icon in actions:
        group.add(win._row(label, None, icon,
                           lambda _r, _a=action: win.run(["app", app_name, _a],
                                                         f"{app_name} — {label}")))
    page.add(group)
    toolbar = Adw.ToolbarView()
    header = Adw.HeaderBar()
    header.set_title_widget(Adw.WindowTitle(title=app_name))
    toolbar.add_top_bar(header)
    toolbar.set_content(page)
    win.nav.push(Adw.NavigationPage(child=toolbar, title=app_name))


def page_maint(win, page):
    group = Adw.PreferencesGroup(title=T("maint"))
    group.add(win._row(T("cache"), T("cache_sub"), "edit-clear-all-symbolic",
                       lambda *_: win.run(["maint", "cache"], T("cache"))))
    group.add(win._row(T("autoremove"), T("autoremove_sub"), "user-trash-symbolic",
                       lambda *_: win.run(["maint", "autoremove"], T("autoremove"),
                                          confirm_text=T("autoremove_sub"))))
    group.add(win._row(T("journals"), T("journals_sub"), "text-x-generic-symbolic",
                       lambda *_: win.run(["maint", "journal"], T("journals"))))
    group.add(win._row(T("tmp"), T("tmp_sub"), "folder-temp-symbolic",
                       lambda *_: win.run(["maint", "tmp"], T("tmp"),
                                          confirm_text=T("tmp_sub"))))
    group.add(win._row(T("thumbs"), T("thumbs_sub"), "image-x-generic-symbolic",
                       lambda *_: win.run(["maint", "thumbs"], T("thumbs"))))
    group.add(win._row(T("disk"), T("disk_sub"), "drive-harddisk-symbolic",
                       lambda *_: win.run(["maint", "df"], T("disk"))))
    page.add(group)


def page_kernel(win, page):
    group = Adw.PreferencesGroup(title=T("kernel"))
    group.add(win._row(T("latest_kernel"), T("latest_kernel_sub"), "software-update-available-symbolic",
                       lambda *_: win.run(["kernel", "latest"], T("latest_kernel"))))
    group.add(win._row(T("install_kernel"), T("install_kernel_sub"), "system-software-install-symbolic",
                       lambda *_: win.run(["kernel", "install"], T("install_kernel"),
                                          confirm_text=T("install_kernel_sub"))))
    group.add(win._row(T("boot_kernel"), T("boot_kernel_sub"), "media-playback-start-symbolic",
                       lambda *_: show_kernels(win)))
    group.add(win._row(T("list_kernel"), T("list_kernel_sub"), "view-list-symbolic",
                       lambda *_: win.run(["kernel", "list"], T("list_kernel"))))
    page.add(group)


def show_kernels(win):
    try:
        out = subprocess.run([SCRIPT, "--cli", "kernel", "list"], capture_output=True, text=True, timeout=30,
                             env=dict(os.environ, PS5_MANAGER_ELEVATED="1"))
        lines = [line for line in out.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.SubprocessError):
        lines = []
    page = Adw.PreferencesPage()
    group = Adw.PreferencesGroup(title=T("boot_kernel"))
    if not lines:
        group.add(Adw.ActionRow(title=T("no_log")))
    for line in lines:
        parts = line.split("\t")
        version = parts[0]
        flags = []
        if len(parts) > 1 and parts[1] == "1":
            flags.append("running")
        if len(parts) > 2 and parts[2] == "1":
            flags.append("/boot/efi")
        subtitle = " · ".join(flags) if flags else None
        group.add(win._row(version, subtitle, "application-x-executable-symbolic",
                           lambda _r, _v=version: win.run(["kernel", "select", _v],
                                                          f"{T('boot_kernel')} {_v}",
                                                          confirm_text=T("boot_kernel_sub"))))
    page.add(group)
    toolbar = Adw.ToolbarView()
    header = Adw.HeaderBar()
    header.set_title_widget(Adw.WindowTitle(title=T("boot_kernel")))
    toolbar.add_top_bar(header)
    toolbar.set_content(page)
    win.nav.push(Adw.NavigationPage(child=toolbar, title=T("boot_kernel")))


def page_ui_lang(win, page):
    group = Adw.PreferencesGroup(title=T("language"))
    current = LANG

    def switch_language(code):
        try:
            os.makedirs(os.path.dirname(LANG_FILE), exist_ok=True)
            with open(LANG_FILE, "w", encoding="utf-8") as fh:
                fh.write(code + "\n")
        except OSError:
            pass
        win.toast(T("restart_hint"))

    for code in ("fr", "en"):
        row = Adw.ActionRow(title=T(code), activatable=True)
        row.add_prefix(Gtk.Image.new_from_icon_name("preferences-desktop-locale-symbolic"))
        if code == current:
            row.add_suffix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
        row.connect("activated", lambda _r, _c=code: switch_language(_c))
        group.add(row)
    page.add(group)


PAGE_BUILDERS = {
    "logs": page_logs,
    "library": page_library,
    "maint": page_maint,
    "kernel": page_kernel,
    "ui_lang": page_ui_lang,
}


# ------------------------------------------------------------------------------
class Ps5App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = Ps5Window(self)
        win.present()


def main():
    import warnings

    warnings.simplefilter("ignore", DeprecationWarning)
    for attr in ("NavigationView", "NavigationPage", "PreferencesPage", "ToolbarView"):
        if not hasattr(Adw, attr):
            sys.stderr.write(
                f"Adw.{attr} est absent : libadwaita 1.4 ou plus récent est requis "
                "(Fedora 39+). Mettez libadwaita à jour, ou utilisez l'interface classique.\n")
            return 1
    if not os.access(SCRIPT, os.X_OK) and not os.path.isfile(SCRIPT):
        sys.stderr.write(
            "ps5-manager.sh est introuvable. Lancez le gestionnaire classique une fois "
            "pour l'installer, ou définissez PS5_MANAGER_SCRIPT.\n")
    app = Ps5App()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
