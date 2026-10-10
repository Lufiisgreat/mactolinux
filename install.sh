#!/bin/sh
set -eu

OWNER="Lufiisgreat"
REPOSITORY="mactolinux"
BRANCH="main"
RELEASE_ASSET="RobloxLinux.AppImage"
SOURCE_URL="https://codeload.github.com/$OWNER/$REPOSITORY/tar.gz/refs/heads/$BRANCH"
COMMIT_URL="https://api.github.com/repos/$OWNER/$REPOSITORY/commits/$BRANCH"

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    BOLD=$(printf '\033[1m')
    DIM=$(printf '\033[2m')
    BLUE=$(printf '\033[34m')
    CYAN=$(printf '\033[36m')
    GREEN=$(printf '\033[32m')
    RED=$(printf '\033[31m')
    RESET=$(printf '\033[0m')
else
    BOLD=""
    DIM=""
    BLUE=""
    CYAN=""
    GREEN=""
    RED=""
    RESET=""
fi

banner() {
    printf '\n%s%s' "$CYAN" "$BOLD"
    printf '  ╭──────────────────────────────────────────────╮\n'
    printf '  │             M A C T O L I N U X              │\n'
    printf '  │          ROBLOX ON LINUX · X86-64            │\n'
    printf '  ╰──────────────────────────────────────────────╯%s\n' "$RESET"
    printf '  Play the macOS Roblox client on your Linux desktop.\n'
    printf '  %sDetected: %s%s\n' "$DIM" "$DISTRO_PRETTY" "$RESET"
    printf '  %sA simple setup; system dependencies may require sudo.%s\n\n' "$DIM" "$RESET"
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

read_distro() {
    DISTRO_NAME="Linux"
    DISTRO_VERSION=""
    DISTRO_PRETTY=""
    if [ -r /etc/os-release ]; then
        . /etc/os-release
        DISTRO_NAME="${NAME:-${ID:-Linux}}"
        DISTRO_VERSION="${VERSION_ID:-${VERSION:-}}"
    fi
    if [ -n "$DISTRO_VERSION" ]; then
        case "${PRETTY_NAME:-}" in
            *"$DISTRO_VERSION"*) DISTRO_PRETTY="$PRETTY_NAME" ;;
            *) DISTRO_PRETTY="$DISTRO_NAME $DISTRO_VERSION" ;;
        esac
    elif [ -n "${BUILD_ID:-}" ]; then
        DISTRO_PRETTY="${PRETTY_NAME:-$DISTRO_NAME} ($BUILD_ID)"
    else
        DISTRO_PRETTY="${PRETTY_NAME:-$DISTRO_NAME}"
    fi
}

cancel_install() {
    printf '\n%s cancelled. No files were changed.\n' \
        "${install_mode:-Installation}"
    exit 0
}

choose_uninstall_mode() {
    printf '\n%s╭────────────────────────────────────────────────╮%s\n' "$BLUE" "$RESET"
    printf '│  %-46s│\n' 'What should be removed?'
    printf '│  %-46s│\n' 'Roblox only   Client and shaders; keep settings'
    printf '│  %-46s│\n' 'Everything    All Mactolinux files and data'
    printf '╰────────────────────────────────────────────────╯\n'
    printf '\n%s❯%s [1] Roblox only    [2] Everything    [3] Cancel\n' "$CYAN" "$RESET"
    printf '\nChoose an option [1-3]: '
    IFS= read -r choice </dev/tty || cancel_install
    case "$choice" in
        1|r|R|roblox|Roblox|roblox-only)
            uninstall_mode=roblox-only
            uninstall_prompt='remove the Roblox client and prepared shaders, keeping your settings and mods'
            ;;
        2|e|E|everything|Everything)
            uninstall_mode=everything
            uninstall_prompt='remove everything, including your settings, mods, AppImage, and launcher files'
            ;;
        *) cancel_install ;;
    esac
}

