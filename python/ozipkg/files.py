"""Ozi Files, the file manager: everything it does to files, without Qt.

Listing a folder, the places on the left (home folders, drives, trash),
copying and moving with progress, the freedesktop trash, archives (bsdtar),
drives (udisksctl), and which programs open a file.
"""
import configparser
import json
import mimetypes
import os
import re
import shutil
import subprocess
import time
import urllib.parse
from datetime import datetime

from . import shell
from .i18n import tr

# ---- what a file is --------------------------------------------------------

ARCHIVES = (".zip", ".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.zst", ".tzst", ".tar.bz2", ".tbz2",
            ".7z", ".rar", ".gz", ".xz", ".zst", ".bz2", ".iso", ".cpio", ".deb", ".rpm")
IMAGE_PREVIEW = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp", "image/svg+xml",
                 "image/x-icon", "image/tiff", "image/avif"}

mimetypes.add_type("text/markdown", ".md")
mimetypes.add_type("application/x-zstd-compressed-tar", ".tar.zst")
mimetypes.add_type("application/vnd.appimage", ".AppImage")
mimetypes.add_type("application/x-iso9660-image", ".iso")
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/avif", ".avif")


def mime_of(path, is_dir=False):
    if is_dir:
        return "inode/directory"
    name = os.path.basename(path).lower()
    if name.endswith(".pkg.tar.zst"):
        return "application/x-zstd-compressed-tar"
    guess, _ = mimetypes.guess_type(name, strict=False)
    if guess:
        return guess
    return "text/plain" if _looks_like_text(path) else "application/octet-stream"


def _looks_like_text(path):
    try:
        with open(path, "rb") as f:
            head = f.read(2048)
    except OSError:
        return False
    if not head:
        return True
    if b"\0" in head:
        return False
    try:
        head.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


GENERIC_ICONS = {"image": "image-x-generic", "video": "video-x-generic", "audio": "audio-x-generic",
                 "text": "text-x-generic", "font": "font-x-generic"}


def icon_for(mime):
    """Icon theme names for a type, the specific one first."""
    if mime == "inode/directory":
        return ["folder"]
    top = mime.split("/")[0]
    names = [mime.replace("/", "-")]
    if top in GENERIC_ICONS:
        names.append(GENERIC_ICONS[top])
    if is_archive_mime(mime):
        names.append("package-x-generic")
    if mime in ("application/x-executable", "application/x-sharedlib", "application/vnd.appimage"):
        names.append("application-x-executable")
    names.append("text-x-generic" if top == "text" else "unknown")
    return names


def is_archive_mime(mime):
    return any(k in mime for k in ("zip", "tar", "7z", "rar", "compressed", "x-xz", "gzip", "bzip", "zstd",
                                   "iso9660", "cpio", "debian-package", "x-rpm"))


def is_archive(path):
    low = path.lower()
    return any(low.endswith(ext) for ext in ARCHIVES)


def human_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return ("%d %s" % (n, unit)) if unit == "B" else ("%.1f %s" % (n, unit)).replace(".0 ", " ")
        n /= 1024.0
    return "%d B" % n


def _natural(name):
    return [int(p) if p.isdigit() else p.casefold() for p in re.split(r"(\d+)", name)]


def entry(path, st=None):
    """One file or folder, as the views show it."""
    try:
        st = st or os.stat(path)
    except OSError:
        st = os.lstat(path)
    is_dir = os.path.isdir(path)
    mime = mime_of(path, is_dir)
    return {
        "name": os.path.basename(path.rstrip("/")) or path,
        "path": path,
        "dir": is_dir,
        "link": os.path.islink(path),
        "hidden": os.path.basename(path).startswith("."),
        "size": 0 if is_dir else st.st_size,
        "sizeText": "" if is_dir else human_size(st.st_size),
        "modified": st.st_mtime,
        "mime": mime,
        "icons": icon_for(mime),
        "preview": mime in IMAGE_PREVIEW and st.st_size < 64 * 1024 * 1024,
        "archive": not is_dir and is_archive(path),
        "executable": not is_dir and os.access(path, os.X_OK),
    }


