# OziOS design

Status: draft 1. This is the spec the code is written against. Where a section
says "verify in VM", nobody has run it on a real system yet.

## 1. What OziOS is

An Arch-based desktop system built on CachyOS packages and KDE Plasma 6, for
people coming from Windows who want speed without the Arch learning curve.
Three things set it apart:

1. Its own desktop on top of Plasma: one visual language from boot menu to
   lock screen, with motion that feels designed rather than default.
2. A package installer that explains what an install will do before it does
   it, and can install Debian/Ubuntu `.deb` files without letting them touch
   the system.
3. Windows programs opened from the file manager, running in a real Windows
   guest (see `winbridge/`).

Ease of use wins over configurability. Anything that needs a terminal is a bug.

## 2. Ground rules

- **Platform**: CachyOS repositories, Plasma 6.7 on Wayland, KWin 6.7, Qt 6.11,
  Python 3.14, bubblewrap 0.11. Verified on the 2026-08 live ISO.
- **No compiled code in this repository.** It is built inside a live session
  on weak hardware. Everything is Python, QML, JavaScript, shell or data.
- **Apps** are Python 3 + PyQt6 shells around QML (Kirigami, Kirigami Addons).
  All logic lives in plain Python with no Qt imports, so it runs under
  `unittest` on any OS. The command line is the API: every GUI action maps to
  an `ozi-pkg` / `ozi` command that also works with `--json`.
- **Plasmoids** run those same commands through the Plasma5Support
  `executable` data engine and contain no logic of their own.
- **Root** is only ever reached through `pkexec` and one small helper with a
  fixed set of verbs (section 6.6). Nothing else runs as root, and no GUI
  process ever does.
- **One package** for now, `ozios-settings`, built by `makepkg` from a
  checkout. Python code installs to `/usr/lib/ozios/python/` (not
  site-packages, so a Python upgrade cannot break it); launchers add that
  directory to `sys.path`. Data goes to `/usr/share/ozios/`.
- **Every entry point also runs from a source checkout**, finding its data
  relative to its own file. That is how it is tested in the VM.
- **Language**: source strings are English. User-facing strings go through
  `tr()`; `data/i18n/tr.json` maps English to Turkish. No compile step.
- **Code style**: English, small functions, comments only where the reason is
  not obvious from the code. LF line endings.
- **Licences**: our code is MIT. Any file derived from KDE or other upstream
  sources keeps its original licence header and is listed in
  `docs/LICENSES.md`.

## 3. Visual identity

The palette is fixed: ink `#080B10`, cyan `#00E5FF`, ice `#F4FCFF`.
The mark is a tesseract. Everything else in this section is derived from how
a tesseract is drawn, so the look is not an arbitrary dark theme.

- **Depth is shown by light, not shadow.** In the logo, near edges are bright
  and thick, far edges dim and thin. The interface uses the same ramp for
  hierarchy: active things are near (cyan `#00E5FF`, 2px), available things
  are mid (`#0098B0`, 1px), inactive things are far (`#00465C`, 1px).
  Drop shadows are not used for emphasis.
- **Lines before fills.** The mark is a wireframe. Controls are outlined; a
  filled cyan button appears at most once per view, for the main action.
- **Nested frames.** A tesseract is a square inside a square joined at the
  corners. Large surfaces that need emphasis (the install review, the welcome
  hero) get short 45 degree corner ticks. Small controls never do.
- **Corners** are tight: 8px windows and sheets, 4px controls, 2px chips.
- **Supporting colours**: raised `#0E131B`, control `#141B26`, muted text
  `#8096A0`, positive `#3CE6A0`, caution `#FFBE5A`, danger `#FF556E`.
- **Type**: one family for interface text and one monospace, both available
  in the repositories with full Turkish coverage. Final choice in section 3.1.
- **Motion** follows one idea, things arrive from depth and recede into it:
  windows open by growing from 92% with a short overshoot, close by shrinking
  and dimming. 200 to 260 ms. Nothing moves unless the user did something,
  except the wallpaper, which stops whenever a window covers it.