confirm_install() {
    if [ ! -r /dev/tty ]; then
        fail "Run this installer from a terminal so you can choose an option and confirm with y."
    fi

    printf '%s╭──────────────────────────────────────────────────╮%s\n' "$BLUE" "$RESET"
    printf '│%14s%sWelcome to Mactolinux%s%15s│\n' '' "$BOLD" "$RESET" ''
    printf '│  %-48s│\n' 'Setup · choose an action'
    printf '├──────────────────────────────────────────────────┤\n'
    printf '│  %-48s│\n' 'Install   Set up the launcher and Roblox client'
    printf '│  %-48s│\n' 'Update    Refresh launcher files; keep your data'
    printf '│  %-48s│\n' 'Uninstall Remove Roblox or all of Mactolinux'
    printf '│  %-48s│\n' 'Quit      Leave everything unchanged'
    printf '╰──────────────────────────────────────────────────╯\n'
    printf '\n%s❯%s [1] Install  [2] Update  [3] Uninstall  [4] Quit\n' "$CYAN" "$RESET"
    printf '\nChoose an option [1-4]: '
    IFS= read -r choice </dev/tty || cancel_install
    case "$choice" in
        1|i|I|install|Install) install_mode=install ;;
        2|u|U|update|Update) install_mode=update ;;
        3|uninstall|Uninstall) install_mode=uninstall ;;
        4|q|Q|quit|Quit) cancel_install ;;
        *) cancel_install ;;
    esac

    if [ "$install_mode" = uninstall ]; then
        [ -f "$INSTALL_DIR/uninstaller.sh" ] ||
            fail "Mactolinux is not installed at $INSTALL_DIR. Nothing to uninstall."
        choose_uninstall_mode
        printf '\nThis will %s. Confirm? Type y or no [y/no]: ' "$uninstall_prompt"
        IFS= read -r confirmation </dev/tty || cancel_install
        case "$confirmation" in
            y|Y|yes|YES|Yes) ;;
            n|N|no|NO|No) cancel_install ;;
            *) cancel_install ;;
        esac
        return
    fi

    if [ "$install_mode" = update ]; then
        [ -x "$INSTALL_DIR/RobloxLinux.AppImage" ] ||
            fail "Mactolinux is not installed at $INSTALL_DIR. Choose Install first."
        printf '\nThis will update Mactolinux launcher files and keep your Roblox runtime and settings.\n'
    else
        printf '\nThis will install Mactolinux for your user and set up the Roblox runtime.\n'
    fi
    printf 'Confirm %s? Type y or no [y/no]: ' "$install_mode"
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
            find "$HOME/Downloads" -type f -name "$RELEASE_ASSET" \
                -print -quit 2>/dev/null || :
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

read_distro
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

DESKTOP_FILE="$APPLICATIONS_DIR/com.robloxlinux.release.desktop"
LEGACY_DESKTOP_FILE="$APPLICATIONS_DIR/mactolinux.desktop"
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

run_uninstall() {
    if command -v xdg-user-dir >/dev/null 2>&1; then
        shortcut_dir=$(xdg-user-dir DESKTOP 2>/dev/null || :)
    else
        shortcut_dir=""
    fi
    [ -n "$shortcut_dir" ] || shortcut_dir="$HOME/Desktop"
    shortcut_path="$shortcut_dir/roblox-linux-release.desktop"

    step "Uninstalling ($uninstall_mode)"
    if sh "$INSTALL_DIR/uninstaller.sh" "$uninstall_mode" "$shortcut_path"; then
        if [ "$uninstall_mode" = everything ]; then
            success "Mactolinux has been removed."
        else
            success "Roblox has been uninstalled."
        fi
    else
        fail "The uninstaller reported an error."
    fi
    exit 0
}

case "${1:-}" in
    --update-noninteractive)
        [ "$#" -eq 1 ] || fail "Usage: install.sh --update-noninteractive"
        install_mode=update
        [ -x "$INSTALL_DIR/RobloxLinux.AppImage" ] ||
            fail "Mactolinux is not installed at $INSTALL_DIR."
        ;;
    "")
        confirm_install
        ;;
    *)
        fail "Unknown installer option: $1"
        ;;
