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

The Launcher page has separate update checks: **Check for Roblox updates** updates
the Roblox client, while **Check for Mactolinux updates** checks GitHub for a
new launcher commit. To install a newer launcher commit, run the installer
again and choose **Update**. Mactolinux also checks for a newer launcher
commit every time it starts; this check does not install updates automatically.

The launcher requires Python 3, GTK 4, and Python GObject introspection. On
CachyOS, install the required packages with:

```sh
sudo pacman -S python gtk4 python-gobject wmctrl
```

For encrypted Roblox sign-in persistence, install WebKitGTK and Secret
Service support:

```sh
sudo pacman -S webkitgtk-6.0 libsecret
```

On Ubuntu or Debian, install them with:

```sh
sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-webkit-6.0 gir1.2-secret-1 wmctrl
```

Discover opens the Roblox website inside the launcher when WebKitGTK 6.0 is
installed. Otherwise, it offers to open the site in your default browser. The
launcher opens its own control page first; choose **Discover** to browse
Roblox. The Roblox `.ROBLOSECURITY` session cookie is saved encrypted through
the desktop Secret Service/keyring, such as KDE Wallet. Mactolinux does not
store your Roblox password. Without keyring support, the embedded browser
does not save your login. Game Play links from Discover are passed directly
to Mactolinux's Roblox AppImage, not the system's default `roblox-player` or
`roblox` URL handler.

`wmctrl` lets the launcher fullscreen Roblox while its player process is
running and restore the window when it exits. In KDE Plasma Wayland, this
requires Roblox to run as an XWayland window; native Wayland windows may not
be controllable by `wmctrl`.

The FFlags page also has a user modifications folder. Put replacement files
there with directory paths matching their locations inside
`RobloxVersion/RobloxPlayer.app`, then enable the folder or choose **Apply mods
now**. Modded files are backed up and can be restored with **Reset all mods to
default**. The launcher restores modifications before Roblox updates and
applies them again the next time you play if they are enabled. Close Roblox
before applying or resetting modifications. These are file replacements, not
FastFlags, and the launcher does not include sound, cursor, or font assets.

The AppImage does not need to be attached to a GitHub Release. Keep the
downloaded file in `~/Downloads` or provide its path when the installer asks.

The Uninstall tab lets you remove just the Roblox client and shaders while
keeping saved data and modification files, or remove the full Mactolinux
installation, including `DO_NOT_SHARE`, modification files, launcher files,
desktop-menu entry, command, and encrypted Roblox session in the desktop
keyring.

## Notes

- This project is unofficial and is not affiliated with Roblox.
- Settings and logs stay in the local `DO_NOT_SHARE` folder and should never
  be uploaded. The Roblox session cookie is encrypted by the desktop keyring.
