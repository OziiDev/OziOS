# OziOS Education

A separate ISO for smart boards and classroom computers. It is the same system
as OziOS with a school desktop on top. It is not Pardus ETAP and makes no claim
to be accepted as it; it gives the same kind of day-to-day experience on a board.

## What is different

- **The OziOS desktop, set up for a board.** The screen pen, whiteboard,
  presentation program, classroom, browser, EBA, file manager, calculator and
  store are pinned to the dock (`/usr/share/ozios/desktop-defaults.json`; the
  user's own `desktop.json` wins over it). No KDE programs.
- **Touch.** oziwm sends a finger to the program under it as a real touch when
  the program takes touches (scrolling and pinching in Firefox, Qt and GTK) and
  works as the mouse elsewhere: a title bar drags, the frame buttons press.
  Pens that report as tablet tools are the mouse; the pen's button is the
  right button.
- **Screen pen** (`ozi-pen`). Draws on top of anything on the screen: pen,
  marker, line, arrow, box and circle, an eraser that takes away a whole
  stroke, a laser pointer with a fading trail and a spotlight that dims
  everything but a round window around the pointer. Six colours, three sizes,
  undo and clear. *Save* writes the drawing, without the screen under it, as a
  PNG in `Pictures/ozi-pen`. *Use screen* lets touches and clicks pass through
  to the programs below while the drawing stays visible; *Draw* takes them
  back. The toolbar can be moved by dragging it. Ctrl+Z undoes, Delete clears
  and Esc switches between drawing and using the screen.
- **Classroom** (`ozi-classroom`). Class lists kept per user, one name per line
  (`~/.local/state/ozios/classes`). *Pick* chooses a student at random and
  gives everybody a turn before anybody gets a second one; *New round* starts
  over. *Groups* shuffles the class into a number of groups whose sizes differ
  by at most one. *Timer* counts down from 1 to 180 minutes and makes a sound
  at the end; the Space key starts and stops it, or picks a student.
- **Whiteboard.** Xournal++ for a page to write on, with pages, images and PDF
  markup. Firefox reads PDFs.
- **Office.** LibreOffice with the Turkish interface.
- **Turkish by default.** Turkish interface language, Turkish Q keyboard and the
  Istanbul time zone in the live session. The installer asks as usual; the
  choices made there win on an installed system.
- **On-screen keyboard.** OziOS's own: it comes up when a finger touches a
  text field (text-input-v3) and from the bar's keyboard button, pushes the
  windows up while open, and takes its keys from the keyboard layout in use.
- **No lock, no sleep.** The screen lock is off and logind ignores idle, sleep
  and lid events, so a board does not go dark in the middle of a lesson.
- **Larger pointer.** A 36 px cursor.
- **Links.** EBA, e-Okul and MEB in the menu.

## Board Bridge, modes, freezing, the tour

- **Tahta Köprüsü** (`ozi-bridge`, `python/ozipkg/bridge.py`): a web server on
  the board while its window is open, two QR codes (made with `qrencode`). The
  teacher's pages (`/k/<random key>/`) are a phone remote: keys through oziwm
  IPC (`press`: Page Up/Down, F5, Esc, B), a touchpad (`pointer`), a live view
  (`screenshot`, shrunk to JPEG) and "share this board", which saves a
  screenshot in `Documents/Ders Notları`. The students' page (`/`) lists
  today's PNG/JPEG/PDF from that folder and `Pictures/ozi-pen`, and makes one
  PDF of them (QPdfWriter). Only listed names are served. `nmcli device wifi
  hotspot` makes the board an access point. `ozi-bridge-firewall.service`
  opens ports 8765-8784 in ufw to private addresses only.
- **Kısıtlı / Yetkili** (`python/ozipkg/mode.py`, `edu/mode/`): the mode is in
  `/run/ozios/mode`, so a board always starts restricted. oziwm
  (`src/policy.rs`), ozi-shell (launcher, dock, search) and Ozi Terminal
  refuse the programs in `BLOCKED_PROGRAMS`; `50-ozios-kisitli.rules` makes
  polkit refuse admin actions (`DENIED_ACTIONS`) unless `ozi-mode-allowed`
  says the board is authorised. `ozi-mode-helper` (root, through pkexec with
  the `org.ozios.mode` action, no polkit password) checks the teacher password
  (PBKDF2 in `/etc/ozios/ogretmen.sifre`, default `ogretmen`) and makes a
  guesser wait 30 s after five wrong tries.
- **Dondurma**: the home folder is copied with rsync to
  `/var/lib/ozios/dondurma/<user>`; `ozi-freeze.service` copies it back at
  every start before the login screen, keeping `Belgeler/Ders Notları`,
  `Resimler/ozi-pen` and `.cache`.
- **OziOS turu** (`ozi-tour`, `python/ozipkg/tour.py`): a layer-shell bar
  along the bottom where Ozi-chan presents each part while the program opens
  above her; programs a scene opened are closed when it ends. With
  `/usr/share/ozios/tanitim` (the `--tanitim` ISO) ozi-shell starts it with
  `--loop`.

## Building the ISO

Same as the ordinary image, with `--edition edu`:

```
sudo iso/remaster.sh --edition edu --kernel <kernel packages> \
     --archive 2026/08/09 --add "python-pyqt6 podman bubblewrap pacman-contrib ttf-overpass"
```

The result is `ozios-edu-<version>-<date>-x86_64.iso`. LibreOffice makes the image
about 1 GB larger. On the installed system the Education package is put in by
the installer's OziOS step, which pulls the school programs from the repositories.

## What it does not do

- It has no management of many boards at once (central updates, remote lock,
  classroom accounts). Each board is its own computer.
- Touch and the on-screen keyboard were tested with simulated touches in a
  nested desktop, not on a board yet. Boards that present themselves as an
  ordinary USB touch screen work; ones that need a vendor driver need that
  driver. With more than one screen, touch maps to the first.
- The screen pen draws with the first pointer only; two fingers do not draw two
  lines at once.
