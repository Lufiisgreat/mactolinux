#!/usr/bin/env python3
import json
import os
import signal
import subprocess
import tempfile
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk


HERE = Path(__file__).resolve().parent
DATA = HERE / "DO_NOT_SHARE"
CLIENT = HERE / "RobloxVersion/RobloxPlayer.app/Contents/MacOS/RobloxPlayer"
VERSION_FILE = HERE / "RobloxVersion/.version"
APPIMAGE = HERE / "RobloxLinux.AppImage"
SETTINGS_FILE = DATA / "settings.json"
FFLAGS_FILE = HERE / "FFlags.json"
TEXTURE_FLAGS = {
    "DFFlagTextureQualityOverrideEnabled",
    "DFIntTextureQualityOverride",
}
DESKTOP_FILE_NAME = "roblox-linux-release.desktop"
DESKTOP_SHORTCUT_MARKER = "X-RobloxLinuxRelease=true"


CSS = b"""
window {
  background: @app_bg;
  color: @app_fg;
}
headerbar {
  background: linear-gradient(180deg, @header_top, @header_bottom);
  border-bottom: 1px solid @border;
  box-shadow: none;
}
headerbar button.titlebutton {
  min-width: 36px;
  min-height: 36px;
  padding: 0;
  margin: 0 3px;
  border-radius: 50%;
}
button {
  background: @button_bg;
  color: @app_fg;
  border-color: @border;
  transition: 100ms ease-out;
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
  padding: 26px 30px 22px;
}
.intro {
  background: linear-gradient(115deg, @intro_start 0%, @intro_end 100%);
  border: 1px solid @intro_border;
  border-radius: 14px;
  padding: 23px 24px;
}
.intro-title {
  font-size: 24px;
  font-weight: 650;
}
.intro-copy {
  color: @secondary_fg;
  font-size: 13px;
}
.welcome-row {
  min-height: 52px;
}
.welcome-icon {
  color: @secondary_fg;
  background: @status_bg;
  border: 1px solid @border;
  border-radius: 12px;
  padding: 10px;
}
.status {
  background: @status_bg;
  border: 1px solid @border;
  border-radius: 10px;
  padding: 14px 16px;
}
.version {
  color: @secondary_fg;
  font-size: 12px;
}
.actions button {
  min-height: 40px;
  padding: 0 13px;
  border-radius: 8px;
}
button.suggested-action {
  background: #596579;
  color: #fff;
  border-color: @suggested_border;
}
button.suggested-action:hover {
  background: @suggested_hover;
}
.footer {
  color: @footer_fg;
  font-size: 11px;
}
.page-title {
  font-size: 22px;
  font-weight: 650;
}
.page-copy {
  color: @secondary_fg;
}
.nav button {
  border-radius: 7px;
}
.danger {
  color: @danger_fg;
}
"""

THEMES = {
    "light": b"""
@define-color app_bg #e8eaed;
@define-color app_fg #24272d;
@define-color header_top #f5f6f7;
@define-color header_bottom #e4e6e9;
@define-color border #d5d8dd;
@define-color button_bg #f4f5f6;
@define-color button_hover #e4e7eb;
@define-color button_selected #d9dee5;
@define-color intro_start #f5f6f7;
@define-color intro_end #e5e7eb;
@define-color intro_border #f9fafb;
@define-color status_bg #f4f5f6;
@define-color secondary_fg #646a73;
@define-color footer_fg #747a83;
@define-color suggested_border #505b6d;
@define-color suggested_hover #4e596c;
@define-color danger_fg #a22c2c;
""",
    "dark": b"""
@define-color app_bg #17191d;
@define-color app_fg #edf0f4;
@define-color header_top #25282e;
@define-color header_bottom #1d2025;
@define-color border #383d46;
@define-color button_bg #292d34;
@define-color button_hover #353a43;
@define-color button_selected #424a57;
@define-color intro_start #272b33;
@define-color intro_end #1d2026;
@define-color intro_border #353a43;
@define-color status_bg #20242a;
@define-color secondary_fg #b0b6c0;
@define-color footer_fg #989faa;
@define-color suggested_border #647a9e;
@define-color suggested_hover #60779c;
@define-color danger_fg #ff8585;
""",
}


