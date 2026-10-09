# Mactolinux

An unofficial GTK launcher for the Roblox macOS client on x86-64 Linux.

## Install

Run this command in a terminal:

```sh
curl -fsSL https://raw.githubusercontent.com/Lufiisgreat/mactolinux/main/install.sh | sh
```

The installer menu offers **Install**, **Update**, and **Cancel**. Choose an
option, then type `y` to confirm (or `no` to cancel). Install looks for
`RobloxLinux.AppImage` in `~/Downloads` and its subfolders. If it cannot find
the file, choose to search again, enter the path yourself, or cancel. You can
drag and drop the AppImage into the terminal when entering its path. Update
refreshes the Mactolinux launcher files from GitHub while keeping the installed
Roblox runtime and settings. The installer adds Mactolinux to your desktop
application menu and creates the `mactolinux` command in
`~/.local/bin`. It does not use `sudo` or remove your saved settings.
Choose **Update** here to refresh Mactolinux itself. The launcher's
**Check for Roblox updates** button updates the Roblox client, not Mactolinux.

The launcher requires Python 3, GTK 4, and Python GObject introspection. On
Ubuntu or Debian, install these first if needed:

```sh
sudo apt install python3 python3-gi gir1.2-gtk-4.0
```

The AppImage does not need to be attached to a GitHub Release. Keep the
downloaded file in `~/Downloads` or provide its path when the installer asks.

The Uninstall tab removes the Roblox client, prepared shaders, and the
Mactolinux desktop shortcut. It keeps your saved login, settings, and logs.

## Notes

- This project is unofficial and is not affiliated with Roblox.
- Roblox session data, settings, and logs stay in the local
  `DO_NOT_SHARE` folder and should never be uploaded.