esac
if [ "$install_mode" = uninstall ]; then
    run_uninstall
fi
if [ "$install_mode" = install ]; then
    read_appimage_path
fi

ensure_gtk_dependencies() {
    distro_pretty="$DISTRO_PRETTY"
    dependency_mode="${1:-interactive}"

    if python3 -c 'import gi; gi.require_version("Gtk", "4.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
        success "GTK 4 launcher dependencies are already available on $distro_pretty."
    else
        if [ "$dependency_mode" = noninteractive ]; then
            fail "GTK 4 and Python GObject introspection are missing. Run install.sh interactively to install them."
        fi

        step "Installing GTK 4 launcher dependencies for $distro_pretty"
        if command -v apt-get >/dev/null 2>&1; then
            pkg_cmd="apt-get install -y python3-gi gir1.2-gtk-4.0"
        elif command -v dnf >/dev/null 2>&1; then
            pkg_cmd="dnf install -y python3-gobject gtk4"
        elif command -v pacman >/dev/null 2>&1; then
            pkg_cmd="pacman -S --needed --noconfirm python gtk4 python-gobject"
        else
            fail "Automatic GTK dependency installation is not supported for your package manager. Install GTK 4 and Python GObject manually."
        fi

        if [ "$(id -u)" -eq 0 ]; then
            $pkg_cmd </dev/tty
        elif command -v sudo >/dev/null 2>&1; then
            sudo $pkg_cmd </dev/tty
        else
            fail "GTK dependencies are missing and sudo is unavailable."
        fi

        if ! python3 -c 'import gi; gi.require_version("Gtk", "4.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
            fail "GTK dependencies were installed, but Python still cannot load GTK 4. Check that the system python3 package is being used."
        fi
        success "GTK 4 launcher dependencies installed successfully on $distro_pretty."
    fi

    if [ "$dependency_mode" = noninteractive ]; then
        return
    fi

    if python3 -c 'import gi; gi.require_version("WebKit", "6.0"); from gi.repository import WebKit' >/dev/null 2>&1 &&
        python3 -c 'import gi; gi.require_version("Secret", "1"); from gi.repository import Secret' >/dev/null 2>&1 &&
        command -v wmctrl >/dev/null 2>&1; then
        success "Optional Discover, keyring, and fullscreen support are already available on $distro_pretty."
        return
    fi

    if command -v apt-get >/dev/null 2>&1; then
        optional_cmd="apt-get install -y gir1.2-webkit-6.0 gir1.2-secret-1 wmctrl"
    elif command -v dnf >/dev/null 2>&1; then
        optional_cmd="dnf install -y webkitgtk6.0 libsecret wmctrl"
    elif command -v pacman >/dev/null 2>&1; then
        optional_cmd="pacman -S --needed --noconfirm webkitgtk-6.0 libsecret wmctrl"
    else
        optional_cmd=""
    fi

    if [ -n "$optional_cmd" ]; then
        step "Installing optional Discover, keyring, and fullscreen support for $distro_pretty"
        if [ "$(id -u)" -eq 0 ]; then
            $optional_cmd </dev/tty || :
        elif command -v sudo >/dev/null 2>&1; then
            sudo $optional_cmd </dev/tty || :
        fi
        success "Optional Discover, keyring, and fullscreen packages are installed where available on $distro_pretty."
    fi
}

if [ "${1:-}" = "--update-noninteractive" ]; then
    ensure_gtk_dependencies noninteractive
else
    ensure_gtk_dependencies interactive
fi

TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/mactolinux-install.XXXXXX") ||
    fail "Could not create a temporary download directory."
cleanup() {
    rm -rf -- "$TEMP_DIR"
}
trap cleanup EXIT HUP INT TERM

step "Checking the latest Mactolinux commit"
if ! curl --proto '=https' --proto-redir '=https' \
    --fail --location --silent --show-error --retry 2 \
    -H 'Accept: application/vnd.github+json' \
    -H 'X-GitHub-Api-Version: 2022-11-28' \
    "$COMMIT_URL" -o "$TEMP_DIR/commit.json"; then
    fail "Could not check the latest Mactolinux commit on GitHub."