- **Words**: sentence case, plain verbs, no all-caps labels. A button names
  what happens ("Install", then "Installed"). Errors say what went wrong and
  what to do next.

### 3.1 Tokens

To be filled in by the visual design pass: type families and scale, spacing
scale, component states, motion curves.

## 4. Desktop

Delivered as standard Plasma packages so System Settings keeps working.

| Piece | Where | Notes |
|---|---|---|
| Global theme `org.ozios.desktop` | `desktop/look-and-feel/` | colours, layout, splash, defaults |
| Layouts | same, `contents/layouts/` | Bridge (top bar + floating dock, default), Deck (one floating bar at the bottom), Classic (Plasma default) |
| Plasma style `OziOS` | `desktop/plasma-style/` | `colors`, `plasmarc`, only the SVGs that must differ from Breeze |
| Colour scheme | `branding/OziOS.colors` | add accent colour and the depth ramp |
| Window decoration | Breeze, configured through `breezerc` | no custom decoration engine |
| Wallpaper `org.ozios.tesseract` | `desktop/wallpaper/` | add settings (animate, speed, size) and still variants |
| Window effects | `desktop/kwin-effects/` | scripted (JavaScript) open/close effect; built-in effects tuned by config |
| Control widget `org.ozios.control` | `desktop/plasmoids/` | tray popup: game mode, effects level, wallpaper motion, power profile, Windows guest, updates |
| Lock screen | `kscreenlockerrc` | uses the tesseract wallpaper |
| Login screen | plasma-login-manager config | verify in VM what can be themed |
| Defaults for new users | `packages/ozios-settings/seed-defaults` | writes config into `/etc/skel` and existing homes so the first login already looks right |

`ozi` gains: `ozi effects full|light|off`, `ozi layout bridge|deck|classic`,
`ozi mode game on|off`, `ozi status --json`.

Performance rules: the wallpaper animates at 20 fps and stops when covered;
on software rendering the light profile is chosen automatically (no blur, no
wobble, still wallpaper); file content indexing is off by default.

## 5. Welcome

`ozi-welcome`, shown once after first login and from the menu. Replaces
CachyOS Hello. Pages: a hero with a tesseract that can be turned by dragging;
Install (live session only, starts the installer); Look (layout, effects
level, wallpaper motion); Apps (opens Packages); Windows programs (guest
setup with the licence notice); Updates.

## 6. Packages

`ozi-pkg` (command line) and the Packages app. Python package `ozipkg`.

### 6.1 What it installs

| Input | How it is installed | Isolation |
|---|---|---|
| Repository package | pacman, signature enforced | none (system package) |
| Local `.pkg.tar.*` | pacman `-U` after review | none |
| AUR package | PKGBUILD review, build in a sandbox without network or home access, then pacman `-U` | build is isolated; result is a system package |
| `.deb` (Debian/Ubuntu) | installed with apt inside a per-app container image; started in a fresh container each launch | cannot change the system; sees only what its permissions allow |
| Flatpak (`.flatpakref`, Flathub search) | flatpak, user installation | Flatpak sandbox, permissions editable |
| AppImage | moved to `~/Applications`, never executed during inspection, launched in a sandbox | bubblewrap sandbox |
| `.exe` / `.msi` | handed to `ozi-winrun` | Windows guest |

### 6.2 `.deb` in a box

podman, rootless. The stack (podman and its helpers) is installed on first
use, not shipped on every system.

- Install: a build container from an Ubuntu LTS or Debian stable base runs
  `apt-get install ./package.deb` with the network on and **no host mounts
  except the `.deb` itself, read-only**. Maintainer scripts therefore run with
  no access to the host system or the user's files. The result is committed as
  image `ozi/<app-id>`.
- Launch: `ozi-box run <app-id>` starts a throwaway container from that image
  with only what the app's permissions allow: display socket, sound socket,
  GPU device, a private home directory, and optionally network, selected
  host folders, camera, other devices.
