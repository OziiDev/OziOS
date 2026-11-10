#!/usr/bin/env bash
# Run a script inside the test VM as the unprivileged user "ozitest".
#
#   tools/vmexec.sh [timeout-seconds] < script
#
# Inside the VM the project is mounted read-only at /srv/ozios and /tmp is
# writable. The test user has no sudo and no access to the desktop session,
# so this is for lint, unit tests and container or sandbox smoke tests, not
# for anything graphical. Qt programs run with the offscreen platform.
#
# Prints the script's output and exits with its status.
set -u
timeout="${1:-120}"
root="$(cd "$(dirname "$0")/.." && pwd)"
vbox="/c/Program Files/Oracle/VirtualBox/VBoxManage.exe"
vm="${OZI_VM:-OziOS-Dev}"

mkdir -p "$root/.bridge"
id="x-$$-$RANDOM"
script="$root/.bridge/$id.sh"
tr -d '\r' > "$script"
trap 'rm -f "$script"' EXIT

out="$(MSYS_NO_PATHCONV=1 "$vbox" guestcontrol "$vm" run --username ozitest --password "" \
  --timeout "$((timeout * 1000))" --exe /bin/bash --wait-stdout --wait-stderr -- -c \
  "cd /tmp && export XDG_RUNTIME_DIR=/run/user/\$(id -u) QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 LC_ALL=C.UTF-8 && bash /srv/ozios/.bridge/$id.sh; rc=\$?; echo; echo __exit=\$rc" 2>&1)"

status="$(printf '%s\n' "$out" | sed -n 's/^__exit=\([0-9]*\)$/\1/p' | tail -n1)"
printf '%s\n' "$out" | grep -v '^__exit=[0-9]*$'
if [ -z "$status" ]; then
  echo "vmexec: the VM did not finish the script (timeout ${timeout}s, or the VM is not ready)" >&2
  exit 124
fi
exit "$status"
