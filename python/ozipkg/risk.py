"""Risk rules: what in a package deserves a person's attention.

This is a check for known bad patterns, not a guarantee. A package that
passes can still be harmful; a package that is flagged is often fine. The
review screen says so plainly.

Each rule has a `kind`:
  system     changes the state of the computer (services, logins, sources...)
  behaviour  looks like malware or sabotage whatever the install target is

For software that is installed inside its own box, `system` findings are
lowered to a notice because they stay in the box; `behaviour` findings keep
their weight.
"""
import re
from dataclasses import dataclass, field

from .i18n import tr

SEVERITIES = ("info", "notice", "warning", "danger")
RANK = {name: n for n, name in enumerate(SEVERITIES)}


@dataclass
class Finding:
    rule: str
    severity: str
    title: str
    detail: str = ""
    evidence: str = ""
    where: str = ""
    kind: str = "system"

    def as_dict(self):
        return {"rule": self.rule, "severity": self.severity, "title": self.title,
                "detail": self.detail, "evidence": self.evidence, "where": self.where, "kind": self.kind}


@dataclass(frozen=True)
class ScriptRule:
    id: str
    severity: str
    kind: str
    pattern: "re.Pattern"
    title: str
    detail: str


def _rule(id, severity, kind, pattern, title, detail):
    return ScriptRule(id, severity, kind, re.compile(pattern), title, detail)


SCRIPT_RULES = [
    _rule("pipe-to-shell", "danger", "behaviour",
          r"\b(curl|wget|fetch)\b[^\n|;]*\|\s*(sudo\s+)?(ba|z|da|k)?sh\b",
          "Downloads code and runs it right away",
          "The script fetches something from the internet and runs it without anyone being able to look at it first."),
    _rule("decode-and-run", "danger", "behaviour",
          r"(base64\s+(-d|--decode)|xxd\s+-r|openssl\s+enc\s+-d)[^\n]*\|\s*(sudo\s+)?(ba|z|da)?sh\b"
          r"|\beval\b[^\n]*\b(base64|xxd)\b",
          "Hides code and runs it",
          "The script decodes text into commands and runs them. Honest installers have no reason to hide what they run."),
    _rule("reverse-shell", "danger", "behaviour",
          r"/dev/(tcp|udp)/|\bnc(at)?\b[^\n]*\s-e\b|\bbash\s+-i\s*>&|\bsocat\b[^\n]*\bexec:",
          "Opens a remote control channel",
          "This pattern is used to give someone else a command line on this computer."),
    _rule("wipe-files", "danger", "behaviour",
          r"\brm\s+(-[a-zA-Z]+\s+)*(--no-preserve-root\s+)?(-[a-zA-Z]*[rR][a-zA-Z]*\s+)?(--no-preserve-root\s+)?(/|/\*|~|~/\*|\$HOME|\$\{HOME\})(\s|$|;)",
          "Deletes everything in an important folder",
          "The script removes the whole system or your whole home folder."),
    _rule("miner", "danger", "behaviour",
          r"\bxmrig\b|stratum\+tcp|\bminerd\b|\bcpuminer\b",
          "Contains cryptocurrency mining code",
          "Mining software uses your computer's power to earn money for someone else."),
    _rule("ssh-keys", "danger", "behaviour",
          r"authorized_keys|\.ssh/id_[a-z0-9]+",
          "Touches SSH keys",
          "The script reads or writes SSH keys, which give access to other computers or let others in."),
    _rule("edit-auth", "danger", "system",
          r"(>>?|\btee\s+(-a\s+)?|\bsed\s+-i[^\n]*)\s*/etc/(sudoers|shadow|passwd|gshadow|pam\.d|ld\.so\.preload|ssh/sshd_config)",
          "Changes how logins and administrator rights work",
          "The script edits files that decide who can log in or run commands as administrator."),
    _rule("ld-preload", "danger", "system",
          r"ld\.so\.preload",
          "Injects a library into every program",
          "A library listed there is loaded by every program on the system."),
    _rule("add-user", "warning", "system",
          r"\b(useradd|adduser|usermod\s+[^\n]*-a?G\s*\S*(sudo|wheel|root))\b",
          "Creates a user or gives one more rights",
          "The script adds an account or puts one in the administrator group."),
    _rule("setuid", "warning", "system",
          r"\bchmod\s+([0-7]?[2467][0-7]{3}\b|[ugoa]*\+s\b)",
          "Makes a program run with someone else's rights",
          "A program marked this way runs with the rights of its owner, often the administrator."),
    _rule("apt-source", "warning", "system",
          r"/etc/apt/(sources\.list|trusted\.gpg|keyrings)|\bapt-key\s+add\b|\badd-apt-repository\b",
          "Adds a software source",
          "From now on the system would also take updates from a source the app's maker chose."),
    _rule("cron", "warning", "system",
          r"\bcrontab\b|/etc/cron|/var/spool/cron",
          "Schedules something to run by itself",
          "The script sets up a repeating task."),
    _rule("shell-profile", "warning", "system",
          r"(\.bashrc|\.zshrc|\.bash_profile|\.zprofile|/etc/profile(\.d)?\b|\.config/fish/)",
          "Changes what runs when a terminal opens",
          "The script edits shell start-up files."),
    _rule("kernel-module", "warning", "system",
          r"\b(insmod|modprobe|dkms)\b",
          "Loads or builds a kernel module",
          "Kernel modules run with full rights and can see everything."),
    _rule("downloads-while-installing", "warning", "system",
          r"\b(curl|wget)\s+[^\n]*(https?|ftp)://",
          "Downloads files while installing",
          "What gets installed is not fully contained in the package you looked at."),
    _rule("service", "notice", "system",
          r"\b(systemctl\s+(--now\s+)?(enable|start|preset)|deb-systemd-helper\s+enable|update-rc\.d)\b",
          "Starts a background service",
          "Something will keep running in the background, possibly from boot."),
    _rule("firewall", "notice", "system",
          r"\b(iptables|ip6tables|nft|ufw|firewall-cmd)\b",
          "Changes firewall rules",
          "Network traffic rules on this computer would change."),
]

