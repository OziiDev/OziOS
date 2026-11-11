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

## Not done yet

- Installing from the ISO is untested. The installer gets an extra step that
  installs `ozios-settings` and, when present, the `linux-ozios` packages into
  the new system, then rebuilds the GRUB menu; whether it runs is unknown.
- The kernel build (`kernel/`) is being exercised on GitHub Actions; no ISO
  has carried the kernel yet.
- Package installer: `ozipkg` has the review rules, package inspection,
  permissions model and container command builders with tests, and the
  `ozi-pkg` command line tool installs .deb packages into boxes (tested with
  a stand-in for podman, not yet on a real system). The privileged helper with
  polkit, AUR support, and the graphical apps (Software, Welcome, the control
  widget) are written and unit tested where they have no Qt in them, but the
  Qt Quick files have only been checked for structure, not started.
- Windows guest: scripts exist (`winbridge/`, `winimage/`) but have never run
  against a real guest. GPU passthrough is not automated.
- Boot menu images, login screen and installer artwork are still CachyOS's.

## Known problems

- The colour scheme was not applied to ordinary applications on the first
  live boot; `tools/apply-branding.sh` now applies it explicitly, which has
  not yet been checked on an ISO.
- CachyOS tools that look up packages by name (`chwd`, CachyOS Hello) may
  still ask for `linux-cachyos-*` once the kernel is renamed.