- Menu entries and icons are copied out of the image and rewritten to call
  `ozi-box run`.
- Remove: delete the image and the private home.

### 6.3 The review

Before anything is installed the user sees one screen:

- what it is, where it came from, whether the signature or checksum checks out;
- "What this will do" in plain language (adds a background service, installs
  a program that runs as administrator, adds a software source, ...);
- findings from the risk rules, each with the evidence line;
- the permissions it will start with (for boxed, Flatpak and sandboxed apps).

A verdict of *looks normal*, *needs a look* or *dangerous* sits at the top.
It is described as a check for known bad patterns, never as a guarantee.

### 6.4 Risk rules

Data-driven (`data/rules/*.json`): id, where it applies (install script,
PKGBUILD, file list, desktop entry), pattern or structural test, severity,
plain-language title and explanation. Structural tests cover setuid and
setgid files, files in sensitive locations (sudoers, PAM, ld.so.preload,
profile.d, systemd units, udev rules, polkit rules, cron, autostart, kernel
modules, apt sources and keys), and for AUR: typosquatting against a list of
popular names, very new or orphaned packages, non-HTTPS or IP-literal
sources, skipped checksums on non-VCS sources, downloads inside `build()`.

### 6.5 Transactions

plan -> confirm -> snapshot (snapper, if the root is btrfs) -> run -> log.
History is JSON lines in `~/.local/state/ozios/history.jsonl` plus the
helper's own log in `/var/log/ozios/`. Undo: snapper undo for system
packages, image removal for boxes, uninstall for Flatpaks.

### 6.6 The privileged helper

`/usr/lib/ozios/ozi-pkg-helper`, started only through `pkexec` with polkit
action `org.ozios.pkg.manage` (administrator password, kept for a few
minutes). Verbs: `install-repo`, `install-file`, `remove`, `upgrade`,
`snapshot`, `undo`. Rules: arguments are validated against strict patterns;
no shell is ever involved; a file to install is first copied into a
root-owned private directory and its SHA-256 compared with the one the user
reviewed; the environment and `PATH` are set by the helper; output is JSON
lines.

## 7. Permissions

One vocabulary for every kind of contained app: Internet, Files (none /
chosen folders / everything), Camera, Microphone and sound, Other devices,
Old-style display access (X11). The Permissions page lists installed apps
with their toggles.

- Flatpak apps: `flatpak override --user`.
- Boxed `.deb` apps: flags for the next `ozi-box run`.
- AppImages and, when the user turns it on, ordinary system apps:
  `ozi-sandbox run`, which builds a bubblewrap command from the app's profile
  and filters D-Bus through `xdg-dbus-proxy`.

Profiles live in `~/.config/ozios/permissions/<app-id>.json`.
The page states plainly what cannot be contained: an ordinary system package
that is not sandboxed can do whatever the user can.

## 8. From power button to desktop

Boot menu images on the ISO, installer branding (`calamares` branding
directory `ozios`), boot splash (Plymouth theme, optional), login screen,
splash, desktop, lock screen. Each uses the same mark and palette. Bitmap
assets are generated by scripts in `tools/` from the same geometry code, never
drawn by hand.

## 9. Packaging and the ISO

- `packages/ozios-settings/PKGBUILD` installs everything above.
- `iso/remaster.sh` converts a CachyOS ISO without rebuilding it. Extra
  packages for the live image must come from the package archive of the
  ISO's build date, otherwise newer libraries get mixed into an older image.
- The installed system gets the package from a Calamares step
  (`patch-installer`, `install-to-target`).

## 10. Testing

- Unit tests (`python -m unittest`) for all `ozipkg` logic; they run on the
  development host.
- In the VM, as an unprivileged test user: `qmllint` for every QML file, an
  offscreen load of each app, container and sandbox smoke tests.
- By the maintainer in the VM's desktop session: screenshots of every screen,
  and one real install of each kind.