# Installed paths. Each entry: id, severity, regex on the path (no leading slash).
PATH_RULES = [
    ("sudoers", "danger", r"^etc/sudoers(\.d/.*)?$", "Changes who may run commands as administrator"),
    ("pam", "danger", r"^(etc/pam\.d/.*|usr/lib/security/.*\.so)$", "Changes how logins and passwords are checked"),
    ("ld-preload", "danger", r"^etc/ld\.so\.preload$", "Injects a library into every program"),
    ("exec-in-tmp", "danger", r"^(tmp|dev/shm|var/tmp)/.+", "Puts files in a temporary folder"),
    ("sshd", "warning", r"^etc/ssh/.*", "Changes the remote login settings"),
    ("profile-d", "warning", r"^etc/profile(\.d/.*)?$", "Runs a script in every login shell"),
    ("cron", "warning", r"^(etc/cron.*|var/spool/cron/.*)$", "Schedules something to run by itself"),
    ("udev", "warning", r"^(etc|usr/lib)/udev/rules\.d/.*", "Reacts when devices are plugged in"),
    ("polkit-rules", "warning", r"^(etc|usr/share)/polkit-1/rules\.d/.*", "Grants permissions without asking for a password"),
    ("dbus-system", "warning", r"^(usr/share/dbus-1/system-services/.*|etc/dbus-1/system\.d/.*|usr/share/dbus-1/system\.d/.*)$",
     "Adds a service on the system message bus"),
    ("kernel", "warning", r"^(usr/lib/modules/.*|boot/.*|usr/src/.*\.ko)$", "Adds kernel files or boot files"),
    ("systemd-system", "notice", r"^(usr/lib|etc|lib)/systemd/system/.*\.(service|timer|socket|path)$", "Adds a background service"),
    ("systemd-user", "notice", r"^(usr/lib|etc)/systemd/user/.*\.(service|timer|socket|path)$", "Adds a background service for your account"),
    ("autostart", "notice", r"^etc/xdg/autostart/.*", "Starts with your desktop"),
    ("polkit-actions", "notice", r"^usr/share/polkit-1/actions/.*", "Defines actions that can ask for an administrator password"),
    ("apt-config", "notice", r"^etc/apt/.*", "Changes the software sources"),
]
_PATH_RULES = [(i, s, re.compile(p), t) for i, s, p, t in PATH_RULES]

STANDARD_ROOTS = ("usr/", "etc/", "opt/", "var/", "srv/", "lib/", "lib64/", "bin/", "sbin/")


def _evidence(line):
    line = line.strip()
    return line if len(line) <= 160 else line[:157] + "..."


