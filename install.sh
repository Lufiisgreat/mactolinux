#!/bin/sh
set -eu

OWNER="Lufiisgreat"
REPOSITORY="mactolinux"
BRANCH="main"
RELEASE_ASSET="RobloxLinux.AppImage"
SOURCE_URL="https://codeload.github.com/$OWNER/$REPOSITORY/tar.gz/refs/heads/$BRANCH"

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    BOLD=$(printf '\033[1m')
    BLUE=$(printf '\033[34m')
    GREEN=$(printf '\033[32m')
    RED=$(printf '\033[31m')
    RESET=$(printf '\033[0m')
else
    BOLD=""
    BLUE=""
    GREEN=""
    RED=""
    RESET=""
fi

banner() {
    printf '\n%s%sMactolinux%s\n' "$BOLD" "$BLUE" "$RESET"
    printf '  Roblox on Linux, ready to play.\n\n'
}

step() {
    printf '%s›%s %s\n' "$BLUE" "$RESET" "$1"
}

success() {
    printf '  %s✓%s %s\n' "$GREEN" "$RESET" "$1"
}

fail() {
    printf '\n%sError:%s %s\n\n' "$RED" "$RESET" "$1" >&2
    exit 1
}

cancel_install() {
    printf '\nInstallation cancelled. No files were changed.\n'
    exit 0
}

confirm_install() {
    if [ ! -r /dev/tty ]; then
        fail "Run this installer from a terminal so you can choose Install and confirm with y."
    fi

    printf '╭────────────────────────────────────────────╮\n'
    printf '│  %sMactolinux Installer%s                      │\n' "$BOLD" "$RESET"
    printf '│  Roblox on Linux, ready to play.           │\n'
    printf '├────────────────────────────────────────────┤\n'
    printf '│  Installs for your user (no sudo):         │\n'
    printf '│  %s\n' "$INSTALL_DIR"
    printf '├────────────────────────────────────────────┤\n'
    printf '│  [1] Install                               │\n'
    printf '│  [2] Cancel                                │\n'
    printf '╰────────────────────────────────────────────╯\n'
    printf '\nChoose an option [1-2]: '
    IFS= read -r choice </dev/tty || cancel_install
    case "$choice" in
        1|i|I|install|Install) ;;
        *) cancel_install ;;
    esac

    printf '\nThis will download launcher files from GitHub and install Mactolinux for your user.\n'
    printf 'Confirm installation? Type y or no [y/no]: '
    IFS= read -r confirmation </dev/tty || cancel_install
    case "$confirmation" in
        y|Y|yes|YES|Yes) ;;
        n|N|no|NO|No) cancel_install ;;
        *) cancel_install ;;
    esac
}

read_appimage_path() {
    find_appimage() {
        if [ -f "$HOME/Downloads/$RELEASE_ASSET" ]; then
            printf '%s\n' "$HOME/Downloads/$RELEASE_ASSET"
        elif [ -d "$HOME/Downloads" ]; then
            find "$HOME/Downloads" -type f -name "$RELEASE_ASSET" -print -quit
        fi
    }

    read_manual_path() {
        printf 'AppImage path (or drag and drop the file here): '
        python3 -c '
import shlex
import sys

try:
    paths = shlex.split(sys.stdin.read())
except ValueError as error:
    print(f"Could not read the dropped path: {error}", file=sys.stderr)
    raise SystemExit(1)
if len(paths) != 1 or "\n" in paths[0] or "\r" in paths[0]:
    print("Drop one AppImage file path, then press Enter.", file=sys.stderr)
    raise SystemExit(1)
print(paths[0])
' </dev/tty
    }

    appimage_path=$(find_appimage)
    if [ -n "$appimage_path" ]; then
        printf '\nFound %s in Downloads:\n  %s\n' \
            "$RELEASE_ASSET" "$appimage_path"
    else
        while :; do
            printf '\nCould not find %s in ~/Downloads.\n' "$RELEASE_ASSET"
            printf '╭────────────────────────────────────────────╮\n'
            printf '│  [1] Try searching Downloads again         │\n'
            printf '│  [2] Enter the file path myself            │\n'
            printf '│  [3] Cancel installation                   │\n'
            printf '╰────────────────────────────────────────────╯\n'
            printf 'Choose an option [1-3]: '
            IFS= read -r choice </dev/tty || cancel_install
            case "$choice" in
                1)
                    appimage_path=$(find_appimage)
                    if [ -n "$appimage_path" ]; then
                        printf '\nFound %s:\n  %s\n' \
                            "$RELEASE_ASSET" "$appimage_path"
                    fi
                    ;;
                2)
                    appimage_path=$(read_manual_path) ||
                        fail "Could not read the AppImage path."
                    ;;
                3) cancel_install ;;
                *) printf 'Please choose 1, 2, or 3.\n' ;;
            esac
            [ -n "$appimage_path" ] && break
        done
    fi

    [ -f "$appimage_path" ] ||
        fail "That path is not a file. Run the installer again and choose another option."
    python3 - "$appimage_path" <<'PY'
import struct
import sys

try:
    with open(sys.argv[1], "rb") as appimage:
        header = appimage.read(20)
except OSError as error:
    print(f"Could not read the AppImage: {error}", file=sys.stderr)
    raise SystemExit(1)

if len(header) < 20 or header[:4] != b"\x7fELF":
    print("The selected file is not a valid Linux AppImage (ELF file).", file=sys.stderr)
    raise SystemExit(1)
