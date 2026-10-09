# Mactolinux

An unofficial GTK launcher for the Roblox macOS client on x86-64 Linux.

## Install

Run this command in a terminal:

```sh
curl -fsSL https://raw.githubusercontent.com/Lufiisgreat/mactolinux/main/install.sh | sh
```

The installer shows an Install/Cancel menu. Choose **Install**, then type `y`
to confirm (or `no` to cancel). When prompted, drag and drop your downloaded
x86-64 Linux `RobloxLinux.AppImage` into the terminal and press Enter. The
installer downloads the launcher files from GitHub and installs everything in
`~/.local/share/mactolinux`, adds it to your desktop application menu, and
creates the `mactolinux` command in `~/.local/bin`. It does not use `sudo` or
remove your saved settings.

The launcher requires Python 3, GTK 4, and Python GObject introspection. On
Ubuntu or Debian, install these first if needed:

```sh
sudo apt install python3 python3-gi gir1.2-gtk-4.0
```

The AppImage does not need to be attached to a GitHub Release. Keep the
downloaded file on your computer and provide its path when the installer asks.

The Uninstall tab removes the Roblox client, prepared shaders, and the
Mactolinux desktop shortcut. It keeps your saved login, settings, and logs.

## Notes

- This project is unofficial and is not affiliated with Roblox.
- Roblox session data, settings, and logs stay in the local
  `DO_NOT_SHARE` folder and should never be uploaded.
