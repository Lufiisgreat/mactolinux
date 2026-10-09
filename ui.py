#!/usr/bin/env python3
import json
import os
import shutil
import signal
import subprocess
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk

try:
    gi.require_version("WebKit", "6.0")
    gi.require_version("Soup", "3.0")
    from gi.repository import WebKit
    from gi.repository import Soup
except (ImportError, ValueError):
    WebKit = None
    Soup = None

try:
    gi.require_version("Secret", "1")
    from gi.repository import Secret
except (ImportError, ValueError):
    Secret = None

import mods


HERE = Path(__file__).resolve().parent
DATA = HERE / "DO_NOT_SHARE"
CLIENT = HERE / "RobloxVersion/RobloxPlayer.app/Contents/MacOS/RobloxPlayer"
VERSION_FILE = HERE / "RobloxVersion/.version"
APPIMAGE = HERE / "RobloxLinux.AppImage"
SETTINGS_FILE = DATA / "settings.json"
LAUNCHER_VERSION_FILE = DATA / "launcher-version"
LATEST_COMMIT_URL = (
    "https://api.github.com/repos/Lufiisgreat/mactolinux/commits/main"
)
FFLAGS_FILE = HERE / "FFlags.json"
TEXTURE_FLAGS = {
    "DFFlagTextureQualityOverrideEnabled",
    "DFIntTextureQualityOverride",
}
DESKTOP_FILE_NAME = "roblox-linux-release.desktop"
DESKTOP_SHORTCUT_MARKER = "X-RobloxLinuxRelease=true"
APP_NAME = "Mactolinux"
ROBLOX_SESSION_SCHEMA = (
    Secret.Schema.new(
        "org.mactolinux.RobloxSession",
        Secret.SchemaFlags.NONE,
        {"application": Secret.SchemaAttributeType.STRING},
    )
    if Secret is not None
    else None
)
ROBLOX_SESSION_ATTRIBUTES = {"application": "mactolinux"}
ROBLOX_SESSION_COOKIE = ".ROBLOSECURITY"


CSS = b"""
window {
  background: @app_bg;
  color: @app_fg;
}
headerbar {
  background: @header_top;
  border-bottom: 1px solid @border;
  box-shadow: none;
  min-height: 44px;
}
headerbar .title {
  font-weight: 700;
}
button {
  background: @button_bg;
  color: @app_fg;
  border-color: @border;
  border-radius: 5px;
  transition: 120ms ease-out;
}
button:hover {
  background: @button_hover;
}
button:active {
  background: @button_selected;
}
button:checked {
  background: @button_selected;
}
.content {
  padding: 28px 32px;
}
.intro {
  background: transparent;
  border: none;
  border-radius: 0;
  padding: 8px 0 12px;
}
.intro-title {
  font-size: 23px;
  font-weight: 700;
}
.intro-copy {
  color: @secondary_fg;
  font-size: 14px;
}
.welcome-row {
  min-height: 52px;
}
.welcome-icon {
  color: @accent;
  background: transparent;
  border-radius: 0;
  padding: 0;
}
.status {
  background: transparent;
  border: none;
  border-radius: 0;
  padding: 8px 0;
}
.version {
  color: @secondary_fg;
  font-size: 12px;
}
.actions button {
  min-height: 40px;
  padding: 0 16px;
}
button.suggested-action {
  background: @accent;
  color: #fff;
  border-color: @accent;
  font-weight: 700;
  border-radius: 5px;
}
button.suggested-action:hover {
  background: @accent_hover;
  border-color: @accent_hover;
}
switch:checked {
  background-color: @accent;
}
.footer {
  color: @footer_fg;
  font-size: 11px;
}
.page-title {
  font-size: 23px;
  font-weight: 700;
}
.page-copy {
  color: @secondary_fg;
}
.app-shell {
  background: @app_bg;
}
.discover-page {
  background: #fff;
}
.discover-status {
  padding: 8px 12px;
  background: @button_hover;
  color: @secondary_fg;
  font-size: 12px;
}
.discover-fallback {
  padding: 32px;
}
.discover-fallback-title {
  font-size: 20px;
  font-weight: 700;
}
.sidebar {
  background: @sidebar_bg;
  border-right: 1px solid @border;
  padding: 14px 8px;
  min-width: 180px;
}
.sidebar-brand {
  padding: 4px 10px 10px;
}
.sidebar-brand-label {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 1px;
}
.nav {
  padding-top: 2px;
}
.nav button.nav-button {
  min-height: 38px;
  padding: 0 9px;
  background: transparent;
  border-color: transparent;
  border-radius: 4px;
  color: @secondary_fg;
  font-size: 13px;
}
.nav button.nav-button:hover {
  background: @button_hover;
  color: @app_fg;
}
.nav button.nav-button.selected {
  background: @nav_selected;
  color: @accent;
  font-weight: 600;
}
.nav-section-label {
  padding: 12px 10px 5px;
  color: @footer_fg;
  font-size: 10px;
  font-weight: 700;
}
.nav-button-content {
  min-width: 150px;
}
.nav-button-content image {
  margin-right: 5px;
}
.nav-button.selected image {
  color: @accent;
}
.heading {
  font-weight: 650;
}
separator {
  background: @border;
}
.danger {
  color: @secondary_fg;
}
.danger:hover {
  color: @app_fg;
}
"""

THEMES = {
    "light": b"""
@define-color app_bg #ffffff;
@define-color app_fg #191b1f;
@define-color header_top #ffffff;
@define-color border #e1e3e6;
@define-color sidebar_bg #f7f7f8;
@define-color button_bg #ffffff;
@define-color button_hover #f2f3f5;
@define-color button_selected #e9eaec;
@define-color nav_selected #eef3ff;
@define-color intro_start #ffffff;
@define-color intro_border #e1e3e6;
@define-color status_bg #ffffff;
@define-color secondary_fg #60656b;
@define-color footer_fg #777d83;
@define-color accent #335fff;
@define-color accent_hover #244fe5;
""",
    "dark": b"""
@define-color app_bg #191a1b;
@define-color app_fg #f7f7f8;
@define-color header_top #191a1b;
@define-color border #343638;
@define-color sidebar_bg #191a1b;
@define-color button_bg #242526;
@define-color button_hover #303234;
@define-color button_selected #3b3d3f;
@define-color nav_selected #252c3b;
@define-color intro_start #191a1b;
@define-color intro_border #343638;
@define-color status_bg #191a1b;
@define-color secondary_fg #b0b4b8;
@define-color footer_fg #858a8e;
@define-color accent #6b91ff;
@define-color accent_hover #527dff;
""",
}


def installed_version():
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def installation_complete(version=None):
    if version is None:
        version = installed_version()
    return (
        APPIMAGE.is_file()
        and os.access(APPIMAGE, os.X_OK)
        and CLIENT.is_file()
        and os.access(CLIENT, os.X_OK)
        and bool(version)
        and (HERE / "RobloxVersion/spv-cache-v1/report.json").is_file()
    )


def desktop_shortcut_path():
    desktop_dir = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP)
    return Path(desktop_dir or (Path.home() / "Desktop")) / DESKTOP_FILE_NAME


def quote_desktop_exec_argument(argument):
    if any(character in argument for character in ('"', "\n", "\r")):
        raise ValueError("The launcher path contains unsupported desktop-entry characters.")
    escaped = argument.replace("%", "%%").replace("\\", "\\\\")
    return f'"{escaped}"'


