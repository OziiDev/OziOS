"""Bozulmayan güncelleme (an update that cannot break the system).

A rolling system's worst moment is the reboot after an update that went
wrong: a kernel without its modules, a desktop that no longer links, a
Python that lost its Qt. Here the update is checked before anyone reboots:

1. a snapper snapshot ("pre") is taken and the boot files are copied aside
   (/boot is not in the snapshot: it is its own partition);
2. pacman updates;
3. the result is checked: every installed kernel has its image, initramfs and
   modules, every boot menu entry points at a file that exists, the desktop's
   programs find all their libraries, Python still loads Qt and OziOS;
4. if something is broken, the system goes back to the snapshot
   (`snapper undochange`) and the boot files are put back, before any reboot.

Run as root (ozi-safe-update). Without snapper (not btrfs) it still checks,
and says what is wrong, but cannot go back.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import time

BACKUP = "/var/lib/ozios/boot-yedek"
DESKTOP_PROGRAMS = ("/usr/bin/oziwm", "/usr/bin/ozi-terminal")
PYTHON_CHECK = ("import sys; sys.path.insert(0, '/usr/lib/ozios/python'); "
                "import PyQt6.QtCore, PyQt6.QtQml, PyQt6.QtQuick; import ozipkg.shell")


# ---- what is checked -------------------------------------------------------

def kernels(root="/"):
    """Installed kernels: {name, version, image} from /usr/lib/modules/*/pkgbase."""
    found = []
    for base in sorted(glob.glob(os.path.join(root, "usr/lib/modules/*/pkgbase"))):
        version = os.path.basename(os.path.dirname(base))
        with open(base) as f:
            name = f.read().strip()
        found.append({"name": name, "version": version, "modules": os.path.dirname(base)})
    return found


def boot_paths(root="/"):
    """Files the boot menu (Limine) loads, as paths under /boot."""
    paths = []
    for conf in ("boot/limine.conf", "boot/limine/limine.conf", "boot/EFI/limine/limine.conf"):
        try:
            with open(os.path.join(root, conf)) as f:
                text = f.read()
        except OSError:
            continue
        for m in re.finditer(r"^\s*(?:kernel_path|module_path|path)\s*:\s*boot\(\):/(\S+)", text, re.M):
            path = m.group(1).split("#")[0]      # "#<hash>": the file's checksum, not part of its name
            # Snapshot entries keep their own copies (limine-snapper-sync); they are not ours to check.
            if "limine_history/" not in path and path not in paths:
                paths.append(path)
    return paths


def missing_libraries(program, run=subprocess.run):
    try:
        out = run(["ldd", program], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.split()[0] for line in out.splitlines() if "not found" in line]


