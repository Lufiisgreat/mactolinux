#!/bin/sh
set -eu

SCRIPT=$0
while [ -L "$SCRIPT" ]; do
    SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$SCRIPT")" && pwd)
    LINK=$(readlink "$SCRIPT")
    case "$LINK" in
        /*) SCRIPT=$LINK ;;
        *) SCRIPT=$SCRIPT_DIR/$LINK ;;
    esac
done
HERE=$(CDPATH= cd -- "$(dirname -- "$SCRIPT")" && pwd)

if ! python3 -c 'import gi; gi.require_version("Gtk", "4.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
    message='The Roblox launch window needs GTK 4 and Python GObject introspection. On Ubuntu or Debian, install them with: sudo apt install python3-gi gir1.2-gtk-4.0'
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title='Launcher dependency missing' --width=460 --text="$message" || :
    fi
    printf '%s\n' "$message" >&2
    exit 1
fi

exec python3 "$HERE/launch.py" "$@"