def listdir(path, hidden=False, sort="name", reverse=False):
    """A folder's contents: folders first, then files, in natural order."""
    path = os.path.abspath(os.path.expanduser(path))
    names = os.listdir(path)  # raises for a missing or forbidden folder: the view says so
    out = []
    for name in names:
        if not hidden and name.startswith("."):
            continue
        full = os.path.join(path, name)
        try:
            out.append(entry(full))
        except OSError:
            continue
    keys = {"name": lambda e: _natural(e["name"]), "size": lambda e: e["size"],
            "modified": lambda e: e["modified"], "type": lambda e: (e["mime"], _natural(e["name"]))}
    out.sort(key=keys.get(sort, keys["name"]), reverse=reverse)
    out.sort(key=lambda e: not e["dir"])
    return {"path": path, "entries": out, "writable": os.access(path, os.W_OK), "free": free_space(path)}


def free_space(path):
    try:
        usage = shutil.disk_usage(path)
        return {"free": usage.free, "total": usage.total, "text": human_size(usage.free)}
    except OSError:
        return {"free": 0, "total": 0, "text": ""}


def search(path, query, hidden=False, limit=500, deadline=8.0):
    """Files and folders under `path` whose name contains `query` (any case)."""
    query = query.casefold().strip()
    if not query:
        return []
    found, start = [], time.monotonic()
    for root, dirs, files in os.walk(path):
        if not hidden:
            dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in dirs + files:
            if (hidden or not name.startswith(".")) and query in name.casefold():
                try:
                    found.append(entry(os.path.join(root, name)))
                except OSError:
                    continue
                if len(found) >= limit:
                    return found
        if time.monotonic() - start > deadline:
            break
    return found


# ---- places ------------------------------------------------------------------

def user_dirs(environ=os.environ):
    """XDG user folders (Desktop, Documents...) as name -> path."""
    home = environ.get("HOME", os.path.expanduser("~"))
    config = environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    out = {}
    try:
        with open(os.path.join(config, "user-dirs.dirs"), encoding="utf-8") as f:
            for line in f:
                m = re.match(r'XDG_(\w+)_DIR="(.*)"', line.strip())
                if m:
                    out[m.group(1)] = m.group(2).replace("$HOME", home)
    except OSError:
        pass
    return out


def trash_dir(environ=os.environ):
    home = environ.get("HOME", os.path.expanduser("~"))
    data = environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return os.path.join(data, "Trash")


def places(environ=os.environ):
    home = environ.get("HOME", os.path.expanduser("~"))
    dirs = user_dirs(environ)
    out = [{"name": tr("Home"), "path": home, "icon": "user-home"}]
    for key, title, icon in (("DESKTOP", "Desktop", "user-desktop"), ("DOCUMENTS", "Documents", "folder-documents"),
                             ("DOWNLOAD", "Downloads", "folder-download"), ("PICTURES", "Pictures", "folder-pictures"),
                             ("MUSIC", "Music", "folder-music"), ("VIDEOS", "Videos", "folder-videos")):
        path = dirs.get(key)
        if path and os.path.isdir(path) and os.path.normpath(path) != os.path.normpath(home):
            out.append({"name": tr(title), "path": path, "icon": icon})
    out.append({"name": tr("Trash"), "path": "trash:", "icon": "user-trash-full" if trash_count(environ) else "user-trash"})
    out.append({"name": tr("Computer"), "path": "/", "icon": "drive-harddisk"})
    return out


def parse_lsblk(text):
    """Drives worth showing: partitions with a file system, on removable or hot-plugged disks,
    or mounted somewhere the user can see."""
    try:
        data = json.loads(text)
    except ValueError:
        return []
    out = []

    def walk(devs, removable=False):
        for d in devs or []:
            rm = removable or bool(d.get("rm")) or bool(d.get("hotplug"))
            mount = d.get("mountpoint") or ""
            fs = d.get("fstype") or ""
            if fs and fs not in ("swap", "crypto_LUKS", "LVM2_member") and d.get("type") in ("part", "disk", "rom"):
                shown = rm or mount.startswith(("/run/media/", "/media/", "/mnt/"))
                if shown:
                    label = d.get("label") or ("%s %s" % (d.get("size") or "", tr("drive"))).strip()
                    out.append({"name": label, "device": "/dev/" + d["name"], "mounted": bool(mount),
                                "path": mount, "icon": "drive-removable-media" if rm else "drive-harddisk",
                                "removable": rm, "size": d.get("size") or ""})
            walk(d.get("children"), rm)

    walk(data.get("blockdevices"))
    return out