def health(root="/", run=subprocess.run):
    """What would stop the next start, as sentences; empty when all is well."""
    problems = []
    found = kernels(root)
    if not found:
        problems.append("Hiç çekirdek kurulu değil.")
    for k in found:
        boot = os.path.join(root, "boot")
        if not os.path.exists(os.path.join(boot, "vmlinuz-" + k["name"])):
            problems.append("%s çekirdeğinin dosyası /boot'ta yok." % k["name"])
        if not os.path.exists(os.path.join(boot, "initramfs-%s.img" % k["name"])):
            problems.append("%s çekirdeğinin initramfs dosyası yok." % k["name"])
        if not os.path.isdir(os.path.join(k["modules"], "kernel")):
            problems.append("%s %s çekirdeğinin modülleri eksik." % (k["name"], k["version"]))
    for path in boot_paths(root):
        if not os.path.exists(os.path.join(root, "boot", path)):
            problems.append("Açılış menüsü olmayan bir dosyayı gösteriyor: /boot/%s" % path)
    for program in DESKTOP_PROGRAMS:
        full = os.path.join(root, program.lstrip("/"))
        if os.path.exists(full):
            libs = missing_libraries(full, run)
            if libs:
                problems.append("%s şu kütüphaneleri bulamıyor: %s" % (os.path.basename(program), ", ".join(libs)))
    if root == "/" and shutil.which("python3"):
        out = run(["python3", "-c", PYTHON_CHECK], capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            last = (out.stderr.strip().splitlines() or ["?"])[-1]
            problems.append("Masaüstü Python'u yüklenemiyor: %s" % last)
    return problems


# ---- the boot partition ------------------------------------------------------

def save_boot(root="/", backup=BACKUP):
    """Copy what the boot menu needs aside: kernels, initramfs, the menu itself."""
    target = os.path.join(root, backup.lstrip("/"))
    shutil.rmtree(target, ignore_errors=True)
    os.makedirs(target, mode=0o700)
    boot = os.path.join(root, "boot")
    names = set(boot_paths(root))
    names.update(os.path.relpath(p, boot) for p in glob.glob(os.path.join(boot, "vmlinuz-*")))
    names.update(os.path.relpath(p, boot) for p in glob.glob(os.path.join(boot, "initramfs-*.img")))
    names.update(c for c in ("limine.conf", "limine/limine.conf", "EFI/limine/limine.conf")
                 if os.path.exists(os.path.join(boot, c)))
    saved = []
    for name in sorted(names):
        source = os.path.join(boot, name)
        if os.path.isfile(source):
            os.makedirs(os.path.dirname(os.path.join(target, name)), exist_ok=True)
            shutil.copy2(source, os.path.join(target, name))
            saved.append(name)
    with open(os.path.join(target, "list.json"), "w") as f:
        json.dump(saved, f)
    return saved


def restore_boot(root="/", backup=BACKUP):
    """Put the saved boot files back; kernels the update added are taken away."""
    target = os.path.join(root, backup.lstrip("/"))
    with open(os.path.join(target, "list.json")) as f:
        saved = json.load(f)
    boot = os.path.join(root, "boot")
    for path in glob.glob(os.path.join(boot, "vmlinuz-*")) + glob.glob(os.path.join(boot, "initramfs-*.img")):
        if os.path.relpath(path, boot) not in saved:
            os.remove(path)
    for name in saved:
        os.makedirs(os.path.dirname(os.path.join(boot, name)), exist_ok=True)
        shutil.copy2(os.path.join(target, name), os.path.join(boot, name))
    return saved


# ---- the update ------------------------------------------------------------------

def snapper_ok(run=subprocess.run):
    if not shutil.which("snapper"):
        return False
    return run(["snapper", "-c", "root", "list"], capture_output=True, text=True).returncode == 0


def update(pacman_args=("-Syu", "--noconfirm"), run=subprocess.run, log=print, root="/", stream=None):
    """The whole safe update. Returns {"ok", "updated", "undone", "problems"}."""
    stream = stream or (lambda argv: run(argv).returncode)
    before = health(root, run)
    if before:
        log("Güncellemeden önce de sorun var (güncelleme bunları düzeltebilir):")
        for p in before:
            log("  - " + p)
    can_undo = snapper_ok(run)
    pre = None
    if can_undo:
        out = run(["snapper", "-c", "root", "create", "--type", "pre", "--print-number", "--cleanup-algorithm", "number",
                   "--description", "ozi güvenli güncelleme"], capture_output=True, text=True)
        pre = out.stdout.strip() if out.returncode == 0 else None
        if pre:
            save_boot(root)
            log("Anlık kopya alındı (#%s); bir şey bozulursa sistem buna döner." % pre)
        else:
            can_undo = False
    if not can_undo:
        log("Anlık kopya alınamıyor (btrfs/snapper yok): güncelleme kontrol edilecek ama geri alınamaz.")

    code = stream(["pacman", *pacman_args])
    post = None
    if pre:
        out = run(["snapper", "-c", "root", "create", "--type", "post", "--pre-number", pre, "--print-number",
                   "--cleanup-algorithm", "number", "--description", "ozi güvenli güncelleme"],
                  capture_output=True, text=True)
        post = out.stdout.strip() if out.returncode == 0 else None

    log("Güncelleme kontrol ediliyor…")
    problems = [p for p in health(root, run) if p not in before]
    if not problems:
        log("Her şey yerinde: yeniden başlatmak güvenli." if code == 0 else "pacman hata verdi ama sistem açılır durumda.")
        return {"ok": code == 0, "updated": code == 0, "undone": False, "problems": []}

    log("Güncelleme sistemi bozmuş olabilir:")
    for p in problems:
        log("  - " + p)
    if not (pre and post):
        log("Geri alınamıyor. Yeniden başlatmadan önce bu sorunları düzelt.")
        return {"ok": False, "updated": code == 0, "undone": False, "problems": problems}
    log("Güncellemeden önceki hâline dönülüyor (#%s)…" % pre)
    undo = run(["snapper", "-c", "root", "undochange", "%s..%s" % (pre, post)], capture_output=True, text=True)
    restore_boot(root)
    after = [p for p in health(root, run) if p not in before]
    if undo.returncode == 0 and not after:
        log("Geri alındı: sistem güncellemeden önceki gibi. Biraz sonra yeniden dene; sorun sürerse bildir.")
        return {"ok": False, "updated": False, "undone": True, "problems": problems}
    log("Geri alma tam olmadı. Açılış menüsünde 'Snapshots' altından #%s anlık kopyasını seçerek açabilirsin." % pre)
    return {"ok": False, "updated": False, "undone": False, "problems": after or problems}


def main(argv):
    if os.geteuid() != 0:
        print("ozi-safe-update: yönetici olarak çalışmalı (sudo)")
        return 1
    args = [a for a in argv if a != "--noconfirm"]
    pacman_args = ["-Syu", *(["--noconfirm"] if "--noconfirm" in argv else []), *args]
    started = time.time()
    result = update(pacman_args, log=lambda line: print(line, flush=True))
    if os.environ.get("OZI_SAFE_UPDATE_JSON"):
        print(json.dumps(dict(result, seconds=round(time.time() - started))))
    return 0 if result["ok"] else (2 if result["undone"] else 1)
