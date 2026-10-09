#!/usr/bin/env python3
import json
import os
import subprocess
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk


HERE = Path(__file__).resolve().parent
DATA = HERE / "DO_NOT_SHARE"
LOG_FILE = DATA / "ui-launch.log"
SETTINGS_FILE = DATA / "settings.json"

THEMES = {
    "dark": b"""
@define-color app_bg #17191d;
@define-color app_fg #edf0f4;
@define-color header_top #25282e;
@define-color header_bottom #1d2025;
@define-color border #383d46;
@define-color intro_start #272b33;
@define-color intro_end #1d2026;
@define-color intro_border #353a43;
@define-color status_bg #20242a;
@define-color secondary_fg #b0b6c0;
@define-color footer_fg #989faa;
@define-color accent #8da8d0;
""",
    "light": b"""
@define-color app_bg #e8eaed;
@define-color app_fg #24272d;
@define-color header_top #f5f6f7;
@define-color header_bottom #e4e6e9;
@define-color border #d5d8dd;
@define-color intro_start #f5f6f7;
@define-color intro_end #e5e7eb;
@define-color intro_border #f9fafb;
@define-color status_bg #f4f5f6;
@define-color secondary_fg #646a73;
@define-color footer_fg #747a83;
@define-color accent #596579;
""",
}

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
.launch-content {
  padding: 26px 30px 22px;
}
.launch-card {
  background: linear-gradient(115deg, @intro_start 0%, @intro_end 100%);
  border: 1px solid @intro_border;
  border-radius: 14px;
  padding: 24px;
}
.launch-title {
  font-size: 22px;
  font-weight: 650;
}
.launch-copy {
  color: @secondary_fg;
  font-size: 13px;
}
.launch-spinner {
  color: @accent;
}
.log-panel {
  background: @status_bg;
  border: 1px solid @border;
  border-radius: 10px;
}
.log-title {
  font-weight: 600;
}
.log-view {
  padding: 10px;
  font-size: 11px;
}
.footer {
  color: @footer_fg;
  font-size: 11px;
}
"""


class RobloxLaunchWindow(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.robloxlinux.release.launch",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
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
        self.window.set_default_size(680, 560)
        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
        )
        content.add_css_class("launch-content")
        self.window.set_child(content)

        header = Gtk.HeaderBar()
        self.window.set_titlebar(header)
        title = Gtk.Label(label="Mactolinux")
        title.add_css_class("title")
        header.set_title_widget(title)

        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        hero.set_vexpand(True)
        hero.set_halign(Gtk.Align.FILL)
        hero.add_css_class("launch-card")
        content.append(hero)

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(76, 76)
        self.spinner.add_css_class("launch-spinner")
        self.spinner.start()
        hero.append(self.spinner)
        self.spinner.set_halign(Gtk.Align.CENTER)

        heading = Gtk.Label(label="Starting Roblox")
        heading.add_css_class("launch-title")
        heading.set_halign(Gtk.Align.CENTER)
        hero.append(heading)

        self.status = Gtk.Label(label="Launching Roblox. Please wait…")
        self.status.add_css_class("launch-copy")
        self.status.set_halign(Gtk.Align.CENTER)
        self.status.set_wrap(True)
        hero.append(self.status)

        logs = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        logs.set_size_request(-1, 170)
        logs.add_css_class("log-panel")
        content.append(logs)

        log_title = Gtk.Label(label="Command output")
        log_title.add_css_class("log-title")
        log_title.set_halign(Gtk.Align.START)
        log_title.set_margin_top(10)
        log_title.set_margin_start(12)
        logs.append(log_title)

        scroller = Gtk.ScrolledWindow()
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)
        scroller.set_margin_bottom(6)
        scroller.set_margin_start(8)
        scroller.set_margin_end(8)
        logs.append(scroller)
        self.log_buffer = Gtk.TextBuffer()
        self.log_view = Gtk.TextView(buffer=self.log_buffer)
        self.log_view.set_editable(False)
        self.log_view.set_cursor_visible(False)
        self.log_view.set_monospace(True)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.add_css_class("log-view")
        scroller.set_child(self.log_view)

    @staticmethod
    def load_theme():
        try:
            settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return "dark"
        except (OSError, json.JSONDecodeError) as error:
            print(f"Could not read launcher theme settings: {error}", flush=True)
            return "dark"
        theme = settings.get("theme", "dark") if isinstance(settings, dict) else "dark"
        if not isinstance(theme, str) or theme not in THEMES:
            print(f"Unknown launcher theme {theme!r}; using dark theme.", flush=True)
            return "dark"
        return theme

    def start_launch(self):
        try:
            DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(DATA, 0o700)
            self.initial_player_pids = self.find_player_processes()
            self.log_file = LOG_FILE.open("w", encoding="utf-8", buffering=1)
            self.process = subprocess.Popen(
                ["sh", str(HERE / "run.sh")],
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
        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, text)
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
        if current_player_pids - self.initial_player_pids:
            self.status.set_text("Roblox is running. Closing this window…")
            self.spinner.stop()
            GLib.timeout_add(1200, self.close_window)
            return GLib.SOURCE_REMOVE

        return_code = self.process.poll()
        if return_code is None:
            return GLib.SOURCE_CONTINUE
        if return_code != 0:
            self.status.set_text(
                f"Roblox exited with status {return_code}. Review the output below."
            )
            self.spinner.stop()
            return GLib.SOURCE_REMOVE

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


if __name__ == "__main__":
    app = RobloxLaunchWindow()
    raise SystemExit(app.run(None))
