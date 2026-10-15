#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk

import glass


HERE = Path(__file__).resolve().parent
DATA = HERE / "DO_NOT_SHARE"
LOG_FILE = DATA / "ui-launch.log"
SETTINGS_FILE = DATA / "settings.json"

THEMES = {
    "dark": b"""
@define-color app_bg #151618;
@define-color app_fg #f0f0f2;
@define-color header_top alpha(#1a1b1e, 0.78);
@define-color border #2a2c30;
@define-color border_hover #3e4148;
@define-color glass_border alpha(#ffffff, 0.08);
@define-color glass_border_hover alpha(#ffffff, 0.16);
@define-color glass_panel_bg alpha(#1e2025, 0.62);
@define-color glass_button_bg alpha(#26282d, 0.6);
@define-color glass_button_hover alpha(#30333a, 0.82);
@define-color status_bg #1e2022;
@define-color log_bg alpha(#121316, 0.72);
@define-color secondary_fg #9fa4aa;
@define-color footer_fg #636870;
@define-color accent #c0b9d8;
@define-color shadow_xs alpha(#000000, 0.18);
@define-color glass_shadow alpha(#000000, 0.18);
""",
    "light": b"""
@define-color app_bg #f6f7fb;
@define-color app_fg #191b1f;
@define-color header_top alpha(#ffffff, 0.75);
@define-color border #e1e3e8;
@define-color border_hover #c8cbd2;
@define-color glass_border alpha(#191b1f, 0.08);
@define-color glass_border_hover alpha(#191b1f, 0.16);
@define-color glass_panel_bg alpha(#ffffff, 0.68);
@define-color glass_button_bg alpha(#ffffff, 0.65);
@define-color glass_button_hover alpha(#ffffff, 0.95);
@define-color status_bg #f8f8f9;
@define-color log_bg alpha(#ffffff, 0.75);
@define-color secondary_fg #5a5f66;
@define-color footer_fg #878d94;
@define-color accent #7b6fa0;
@define-color shadow_xs alpha(#000000, 0.05);
@define-color glass_shadow alpha(#191b1f, 0.04);
""",
}

CSS = b"""
window {
  background: @app_bg;
  color: @app_fg;
}
button {
  background: @glass_button_bg;
  color: @app_fg;
  border: 1px solid @glass_border;
  border-radius: 12px;
  font-weight: 500;
  transition: all 140ms cubic-bezier(0.2, 0, 0, 1);
}
button:hover {
  background: @glass_button_hover;
  border-color: @glass_border_hover;
}
button:active {
  background: @button_selected;
}
headerbar {
  background: @header_top;
  border-bottom: 1px solid @glass_border;
  box-shadow: none;
  min-height: 46px;
  padding: 0 8px;
}
.launch-content {
  padding: 28px 32px 24px;
}
.launch-card {
  background: @glass_panel_bg;
  border: 1px solid @glass_border;
  border-radius: 12px;
  padding: 16px;
}
.launch-title {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.3px;
}
.launch-copy {
  color: @secondary_fg;
  font-size: 13px;
  margin-top: 3px;
}
.launch-spinner {
  color: @accent;
}
.log-panel {
  background: @glass_panel_bg;
  border: 1px solid @glass_border;
  border-radius: 12px;
  box-shadow: 0 2px 10px @glass_shadow;
}
.log-header {
  padding: 10px 14px;
  border-bottom: 1px solid @glass_border;
}
.log-title {
  color: @secondary_fg;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1.4px;
}
textview.log-view {
  background: @log_bg;
  color: @app_fg;
}
.log-view {
  padding: 12px 14px;
  font-size: 12px;
}
.footer {
  color: @footer_fg;
  font-size: 11px;
}
"""


