#!/bin/sh
set -eu

OWNER="Lufiisgreat"
REPOSITORY="mactolinux"
BRANCH="main"
RELEASE_ASSET="RobloxLinux.AppImage"
SOURCE_URL="https://codeload.github.com/$OWNER/$REPOSITORY/tar.gz/refs/heads/$BRANCH"
APPIMAGE_URL="https://github.com/$OWNER/$REPOSITORY/releases/latest/download/$RELEASE_ASSET"

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

for command_name in curl tar python3 install mktemp readlink grep sed; do
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

for source_file in ui.py launch.py ui.sh launch.sh run.sh update-roblox.sh FFlags.json roblox-linux-release.png; do
    [ -f "$TEMP_DIR/source/$source_file" ] ||
        fail "The source archive is missing $source_file."
done

step "Downloading the Roblox runtime"
if ! curl --proto '=https' --proto-redir '=https' \
    --fail --location --silent --show-error --retry 2 \
    "$APPIMAGE_URL" -o "$TEMP_DIR/$RELEASE_ASSET"; then
    fail "No AppImage was found in the latest GitHub Release. Publish a release with the asset named $RELEASE_ASSET, then try again."
fi
[ -s "$TEMP_DIR/$RELEASE_ASSET" ] ||
    fail "The downloaded AppImage is empty."

step "Installing to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$APPLICATIONS_DIR"

for source_file in ui.py launch.py FFlags.json roblox-linux-release.png README.md; do
    if [ "$source_file" = "FFlags.json" ] && [ -e "$INSTALL_DIR/FFlags.json" ]; then
        continue
    fi
    install -m 644 "$TEMP_DIR/source/$source_file" "$INSTALL_DIR/$source_file"
done

for source_file in ui.sh launch.sh run.sh update-roblox.sh; do
    install -m 755 "$TEMP_DIR/source/$source_file" "$INSTALL_DIR/$source_file"
done

install -m 755 "$TEMP_DIR/$RELEASE_ASSET" "$INSTALL_DIR/.RobloxLinux.AppImage.new"
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
