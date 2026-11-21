# Installing OziOS

OziOS is early software. It has been installed and started in a virtual machine
(VirtualBox, UEFI); it has not been tried on real hardware yet. Keep a backup of
anything on the computer you care about.

## What you need

- A 64-bit computer that starts in UEFI mode. BIOS mode has not been tried.
- 4 GB of memory or more, and a disk of at least 25 GB for OziOS.
- A USB stick of 8 GB or more.
- An internet connection during the installation. The installer downloads the
  system while it works (about 2 GB), so a cable or a Wi-Fi network you can
  join from the live desktop is required. If the connection drops for a while
  during the download, the installer waits for it and carries on.

## 1. Put the ISO on a USB stick

Compare the checksum first; the `.sha256` file sits next to the ISO.

```
sha256sum -c ozios-<version>-<date>-x86_64.iso.sha256
```

Then one of:

- **Ventoy.** Copy the `.iso` file onto the Ventoy stick. Nothing else to do.
- **Windows.** Rufus, in "DD image" mode.
- **Linux.** `sudo dd if=ozios-....iso of=/dev/sdX bs=4M status=progress oflag=sync`,
  where `/dev/sdX` is the stick. Everything on the stick is erased.

## 2. Start from the stick

Restart the computer and open its boot menu (often F12, F9, Esc or F2 right
after power on). Choose the USB stick, in UEFI mode. The OziOS desktop appears
after a minute or two. Nothing on the computer has changed at this point: you
can look around, connect to the network, and switch off again.

## 3. Install

The Welcome window has an **Install** button. The installer asks, in order:

1. Language.
2. Where you are, for the clock.
3. Keyboard layout.
4. The disk. "Erase disk" gives the whole disk to OziOS and removes everything
   on it. To keep another system, choose the manual option and know what you
   are doing; installing next to Windows has not been tested.
5. Desktop: leave it on Plasma.
6. Extra packages: the defaults are fine.
7. Your name, a user name and a password.
8. A summary. Nothing is written to the disk until you press **Install** here
   and confirm.

The installation takes 30 to 60 minutes, most of it downloading. When it says
it is done, restart and remove the stick.

## 4. First start

Log in with the user you made. The Welcome window opens again; from there:

- **Games** installs Steam, game mode and the graphics libraries that fit the
  graphics card (`ozi gaming` in a terminal does the same and shows the list
  first).
- **Get software** installs programs and checks packages before they go on.
- `ozi doctor` in a terminal checks the installation and says how to fix what
  it finds; `ozi update` updates the system and takes a snapshot first.

## If something goes wrong

- The installer stops with an error: note the text, then start it again from the
  Welcome window. A run that failed can be repeated.
- The computer does not start from the disk afterwards: start from the stick
  again, open a terminal and run `ozi report`. It writes a text file, with
  names and addresses removed, to attach to an issue at
  <https://github.com/OziiDev/OziOS/issues>.

Turkish: [KURULUM.md](KURULUM.md)
