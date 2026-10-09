#!/bin/sh
set -eu
umask 077

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DATA=$HERE/DO_NOT_SHARE
DESKTOP_SHORTCUT_MARKER="X-RobloxLinuxRelease=true"

if [ "$#" -ne 1 ]; then
    echo "Usage: sh uninstaller.sh DESKTOP_SHORTCUT_PATH" >&2
    exit 2
fi

shortcut_path=$1
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

if [ -e "$HERE/RobloxVersion" ] || [ -L "$HERE/RobloxVersion" ]; then
    rm -rf -- "$HERE/RobloxVersion"
fi

if [ -f "$shortcut_path" ] &&
   grep -Fqx "$DESKTOP_SHORTCUT_MARKER" "$shortcut_path"; then
    rm -- "$shortcut_path"
    echo "Removed the Mactolinux desktop shortcut."
fi

echo "Removed the installed Roblox client and prepared shaders."
echo "Saved login, settings, and logs were kept in DO_NOT_SHARE."