fi
COMMIT_SHA=$(python3 - "$TEMP_DIR/commit.json" <<'PY'
import json
import re
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as response:
        sha = json.load(response)["sha"]
except (OSError, KeyError, json.JSONDecodeError, TypeError) as error:
    print(f"Could not read the latest commit from GitHub: {error}", file=sys.stderr)
    raise SystemExit(1)

if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{40}", sha) is None:
    print("GitHub returned an invalid commit ID.", file=sys.stderr)
    raise SystemExit(1)
print(sha)
PY
) || fail "Could not read the latest Mactolinux commit."
SOURCE_URL="https://codeload.github.com/$OWNER/$REPOSITORY/tar.gz/$COMMIT_SHA"

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

for source_file in \
    ui.py launch.py mods.py ui.sh launch.sh run.sh update-roblox.sh \
    uninstaller.sh FFlags.json roblox-linux-release.png; do
    [ -f "$TEMP_DIR/source/$source_file" ] ||
        fail "The source archive is missing $source_file."
done

step "Installing to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$APPLICATIONS_DIR"

for source_file in \
    ui.py launch.py mods.py FFlags.json roblox-linux-release.png README.md; do
    if [ "$source_file" = "FFlags.json" ] && [ -e "$INSTALL_DIR/FFlags.json" ]; then
        continue
    fi
    install -m 644 "$TEMP_DIR/source/$source_file" "$INSTALL_DIR/$source_file"
done

for source_file in ui.sh launch.sh run.sh update-roblox.sh uninstaller.sh; do
    install -m 755 "$TEMP_DIR/source/$source_file" "$INSTALL_DIR/$source_file"
done

if [ "$install_mode" = install ]; then
    install -m 755 "$appimage_path" "$INSTALL_DIR/.RobloxLinux.AppImage.new"
    mv -f "$INSTALL_DIR/.RobloxLinux.AppImage.new" "$INSTALL_DIR/RobloxLinux.AppImage"
fi

mkdir -p "$INSTALL_DIR/DO_NOT_SHARE"
chmod 700 "$INSTALL_DIR/DO_NOT_SHARE"
printf '%s\n' "$COMMIT_SHA" > "$INSTALL_DIR/DO_NOT_SHARE/launcher-version"
chmod 600 "$INSTALL_DIR/DO_NOT_SHARE/launcher-version"

ln -sfn "$INSTALL_DIR/ui.sh" "$BIN_LINK"
desktop_exec=$(printf '%s' "$INSTALL_DIR/ui.sh" |
    sed 's/\\/\\\\/g; s/"/\\"/g; s/\$/\\$/g; s/`/\\`/g; s/%/%%/g')
cat > "$TEMP_DIR/mactolinux.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Mactolinux
GenericName=Roblox launcher
Comment=Play Roblox on Linux
Exec=sh "$desktop_exec"
Icon=$INSTALL_DIR/roblox-linux-release.png
StartupWMClass=Mactolinux
Terminal=false
Categories=Game;
Keywords=Roblox;Mactolinux;Game;
X-Mactolinux-Managed=true
EOF
install -m 644 "$TEMP_DIR/mactolinux.desktop" "$DESKTOP_FILE"
if [ -f "$LEGACY_DESKTOP_FILE" ] &&
   grep -Fqx 'X-Mactolinux-Managed=true' "$LEGACY_DESKTOP_FILE"; then
    rm -- "$LEGACY_DESKTOP_FILE"
fi

if [ "$install_mode" = update ]; then
    success "Mactolinux update complete."
else
    success "Mactolinux installation complete."
fi
printf '\nOpen it from your applications menu, or run:\n\n'
printf '  %smactolinux%s\n\n' "$BOLD" "$RESET"
case ":${PATH:-}:" in
    *":$BIN_DIR:"*) ;;
    *) printf 'If that command is not found, open a new terminal or run:\n\n  %s\n\n' "$BIN_LINK" ;;
esac
