# Development

How the pieces fit, how to build an ISO, and what is not done yet. The design
of the desktop and the package installer is in [DESIGN.md](DESIGN.md).

## How the ISO is made

OziOS does not rebuild the whole system. `iso/remaster.sh` takes a CachyOS
live ISO and converts it:

1. Unpack the root image (`airootfs.sfs`).
2. Build the `ozios-settings` package from `packages/ozios-settings` and
   install it into the image. It brings the theme, the commands and the first
   login setup, rewrites `os-release` and adds an OziOS step to the installer.
3. Optionally swap the kernel (`--kernel`, see `kernel/README.md`).
4. Repack the image, retitle the boot menus, write a new ISO with `xorriso`
   that keeps the original boot records and volume id.

It must run inside the live session of the ISO being converted (it uses that
medium as the source) and needs about 16 GB of disk: `iso/build.sh
--prepare-disk /dev/sdX` prepares an empty disk, then `sudo iso/remaster.sh`.
Expect 30 to 60 minutes on a slow machine.

`iso/build.sh` builds a CachyOS profile from scratch with `mkarchiso` instead.
It works as far as the package list but was not finished.

## Testing

- Unit tests run anywhere with Python 3.14 or newer:
  `python -m unittest discover -s tests`.
- Shell scripts are checked with `bash -n`; QML and desktop behaviour need a
  Plasma session.
- `tools/vm-bridge.sh` (inside a test VM, as root) and `tools/vmrun.sh` /
  `tools/vmexec.sh` (on the host) run scripts in a VirtualBox VM through the
  shared folder, so a VM can be driven without a network login.
  `tools/archive-install.sh` installs extra packages into a live session from
  the Arch Linux Archive snapshot the ISO was built from.
- On a live ISO the root file system is an overlay, which rootless Podman
  cannot use; `ozipkg.box.storage_driver()` falls back to `vfs` there.

## State of things

Checked in a virtual machine (VirtualBox, UEFI) with the live ISO:

- The live ISO boots on `linux-ozios` and shows the OziOS desktop; Software and
  Welcome start without Qt warnings.
- `.deb` packages install into rootless podman boxes and run with their saved
  permissions; AppImages install and run in a bubblewrap sandbox. The helper
  runs through `pkexec`.
- The installer step (`install-to-target`) was run against a base system made
  with `tools/test-install-target.sh`: it installs `ozios-settings` and the
  `linux-ozios` packages, builds the initramfs, puts the OziOS kernel first in
  the GRUB menu, and the result boots to a login prompt on `7.1.6-1-ozios`.

## Not done yet

- A complete installation through the Calamares windows has not been run. The
  CachyOS installer installs online (pacstrap and a net install list); only the
  OziOS step at its end was exercised, on its own.
- The live session has a polkit rule that allows everything without a password,
  so the password prompt of the helper has not been seen. It is the stock
  `auth_admin_keep` action.
- AUR builds have not been run against real podman and the real AUR.
- Windows guest: scripts exist (`winbridge/`, `winimage/`) but have never run
  against a real guest, because the development machine cannot run one. GPU
  passthrough is not automated; `ozi hw` only reports what the machine can do.
- The login screen is still the one the installer sets up.
- Nothing has been run on real hardware.

## What is still CachyOS

The image and the installed system carry no CachyOS kernel, program or artwork.
These parts of CachyOS stay, on purpose, because the installer and the hardware
tools are built on them:

- The repositories (`[cachyos]`, the v3 and v4 builds), `cachyos-keyring` and
  the mirror lists. Without them the installer can not fetch its base system.
- `cachyos-settings` (kernel and I/O tuning, zram), `cachyos-hooks`,
  `cachyos-rate-mirrors`, `cachyos-kde-settings`, `cachyos-fish-config` and
  `chwd` (graphics driver detection).
- The Calamares build (`cachyos-calamares-next`), with its modules and scripts.
  Its look, package list, boot loader entry name and host name are replaced
  (`python/ozipkg/installer.py`).
- `ID=cachyos` in `os-release`, which those tools read to see that they are on
  a supported system. `NAME`, `PRETTY_NAME`, the links and the logo are ours.

Cutting these needs an installer and a package repository of our own; that is a
project of its own.

## Known problems

- `chwd` may still look for `linux-cachyos-*` module packages for the graphics
  drivers; the OziOS kernel brings its own NVIDIA modules.