def run_logged(args, log_path):
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DATA, 0o700)
    with log_path.open("w", encoding="utf-8") as log:
        result = subprocess.run(
            args,
            cwd=HERE,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return result.returncode


class RobloxLauncher(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.robloxlinux.release",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.window = None
        self.stack = None
        self.navigation = None
        self.navigation_buttons = {}
        self.sidebar = None
        self.discover_status = None
        self.web_view = None
        self.web_network_session = None
        self.web_cookie_manager = None
        self.discover_loaded = False
        self.cookie_restore_pending = 0
        self.cookie_restore_errors = []
        self.cookie_save_source = 0
        self.cookie_save_generation = 0
        self.cookie_save_lock = threading.Lock()
        self.startup_check_started = False
        self.launcher_startup_check_started = False
        self.running_monitor_started = False
        self.fullscreen_window_ids = {}
        self.fullscreen_warning_shown = False
        self.job_running = False
        self.play_button = None
        self.terminate_button = None
        self.update_button = None
        self.launcher_update_button = None
        self.desktop_button = None
        self.remove_desktop_button = None
        self.sidebar_play_button = None
        self.uninstall_action = None
        self.uninstall_status = None
        self.status_title = None
        self.status_copy = None
        self.status_icon = None
        self.spinner = None
        self.theme_provider = None
        self.settings = {
            "theme": "light",
            "check_updates_on_startup": True,
            "modifications_enabled": False,
        }
        self.settings_error = ""
        self.settings_status = None
        self.theme_buttons = {}
        self.startup_updates_switch = None
        self.fflag_enabled_switch = None
        self.fflag_quality_dropdown = None
        self.fflag_status = None
        self.fflag_values = {}
        self.fflag_error = ""
        self.modifications_switch = None
        self.modifications_switch_handler = None
        self.modifications_status = None
        self.modifications_button = None
        self.apply_modifications_button = None
        self.reset_modifications_button = None

        try:
            if SETTINGS_FILE.exists():
                saved_settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                if not isinstance(saved_settings, dict):
                    raise ValueError("Settings must be a JSON object.")
                theme = saved_settings.get("theme", "light")
                check_updates = saved_settings.get("check_updates_on_startup", True)
                modifications_enabled = saved_settings.get(
                    "modifications_enabled", False
                )
                if theme not in THEMES:
                    raise ValueError("The saved theme must be 'light' or 'dark'.")
                if not isinstance(check_updates, bool):
                    raise ValueError("The startup update setting must be a boolean.")
                if not isinstance(modifications_enabled, bool):
                    raise ValueError("The modifications setting must be a boolean.")
                self.settings.update(
                    theme=theme,
                    check_updates_on_startup=check_updates,
                    modifications_enabled=modifications_enabled,
                )
        except (OSError, json.JSONDecodeError, ValueError) as error:
            self.settings_error = f"Could not load settings: {error}"

    def do_activate(self):
        if self.window is None:
            self.build_window()
        self.refresh_state()
        self.window.present()
        if not self.running_monitor_started:
            self.running_monitor_started = True
            GLib.timeout_add_seconds(2, self.refresh_running_state)
        if self.settings["check_updates_on_startup"] and not self.startup_check_started:
            self.startup_check_started = True
            GLib.idle_add(self.startup_update)
        elif not self.launcher_startup_check_started:
            self.launcher_startup_check_started = True
            GLib.idle_add(self.check_launcher_updates)

    def build_window(self):
        display = Gdk.Display.get_default()
        self.theme_provider = Gtk.CssProvider()
        self.theme_provider.load_from_data(THEMES["dark"] + CSS)
        Gtk.StyleContext.add_provider_for_display(
            display, self.theme_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.window = Gtk.ApplicationWindow(application=self, title=APP_NAME)
        self.window.set_default_size(1200, 760)

        header = Gtk.HeaderBar()
        self.window.set_titlebar(header)
        menu_button = Gtk.Button.new_from_icon_name("open-menu-symbolic")
        menu_button.add_css_class("flat")
        menu_button.set_tooltip_text("Show or hide navigation")
        menu_button.connect("clicked", self.toggle_sidebar)
        header.pack_start(menu_button)

        header_title = Gtk.Label(label="ROBLOX")
        header_title.add_css_class("sidebar-brand-label")
        header.set_title_widget(header_title)

        account_button = Gtk.Button.new_from_icon_name(
            "preferences-system-symbolic"
        )
        account_button.add_css_class("flat")
        account_button.set_tooltip_text("Settings")
        account_button.connect("clicked", self.show_page, "settings")
        header.pack_end(account_button)

        shell = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=0
        )
        shell.add_css_class("app-shell")
        self.window.set_child(shell)

        self.sidebar = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=10
        )
        self.sidebar.set_size_request(185, -1)
        self.sidebar.add_css_class("sidebar")
        shell.append(self.sidebar)

        self.sidebar.append(self.secondary_label("MENU", "nav-section-label"))

        self.navigation = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4
        )
        self.navigation.add_css_class("nav")
        self.sidebar.append(self.navigation)
        for page_name, label, icon_name in (
            ("home", "Discover", "go-home-symbolic"),
            ("launcher", "Launcher", "applications-games-symbolic"),
            ("fflags", "FFlags & Mods", "applications-system-symbolic"),
            ("settings", "Settings", "preferences-system-symbolic"),
            ("info", "About", "help-about-symbolic"),
            ("uninstall", "Uninstall", "user-trash-symbolic"),
        ):
            button = Gtk.Button()
            button.add_css_class("nav-button")
            if page_name == "home":
                button.add_css_class("selected")
            button.connect("clicked", self.show_page, page_name)
            button_content = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL, spacing=10
            )
            button_content.add_css_class("nav-button-content")
            button_content.append(Gtk.Image.new_from_icon_name(icon_name))
            button_content.append(Gtk.Label(label=label))
            button.set_child(button_content)
            self.navigation_buttons[page_name] = button
            self.navigation.append(button)

        self.sidebar.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self.sidebar_play_button = Gtk.Button(label="Play Roblox")
        self.sidebar_play_button.add_css_class("suggested-action")
        self.sidebar_play_button.connect("clicked", self.play)
        self.sidebar_play_button.set_margin_top(4)
        self.sidebar_play_button.set_margin_start(4)
        self.sidebar_play_button.set_margin_end(4)
        self.sidebar.append(self.sidebar_play_button)
        self.sidebar.set_visible(False)

        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)
        shell.append(self.stack)
        self.apply_theme(self.settings["theme"])

        discover_page = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=0
        )
        discover_page.add_css_class("discover-page")
        self.stack.add_named(discover_page, "home")
        if WebKit is not None:
            try:
                self.web_network_session = WebKit.NetworkSession.new_ephemeral()
                self.web_view = WebKit.WebView(
                    network_session=self.web_network_session
                )
            except (OSError, GLib.Error) as error:
                self.build_discover_fallback(
                    discover_page,
                    f"Could not prepare private Roblox browser data: {error}",
                )
            else:
                self.discover_status = Gtk.Label()
                self.discover_status.add_css_class("discover-status")
                self.discover_status.set_xalign(0)
                self.discover_status.set_wrap(True)
                self.discover_status.set_visible(False)
                discover_page.append(self.discover_status)
                self.web_view.set_hexpand(True)
                self.web_view.set_vexpand(True)
                self.web_view.connect(
                    "decide-policy", self.on_web_decide_policy
                )
                self.web_view.connect("load-failed", self.on_web_load_failed)
                discover_page.append(self.web_view)
                self.web_cookie_manager = (
                    self.web_network_session.get_cookie_manager()
                )
                self.web_cookie_manager.connect(
                    "changed", self.on_browser_cookies_changed
                )
                if Secret is None:
                    self.show_discover_message(
                        "KDE Wallet support is unavailable; your Roblox login "
                        "will not be saved."
                    )
        else:
            self.build_discover_fallback(
                discover_page,
                "The embedded Roblox website needs WebKitGTK 6.0.",
            )

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        content.add_css_class("content")
        content.set_margin_start(2)
        self.stack.add_named(content, "launcher")

        intro = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        intro.add_css_class("intro")
        content.append(intro)
        welcome_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        welcome_row.add_css_class("welcome-row")
        intro.append(welcome_row)
        welcome_icon = Gtk.Image.new_from_icon_name("applications-games-symbolic")
        welcome_icon.set_pixel_size(36)
        welcome_icon.add_css_class("welcome-icon")
        welcome_row.append(welcome_icon)
        welcome_text = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=5
        )
        welcome_text.set_valign(Gtk.Align.CENTER)
        welcome_row.append(welcome_text)
        heading = self.label("For You")
        heading.add_css_class("intro-title")
        welcome_text.append(heading)
        welcome_copy = self.secondary_label(
            "Your Roblox client, ready to play.",
            "intro-copy",
        )
        welcome_copy.set_wrap(True)
        welcome_text.append(welcome_copy)

        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        status_row.add_css_class("status")
        content.append(status_row)
        self.status_icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
        status_row.append(self.status_icon)
        status_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        status_text.set_hexpand(True)
        status_row.append(status_text)
        self.status_title = self.label("")
        self.status_title.add_css_class("heading")
        self.status_copy = self.secondary_label("", "dim-label")
        self.status_copy.set_wrap(True)
        status_text.append(self.status_title)
        status_text.append(self.status_copy)
        self.spinner = Gtk.Spinner()
        status_row.append(self.spinner)

        self.version_badge = self.secondary_label("", "version")
        content.append(self.version_badge)

        self.play_button = self.action_button(
            "media-playback-start-symbolic", "Play Roblox", self.play
        )
        self.play_button.add_css_class("suggested-action")
        self.terminate_button = self.action_button(
            "process-stop-symbolic", "Terminate Roblox", self.terminate_roblox
        )
        self.terminate_button.add_css_class("danger")
        self.terminate_button.set_visible(False)
        self.update_button = self.action_button(
            "software-update-available-symbolic",
            "Check for Roblox updates",
            self.start_update,
        )
        self.launcher_update_button = self.action_button(
            "software-update-available-symbolic",
            "Check for Mactolinux updates",
            self.check_launcher_updates,
        )

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        buttons.add_css_class("actions")
        buttons.append(self.play_button)
        buttons.append(self.terminate_button)
        buttons.append(self.update_button)
        content.append(buttons)

        launcher_update_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=9
        )
        launcher_update_row.add_css_class("actions")
        launcher_update_row.append(self.launcher_update_button)
        content.append(launcher_update_row)

        shortcut_buttons = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=9
        )
        self.desktop_button = Gtk.Button(label="Create desktop shortcut")
        self.desktop_button.connect("clicked", self.create_desktop_shortcut)
        shortcut_buttons.append(self.desktop_button)
        self.remove_desktop_button = Gtk.Button(label="Remove desktop shortcut")
        self.remove_desktop_button.connect(
            "clicked", self.remove_desktop_shortcut
        )
        self.remove_desktop_button.set_visible(False)
        shortcut_buttons.append(self.remove_desktop_button)
        content.append(shortcut_buttons)

        separator = Gtk.Separator()
        content.append(separator)
        footer = self.secondary_label(
            "Roblox login sessions are encrypted in the desktop keyring; "
            "diagnostic logs remain in DO_NOT_SHARE.",
            "footer",
        )
        footer.set_wrap(True)
        content.append(footer)

        uninstall_page = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=16
        )
        uninstall_page.add_css_class("content")
        self.stack.add_named(uninstall_page, "uninstall")
        uninstall_title = self.label("Uninstall Roblox")
        uninstall_title.add_css_class("page-title")
        uninstall_page.append(uninstall_title)
        uninstall_page.append(
            self.secondary_label(
                "Remove the installed Roblox client, prepared shaders and "
                "desktop shortcut.",
                "page-copy",
            )
        )
        data_note = self.secondary_label(
            "Your encrypted Roblox login in the desktop keyring, settings "
            "and logs will be kept.",
            "page-copy",
        )
        data_note.set_wrap(True)
        uninstall_page.append(data_note)
        self.uninstall_status = self.secondary_label(
            "An update is running. Wait for it to finish before uninstalling.",
            "page-copy",
        )
        self.uninstall_status.set_wrap(True)
        self.uninstall_status.set_visible(False)
        uninstall_page.append(self.uninstall_status)
        self.uninstall_action = Gtk.Button(label="Uninstall Roblox")
        self.uninstall_action.add_css_class("danger")
        self.uninstall_action.set_halign(Gtk.Align.START)
        self.uninstall_action.connect("clicked", self.confirm_uninstall)
        uninstall_page.append(self.uninstall_action)

        self.build_fflags_page()
        self.build_settings_page()
        info_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        info_page.add_css_class("content")
        self.stack.add_named(info_page, "info")
        info_title = self.label("Info")
        info_title.add_css_class("page-title")
        info_page.append(info_title)
        info_message = self.secondary_label(
            "Mactolinux helps you install and launch the Roblox macOS client "
            "on Linux. Use the Launcher page to play or update, Discover to "
            "browse Roblox, FFlags to manage the "
            "texture-quality override, and Settings to choose a theme or "
            "startup update checks.",
            "page-copy",
        )
        info_message.set_wrap(True)
        info_page.append(info_message)
        info_links = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=9
        )
        info_page.append(info_links)
        icon_theme = Gtk.IconTheme.get_for_display(display)
        github_icon = (
            "github"
            if icon_theme.has_icon("github")
            else "web-browser-symbolic"
        )
        for uri, label_text in (
            ("https://github.com/Lufiisgreat/mactolinux", "GitHub repository"),
            ("https://github.com/Lufiisgreat", "Made by Lufiisgreat"),
        ):
            link_button = Gtk.LinkButton(uri=uri)
            link_row = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL, spacing=7
            )
            link_row.append(Gtk.Image.new_from_icon_name(github_icon))
            link_row.append(Gtk.Label(label=label_text))
            link_button.set_child(link_row)
            info_links.append(link_button)

        checking_page = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=16
        )
        checking_page.add_css_class("content")
        checking_page.set_valign(Gtk.Align.CENTER)
        checking_page.set_halign(Gtk.Align.CENTER)
        self.stack.add_named(checking_page, "checking")
        self.loading_spinner = Gtk.Spinner()
        self.loading_spinner.set_size_request(42, 42)
        self.loading_spinner.set_halign(Gtk.Align.CENTER)
        checking_page.append(self.loading_spinner)
        self.loading_title = self.label("Checking for Roblox updates")
        self.loading_title.add_css_class("page-title")
        self.loading_title.set_halign(Gtk.Align.CENTER)
        checking_title_row = Gtk.Box()
        checking_title_row.set_halign(Gtk.Align.CENTER)
        checking_title_row.append(self.loading_title)
        checking_page.append(checking_title_row)
        self.loading_copy = self.secondary_label(
            "This may take a moment. Your launcher menu will appear when the "
            "check is complete.",
            "page-copy",
        )
        self.loading_copy.set_xalign(0.5)
        self.loading_copy.set_halign(Gtk.Align.CENTER)
        self.loading_copy.set_wrap(True)
        checking_page.append(self.loading_copy)
        self.show_page(None, "launcher")

    def apply_theme(self, theme):
        self.theme_provider.load_from_data(THEMES[theme] + CSS)
        Gtk.Settings.get_default().set_property(
            "gtk-interface-color-scheme",
            Gtk.InterfaceColorScheme.DARK
            if theme == "dark"
            else Gtk.InterfaceColorScheme.LIGHT,
        )

    def save_settings(self):
        temporary_path = None
        try:
            DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(DATA, 0o700)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=DATA,
                prefix=".settings-",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(self.settings, temporary_file, indent=2)
                temporary_file.write("\n")
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, SETTINGS_FILE)
            self.settings_status.set_text("Settings saved.")
        except OSError as error:
            self.settings_status.set_text(f"Could not save settings: {error}")
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

    def on_theme_toggled(self, button, theme):
        if button.get_active():
            self.settings["theme"] = theme
            self.apply_theme(theme)
            self.save_settings()

    def on_startup_updates_toggled(self, switch, _state):
        self.settings["check_updates_on_startup"] = switch.get_active()
        self.save_settings()

    def build_settings_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.add_css_class("content")
        self.stack.add_named(page, "settings")
        title = self.label("Settings")
        title.add_css_class("page-title")
        page.append(title)
        page.append(
            self.secondary_label(
                "Customize how the launcher looks and checks for Roblox updates.",
                "page-copy",
            )
        )

        appearance_heading = self.label("Appearance")
        appearance_heading.add_css_class("heading")
        page.append(appearance_heading)
        appearance = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        page.append(appearance)
        first_theme_button = None
        for theme in ("light", "dark"):
            button = Gtk.ToggleButton(label=theme.capitalize())
            if first_theme_button:
                button.set_group(first_theme_button)
            else:
                first_theme_button = button
            button.set_active(theme == self.settings["theme"])
            button.connect("toggled", self.on_theme_toggled, theme)
            self.theme_buttons[theme] = button
            appearance.append(button)

        update_heading = self.label("Updates")
        update_heading.add_css_class("heading")
        page.append(update_heading)
        update_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        page.append(update_row)
        update_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        update_text.set_hexpand(True)
        update_row.append(update_text)
        update_text.append(self.label("Check for updates on startup"))
        update_text.append(
            self.secondary_label(
                "Automatically check for a newer Roblox client when the launcher opens.",
                "page-copy",
            )
        )
        self.startup_updates_switch = Gtk.Switch()
        self.startup_updates_switch.set_valign(Gtk.Align.CENTER)
        self.startup_updates_switch.set_active(
            self.settings["check_updates_on_startup"]
        )
        self.startup_updates_switch.connect(
            "notify::active", self.on_startup_updates_toggled
        )
        update_row.append(self.startup_updates_switch)

        self.settings_status = self.secondary_label("", "page-copy")
        self.settings_status.set_wrap(True)
        page.append(self.settings_status)
        if self.settings_error:
            self.settings_status.set_text(self.settings_error)

    def build_fflags_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.add_css_class("content")
        self.stack.add_named(page, "fflags")
        title = self.label("Recommended FFlags")
        title.add_css_class("page-title")
        page.append(title)
        description = self.secondary_label(
            "Manage the recommended texture-quality override. These are the only "
            "flags exposed here; Roblox may ignore unsupported flags.",
            "page-copy",
        )
        description.set_wrap(True)
        page.append(description)

        try:
            self.fflag_values = json.loads(FFLAGS_FILE.read_text(encoding="utf-8"))
            if not isinstance(self.fflag_values, dict):
                raise ValueError("FFlags.json must contain a JSON object.")
            if any(not isinstance(value, str) for value in self.fflag_values.values()):
                raise ValueError("FFlags.json values must be strings.")
        except (OSError, json.JSONDecodeError, ValueError) as error:
            self.fflag_error = f"Could not load FFlags.json: {error}"
            self.fflag_values = {}

        enabled_value = self.fflag_values.get(
            "DFFlagTextureQualityOverrideEnabled", "False"
        )
        quality_value = self.fflag_values.get("DFIntTextureQualityOverride", "3")
        if enabled_value not in ("True", "False"):
            self.fflag_error = (
                "Could not load FFlags.json: "
                "DFFlagTextureQualityOverrideEnabled must be 'True' or 'False'."
            )
            enabled_value = "False"
        if quality_value not in ("0", "1", "2", "3"):
            self.fflag_error = (
                "Could not load FFlags.json: DFIntTextureQualityOverride "
                "must be between 0 and 3."
            )
            quality_value = "3"

        flag_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        page.append(flag_row)
        flag_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        flag_text.set_hexpand(True)
        flag_row.append(flag_text)
        flag_text.append(self.label("Enable texture-quality override"))
        flag_text.append(
            self.secondary_label(
                "Request a higher Roblox texture quality without changing the "
                "in-game graphics slider.",
                "page-copy",
            )
        )
        self.fflag_enabled_switch = Gtk.Switch()
        self.fflag_enabled_switch.set_valign(Gtk.Align.CENTER)
        self.fflag_enabled_switch.set_active(enabled_value == "True")
        self.fflag_enabled_switch.connect("notify::active", self.on_fflag_changed)
        flag_row.append(self.fflag_enabled_switch)

        quality_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        page.append(quality_row)
        quality_label = self.label("Texture quality level")
        quality_label.set_hexpand(True)
        quality_row.append(quality_label)
        self.fflag_quality_dropdown = Gtk.DropDown.new_from_strings(
            ["0", "1", "2", "3"]
        )
        self.fflag_quality_dropdown.set_selected(int(quality_value))
        self.fflag_quality_dropdown.set_sensitive(enabled_value == "True")
        self.fflag_quality_dropdown.connect("notify::selected", self.on_fflag_changed)
        quality_row.append(self.fflag_quality_dropdown)

        self.fflag_status = self.secondary_label("", "page-copy")
        self.fflag_status.set_wrap(True)
        page.append(self.fflag_status)
        if self.fflag_error:
            self.fflag_status.set_text(self.fflag_error)
            self.fflag_enabled_switch.set_sensitive(False)
            self.fflag_quality_dropdown.set_sensitive(False)

        modifications_heading = self.label("User modifications")
        modifications_heading.add_css_class("heading")
        page.append(modifications_heading)
        modifications_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=12
        )
        page.append(modifications_row)
        modifications_text = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=3
        )
        modifications_text.set_hexpand(True)
        modifications_row.append(modifications_text)
        modifications_text.append(self.label("Enable modifications folder"))
        modifications_text.append(
            self.secondary_label(
                "Overlay files from modifications/ onto Roblox when you play. "
                "Keep the same paths they have inside RobloxPlayer.app.",
                "page-copy",
            )
        )
        self.modifications_switch = Gtk.Switch()
        self.modifications_switch.set_valign(Gtk.Align.CENTER)
        self.modifications_switch.set_active(
            self.settings["modifications_enabled"]
        )
        self.modifications_switch_handler = self.modifications_switch.connect(
            "notify::active", self.on_modifications_toggled
        )
        modifications_row.append(self.modifications_switch)

        folder_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        page.append(folder_row)
        folder_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        folder_text.set_hexpand(True)
        folder_row.append(folder_text)
        folder_text.append(self.label("Open modifications folder"))
        folder_text.append(
            self.secondary_label(
                "Put replacement files here using paths relative to RobloxPlayer.app.",
                "page-copy",
            )
        )
        self.modifications_button = Gtk.Button(label="Open")
        self.modifications_button.connect(
            "clicked", self.open_modifications_folder
        )
        folder_row.append(self.modifications_button)

        self.apply_modifications_button = Gtk.Button(label="Apply mods now")
        self.apply_modifications_button.connect(
            "clicked", self.apply_modifications
        )
        page.append(self.apply_modifications_button)
        self.reset_modifications_button = Gtk.Button(
            label="Reset all mods to default"
        )
        self.reset_modifications_button.connect(
            "clicked", self.reset_modifications
        )
        page.append(self.reset_modifications_button)
        self.modifications_status = self.secondary_label("", "page-copy")
        self.modifications_status.set_wrap(True)
        page.append(self.modifications_status)

    def on_fflag_changed(self, *_args):
        self.fflag_quality_dropdown.set_sensitive(
            self.fflag_enabled_switch.get_active() and not self.fflag_error
        )
        if self.fflag_error:
            return
        if self.fflag_enabled_switch.get_active():
            self.fflag_values["DFFlagTextureQualityOverrideEnabled"] = "True"
            self.fflag_values["DFIntTextureQualityOverride"] = str(
                self.fflag_quality_dropdown.get_selected()
            )
        else:
            self.fflag_values.pop("DFFlagTextureQualityOverrideEnabled", None)
            self.fflag_values.pop("DFIntTextureQualityOverride", None)

        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=HERE,
                prefix=".FFlags-",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(self.fflag_values, temporary_file, indent=2)
                temporary_file.write("\n")
            os.replace(temporary_path, FFLAGS_FILE)
            self.fflag_status.set_text("FFlags.json saved.")
        except OSError as error:
            self.fflag_status.set_text(f"Could not save FFlags.json: {error}")
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

    def on_modifications_toggled(self, switch, *_args):
        if self.job_running or self.running_roblox_processes():
            self.set_modifications_switch(not switch.get_active())
            self.modifications_status.set_text(
                "Close Roblox before changing client modifications."
            )
            return

        enabled = switch.get_active()
        try:
            if enabled:
                applied_count = mods.apply_modifications()
                self.modifications_status.set_text(
                    f"Applied {applied_count} modification file(s)."
                    if applied_count
                    else "Folder enabled; there are no files to apply yet."
                )
            else:
                mods.reset_modifications()
                self.modifications_status.set_text(
                    "Roblox client files are back to their defaults."
                )
        except (OSError, ValueError, RuntimeError) as error:
            self.set_modifications_switch(not enabled)
            self.modifications_status.set_text(
                f"Could not change modifications: {error}"
            )
            return

        self.settings["modifications_enabled"] = enabled
        self.save_settings()

    def set_modifications_switch(self, enabled):
        self.modifications_switch.handler_block(self.modifications_switch_handler)
        try:
            self.modifications_switch.set_active(enabled)
        finally:
            self.modifications_switch.handler_unblock(
                self.modifications_switch_handler
            )

    def open_modifications_folder(self, _button):
        try:
            mods.MODIFICATIONS.mkdir(mode=0o700, parents=True, exist_ok=True)
            if not Gio.AppInfo.launch_default_for_uri(
                mods.MODIFICATIONS.as_uri(), None
            ):
                raise OSError("No file manager is available for this folder.")
        except (OSError, GLib.Error) as error:
            self.modifications_status.set_text(
                f"Could not open modifications folder: {error}"
            )

    def apply_modifications(self, _button=None):
        if self.job_running or self.running_roblox_processes():
            self.modifications_status.set_text(
                "Close Roblox before applying modifications."
            )
            return
        try:
            applied_count = mods.apply_modifications()
        except (OSError, ValueError, RuntimeError) as error:
            self.modifications_status.set_text(
                f"Could not apply modifications: {error}"
            )
            return
        self.set_modifications_switch(True)
        self.settings["modifications_enabled"] = True
        self.save_settings()
        self.modifications_status.set_text(
            f"Applied {applied_count} modification file(s)."
            if applied_count
            else "Folder enabled; there are no files to apply yet."
        )

    def reset_modifications(self, _button=None):
        if self.job_running or self.running_roblox_processes():
            self.modifications_status.set_text(
                "Close Roblox before resetting modifications."
            )
            return
        try:
            mods.reset_modifications()
        except (OSError, ValueError) as error:
            self.modifications_status.set_text(
                f"Could not reset modifications: {error}"
            )
            return
        self.set_modifications_switch(False)
        self.settings["modifications_enabled"] = False
        self.save_settings()
        self.modifications_status.set_text(
            "Roblox client files are back to their defaults."
        )

    def show_page(self, _button, page_name):
        self.stack.set_visible_child_name(page_name)
        self.sidebar.set_visible(page_name != "home")
        if page_name == "home":
            self.load_discover_page()
        for name, button in self.navigation_buttons.items():
            if name == page_name:
                button.add_css_class("selected")
            else:
                button.remove_css_class("selected")

    def toggle_sidebar(self, _button):
        self.sidebar.set_visible(not self.sidebar.get_visible())

    def load_discover_page(self):
        if self.discover_loaded or self.web_view is None:
            return
        self.discover_loaded = True
        if Secret is None:
            self.web_view.load_uri("https://www.roblox.com/home")
            return

        try:
            saved_session = Secret.password_lookup_sync(
                ROBLOX_SESSION_SCHEMA,
                ROBLOX_SESSION_ATTRIBUTES,
                None,
            )
        except GLib.Error as error:
            self.show_discover_message(
                f"Could not read your encrypted Roblox session: {error.message}"
            )
            self.web_view.load_uri("https://www.roblox.com/home")
            return
        if not saved_session:
            self.web_view.load_uri("https://www.roblox.com/home")
            return

        try:
            session_cookies = json.loads(saved_session)
            if not isinstance(session_cookies, list) or len(session_cookies) > 8:
                raise ValueError("The saved session cookie data is invalid.")
            cookies = [
                self.restore_session_cookie(item) for item in session_cookies
            ]
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            self.show_discover_message(
                f"Could not restore your encrypted Roblox session: {error}"
            )
            self.web_view.load_uri("https://www.roblox.com/home")
            return

        self.cookie_restore_pending = len(cookies)
        self.cookie_restore_errors = []
        if not cookies:
            self.web_view.load_uri("https://www.roblox.com/home")
            return
        for cookie in cookies:
            self.web_cookie_manager.add_cookie(
                cookie, None, self.on_session_cookie_restored, None
            )

    @staticmethod
    def restore_session_cookie(item):
        if not isinstance(item, dict):
            raise ValueError("The saved session cookie data is invalid.")
        name = item.get("name")
        value = item.get("value")
        domain = item.get("domain")
        path = item.get("path")
        normalized_domain = (
            domain.lstrip(".").casefold() if isinstance(domain, str) else ""
        )
        if (
            name != ROBLOX_SESSION_COOKIE
            or not isinstance(value, str)
            or not value
            or len(value) > 8192
            or normalized_domain != "roblox.com"
            or not isinstance(path, str)
            or not path.startswith("/")
            or len(path) > 2048
        ):
            raise ValueError("The saved Roblox session cookie is invalid.")

        cookie = Soup.Cookie.new(name, value, domain, path, -1)
        cookie.set_secure(bool(item.get("secure", True)))
        cookie.set_http_only(bool(item.get("http_only", True)))
        same_site = item.get("same_site")
        if isinstance(same_site, int) and same_site in (0, 1, 2):
            cookie.set_same_site_policy(Soup.SameSitePolicy(same_site))
        return cookie

    def on_session_cookie_restored(self, cookie_manager, result, _user_data):
        try:
            cookie_manager.add_cookie_finish(result)
        except GLib.Error as error:
            self.cookie_restore_errors.append(error.message)
        self.cookie_restore_pending -= 1
        if self.cookie_restore_pending:
            return
        if self.cookie_restore_errors:
            self.show_discover_message(
                "Could not restore the Roblox login cookie: "
                + "; ".join(self.cookie_restore_errors)
            )
        self.web_view.load_uri("https://www.roblox.com/home")

    def on_browser_cookies_changed(self, _cookie_manager):
        if Secret is None or self.cookie_restore_pending:
            return
        if self.cookie_save_source:
            GLib.source_remove(self.cookie_save_source)
        self.cookie_save_source = GLib.timeout_add(
            1200, self.snapshot_browser_session
        )

    def snapshot_browser_session(self):
        self.cookie_save_source = 0
        self.cookie_save_generation += 1
        self.web_cookie_manager.get_all_cookies(
            None,
            self.on_browser_cookies_loaded,
            self.cookie_save_generation,
        )
        return GLib.SOURCE_REMOVE

    def on_browser_cookies_loaded(self, cookie_manager, result, generation):
        try:
            cookies = cookie_manager.get_all_cookies_finish(result)
        except GLib.Error as error:
            self.show_discover_message(
                f"Could not save your Roblox login securely: {error.message}"
            )
            return

        session_cookies = []
        for cookie in cookies:
            domain = cookie.get_domain()
            normalized_domain = (
                domain.lstrip(".").casefold() if domain else ""
            )
            if (
                cookie.get_name() != ROBLOX_SESSION_COOKIE
                or normalized_domain != "roblox.com"
            ):
                continue
            same_site = cookie.get_same_site_policy()
            session_cookies.append(
                {
                    "name": cookie.get_name(),
                    "value": cookie.get_value(),
                    "domain": domain,
                    "path": cookie.get_path(),
                    "secure": cookie.get_secure(),
                    "http_only": cookie.get_http_only(),
                    "same_site": int(same_site) if same_site is not None else None,
                }
            )
        if len(session_cookies) > 8:
            self.show_discover_message(
                "Roblox returned an unexpected number of login cookies; "
                "the session was not saved."
            )
            return

        serialized_session = (
            json.dumps(session_cookies, separators=(",", ":"))
            if session_cookies
            else None
        )
        threading.Thread(
            target=self.store_browser_session,
            args=(serialized_session, generation),
            daemon=True,
        ).start()

    def store_browser_session(self, serialized_session, generation):
        try:
            with self.cookie_save_lock:
                if generation != self.cookie_save_generation:
                    return
                if serialized_session is None:
                    Secret.password_clear_sync(
                        ROBLOX_SESSION_SCHEMA,
                        ROBLOX_SESSION_ATTRIBUTES,
                        None,
                    )
                else:
                    stored = Secret.password_store_sync(
                        ROBLOX_SESSION_SCHEMA,
                        ROBLOX_SESSION_ATTRIBUTES,
                        None,
                        "Mactolinux Roblox session",
                        serialized_session,
                        None,
                    )
                    if not stored:
                        raise RuntimeError(
                            "The desktop keyring did not save the session."
                        )
        except (GLib.Error, RuntimeError) as error:
            message = str(error)
            GLib.idle_add(
                self.show_discover_message,
                f"Could not save your Roblox login securely: {message}",
            )
            return
        if serialized_session is not None:
            GLib.idle_add(
                self.show_discover_message,
                "Roblox login saved securely in your desktop keyring.",
            )

    def on_web_decide_policy(self, web_view, decision, decision_type):
        if decision_type not in (
            WebKit.PolicyDecisionType.NAVIGATION_ACTION,
            WebKit.PolicyDecisionType.NEW_WINDOW_ACTION,
        ):
            return False

        navigation_action = decision.get_navigation_action()
        request = navigation_action.get_request()
        uri = request.get_uri()
        try:
            scheme = urlsplit(uri).scheme.casefold()
        except ValueError:
            self.show_discover_message("Roblox requested an invalid game link.")
            decision.ignore()
            return True

        if scheme in ("roblox-player", "roblox"):
            try:
                page_host = urlsplit(web_view.get_uri() or "").hostname
            except ValueError:
                page_host = None
            if page_host != "roblox.com" and not (
                page_host and page_host.endswith(".roblox.com")
            ):
                self.show_discover_message(
                    "Only game links opened from the Roblox website can be launched."
                )
                decision.ignore()
                return True
            self.open_game_uri(uri)
            decision.ignore()
            return True

        if decision_type == WebKit.PolicyDecisionType.NEW_WINDOW_ACTION:
            if scheme in ("http", "https"):
                web_view.load_uri(uri)
            decision.ignore()
            return True

        return False

    def open_game_uri(self, uri):
        try:
            scheme = urlsplit(uri).scheme.casefold()
        except ValueError as error:
            self.show_discover_message(f"Roblox sent an invalid game link: {error}")
            return
        if scheme not in ("roblox-player", "roblox"):
            self.show_discover_message(
                "The selected link is not a Roblox game launch link."
            )
            return
        try:
            started = self.play(None, uri)
        except (OSError, ValueError, RuntimeError) as error:
            self.show_discover_message(
                f"Could not start this game with Mactolinux: {error}"
            )
            return
        if not started:
            self.show_discover_message(
                "Mactolinux could not start the selected Roblox game."
            )
            return
        self.show_discover_message("Starting this game with Mactolinux…")

    def on_web_load_failed(self, _web_view, _event, _failing_uri, error):
        self.show_discover_message(
            f"Could not load the Roblox website: {error.message}"
        )
        return False

    def show_discover_message(self, message):
        if self.discover_status is not None:
            self.discover_status.set_text(message)
            self.discover_status.set_visible(True)

    def build_discover_fallback(self, page, message):
        fallback = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        fallback.add_css_class("discover-fallback")
        fallback.set_valign(Gtk.Align.CENTER)
        page.append(fallback)
        fallback_title = self.label("Roblox Discover")
        fallback_title.add_css_class("discover-fallback-title")
        fallback.append(fallback_title)
        fallback_copy = self.secondary_label(message, "page-copy")
        fallback_copy.set_wrap(True)
        fallback.append(fallback_copy)
        open_website = Gtk.LinkButton(
            uri="https://www.roblox.com/home",
            label="Open Roblox website",
        )
        open_website.set_halign(Gtk.Align.START)
        fallback.append(open_website)

    @staticmethod
    def label(text):
        label = Gtk.Label(label=text)
        label.set_xalign(0)
        return label

    @staticmethod
    def secondary_label(text, style):
        label = Gtk.Label(label=text)
        label.add_css_class(style)
        label.set_xalign(0)
        return label

    def action_button(self, icon_name, title, callback):
        button = Gtk.Button()
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        row.append(Gtk.Image.new_from_icon_name(icon_name))
        row.append(Gtk.Label(label=title))
        button.set_child(row)
        button.connect("clicked", callback)
        return button

    def refresh_state(self):
        version = installed_version()
        ready = installation_complete(version)
        processes = self.running_roblox_processes()
        self.refresh_running_state(processes)
        if version:
            short_version = version.removeprefix("version-")
            self.version_badge.set_text(
                f"Roblox client version: {short_version}"
            )
        else:
            self.version_badge.set_text("Roblox client is not installed yet")
        self.play_button.set_sensitive(not self.job_running)
        self.sidebar_play_button.set_sensitive(not self.job_running)
        self.terminate_button.set_sensitive(not self.job_running)
        self.update_button.set_sensitive(not self.job_running)
        self.launcher_update_button.set_sensitive(not self.job_running)
        self.desktop_button.set_sensitive(not self.job_running)
        self.remove_desktop_button.set_sensitive(not self.job_running)
        self.uninstall_action.set_sensitive(not self.job_running)
        modifications_available = (
            not self.job_running and not processes
        )
        self.modifications_switch.set_sensitive(modifications_available)
        self.modifications_button.set_sensitive(modifications_available)
        self.apply_modifications_button.set_sensitive(modifications_available)
        self.reset_modifications_button.set_sensitive(modifications_available)
        self.uninstall_status.set_visible(self.job_running)
        if not self.job_running:
            if ready:
                self.status_title.set_text("Ready to play")
                self.status_copy.set_text("Your Roblox client is installed.")
                self.status_icon.set_from_icon_name("emblem-ok-symbolic")
            else:
                self.status_title.set_text("Setup required")
                self.status_copy.set_text(
                    "Click Play to reinstall Roblox and prepare its shaders."
                )
                self.status_icon.set_from_icon_name("dialog-information-symbolic")
        shortcut_error = self.refresh_desktop_shortcut_controls()
        if shortcut_error and not self.job_running:
            self.status_title.set_text("Could not check desktop shortcut")
            self.status_copy.set_text(shortcut_error)
            self.status_icon.set_from_icon_name("dialog-error-symbolic")

    @staticmethod
    def running_roblox_processes():
        processes = {}
        try:
            for entry in Path("/proc").iterdir():
                if not entry.name.isdigit():
                    continue
                try:
                    command_line = (entry / "cmdline").read_bytes().split(b"\0")
                    process_name = (entry / "comm").read_text(
                        encoding="utf-8"
                    ).strip()
                    if (
                        b"RobloxPlayer" not in b" ".join(command_line)
                        and "RobloxPlayer" not in process_name
                    ):
                        continue
                    stat = (entry / "stat").read_text(encoding="ascii")
                except (OSError, UnicodeError):
                    continue

                stat_fields = stat[stat.rfind(")") + 2 :].split()
                if len(stat_fields) >= 4:
                    processes[int(entry.name)] = int(stat_fields[3])
        except OSError:
            return {}
        return processes

    @staticmethod
    def running_roblox_sessions():
        return set(RobloxLauncher.running_roblox_processes().values())

    def refresh_running_state(self, processes=None):
        if processes is None:
            processes = self.running_roblox_processes()
        sessions = set(processes.values())
        self.terminate_button.set_visible(bool(sessions))
        self.terminate_button.set_sensitive(bool(sessions) and not self.job_running)
        self.update_roblox_fullscreen(set(processes))
        return GLib.SOURCE_CONTINUE

    def update_roblox_fullscreen(self, player_pids):
        if not player_pids:
            self.restore_roblox_windows()
            self.fullscreen_warning_shown = False
            return

        wmctrl = shutil.which("wmctrl")
        if wmctrl is None:
            self.show_fullscreen_warning(
                "Automatic fullscreen needs wmctrl. On CachyOS, install it "
                "with `sudo pacman -S wmctrl`."
            )
            return

        try:
            result = subprocess.run(
                [wmctrl, "-lp"],
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            self.show_fullscreen_warning(
                f"Could not inspect Roblox windows: {error}"
            )
            return

        if result.returncode != 0:
            details = result.stderr.strip() or "wmctrl returned an error."
            self.show_fullscreen_warning(
                f"Could not inspect Roblox windows: {details}"
            )
            return

        for line in result.stdout.splitlines():
            fields = line.split(None, 4)
            if len(fields) < 3 or not fields[2].isdigit():
                continue
            if int(fields[2]) not in player_pids:
                continue

            window_id = fields[0]
            if window_id in self.fullscreen_window_ids:
                continue
            try:
                fullscreen_result = subprocess.run(
                    [wmctrl, "-ir", window_id, "-b", "add,fullscreen"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                self.show_fullscreen_warning(
                    f"Could not fullscreen the Roblox window: {error}"
                )
                continue
            if fullscreen_result.returncode != 0:
                details = (
                    fullscreen_result.stderr.strip()
                    or "wmctrl returned an error."
                )
                self.show_fullscreen_warning(
                    f"Could not fullscreen the Roblox window: {details}"
                )
                continue
            self.fullscreen_window_ids[window_id] = int(fields[2])

    def restore_roblox_windows(self):
        wmctrl = shutil.which("wmctrl")
        if wmctrl is None:
            self.fullscreen_window_ids.clear()
            return

        try:
            result = subprocess.run(
                [wmctrl, "-lp"],
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            self.fullscreen_window_ids.clear()
            self.show_fullscreen_warning(
                f"Could not inspect Roblox windows while restoring: {error}"
            )
            return
        if result.returncode != 0:
            self.fullscreen_window_ids.clear()
            details = result.stderr.strip() or "wmctrl returned an error."
            self.show_fullscreen_warning(
                f"Could not inspect Roblox windows while restoring: {details}"
            )
            return

        live_windows = {}
        for line in result.stdout.splitlines():
            fields = line.split(None, 4)
            if len(fields) >= 3 and fields[2].isdigit():
                live_windows[fields[0]] = int(fields[2])

        errors = []
        for window_id, player_pid in self.fullscreen_window_ids.items():
            if live_windows.get(window_id) != player_pid:
                continue
            try:
                result = subprocess.run(
                    [wmctrl, "-ir", window_id, "-b", "remove,fullscreen"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                errors.append(str(error))
                continue
            if result.returncode != 0 and result.stderr.strip():
                errors.append(result.stderr.strip())

        self.fullscreen_window_ids.clear()
        if errors:
            self.show_fullscreen_warning(
                f"Could not restore a Roblox window: {'; '.join(errors)}"
            )

    def show_fullscreen_warning(self, message):
        if self.fullscreen_warning_shown:
            return
        self.fullscreen_warning_shown = True
        self.status_title.set_text("Automatic fullscreen is unavailable")
        self.status_copy.set_text(message)
        self.status_icon.set_from_icon_name("dialog-warning-symbolic")

    def terminate_roblox(self, _button):
        sessions = self.running_roblox_sessions()
        if not sessions:
            self.refresh_running_state()
            return

        errors = []
        for session_id in sessions:
            try:
                os.killpg(session_id, signal.SIGTERM)
            except ProcessLookupError:
                continue
            except OSError as error:
                errors.append(str(error))

        if errors:
            self.status_title.set_text("Could not terminate Roblox")
            self.status_copy.set_text("; ".join(errors))
            self.status_icon.set_from_icon_name("dialog-error-symbolic")
        else:
            self.status_title.set_text("Roblox is shutting down")
            self.status_copy.set_text("The Roblox launch session was terminated.")
            self.status_icon.set_from_icon_name("dialog-information-symbolic")
        self.refresh_running_state()

    def refresh_desktop_shortcut_controls(self):
        shortcut_path = desktop_shortcut_path()
        try:
            shortcut_exists = (
                shortcut_path.is_file()
                and DESKTOP_SHORTCUT_MARKER
                in shortcut_path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError) as error:
            self.desktop_button.set_visible(False)
            self.remove_desktop_button.set_visible(False)
            return str(error)

        self.desktop_button.set_visible(not shortcut_exists)
        self.remove_desktop_button.set_visible(shortcut_exists)
        return ""

    def create_desktop_shortcut(self, _button):
        shortcut_path = desktop_shortcut_path()
        temporary_path = None
        try:
            shortcut_path.parent.mkdir(parents=True, exist_ok=True)
            if shortcut_path.exists():
                existing_contents = shortcut_path.read_text(encoding="utf-8")
                if DESKTOP_SHORTCUT_MARKER not in existing_contents:
                    raise FileExistsError(
                        f"Not overwriting an existing file: {shortcut_path}"
                    )

            launcher_script = HERE / "ui.sh"
            desktop_entry = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                f"Name={APP_NAME}\n"
                f"Comment=Open {APP_NAME}\n"
                f"Exec=sh {quote_desktop_exec_argument(str(launcher_script))}\n"
                f"Icon={HERE / 'roblox-linux-release.png'}\n"
                "Terminal=false\n"
                "Categories=Game;\n"
                "X-RobloxLinuxRelease=true\n"
            )
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=shortcut_path.parent,
                prefix=".roblox-launcher-",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(desktop_entry)
            os.chmod(temporary_path, 0o755)
            os.replace(temporary_path, shortcut_path)
            shortcut_error = self.refresh_desktop_shortcut_controls()
            if shortcut_error:
                self.status_title.set_text(
                    "Desktop shortcut created, but controls could not refresh"
                )
                self.status_copy.set_text(shortcut_error)
                self.status_icon.set_from_icon_name("dialog-error-symbolic")
            else:
                self.status_title.set_text("Desktop shortcut created")
                self.status_copy.set_text(
                    f"Open Mactolinux from {shortcut_path}."
                )
                self.status_icon.set_from_icon_name("emblem-ok-symbolic")
        except (OSError, UnicodeError, ValueError) as error:
            self.status_title.set_text("Could not create desktop shortcut")
            self.status_copy.set_text(str(error))
            self.status_icon.set_from_icon_name("dialog-error-symbolic")
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

    def remove_desktop_shortcut(self, _button):
        shortcut_path = desktop_shortcut_path()
        try:
            contents = shortcut_path.read_text(encoding="utf-8")
            if DESKTOP_SHORTCUT_MARKER not in contents:
                raise ValueError(
                    f"Not removing a shortcut not created by Mactolinux: "
                    f"{shortcut_path}"
                )
            shortcut_path.unlink()
            shortcut_error = self.refresh_desktop_shortcut_controls()
            if shortcut_error:
                raise OSError(shortcut_error)
            self.status_title.set_text("Desktop shortcut removed")
            self.status_copy.set_text(
                "The Mactolinux desktop shortcut was removed."
            )
            self.status_icon.set_from_icon_name("emblem-ok-symbolic")
        except (OSError, UnicodeError, ValueError) as error:
            self.status_title.set_text("Could not remove desktop shortcut")
            self.status_copy.set_text(str(error))
            self.status_icon.set_from_icon_name("dialog-error-symbolic")

    def startup_update(self):
        return self.start_update(startup=True)

    def check_launcher_updates(self, _button=None):
        if self.job_running:
            return GLib.SOURCE_REMOVE
        self.job_running = True
        self.refresh_state()
        self.status_title.set_text("Checking for Mactolinux updates")
        self.status_copy.set_text("Checking GitHub for the latest commit.")
        self.status_icon.set_from_icon_name("content-loading-symbolic")
        self.spinner.start()

        def worker():
            request = urllib.request.Request(
                LATEST_COMMIT_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "Mactolinux",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    payload = json.load(response)
                if not isinstance(payload, dict):
                    raise ValueError("GitHub returned an invalid commit response.")
                latest_commit = payload.get("sha")
                if (
                    not isinstance(latest_commit, str)
                    or len(latest_commit) != 40
                    or any(character not in "0123456789abcdef" for character in latest_commit)
                ):
                    raise ValueError("GitHub returned an invalid commit ID.")
                try:
                    installed_commit = LAUNCHER_VERSION_FILE.read_text(
                        encoding="utf-8"
                    ).strip()
                except FileNotFoundError:
                    installed_commit = ""
                GLib.idle_add(
                    self.finish_launcher_update_check,
                    latest_commit,
                    installed_commit,
                    "",
                )
            except (
                OSError,
                urllib.error.URLError,
                json.JSONDecodeError,
                ValueError,
            ) as error:
                GLib.idle_add(
                    self.finish_launcher_update_check,
                    "",
                    "",
                    str(error),
                )

        threading.Thread(target=worker, daemon=True).start()
        return GLib.SOURCE_REMOVE

    def finish_launcher_update_check(self, latest_commit, installed_commit, error):
        self.job_running = False
        self.spinner.stop()
        self.refresh_state()
        if error:
            self.status_title.set_text("Could not check Mactolinux updates")
            self.status_copy.set_text(error)
            self.status_icon.set_from_icon_name("dialog-error-symbolic")
        elif not installed_commit:
            self.status_title.set_text("Mactolinux update available")
            self.status_copy.set_text(
                "This installation has no saved commit ID. Use Update in the "
                "installer once to sync with GitHub and enable future checks."
            )
            self.status_icon.set_from_icon_name("software-update-available-symbolic")
        elif latest_commit == installed_commit:
            self.status_title.set_text("Mactolinux is up to date")
            self.status_copy.set_text(
                f"You're using the latest launcher commit "
                f"{latest_commit[:12]}."
            )
            self.status_icon.set_from_icon_name("emblem-ok-symbolic")
        else:
            self.status_title.set_text("Mactolinux update available")
            self.status_copy.set_text(
                f"GitHub has commit {latest_commit[:12]}. Run the installer "
                "and choose Update to install the latest launcher."
            )
            self.status_icon.set_from_icon_name("software-update-available-symbolic")
        return GLib.SOURCE_REMOVE

    def start_update(
        self,
        _button=None,
        launch_after_update=False,
        startup=False,
        launch_uri=None,
    ):
        if self.job_running:
            return GLib.SOURCE_REMOVE
        self.job_running = True
        self.refresh_state()
        if startup:
            self.loading_spinner.start()
        self.status_title.set_text("Checking for updates")
        self.status_copy.set_text(
            "This can take a moment if a new client is available."
        )
        self.status_icon.set_from_icon_name("content-loading-symbolic")
        self.spinner.start()

        def worker():
            log_path = DATA / "ui-update.log"
            try:
                result = run_logged(
                    ["sh", str(HERE / "update-roblox.sh")], log_path
                )
            except OSError as error:
                GLib.idle_add(
                    self.finish_update,
                    False,
                    log_path,
                    str(error),
                    launch_after_update,
                    startup,
                    launch_uri,
                )
                return
            GLib.idle_add(
                self.finish_update,
                result == 0,
                log_path,
                "",
                launch_after_update,
                startup,
                launch_uri,
            )

        threading.Thread(target=worker, daemon=True).start()
        return GLib.SOURCE_REMOVE

    def finish_update(
        self,
        succeeded,
        log_path,
        error,
        launch_after_update,
        startup,
        launch_uri,
    ):
        self.job_running = False
        self.spinner.stop()
        if startup:
            self.loading_spinner.stop()
        self.refresh_state()
        if succeeded and (not launch_after_update or installation_complete()):
            self.status_title.set_text("Ready to play")
            self.status_copy.set_text("Roblox is installed and up to date.")
            self.status_icon.set_from_icon_name("emblem-ok-symbolic")
            if launch_after_update:
                self.launch_client(launch_uri)
        else:
            self.status_title.set_text("Could not check or update Roblox")
            failure = error or (
                "The installation is still incomplete. "
                "Review the updater log for details."
            )
            self.status_copy.set_text(
                f"{failure} Log: {log_path.relative_to(HERE)}"
            )
            self.status_icon.set_from_icon_name("dialog-error-symbolic")
        if startup:
            if not self.launcher_startup_check_started:
                self.launcher_startup_check_started = True
                GLib.idle_add(self.check_launcher_updates)
        return GLib.SOURCE_REMOVE

    def confirm_uninstall(self, _button):
        if self.job_running:
            return
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.CANCEL,
            text="Choose what to uninstall",
            secondary_text=(
                "Remove only Roblox and its prepared shaders, or remove the "
                "entire Mactolinux installation? Removing everything also "
                "deletes DO_NOT_SHARE, your modifications folder, settings, "
                "logs, the AppImage, launcher files, command, and "
                "applications-menu entry, as well as your encrypted Roblox "
                "session from the desktop keyring."
            ),
        )
        dialog.add_button("Remove Roblox only", Gtk.ResponseType.APPLY)
        dialog.add_button("Remove everything", Gtk.ResponseType.ACCEPT)
        dialog.connect("response", self.uninstall_response)
        dialog.present()

    def uninstall_response(self, dialog, response):
        dialog.destroy()
        if response not in (Gtk.ResponseType.APPLY, Gtk.ResponseType.ACCEPT):
            return
        uninstall_mode = (
            "everything" if response == Gtk.ResponseType.ACCEPT else "roblox-only"
        )
        self.job_running = True
        self.refresh_state()
        shortcut_path = desktop_shortcut_path()

        def worker():
            if uninstall_mode == "everything" and Secret is not None:
                try:
                    Secret.password_clear_sync(
                        ROBLOX_SESSION_SCHEMA,
                        ROBLOX_SESSION_ATTRIBUTES,
                        None,
                    )
                except GLib.Error as error:
                    GLib.idle_add(
                        self.finish_uninstall,
                        False,
                        "Could not remove the encrypted Roblox login from "
                        f"your desktop keyring: {error.message}",
                        uninstall_mode,
                    )
                    return
            try:
                result = subprocess.run(
                    [
                        "sh",
                        str(HERE / "uninstaller.sh"),
                        uninstall_mode,
                        str(shortcut_path),
                    ],
                    cwd=HERE,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
            except OSError as error:
                GLib.idle_add(
                    self.finish_uninstall, False, str(error), uninstall_mode
                )
                return
            GLib.idle_add(
                self.finish_uninstall,
                result.returncode == 0,
                result.stdout,
                uninstall_mode,
            )

        threading.Thread(target=worker, daemon=True).start()

    def finish_uninstall(self, succeeded, output, uninstall_mode):
        self.job_running = False
        self.refresh_state()
        if succeeded:
            if uninstall_mode == "everything":
                self.status_title.set_text("Mactolinux has been removed")
                self.status_copy.set_text(
                    "The launcher, Roblox client, application-menu entry, "
                    "command, and saved data were removed."
                )
            else:
                self.status_title.set_text("Roblox has been uninstalled")
                self.status_copy.set_text(
                    "The Roblox client and shaders were removed. Your saved "
                    "encrypted login remains in the desktop keyring."
                )
            self.status_icon.set_from_icon_name("emblem-ok-symbolic")
        else:
            details = output.strip() or "The uninstaller returned an error."
            self.status_title.set_text("Could not uninstall Roblox")
            self.status_copy.set_text(details)
            self.status_icon.set_from_icon_name("dialog-error-symbolic")
        self.stack.set_visible_child_name("launcher")
        return GLib.SOURCE_REMOVE

    def play(self, _button, launch_uri=None):
        if self.job_running:
            return False
        if not APPIMAGE.is_file() or not os.access(APPIMAGE, os.X_OK):
            self.status_title.set_text("Cannot reinstall Roblox")
            self.status_copy.set_text(
                "RobloxLinux.AppImage is missing or not executable. "
                "Restore it from the release archive, then click Play again."
            )
            self.status_icon.set_from_icon_name("dialog-error-symbolic")
            return False
        if not installation_complete():
            self.start_update(
                launch_after_update=True,
                launch_uri=launch_uri,
            )
            return True
        return self.launch_client(launch_uri)

    def launch_client(self, launch_uri=None):
        try:
            if self.settings["modifications_enabled"]:
                mods.apply_modifications()
            DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(DATA, 0o700)
            command = ["sh", str(HERE / "launch.sh")]
            if launch_uri is not None:
                command.append(launch_uri)
            subprocess.Popen(
                command,
                cwd=HERE,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
            self.status_title.set_text("Roblox is starting")
            self.status_copy.set_text(
                "Launch progress is shown in the Roblox launch window."
            )
            return True
        except (OSError, ValueError, RuntimeError) as error:
            self.status_title.set_text("Could not start Roblox")
            self.status_copy.set_text(str(error))
            return False


if __name__ == "__main__":
    app = RobloxLauncher()
    raise SystemExit(app.run(None))