def drives():
    try:
        out = subprocess.run(["lsblk", "-J", "-o", "NAME,LABEL,MOUNTPOINT,RM,HOTPLUG,SIZE,TYPE,FSTYPE"],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return parse_lsblk(out)


def mount(device):
    """Mount a drive through udisks (no password for the person at the computer); its folder."""
    out = subprocess.run(["udisksctl", "mount", "-b", device, "--no-user-interaction"],
                         capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise ValueError(out.stderr.strip() or tr("Could not open the drive"))
    m = re.search(r" at (.+?)\.?$", out.stdout.strip())
    return m.group(1) if m else ""


def unmount(device, power_off=True):
    out = subprocess.run(["udisksctl", "unmount", "-b", device], capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise ValueError(out.stderr.strip() or tr("The drive is in use"))
    if power_off:
        disk = re.sub(r"(p?\d+)$", "", device) if re.search(r"(sd[a-z]|mmcblk\d+p?)\d+$", device) else device
        subprocess.run(["udisksctl", "power-off", "-b", disk], capture_output=True, timeout=30)
    return True


# ---- making room for names ---------------------------------------------------------

def free_name(folder, name):
    """`name`, or "name (2).ext", "name (3).ext"... if it is taken in `folder`."""
    if not os.path.lexists(os.path.join(folder, name)):
        return name
    stem, ext = name, ""
    for e in sorted(ARCHIVES, key=len, reverse=True):
        if name.lower().endswith(e) and len(name) > len(e):
            stem, ext = name[: -len(e)], name[-len(e):]
            break
    else:
        stem, ext = os.path.splitext(name)
        if not stem:            # ".bashrc"
            stem, ext = name, ""
    m = re.match(r"^(.*) \((\d+)\)$", stem)
    base, n = (m.group(1), int(m.group(2))) if m else (stem, 1)
    while True:
        n += 1
        candidate = "%s (%d)%s" % (base, n, ext)
        if not os.path.lexists(os.path.join(folder, candidate)):
            return candidate


def check_name(name):
    name = name.strip()
    if not name or name in (".", "..") or "/" in name or "\0" in name:
        raise ValueError(tr("That name cannot be used."))
    return name


def rename(path, new_name):
    new_name = check_name(new_name)
    target = os.path.join(os.path.dirname(path), new_name)
    if os.path.lexists(target) and os.path.normcase(target) != os.path.normcase(path):
        raise ValueError(tr("Something with that name is already there."))
    os.rename(path, target)
    return target


def make_folder(folder, name):
    name = free_name(folder, check_name(name))
    path = os.path.join(folder, name)
    os.mkdir(path)
    return path


def make_file(folder, name):
    name = free_name(folder, check_name(name))
    path = os.path.join(folder, name)
    with open(path, "x"):
        pass
    return path


# ---- copy and move -------------------------------------------------------------

def _total_size(paths):
    total = 0
    for p in paths:
        if os.path.isdir(p) and not os.path.islink(p):
            for root, _, files in os.walk(p):
                for f in files:
                    try:
                        total += os.lstat(os.path.join(root, f)).st_size
                    except OSError:
                        pass
        else:
            try:
                total += os.lstat(p).st_size
            except OSError:
                pass
    return total


def transfer(paths, dest, move=False, log=None):
    """Copy (or move) files and folders into `dest`. Names that are taken get
    " (2)". `log` hears "progress <done> <total>" lines. Returns the new paths."""
    dest = os.path.abspath(dest)
    if not os.path.isdir(dest):
        raise ValueError(tr("The folder is not there any more."))
    for p in paths:
        p = os.path.abspath(p)
        if os.path.isdir(p) and (dest + "/").startswith(p.rstrip("/") + "/"):
            raise ValueError(tr("A folder cannot go inside itself."))
    total = max(1, _total_size(paths))
    done = [0]
    last = [0.0]

    def tick(n):
        done[0] += n
        now = time.monotonic()
        if log and now - last[0] > 0.1:
            last[0] = now
            log("progress %d %d" % (min(done[0], total), total))

    def copy_file(src, dst):
        if os.path.islink(src):
            os.symlink(os.readlink(src), dst)
            return
        with open(src, "rb") as fi, open(dst, "xb") as fo:
            while True:
                chunk = fi.read(1024 * 1024)
                if not chunk:
                    break
                fo.write(chunk)
                tick(len(chunk))
        shutil.copystat(src, dst, follow_symlinks=False)

    def copy_tree(src, dst):
        os.mkdir(dst)
        for name in os.listdir(src):
            s, d = os.path.join(src, name), os.path.join(dst, name)
            if os.path.isdir(s) and not os.path.islink(s):
                copy_tree(s, d)
            else:
                copy_file(s, d)
        shutil.copystat(src, dst, follow_symlinks=False)

    made = []
    for src in paths:
        src = os.path.abspath(src)
        name = os.path.basename(src.rstrip("/"))
        if move and os.path.dirname(src) == dest:
            made.append(src)          # moved onto itself: nothing to do
            continue
        target = os.path.join(dest, free_name(dest, name))
        if move:
            try:
                os.rename(src, target)          # same file system: instant
                tick(_total_size([target]))
                made.append(target)
                continue
            except OSError:
                pass
        if os.path.isdir(src) and not os.path.islink(src):
            copy_tree(src, target)
        else:
            copy_file(src, target)
        if move:
            if os.path.isdir(src) and not os.path.islink(src):
                shutil.rmtree(src)
            else:
                os.remove(src)
        made.append(target)
    if log:
        log("progress %d %d" % (total, total))
    return made


# ---- the trash (freedesktop.org Trash spec, the home trash) -------------------------------

def _trash_paths(environ):
    base = trash_dir(environ)
    files, info = os.path.join(base, "files"), os.path.join(base, "info")
    os.makedirs(files, exist_ok=True)
    os.makedirs(info, exist_ok=True)
    return files, info


def _same_device(a, b):
    try:
        return os.stat(a).st_dev == os.stat(b).st_dev
    except OSError:
        return False


def trash(paths, environ=os.environ):
    """Move to the trash. Files on another drive go to that drive's own trash
    through gio, so nothing is copied across."""
    files, info = _trash_paths(environ)
    moved = []
    for p in paths:
        p = os.path.abspath(p)
        if not _same_device(p, files):
            out = subprocess.run(["gio", "trash", p], capture_output=True, text=True, timeout=60)
            if out.returncode != 0:
                raise ValueError(out.stderr.strip() or tr("Could not move it to the trash."))
            moved.append(p)
            continue
        name = free_name(files, os.path.basename(p.rstrip("/")))
        while os.path.exists(os.path.join(info, name + ".trashinfo")):
            name = free_name(files, name + "_")
        with open(os.path.join(info, name + ".trashinfo"), "x", encoding="utf-8") as f:
            f.write("[Trash Info]\nPath=%s\nDeletionDate=%s\n" % (
                urllib.parse.quote(p), datetime.now().strftime("%Y-%m-%dT%H:%M:%S")))
        try:
            os.rename(p, os.path.join(files, name))
        except OSError:
            os.remove(os.path.join(info, name + ".trashinfo"))
            raise
        moved.append(p)
    return moved


def trash_list(environ=os.environ):
    files, info = _trash_paths(environ)
    out = []
    for name in os.listdir(files):
        full = os.path.join(files, name)
        original, deleted = "", 0.0
        parser = configparser.RawConfigParser(interpolation=None)
        try:
            parser.read(os.path.join(info, name + ".trashinfo"), encoding="utf-8")
            original = urllib.parse.unquote(parser.get("Trash Info", "Path", fallback=""))
            date = parser.get("Trash Info", "DeletionDate", fallback="")
            deleted = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S").timestamp() if date else 0.0
        except (configparser.Error, ValueError, OSError):
            pass
        try:
            e = entry(full)
        except OSError:
            continue
        e.update({"name": os.path.basename(original) or name, "original": original, "deleted": deleted,
                  "trashName": name})
        out.append(e)
    out.sort(key=lambda e: e["deleted"], reverse=True)
    return {"path": "trash:", "entries": out, "writable": False, "free": free_space(files)}


def trash_count(environ=os.environ):
    try:
        return len(os.listdir(os.path.join(trash_dir(environ), "files")))
    except OSError:
        return 0


def restore(trash_names, environ=os.environ):
    files, info = _trash_paths(environ)
    restored = []
    for name in trash_names:
        parser = configparser.RawConfigParser(interpolation=None)
        parser.read(os.path.join(info, name + ".trashinfo"), encoding="utf-8")
        original = urllib.parse.unquote(parser.get("Trash Info", "Path", fallback=""))
        if not original:
            raise ValueError(tr("Where it came from is not known."))
        folder = os.path.dirname(original)
        os.makedirs(folder, exist_ok=True)
        target = os.path.join(folder, free_name(folder, os.path.basename(original)))
        shutil.move(os.path.join(files, name), target)
        os.remove(os.path.join(info, name + ".trashinfo"))
        restored.append(target)
    return restored


def empty_trash(trash_names=None, environ=os.environ):
    """Delete for good: everything in the trash, or the named items."""
    files, info = _trash_paths(environ)
    names = trash_names if trash_names is not None else os.listdir(files)
    for name in names:
        full = os.path.join(files, name)
        if os.path.isdir(full) and not os.path.islink(full):
            shutil.rmtree(full, ignore_errors=True)
        elif os.path.lexists(full):
            os.remove(full)
        try:
            os.remove(os.path.join(info, name + ".trashinfo"))
        except OSError:
            pass
    return len(names)


def delete(paths):
    """Delete for good, without the trash."""
    for p in paths:
        if os.path.isdir(p) and not os.path.islink(p):
            shutil.rmtree(p)
        else:
            os.remove(p)
    return len(paths)


# ---- archives --------------------------------------------------------------------

def archive_stem(name):
    low = name.lower()
    for ext in sorted(ARCHIVES, key=len, reverse=True):
        if low.endswith(ext):
            return name[: -len(ext)] or name
    return os.path.splitext(name)[0] or name


def extract(path, log=None):
    """Unpack next to the archive, into a folder named after it."""
    folder = os.path.dirname(path)
    target = os.path.join(folder, free_name(folder, archive_stem(os.path.basename(path))))
    os.mkdir(target)
    out = subprocess.run(["bsdtar", "-xf", path, "-C", target], capture_output=True, text=True)
    if out.returncode != 0:
        shutil.rmtree(target, ignore_errors=True)
        raise ValueError(out.stderr.strip().splitlines()[-1] if out.stderr.strip() else tr("Could not unpack it."))
    # One folder inside? Use it instead of a folder in a folder.
    inner = os.listdir(target)
    if len(inner) == 1 and os.path.isdir(os.path.join(target, inner[0])):
        parked = os.path.join(folder, free_name(folder, ".ozi-unpack"))
        os.rename(os.path.join(target, inner[0]), parked)
        os.rmdir(target)            # its name is free again for the folder inside
        final = os.path.join(folder, free_name(folder, inner[0]))
        os.rename(parked, final)
        target = final
    return target


def compress(paths, log=None):
    """Pack into a .zip next to the first one."""
    folder = os.path.dirname(os.path.abspath(paths[0]))
    base = os.path.basename(paths[0].rstrip("/")) if len(paths) == 1 else tr("Archive")
    name = free_name(folder, archive_stem(base) + ".zip")
    target = os.path.join(folder, name)
    rel = [os.path.relpath(os.path.abspath(p), folder) for p in paths]
    out = subprocess.run(["bsdtar", "-a", "-cf", target, "-C", folder, "--", *rel], capture_output=True, text=True)
    if out.returncode != 0:
        raise ValueError(out.stderr.strip() or tr("Could not pack it."))
    return target


# ---- opening ----------------------------------------------------------------------

def _mime_apps(environ=os.environ):
    """mime type -> [desktop ids], from every program's MimeType= list."""
    table = {}
    for base in shell.data_dirs(environ):
        root = os.path.join(base, "applications")
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if not name.endswith(".desktop"):
                continue
            try:
                with open(os.path.join(root, name), encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            m = re.search(r"^MimeType=(.*)$", text, re.M)
            if not m or re.search(r"^NoDisplay=true", text, re.M | re.I):
                continue
            for mime in m.group(1).split(";"):
                if mime:
                    table.setdefault(mime, [])
                    if name[:-8] not in table[mime]:
                        table[mime].append(name[:-8])
    return table


def default_app(mime):
    try:
        out = subprocess.run(["xdg-mime", "query", "default", mime], capture_output=True, text=True, timeout=5)
        return out.stdout.strip().removesuffix(".desktop")
    except (OSError, subprocess.SubprocessError):
        return ""


def apps_for(path):
    """Programs that say they open this kind of file, the default first."""
    mime = mime_of(path, os.path.isdir(path))
    ids = list(_mime_apps().get(mime, []))
    top = mime.split("/")[0]
    if top == "text" or mime in ("application/json", "application/xml", "application/x-shellscript"):
        ids += [i for i in _mime_apps().get("text/plain", []) if i not in ids]
    by_id = {a["id"]: a for a in shell.applications()}
    first = default_app(mime)
    ids.sort(key=lambda i: i != first)
    return [{"id": i, "name": by_id[i]["name"], "icon": by_id[i]["icon"], "default": i == first}
            for i in ids if i in by_id]


def _spawn(argv, cwd=None):
    subprocess.Popen(argv, cwd=cwd, start_new_session=True, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def open_path(path):
    """Open with the default program."""
    if os.path.isdir(path):
        raise ValueError("a folder opens in Ozi Files itself")
    _spawn(["xdg-open", path], cwd=os.path.dirname(path))
    return True


def open_with(path, app_id, remember=False):
    """Open with one program; with `remember`, it becomes the default for this kind of file."""
    for app in shell.applications():
        if app["id"] == app_id:
            argv = command_with_file(app["exec"], path)
            if app["terminal"]:
                argv = shell.terminal_argv() + argv
            _spawn(argv, cwd=os.path.dirname(path))
            if remember:
                subprocess.run(["xdg-mime", "default", app_id + ".desktop", mime_of(path)], capture_output=True)
            return True
    raise ValueError(tr("That program is not installed."))


def command_with_file(exec_line, path):
    """Exec= with the file in its %f/%F/%u/%U place (at the end if there is none)."""
    import shlex
    try:
        argv = shlex.split(exec_line)
    except ValueError:
        argv = exec_line.split()
    url = "file://" + urllib.parse.quote(path)
    out, placed = [], False
    for a in argv:
        if a in ("%f", "%F"):
            out.append(path)
            placed = True
        elif a in ("%u", "%U"):
            out.append(url)
            placed = True
        elif re.fullmatch(r"%[dDnNickvm]", a):
            continue
        else:
            out.append(a.replace("%%", "%"))
    if not placed:
        out.append(path)
    return out


def terminal_here(folder):
    _spawn(shell.terminal_argv()[:1] + ["-d", folder], cwd=folder)
    return True


def properties(path):
    """Size (folders counted), dates, owner and permissions."""
    st = os.lstat(path)
    e = entry(path, os.stat(path) if os.path.exists(path) else st)
    count = 0
    size = e["size"]
    if e["dir"]:
        size = 0
        for root, dirs, files in os.walk(path):
            count += len(files) + len(dirs)
            for f in files:
                try:
                    size += os.lstat(os.path.join(root, f)).st_size
                except OSError:
                    pass
    import pwd
    try:
        owner = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        owner = str(st.st_uid)
    e.update({"totalSize": size, "totalText": human_size(size), "items": count, "owner": owner,
              "mode": oct(st.st_mode & 0o777)[2:], "accessed": st.st_atime,
              "target": os.readlink(path) if os.path.islink(path) else ""})
    return e


def set_executable(path, on):
    mode = os.stat(path).st_mode
    os.chmod(path, mode | 0o111 if on else mode & ~0o111)
    return True