def scan_script(text, where, contained=False):
    """Findings for one shell script. Each rule reports its first matching line."""
    findings = []
    seen = set()
    lines = text.splitlines()
    for number, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for rule in SCRIPT_RULES:
            if rule.id in seen or not rule.pattern.search(raw):
                continue
            seen.add(rule.id)
            findings.append(Finding(rule.id, rule.severity, tr(rule.title), tr(rule.detail),
                                    "%d: %s" % (number, _evidence(raw)), where, rule.kind))
    return lower_if_contained(findings) if contained else findings


def scan_paths(entries, contained=False):
    """Findings for a package's file list.

    `entries` is an iterable of (path, mode, is_file). Paths may start with
    "./" or "/"; both are normalized.
    """
    findings = []
    seen = {}
    odd_roots = []
    for path, mode, is_file in entries:
        clean = path.lstrip("./") if path.startswith("./") else path.lstrip("/")
        if not clean:
            continue
        if is_file and mode & 0o6000:
            kind = "setuid" if mode & 0o4000 else "setgid"
            key = (kind, clean)
            if key not in seen:
                seen[key] = True
                findings.append(Finding(
                    "setuid-file", "warning", tr("Contains a program that runs with someone else's rights"),
                    tr("A program marked this way runs with the rights of its owner, often the administrator."),
                    "/" + clean, "files", "system"))
        for rule_id, severity, pattern, title in _PATH_RULES:
            if pattern.search(clean):
                if rule_id not in seen:
                    seen[rule_id] = Finding(rule_id, severity, tr(title), "", "/" + clean, "files", "system")
                    findings.append(seen[rule_id])
                break
        else:
            if is_file and not clean.startswith(STANDARD_ROOTS) and len(odd_roots) < 3:
                odd_roots.append("/" + clean)
    if odd_roots:
        findings.append(Finding(
            "odd-location", "notice", tr("Puts files in unusual places"),
            tr("Programs normally install under /usr, /opt or /etc."), ", ".join(odd_roots), "files", "system"))
    return lower_if_contained(findings) if contained else findings


def lower_if_contained(findings):
    """System-state findings inside a box are only worth a notice."""
    for finding in findings:
        if finding.kind == "system" and RANK[finding.severity] > RANK["notice"]:
            finding.severity = "notice"
            finding.detail = (finding.detail + " " if finding.detail else "") + tr("This stays inside the app's own box.")
    return findings


def verdict(findings):
    """'danger', 'look' or 'normal'."""
    worst = max((RANK[f.severity] for f in findings), default=0)
    if worst >= RANK["danger"]:
        return "danger"
    if worst >= RANK["warning"]:
        return "look"
    return "normal"


def sort_findings(findings):
    return sorted(findings, key=lambda f: -RANK[f.severity])


# --- AUR metadata -------------------------------------------------------

def edit_distance(a, b, limit=3):
    """Levenshtein distance, giving up above `limit`."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        if min(current) > limit:
            return limit + 1
        previous = current
    return previous[-1]


def lookalike(name, popular):
    """A popular package this name could be a misspelling of, or None."""
    name = name.lower()
    if name in popular:
        return None
    for other in popular:
        limit = 1 if len(other) < 8 else 2
        if edit_distance(name, other, limit) <= limit and name != other:
            return other
    return None


def scan_aur_meta(info, popular, now):
    """Findings from an AUR RPC record (a dict) and the current Unix time."""
    findings = []
    name = info.get("Name", "")
    twin = lookalike(name, popular)
    if twin:
        findings.append(Finding(
            "lookalike", "warning", tr("The name is close to a well-known package"),
            tr("{name} looks like {other}. Attackers use names like this to get installed by mistake.",
               name=name, other=twin), twin, "aur", "behaviour"))
    first = info.get("FirstSubmitted")
    if first and now - first < 30 * 86400:
        findings.append(Finding(
            "new-package", "notice", tr("Added very recently"),
            tr("Packages that are only days old have not been looked at by many people."), "", "aur", "behaviour"))
    if not info.get("Maintainer"):
        findings.append(Finding(
            "orphaned", "notice", tr("Nobody maintains this package"),
            tr("It may be out of date, and anyone can take it over."), "", "aur", "behaviour"))
    votes = info.get("NumVotes", 0)
    if votes < 5:
        findings.append(Finding(
            "few-votes", "notice", tr("Few people use it"),
            tr("Only {n} people have voted for this package.", n=votes), "", "aur", "behaviour"))
    return findings
