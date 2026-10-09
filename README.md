# Mactolinux

An unofficial GTK launcher for the Roblox macOS client on x86-64 Linux.

## Install

Once a GitHub Release is published with `RobloxLinux.AppImage` attached, install
the launcher with:

```sh
curl -fsSL https://raw.githubusercontent.com/Lufiisgreat/mactolinux/main/install.sh | sh
```

The installer places Mactolinux in `~/.local/share/mactolinux`, adds it to your
desktop application menu, and creates the `mactolinux` command in
`~/.local/bin`. It does not use `sudo` or remove your saved settings.

The launcher requires Python 3, GTK 4, and Python GObject introspection. On
Ubuntu or Debian, install these first if needed:

```sh
sudo apt install python3 python3-gi gir1.2-gtk-4.0
```

