# Mactolinux

An unofficial GTK launcher for the Roblox macOS client on x86-64 Linux.
WE GOT UBUNTU AND FEDORA SUPPORTTT

## Install

Run this command in a terminal:

```sh
curl -fsSL https://raw.githubusercontent.com/Lufiisgreat/mactolinux/main/install.sh | sh
```

The installer menu offers **Install**, **Update**, and **Quit**. Choose an
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

## Screenshots

![Mactolinux launcher page](/launcher.png)

![Roblox Discover page in Mactolinux](/discover.png)

The Launcher page has separate update actions: **Check for Roblox updates**
updates the Roblox client, while **Check for Mactolinux updates** checks GitHub
and automatically installs a newer launcher commit, then restarts Mactolinux.
When **Check for updates on startup** is enabled, Mactolinux automatically
installs launcher updates from GitHub and restarts, then checks and updates the
Roblox client from the GUI. When startup checks are disabled, neither update
is checked automatically.

## Install

TO install, its recommended you install these with mactolinux. Below is both required and optional 
packages but i recommend you install all of it.


*Ubuntu/Debian: (apt)	python3-gi gir1.2-gtk-4.0 gir1.2-webkit-6.0 gir1.2-secret-1 wmctrl*

*Fedora: (dnf) python3-gobject gtk4 webkitgtk6.0 libsecret wmctrl*

*Arch: (pacman)	python gtk4 python-gobject webkitgtk-6.0 libsecret wmctrl*

**For encrypted Roblox sign-in persistence, install WebKitGTK and Secret
Service support.**

On Ubuntu, Debian, or fedora, mactolinux is a bit experimental for now, ill fix it soon.

Discover opens the Roblox website inside the launcher when WebKitGTK 6.0 is
installed. Otherwise, it offers to open the site in your default browser. The
launcher opens its own control page first; choose **Discover** to browse
Roblox. The Roblox `.ROBLOSECURITY` session cookie is saved encrypted through
the desktop Secret Service/keyring, such as KDE Wallet. Mactolinux does not
store your Roblox password. Without keyring support, the embedded browser
does not save your login. Game Play links from Discover are passed directly
to Mactolinux's Roblox AppImage, not the system's default `roblox-player` or
`roblox` URL handler. Roblox `games/start` links are handed to the client,
including HTTPS links and experience-start links; the latter are converted to
Roblox's direct `roblox://placeId=` format while preserving other launch
parameters. Friend-join links are passed through unchanged.

`wmctrl` lets the launcher fullscreen Roblox while its player process is
running and restore the window when it exits. In KDE Plasma Wayland, this
requires Roblox to run as an XWayland window; native Wayland windows may not
be controllable by `wmctrl`.

On KDE Plasma Wayland, choose the Roblox display scale in Settings (100%,
150%, 175%, or 200%); changes apply the next time Roblox starts. Mactolinux
applies the selected scale to the primary display before launching Roblox,
then restores the previous scale after the Roblox process exits. Changing
scale before the client starts avoids resizing its camera window during play
and prevents the desktop from enlarging Roblox's framebuffer on high-DPI
displays. If you change the display scale yourself while Roblox is running,
Mactolinux leaves that new scale in place. Keep the launcher running until
Roblox exits so its background monitor can restore the display scale.

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
  be uploaded. `discover-handoff.log` records only link hosts, paths, and
  handoff stages; it omits query parameters. The Roblox session cookie is
  encrypted by the desktop keyring.
