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
  the Arch Linux Archive snapshot the ISO was built from. While the archive does
  not answer, `archive-install.sh current` takes today's packages from the live
  system's mirrors, but only if nothing installed would change; the VM build
  uses it for its own tools (xorriso, cmake), and `iso/remaster.sh` installs the
  image's additions from what an earlier build of the same snapshot left in
  `/mnt/build/remaster/pkgcache`.
- On a live ISO the root file system is an overlay, which rootless Podman
  cannot use; `ozipkg.box.storage_driver()` falls back to `vfs` there.
- In a live session of the test VM (as root, with the checkout at `/mnt/ozios`):
  `tools/sync-live.sh` puts the checkout on top of the running image, so a change
  can be tried without building an ISO; `tools/check-image.sh [edu]` checks the
  booted image against what `iso/remaster.sh` promises; `tools/launch-installer.sh`
  starts the installer on an empty disk and `tools/drive-calamares.sh` (on the
  host) clicks through its pages.
- `tools/qml-shot.py <app> ...` runs an app's window offscreen, drives it with
  script steps and pointer events and saves pictures, so an interface can be looked
  at and exercised without a desktop. `tools/qml-check.py` only loads the window
  and reports every warning Qt printed.

### A test VM on a Windows host

VirtualBox on Windows works for all of the above. What was found setting it up:

- Give the VM two shared folders with auto-mount points: the checkout (or a
  worktree) as `ozios` at `/mnt/ozios`, and, read-only, the folder with the
  big files (`CachyOS.iso`, `.kernel-pkgs`) as `ozihost` at `/mnt/ozihost`.
  Attach only one ISO with the CachyOS volume id at boot: both the CachyOS ISO
  and ours carry `COS_202608`, and the live system mounts the root image of
  whichever it finds first (an OziOS kernel with CachyOS modules does not work).
- `VBoxManage guestcontrol <vm> run --username liveuser --password x` runs
  commands in the live session (its empty password takes anything); with
  `sudo -n` they run as root. In PowerShell 5 an empty `--password ""` is lost,
  so pass some text. Under Git Bash set `MSYS_NO_PATHCONV=1`.
- `VBoxManage controlvm <vm> screenshotpng` takes pictures; keys go in with
  `keyboardputscancode` (Meta is `e0 5b e0 db`). Pointer clicks need the COM
  API: `IConsole.Mouse.PutMouseEventAbsolute(x, y, 0, 0, buttons)` after
  `LockMachine` with a shared lock, from PowerShell through
  `New-Object -ComObject VirtualBox.VirtualBoxClient`.
- Files copied from a shared folder are `rwxrwx---`: copy them and fix the
  modes (`tools/sync-live.sh` does).
- With 3D acceleration off the VM draws in software (llvmpipe). KWin then
  switches every animation off unless `KWIN_EFFECTS_FORCE_ANIMATIONS=1` is set
  (OziOS sets it), and every moving frame of a full screen costs a processor
  core, which is what the light profile is for.
- Restarting `plasma-kwin_wayland.service` inside a session does not come back
  cleanly; log in again instead (restart `plasmalogin.service` in a live session).
- `tools/build-iso-in-vm.sh` converts from an OziOS live session too:
  `OZI_SOURCE_ISO=/mnt/ozihost/CachyOS.iso OZI_KERNEL_DIR=/mnt/ozihost/.kernel-pkgs`.

## State of things

Checked in a virtual machine (VirtualBox, UEFI) with the live ISO:

- The live ISO boots on `linux-ozios` and shows the OziOS desktop; Software and
  Welcome start without Qt warnings.
- `.deb` packages install into rootless podman boxes and run with their saved
  permissions; AppImages install and run in a bubblewrap sandbox. The helper
  runs through `pkexec`.
- A full installation through the Calamares windows, on an empty disk: the
  installer rewrite, the OziOS step (`install-to-target`), the OziOS kernel,
  Limine as boot loader and the first login all work. The installed system
  starts on `7.1.6-1-ozios` with no CachyOS kernel, shows the OziOS login
  screen and desktop, and the boot menu starts it by itself. `tools/launch-installer.sh`,
  `tools/drive-calamares.sh` and `tools/inspect-target.sh` repeat that test.

- The OziOS shell in a Plasma session (VirtualBox, drawn in software): the dock,
  the launcher with search and categories, the control widget switching themes,
  Alt+Tab with live pictures, the window motion (seen frame by frame with slowed
  animations), the shadows; plasmashell reported no QML errors for OziOS. With
  the light profile an idle desktop uses under one percent of a processor.

## Not done yet

- The shell has not been seen with a real graphics card, where the full profile
  (blur, wobble, the moving wallpaper) applies.
- The boot splash has not been seen on a real boot. If the screen stays black
  or shows text, `plymouth-set-default-theme -l` should list `ozios`, and
  `/etc/plymouth/plymouthd.conf` should name it.
- The installer fix for the driver step (`chwd`) is tested against stand-ins,
  not yet on a machine with an NVIDIA card.
- The live session has a polkit rule that allows everything without a password,
  so the password prompt of the helper has not been seen. It is the stock
  `auth_admin_keep` action.
- AUR builds have not been run against real podman and the real AUR.
- Installing next to another system (dual boot), BIOS mode, encrypted disks
  and ZFS (not offered) have not been tried.
- Nothing has been run on real hardware. A virtual machine does not show how
  a real graphics card, Wi-Fi chip or touch screen behaves.

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
  (`python/ozipkg/installer.py`). That includes code: the module that installs
  the base system adds the CachyOS kernels and, for GRUB, a CachyOS theme on its
  own, so the rewrite edits those lines out of the module.
- `ID=cachyos` in `os-release`, which those tools read to see that they are on
  a supported system. `NAME`, `PRETTY_NAME`, the links and the logo are ours.

Cutting these needs an installer and a package repository of our own; that is a
project of its own.

## The driver step of the installer

The installer runs `chwd --autoconfigure` in the new system right after the base
system (`chwd` step). It used to stop the whole installation on some NVIDIA
cards ("Failed to run chwd"): with the CachyOS kernels gone from the base system
there was no kernel yet, and the profile for older cards (GTX 900 and 1000
series, the 580xx driver) asks pacman for `<kernel>-headers`, which became
`-headers`. Now:

- `install-to-target kernel` runs right after the base system, before `chwd`. It
  keeps the OziOS packages on the new disk as a package source (`[ozios]` in
  `/etc/pacman.conf`, `file:///opt/ozios`) and installs `linux-ozios` and
  `linux-ozios-headers` by name, so `chwd` finds a kernel and can ask for its
  headers, now and later (`sudo chwd -a`).
- NVIDIA modules on an installed system come from DKMS (`chwd` falls back to it
  for kernels that are not CachyOS's), so they always match the driver that is
  installed and survive driver updates. The prebuilt `linux-ozios-nvidia-open`
  stays in the package source and on the live medium, where its version fits.
- If `chwd` still fails, the installation goes on with the generic driver; the
  failure and chwd's last lines are kept in `/var/lib/ozios/chwd-failed`, and
  `ozi doctor` shows them next to the driver that is not loaded.

## Known problems

- None recorded for the installer at the moment; see "Not done yet".
