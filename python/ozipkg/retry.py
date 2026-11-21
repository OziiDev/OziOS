"""Run a download again when the network drops out under it.

The installer downloads the whole base system with pacstrap, and runs it
through `/usr/lib/ozios/retry-download`. pacman gives up on a file once every
mirror has failed it, and a few seconds without a network are enough for that:
when Wi-Fi drops or a router restarts, names stop resolving and every mirror
fails at the same moment. The installation then stopped with "Failed to run
pacstrap", and everything had to start again from the partitions.

Run again, the command carries on where it stopped: the files already
downloaded stay in the cache, and pacstrap's `--needed` skips what is
installed. Only a failed download is tried again. Any other failure, a file
conflict or a full disk, is the command's own answer and comes back at once.
"""
import re
import socket
import subprocess
import sys
import time

# pacman's last word when the download, not the packages, failed: the files, the package
# lists, or a file that arrived cut short (its checksum is wrong, and pacman deletes it).
NETWORK = re.compile(r"failed to retrieve some files|failed to synchronize|download library error|"
                     r"invalid or corrupted package \(checksum\)")
TRIES = 4
PAUSES = (15, 30, 60)          # seconds before the second, third and fourth try
STEP = 5                       # seconds between looks at the network
WAIT_FOR_NETWORK = 300         # seconds, at most, to wait for names to resolve again
PROBES = ("archlinux.org", "cachyos.org")
MIRRORLIST = "/etc/pacman.d/mirrorlist"
KEEP = 200                     # lines of output kept to tell what went wrong


def network_failure(lines):
    """Did the command fail because a download broke off?"""
    return any(NETWORK.search(line) for line in lines)


def mirror_hosts(path=MIRRORLIST, limit=2):
    """The first mirrors pacman will ask: the best sign that it can download again."""
    hosts = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"^\s*Server\s*=\s*\w+://([^/:\s]+)", line)
                if m and m.group(1) not in hosts:
                    hosts.append(m.group(1))
                    if len(hosts) == limit:
                        break
    except OSError:
        pass
    return hosts


def online(hosts=None, connect=socket.create_connection):
    """Can this computer reach a mirror again? A name alone is not enough: the
    resolver answers from its cache while the cable is still out."""
    for host in (mirror_hosts() if hosts is None else hosts) + list(PROBES):
        try:
            connect((host, 443), timeout=5).close()
            return True
        except (OSError, UnicodeError):
            continue
    return False


def say(out, text):
    out.write("ozios: " + text + "\n")
    out.flush()


def run_once(command, out, popen=subprocess.Popen):
    """Run the command once and pass its output on as it comes, line by line, for the
    installer to show. Returns the exit status and the last lines of output."""
    try:
        proc = popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                     errors="replace")
    except OSError as err:
        say(out, "could not run %s: %s" % (command[0], err))
        return 127, []
    lines = []
    for line in proc.stdout:
        out.write(line)
        out.flush()
        lines.append(line)
        del lines[:-KEEP]
    return proc.wait(), lines


def wait_for_network(out, sleep, is_online, limit=WAIT_FOR_NETWORK):
    waited = 0
    while not is_online() and waited < limit:
        if waited == 0:
            say(out, "waiting for the network to come back")
        sleep(STEP)
        waited += STEP


def main(argv, out=sys.stdout, popen=subprocess.Popen, sleep=time.sleep, is_online=online, tries=TRIES):
    if not argv:
        out.write("usage: retry-download COMMAND [ARGUMENT...]\n")
        return 2
    status = 0
    for attempt in range(1, tries + 1):
        status, lines = run_once(argv, out, popen)
        if status == 0:
            if attempt > 1:
                say(out, "the download finished on try %d" % attempt)
            return 0
        if attempt == tries or not network_failure(lines):
            return status
        pause = PAUSES[min(attempt, len(PAUSES)) - 1]
        say(out, "the download broke off; trying again in %d s (try %d of %d)" % (pause, attempt + 1, tries))
        sleep(pause)
        wait_for_network(out, sleep, is_online)
    return status