byte_order = "<" if header[5:6] == b"\x01" else ">" if header[5:6] == b"\x02" else None
if byte_order is None or struct.unpack(f"{byte_order}H", header[18:20])[0] != 62:
    print("The selected AppImage is not built for x86-64 Linux.", file=sys.stderr)
    raise SystemExit(1)
PY
    [ -s "$appimage_path" ] || fail "The selected AppImage is empty."
}

banner

: "${HOME:?Could not determine your home directory.}"
INSTALL_DIR="${XDG_DATA_HOME:-"$HOME/.local/share"}/mactolinux"
BIN_DIR="$HOME/.local/bin"
APPLICATIONS_DIR="${XDG_DATA_HOME:-"$HOME/.local/share"}/applications"

case "$(uname -s)" in
    Linux) ;;
    *) fail "Mactolinux can only be installed on Linux." ;;
esac

case "$(uname -m)" in
    x86_64|amd64) ;;
    *) fail "Mactolinux currently supports x86-64 Linux only." ;;
esac

for command_name in curl tar python3 install mktemp readlink grep sed find; do
    command -v "$command_name" >/dev/null 2>&1 ||
        fail "Required command '$command_name' was not found."
done

if ! python3 -c 'import gi; gi.require_version("Gtk", "4.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
    printf 'GTK 4 and Python GObject introspection are required.\n'
    printf 'On Ubuntu or Debian, install them with:\n\n'
    printf '  sudo apt install python3 python3-gi gir1.2-gtk-4.0\n\n'
    exit 1
fi

DESKTOP_FILE="$APPLICATIONS_DIR/mactolinux.desktop"
BIN_LINK="$BIN_DIR/mactolinux"
if [ -e "$BIN_LINK" ] || [ -L "$BIN_LINK" ]; then
    if [ ! -L "$BIN_LINK" ] || [ "$(readlink "$BIN_LINK")" != "$INSTALL_DIR/ui.sh" ]; then
        fail "Refusing to replace the existing file $BIN_LINK."
    fi
fi
if [ -e "$DESKTOP_FILE" ] &&
   ! grep -q '^X-Mactolinux-Managed=true$' "$DESKTOP_FILE"; then
    fail "Refusing to replace the existing desktop entry $DESKTOP_FILE."
fi

confirm_install
read_appimage_path

TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/mactolinux-install.XXXXXX") ||
    fail "Could not create a temporary download directory."
cleanup() {
    rm -rf -- "$TEMP_DIR"
}
trap cleanup EXIT HUP INT TERM

step "Downloading launcher files"
if ! curl --proto '=https' --proto-redir '=https' \
    --fail --location --silent --show-error --retry 2 \
    "$SOURCE_URL" -o "$TEMP_DIR/source.tar.gz"; then
    fail "Could not download the project source from GitHub."
fi
mkdir "$TEMP_DIR/source"
if ! tar -xzf "$TEMP_DIR/source.tar.gz" \
    --strip-components=1 -C "$TEMP_DIR/source"; then
    fail "The downloaded source archive could not be extracted."
fi

for source_file in ui.py launch.py ui.sh launch.sh run.sh update-roblox.sh uninstaller.sh FFlags.json roblox-linux-release.png; do
    [ -f "$TEMP_DIR/source/$source_file" ] ||
        fail "The source archive is missing $source_file."
done

step "Installing to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$APPLICATIONS_DIR"

for source_file in ui.py launch.py FFlags.json roblox-linux-release.png README.md; do
    if [ "$source_file" = "FFlags.json" ] && [ -e "$INSTALL_DIR/FFlags.json" ]; then
        continue
    fi
    install -m 644 "$TEMP_DIR/source/$source_file" "$INSTALL_DIR/$source_file"
done

for source_file in ui.sh launch.sh run.sh update-roblox.sh uninstaller.sh; do
    install -m 755 "$TEMP_DIR/source/$source_file" "$INSTALL_DIR/$source_file"
done

install -m 755 "$appimage_path" "$INSTALL_DIR/.RobloxLinux.AppImage.new"
mv -f "$INSTALL_DIR/.RobloxLinux.AppImage.new" "$INSTALL_DIR/RobloxLinux.AppImage"

ln -sfn "$INSTALL_DIR/ui.sh" "$BIN_LINK"
desktop_exec=$(printf '%s' "$INSTALL_DIR/ui.sh" |
    sed 's/\\/\\\\/g; s/"/\\"/g; s/\$/\\$/g; s/`/\\`/g; s/%/%%/g')
cat > "$TEMP_DIR/mactolinux.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Mactolinux
Comment=Play Roblox on Linux
Exec=sh "$desktop_exec"
Icon=$INSTALL_DIR/roblox-linux-release.png
Terminal=false
Categories=Game;
X-Mactolinux-Managed=true
EOF
install -m 644 "$TEMP_DIR/mactolinux.desktop" "$DESKTOP_FILE"

success "Mactolinux is installed."
printf '\nOpen it from your applications menu, or run:\n\n'
printf '  %smactolinux%s\n\n' "$BOLD" "$RESET"
case ":${PATH:-}:" in
    *":$BIN_DIR:"*) ;;
    *) printf 'If that command is not found, open a new terminal or run:\n\n  %s\n\n' "$BIN_LINK" ;;
esac
