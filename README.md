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

## Publish a release

The AppImage is intentionally not stored in the Git repository. To make the
installer available, create a GitHub Release and attach the x86-64 AppImage
with this exact filename:

```text
RobloxLinux.AppImage
```

The installer downloads the launcher sources from the `main` branch and the
AppImage from the latest GitHub Release.

## Notes

- This project is unofficial and is not affiliated with Roblox.
- Roblox session data, settings, and logs stay in the local
  `DO_NOT_SHARE` folder and should never be uploaded.
