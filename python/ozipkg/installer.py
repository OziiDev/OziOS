"""What OziOS changes in the Calamares installer it inherits from CachyOS.

Every function takes the text of one configuration file and returns the new
text, so the rules can be tested without an installer. They are safe to run
more than once. `apply` walks the files of a live system and rewrites them.

The installer installs software over the network from lists that name CachyOS
kernels, CachyOS programs and CachyOS artwork. Here those are replaced: the
target system gets the OziOS kernel (put in early, so the initramfs and boot
loader steps see it like any other kernel), the OziOS look, and none of the
CachyOS kernels or programs. The CachyOS repositories, keyring and mirror lists
stay, because the rest of the installer is built on them.
"""
import glob
import os
import re

STEP = "shellprocess@ozios"
EARLY = "shellprocess@ozios_early"
THEME = "/usr/share/grub/themes/ozios/theme.txt"
SPLASH = "/usr/share/ozios/branding/limine-splash.png"

LATE_CONF = """\
# Added by ozios-settings.
dontChroot: true
timeout: 600
script:
    - "/usr/lib/ozios/install-to-target late"
"""
EARLY_CONF = """\
# Added by ozios-settings.
dontChroot: true
timeout: 1800
script:
    - "/usr/lib/ozios/install-to-target early"
"""

# Packages the installer must not put on a new system.
UNWANTED = re.compile(
    r"^\s*-\s+(linux-cachyos[\w.+-]*|cachyos-kernel-manager|cachyos-hello|cachyos-packageinstaller|"
    r"cachyos-wallpapers|cachy-update|cachyos-iridescent-kde|cachyos-emerald-kde-theme-git|"
    r"cachyos-nord-kde-theme-git|cachyos-cli-installer[\w.+-]*)\s*$")


def _instance(lines, name, module, config):
    """Add an instance of a module to the `instances:` list."""
    entry = ["- id: " + name, "  module: " + module, "  config: " + config]
    for i, line in enumerate(lines):
        if re.match(r"^instances:\s*$", line):
            indent = ""
            for following in lines[i + 1:]:
                m = re.match(r"^(\s*)-\s", following)
                if m:
                    indent = m.group(1)
                    break
                if following.strip() and not following.lstrip().startswith("#"):
                    break
            lines[i + 1:i + 1] = [indent + part for part in entry]
            return
    lines += ["", "instances:"] + entry


def patch_settings(text):
    """Own branding, an early step for the kernel, a late step for the finish."""
    lines = text.split("\n")
    changed = False

    if STEP not in text:
        for i, line in enumerate(lines):
            m = re.match(r"^(\s*)-\s+umount\s*$", line)
            if m:
                lines.insert(i, "%s- %s" % (m.group(1), STEP))
                _instance(lines, "ozios", "shellprocess", "shellprocess_ozios.conf")
                changed = True
                break
    if EARLY not in text:
        # Right after the extra packages: the kernel then exists before the
        # initramfs and boot loader steps look for kernels.
        for i, line in enumerate(lines):
            m = re.match(r"^(\s*)-\s+packages@online\s*$", line)
            if m:
                lines.insert(i + 1, "%s- %s" % (m.group(1), EARLY))
                _instance(lines, "ozios_early", "shellprocess", "shellprocess_ozios_early.conf")
                changed = True
                break

    out = []
    for line in lines:
        if re.match(r"^\s*-\s+plymouthcfg\s*$", line):      # no CachyOS boot animation is installed
            changed = True
            continue
        if re.match(r"^branding:\s*cachyos\s*$", line):
            line = "branding: ozios"
            changed = True
        out.append(line)
    return "\n".join(out) if changed else text


def patch_netinstall_conf(text):
    """Use only the local package list, not the one the CachyOS project publishes."""
    return "\n".join(line for line in text.split("\n") if not re.match(r"^\s*-\s+https?://", line))