class RobloxLaunchWindow(Gtk.Application):
    def __init__(self, launch_uri=None):
        super().__init__(
            application_id="com.robloxlinux.release.launch",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.launch_uri = launch_uri
        self.window = None
        self.status = None
        self.spinner = None
        self.log_buffer = None
        self.log_view = None
        self.theme_provider = None
        self.process = None
        self.log_file = None
        self.log_reader = None
        self.initial_player_pids = set()
        self.player_detected = False
        self.launch_finished_at = None

    def do_activate(self):
        if self.window is None:
            self.build_window()
            self.start_launch()
        self.window.present()

    def build_window(self):
        display = Gdk.Display.get_default()
        self.theme_provider = Gtk.CssProvider()
        self.theme_provider.load_from_data(THEMES[self.load_theme()] + CSS)
        Gtk.StyleContext.add_provider_for_display(
            display, self.theme_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.window = Gtk.ApplicationWindow(application=self, title="Mactolinux")
        self.window.set_default_size(860, 700)
        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        content.add_css_class("launch-content")
        backdrop = glass.GlassBackdrop()
        glass.FrostedBox.backdrop = backdrop
        glass_overlay = Gtk.Overlay()
        glass_overlay.set_child(backdrop)
        glass_overlay.add_overlay(content)
        self.window.set_child(glass_overlay)

        header = Gtk.HeaderBar()
        self.window.set_titlebar(header)
        title = Gtk.Label(label="ROBLOX")
        title.add_css_class("title")
        header.set_title_widget(title)

        hero = glass.FrostedBox(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        hero.set_halign(Gtk.Align.FILL)
        hero.add_css_class("launch-card")
        content.append(hero)

        logo_path = HERE / "roblox-logo-white.png"
        if logo_path.exists():
            logo = Gtk.Image.new_from_file(str(logo_path))
            logo.set_pixel_size(64)
            logo.set_halign(Gtk.Align.CENTER)
            hero.append(logo)

        heading = Gtk.Label(
            label="Joining Roblox game"
            if self.launch_uri
            else "Starting Roblox"
        )
        heading.add_css_class("launch-title")
        heading.set_halign(Gtk.Align.CENTER)
        hero.append(heading)

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(48, 48)
        self.spinner.add_css_class("launch-spinner")
        self.spinner.start()
        hero.append(self.spinner)
        self.spinner.set_halign(Gtk.Align.CENTER)

        self.status = Gtk.Label(
            label=(
                "Launching your selected game. Please wait…"
                if self.launch_uri
                else "Launching Roblox. Please wait…"
            )
        )
        self.status.add_css_class("launch-copy")
        self.status.set_halign(Gtk.Align.CENTER)
        self.status.set_wrap(True)
        hero.append(self.status)

        logs = glass.FrostedBox(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        logs.set_vexpand(True)
        logs.set_size_request(-1, 260)
        logs.add_css_class("log-panel")
        content.append(logs)

        log_header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=8
        )
        log_header.add_css_class("log-header")
        logs.append(log_header)
        log_title = Gtk.Label(label="LAUNCH LOG")
        log_title.add_css_class("log-title")
        log_title.set_halign(Gtk.Align.START)
        log_header.append(log_title)

        scroller = Gtk.ScrolledWindow()
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)
        scroller.set_margin_bottom(4)
        scroller.set_margin_start(4)
        scroller.set_margin_end(4)
        logs.append(scroller)
        self.log_buffer = Gtk.TextBuffer()
        self.log_view = Gtk.TextView(buffer=self.log_buffer)
        self.log_view.set_editable(False)
        self.log_view.set_cursor_visible(False)
        self.log_view.set_monospace(True)
        self.log_view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.log_view.add_css_class("log-view")
        scroller.set_child(self.log_view)

    @staticmethod
    def load_theme():
        try:
            settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return "light"
        except (OSError, json.JSONDecodeError) as error:
            print(f"Could not read launcher theme settings: {error}", flush=True)
            return "light"
        theme = settings.get("theme", "light") if isinstance(settings, dict) else "light"
        if not isinstance(theme, str) or theme not in THEMES:
            print(f"Unknown launcher theme {theme!r}; using light theme.", flush=True)
            return "light"
        return theme

    def start_launch(self):
        try:
            DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(DATA, 0o700)
            self.initial_player_pids = self.find_player_processes()
            self.log_file = LOG_FILE.open("w", encoding="utf-8", buffering=1)
            command = ["sh", str(HERE / "run.sh")]
            if self.launch_uri is not None:
                command.append(self.launch_uri)
            self.process = subprocess.Popen(
                command,
                cwd=HERE,
                stdin=subprocess.DEVNULL,
                stdout=self.log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )
            self.log_reader = LOG_FILE.open(
                "r", encoding="utf-8", errors="replace"
            )
        except OSError as error:
            message = f"Could not start Roblox: {error}\n"
            if self.log_file is not None:
                self.log_file.write(message)
                self.log_file.flush()
            self.append_log(message)
            self.status.set_text("Could not start Roblox. Review the output below.")
            self.spinner.stop()
            return

        GLib.timeout_add(300, self.check_launch)

    def read_new_output(self):
        text = self.log_reader.read()
        if text:
            self.append_log(text)

    def append_log(self, text):
        adjustment = (
            self.log_view.get_parent().get_vadjustment()
            if self.log_view.get_parent() is not None
            else None
        )
        follow_output = (
            adjustment is not None
            and adjustment.get_value() + adjustment.get_page_size()
            >= adjustment.get_upper() - 8
        )
        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, text)
        if follow_output:
            end = self.log_buffer.get_end_iter()
            self.log_view.scroll_to_iter(end, 0.0, False, 0.0, 1.0)
        return GLib.SOURCE_REMOVE

    @staticmethod
    def find_player_processes():
        player_pids = set()
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                command_line = (entry / "cmdline").read_bytes().replace(b"\0", b" ")
                process_name = (entry / "comm").read_text(encoding="utf-8").strip()
            except (OSError, PermissionError):
                continue
            if b"RobloxPlayer" in command_line or "RobloxPlayer" in process_name:
                player_pids.add(int(entry.name))
        return player_pids

    def check_launch(self):
        self.read_new_output()
        current_player_pids = self.find_player_processes()
        if not self.player_detected and current_player_pids - self.initial_player_pids:
            self.player_detected = True
            self.status.set_text("Roblox is running. Closing this window…")
            self.spinner.stop()
            GLib.timeout_add(1200, self.close_window)
            return GLib.SOURCE_REMOVE
        return_code = self.process.poll()
        if return_code is None:
            return GLib.SOURCE_CONTINUE
        if return_code != 0:
            self.status.set_text(
                f"Roblox launch exited with status {return_code}. "
                "Complete output remains below."
            )
            self.spinner.stop()
            return GLib.SOURCE_REMOVE

        self.read_new_output()
        if self.launch_finished_at is None:
            self.launch_finished_at = time.monotonic()
        if time.monotonic() - self.launch_finished_at < 30:
            return GLib.SOURCE_CONTINUE

        self.status.set_text(
            "Roblox did not appear to start. Review the output below."
        )
        self.spinner.stop()
        return GLib.SOURCE_REMOVE

    def close_window(self):
        if self.log_reader is not None:
            self.log_reader.close()
        if self.log_file is not None:
            self.log_file.close()
        self.quit()
        return GLib.SOURCE_REMOVE


def parse_launch_uri(arguments):
    if not arguments:
        return None
    if len(arguments) != 1:
        raise ValueError("Expected one Roblox game launch URI.")
    uri = arguments[0]
    if len(uri) > 32768 or any(character.isspace() for character in uri):
        raise ValueError("The Roblox game launch URI is invalid.")
    try:
        parsed_uri = urlsplit(uri)
        scheme = parsed_uri.scheme.casefold()
    except ValueError as error:
        raise ValueError("The Roblox game launch URI is invalid.") from error
    if scheme in ("http", "https"):
        try:
            hostname = (parsed_uri.hostname or "").casefold()
            port = parsed_uri.port
        except ValueError as error:
            raise ValueError("The Roblox game launch URI is invalid.") from error
        is_roblox_game_start = (
            (hostname == "roblox.com" or hostname.endswith(".roblox.com"))
            and parsed_uri.username is None
            and parsed_uri.password is None
            and port is None
            and re.fullmatch(
                r"(?:/[a-z]{2}(?:-[a-z0-9]{2,3})?)?/games/start/?",
                parsed_uri.path,
                re.IGNORECASE,
            )
        )
        if not is_roblox_game_start:
            raise ValueError("Only Roblox game launch URIs are supported.")
        return uri
    if scheme not in ("roblox-player", "roblox"):
        raise ValueError("Only Roblox game launch URIs are supported.")
    return uri


if __name__ == "__main__":
    try:
        launch_uri = parse_launch_uri(sys.argv[1:])
    except ValueError as error:
        print(error, file=sys.stderr)
        raise SystemExit(2) from error
    app = RobloxLaunchWindow(launch_uri)
    raise SystemExit(app.run(None))
