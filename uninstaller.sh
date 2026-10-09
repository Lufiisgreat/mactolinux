#!/bin/sh
set -eu
umask 077

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DATA=$HERE/DO_NOT_SHARE
DESKTOP_SHORTCUT_MARKER="X-RobloxLinuxRelease=true"
APPLICATIONS_DIR="${XDG_DATA_HOME:-"$HOME/.local/share"}/applications"
APP_MENU_FILE="$APPLICATIONS_DIR/com.robloxlinux.release.desktop"
LEGACY_APP_MENU_FILE="$APPLICATIONS_DIR/mactolinux.desktop"
COMMAND_LINK="$HOME/.local/bin/mactolinux"

if [ "$#" -ne 2 ]; then
    echo "Usage: sh uninstaller.sh roblox-only|everything DESKTOP_SHORTCUT_PATH" >&2
    exit 2
fi

mode=$1
shortcut_path=$2
case "$mode" in
    roblox-only|everything) ;;
    *)
        echo "Choose roblox-only or everything." >&2
        exit 2
        ;;
esac

if [ "$(basename -- "$shortcut_path")" != "roblox-linux-release.desktop" ]; then
    echo "Refusing to remove an unexpected desktop shortcut path." >&2
    exit 2
fi

command -v flock >/dev/null 2>&1 || {
    echo "The uninstaller requires flock." >&2
    exit 1
}

mkdir -p "$DATA"
chmod 700 "$DATA"
exec 9>"$DATA/instance.lock"
if ! flock -n 9; then
    echo "Close Roblox before uninstalling it." >&2
    exit 1
fi

if [ -f "$DATA/modifications-manifest.json" ]; then
    python3 "$HERE/mods.py" reset --quiet
fi

if [ -f "$shortcut_path" ] &&
   grep -Fqx "$DESKTOP_SHORTCUT_MARKER" "$shortcut_path"; then
    rm -- "$shortcut_path"
    echo "Removed the Mactolinux desktop shortcut."
fi

if [ "$mode" = roblox-only ]; then
    if [ -e "$HERE/RobloxVersion" ] || [ -L "$HERE/RobloxVersion" ]; then
        rm -rf -- "$HERE/RobloxVersion"
    fi
    echo "Removed the installed Roblox client and prepared shaders."
    echo "Settings and logs were kept in DO_NOT_SHARE."
    echo "The encrypted Roblox session remains in the desktop keyring."
    exit 0
fi

if [ -f "$APP_MENU_FILE" ] &&
   grep -Fqx 'X-Mactolinux-Managed=true' "$APP_MENU_FILE"; then
    rm -- "$APP_MENU_FILE"
    echo "Removed the Mactolinux applications-menu entry."
fi
if [ -f "$LEGACY_APP_MENU_FILE" ] &&
   grep -Fqx 'X-Mactolinux-Managed=true' "$LEGACY_APP_MENU_FILE"; then
    rm -- "$LEGACY_APP_MENU_FILE"
    echo "Removed the legacy Mactolinux applications-menu entry."
fi

if [ -L "$COMMAND_LINK" ] &&
   [ "$(readlink "$COMMAND_LINK")" = "$HERE/ui.sh" ]; then
    rm -- "$COMMAND_LINK"
    echo "Removed the mactolinux command."
fi

for file in \
    FFlags.json README.md install.sh launch.py launch.sh mods.py \
    roblox-linux-release.png run.sh ui.py ui.sh update-roblox.sh \
    uninstaller.sh RobloxLinux.AppImage .RobloxLinux.AppImage.new; do
    if [ -f "$HERE/$file" ] || [ -L "$HERE/$file" ]; then
        rm -f -- "$HERE/$file"
    fi
done

for directory in RobloxVersion DO_NOT_SHARE modifications; do
    if [ -e "$HERE/$directory" ] || [ -L "$HERE/$directory" ]; then
        rm -rf -- "$HERE/$directory"
    fi
done

echo "Removed the Mactolinux launcher, Roblox client, app-menu entry, command, and saved data."