def patch_netinstall_yaml(text):
    """Drop the CachyOS kernels, programs and artwork from the package groups."""
    groups, current = [], []
    for line in text.split("\n"):
        if line.startswith("- name:") and current:
            groups.append(current)
            current = []
        current.append(line)
    if current:
        groups.append(current)

    kept = []
    for group in groups:
        if re.match(r'^- name:\s*"?CachyOS kernels', group[0]):
            continue
        out = []
        for line in group:
            if UNWANTED.match(line):
                continue
            out.append(line)
        head = out[0]
        out[0] = head.replace('"CachyOS Packages"', '"System packages"').replace('"CachyOS shell configuration"', '"Shell configuration"')
        kept.append("\n".join(out))
    return "\n".join(kept)


def patch_pacstrap(text):
    return "\n".join(line for line in text.split("\n")
                     if not re.match(r"^\s*-\s+cachyos-plymouth-(bootanimation|theme)\s*$", line))


def patch_grubcfg(text):
    text = re.sub(r'(GRUB_THEME:\s*)"[^"]*"', r'\1"%s"' % THEME, text)
    text = re.sub(r'(GRUB_TOP_LEVEL:\s*)"[^"]*"', r'\1"/boot/vmlinuz-linux-ozios"', text)
    return text


def patch_bootloader(text):
    text = re.sub(r'(efiBootloaderId:\s*)"cachyos"', r'\1"ozios"', text)
    text = re.sub(r'(limineSplashLogo:\s*)"[^"]*"', r'\1"%s"' % SPLASH, text)
    if "linux-ozios" not in text:
        text = re.sub(r'(refindKernelList:\s*\[\s*)', r'\1"linux-ozios",', text)
    return text


def patch_users(text):
    return text.replace('template: "cachyos-${cpu}"', 'template: "ozios-${cpu}"')


def patch_names(text):
    """Text shown while installing: lines that start with `name`."""
    return "\n".join(re.sub("CachyOS", "OziOS", line) if re.match(r"^\s*name(\[\w+\])?:", line) else line
                     for line in text.split("\n"))


def patch_script(text):
    return (text.replace('TARGET_OS_NAME="CachyOS"', 'TARGET_OS_NAME="OziOS"')
                .replace("Fresh CachyOS Installation", "Fresh OziOS Installation"))


MODULES = {
    "netinstall.conf": patch_netinstall_conf,
    "netinstall.yaml": patch_netinstall_yaml,
    "pacstrap.conf": patch_pacstrap,
    "grubcfg.conf": patch_grubcfg,
    "bootloader.conf": patch_bootloader,
    "users.conf": patch_users,
    "shellprocess-before.conf": patch_names,
    "shellprocess-before-online.conf": patch_names,
}


def _rewrite(path, func):
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeError):
        return False
    new = func(text)
    if new == text:
        return False
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    return True


def apply(bases=("/etc/calamares", "/usr/share/calamares"), etc="/etc/calamares"):
    """Rewrite the installer configuration found under `bases`. Returns the changed paths."""
    changed = []
    for base in bases:
        for path in sorted(glob.glob(os.path.join(base, "settings*.conf"))):
            if _rewrite(path, patch_settings):
                changed.append(path)
        for name, func in MODULES.items():
            path = os.path.join(base, "modules", name)
            if os.path.isfile(path) and _rewrite(path, func):
                changed.append(path)
        for path in sorted(glob.glob(os.path.join(base, "scripts", "*"))):
            if os.path.isfile(path) and _rewrite(path, patch_script):
                changed.append(path)
    if changed:
        modules = os.path.join(etc, "modules")
        os.makedirs(modules, exist_ok=True)
        for name, text in (("shellprocess_ozios.conf", LATE_CONF), ("shellprocess_ozios_early.conf", EARLY_CONF)):
            with open(os.path.join(modules, name), "w", encoding="utf-8") as fh:
                fh.write(text)
    return changed