def installed_version():
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def installation_complete():
    return (
        APPIMAGE.is_file()
        and os.access(APPIMAGE, os.X_OK)
        and CLIENT.is_file()
        and os.access(CLIENT, os.X_OK)
        and bool(installed_version())
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
        self.startup_check_started = False
        self.running_monitor_started = False
        self.job_running = False
        self.play_button = None
        self.terminate_button = None
        self.update_button = None
        self.desktop_button = None
        self.remove_desktop_button = None
        self.uninstall_action = None
        self.uninstall_status = None
        self.status_title = None
        self.status_copy = None
        self.status_icon = None
        self.spinner = None
        self.theme_provider = None
        self.settings = {
            "theme": "dark",
            "check_updates_on_startup": True,
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

        try:
            if SETTINGS_FILE.exists():
                saved_settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                if not isinstance(saved_settings, dict):
                    raise ValueError("Settings must be a JSON object.")
                theme = saved_settings.get("theme", "dark")
                check_updates = saved_settings.get("check_updates_on_startup", True)
                if theme not in THEMES:
                    raise ValueError("The saved theme must be 'light' or 'dark'.")
                if not isinstance(check_updates, bool):
                    raise ValueError("The startup update setting must be a boolean.")
                self.settings.update(
                    theme=theme, check_updates_on_startup=check_updates
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

    def build_window(self):
        display = Gdk.Display.get_default()
        self.theme_provider = Gtk.CssProvider()
        self.theme_provider.load_from_data(THEMES["dark"] + CSS)
        Gtk.StyleContext.add_provider_for_display(
            display, self.theme_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.window = Gtk.ApplicationWindow(application=self, title="Mactolinux")
        self.window.set_default_size(600, 490)

        header = Gtk.HeaderBar()
        self.window.set_titlebar(header)
        title = Gtk.Label(label="Mactolinux")
        title.add_css_class("title")
        header.set_title_widget(title)

        self.navigation = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=4
        )
        self.navigation.add_css_class("nav")
        header.pack_start(self.navigation)
        home_button = Gtk.Button(label="Home")
        home_button.connect("clicked", self.show_page, "home")
        self.navigation.append(home_button)
        fflags_button = Gtk.Button(label="FFlags")
        fflags_button.connect("clicked", self.show_page, "fflags")
        self.navigation.append(fflags_button)
        settings_button = Gtk.Button(label="Settings")
        settings_button.connect("clicked", self.show_page, "settings")
        self.navigation.append(settings_button)
        info_button = Gtk.Button(label="Info")
        info_button.connect("clicked", self.show_page, "info")
        self.navigation.append(info_button)
        uninstall_button = Gtk.Button(label="Uninstall")
        uninstall_button.connect("clicked", self.show_page, "uninstall")
        self.navigation.append(uninstall_button)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)
        self.window.set_child(self.stack)
        self.apply_theme(self.settings["theme"])

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        content.add_css_class("content")
        self.stack.add_named(content, "home")

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
        heading = self.label("Welcome to Mactolinux")
        heading.add_css_class("intro-title")
        welcome_text.append(heading)
        welcome_copy = self.secondary_label(
            "Your home for setting up and playing Roblox on Linux.",
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
            "Check for updates",
            self.start_update,
        )

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        buttons.add_css_class("actions")
        buttons.append(self.play_button)
        buttons.append(self.terminate_button)
        buttons.append(self.update_button)
        content.append(buttons)

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
            "Roblox session data and diagnostic logs are stored locally in "
            "DO_NOT_SHARE.",
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
            "Your saved login, settings and logs in DO_NOT_SHARE will be kept.",
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
            "on Linux. Use Home to play or update, FFlags to manage the "
            "texture-quality override, and Settings to choose a theme or "
            "startup update checks.",
            "page-copy",
        )
        info_message.set_wrap(True)
        info_page.append(info_message)

        checking_page = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=16
        )
        checking_page.add_css_class("content")
        checking_page.set_valign(Gtk.Align.CENTER)
        self.stack.add_named(checking_page, "checking")
        checking_card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=12
        )
        checking_card.add_css_class("intro")
        checking_card.set_halign(Gtk.Align.FILL)
        checking_page.append(checking_card)
        self.loading_spinner = Gtk.Spinner()
        self.loading_spinner.set_size_request(42, 42)
        self.loading_spinner.set_halign(Gtk.Align.CENTER)
        checking_card.append(self.loading_spinner)
        self.loading_title = self.label("Checking for Roblox updates")
        self.loading_title.add_css_class("page-title")
        self.loading_title.set_halign(Gtk.Align.CENTER)
        checking_card.append(self.loading_title)
        self.loading_copy = self.secondary_label(
            "This may take a moment. Your launcher menu will appear when the "
            "check is complete.",
            "page-copy",
        )
        self.loading_copy.set_halign(Gtk.Align.CENTER)
        self.loading_copy.set_wrap(True)
        checking_card.append(self.loading_copy)

    def apply_theme(self, theme):
        self.theme_provider.load_from_data(THEMES[theme] + CSS)
        Gtk.Settings.get_default().set_property(
            "gtk-application-prefer-dark-theme", theme == "dark"
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

    def show_page(self, _button, page_name):
        self.stack.set_visible_child_name(page_name)

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
        ready = installation_complete()
        self.refresh_running_state()
        if version:
            short_version = version.removeprefix("version-")
            self.version_badge.set_text(f"Installed version: {short_version}")
        else:
            self.version_badge.set_text("Roblox is not installed yet")
        self.play_button.set_sensitive(not self.job_running)
        self.terminate_button.set_sensitive(not self.job_running)
        self.update_button.set_sensitive(not self.job_running)
        self.desktop_button.set_sensitive(not self.job_running)
        self.remove_desktop_button.set_sensitive(not self.job_running)
        self.uninstall_action.set_sensitive(not self.job_running)
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
    def running_roblox_sessions():
        sessions = set()
        try:
            processes = Path("/proc").iterdir()
            for entry in processes:
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
                    session_id = int(stat_fields[3])
                    sessions.add(session_id)
        except OSError:
            return set()
        return sessions

    def refresh_running_state(self):
        sessions = self.running_roblox_sessions()
        self.terminate_button.set_visible(bool(sessions))
        self.terminate_button.set_sensitive(bool(sessions) and not self.job_running)
        return GLib.SOURCE_CONTINUE

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
                "Name=Mactolinux\n"
                "Comment=Open Mactolinux\n"
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

    def start_update(
        self, _button=None, launch_after_update=False, startup=False
    ):
        if self.job_running:
            return GLib.SOURCE_REMOVE
        self.job_running = True
        self.refresh_state()
        if startup:
            self.navigation.set_sensitive(False)
            self.loading_spinner.start()
            self.stack.set_visible_child_name("checking")
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
                )
                return
            GLib.idle_add(
                self.finish_update,
                result == 0,
                log_path,
                "",
                launch_after_update,
                startup,
            )

        threading.Thread(target=worker, daemon=True).start()
        return GLib.SOURCE_REMOVE

    def finish_update(
        self, succeeded, log_path, error, launch_after_update, startup
    ):
        self.job_running = False
        self.spinner.stop()
        if startup:
            self.loading_spinner.stop()
            self.navigation.set_sensitive(True)
        self.refresh_state()
        if succeeded and (not launch_after_update or installation_complete()):
            self.status_title.set_text("Ready to play")
            self.status_copy.set_text("Roblox is installed and up to date.")
            self.status_icon.set_from_icon_name("emblem-ok-symbolic")
            if launch_after_update:
                self.launch_client()
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
            self.stack.set_visible_child_name("home")
        return GLib.SOURCE_REMOVE

    def confirm_uninstall(self, _button):
        if self.job_running:
            return
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.CANCEL,
            text="Uninstall Roblox?",
            secondary_text=(
                "The installed client, shaders and desktop shortcut will be "
                "removed. Your saved login and settings will be kept."
            ),
        )
        dialog.add_button("Uninstall", Gtk.ResponseType.ACCEPT)
        dialog.connect("response", self.uninstall_response)
        dialog.present()

    def uninstall_response(self, dialog, response):
        dialog.destroy()
        if response != Gtk.ResponseType.ACCEPT:
            return
        self.job_running = True
        self.refresh_state()
        shortcut_path = desktop_shortcut_path()

        def worker():
            try:
                result = subprocess.run(
                    [
                        "sh",
                        str(HERE / "uninstaller.sh"),
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
                GLib.idle_add(self.finish_uninstall, False, str(error))
                return
            GLib.idle_add(
                self.finish_uninstall,
                result.returncode == 0,
                result.stdout,
            )

        threading.Thread(target=worker, daemon=True).start()

    def finish_uninstall(self, succeeded, output):
        self.job_running = False
        self.refresh_state()
        if succeeded:
            self.status_title.set_text("Roblox has been uninstalled")
            self.status_copy.set_text(
                "The Roblox client and shaders were removed. Your saved login "
                "and settings are still in DO_NOT_SHARE."
            )
            self.status_icon.set_from_icon_name("emblem-ok-symbolic")
        else:
            details = output.strip() or "The uninstaller returned an error."
            self.status_title.set_text("Could not uninstall Roblox")
            self.status_copy.set_text(details)
            self.status_icon.set_from_icon_name("dialog-error-symbolic")
        self.stack.set_visible_child_name("home")
        return GLib.SOURCE_REMOVE

    def play(self, _button):
        if self.job_running:
            return
        if not APPIMAGE.is_file() or not os.access(APPIMAGE, os.X_OK):
            self.status_title.set_text("Cannot reinstall Roblox")
            self.status_copy.set_text(
                "RobloxLinux.AppImage is missing or not executable. "
                "Restore it from the release archive, then click Play again."
            )
            self.status_icon.set_from_icon_name("dialog-error-symbolic")
            return
        if not installation_complete():
            self.start_update(launch_after_update=True)
            return
        self.launch_client()

    def launch_client(self):
        try:
            DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(DATA, 0o700)
            subprocess.Popen(
                ["sh", str(HERE / "launch.sh")],
                cwd=HERE,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
            self.window.minimize()
            self.status_title.set_text("Roblox is starting")
            self.status_copy.set_text(
                "Launch progress is shown in the Roblox launch window."
            )
        except OSError as error:
            self.status_title.set_text("Could not start Roblox")
            self.status_copy.set_text(str(error))


if __name__ == "__main__":
    app = RobloxLauncher()
    raise SystemExit(app.run(None))
