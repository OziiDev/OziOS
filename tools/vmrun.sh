#!/usr/bin/env bash
# Host side of tools/vm-bridge.sh: run a script inside the test VM and wait for it.
#
#   tools/vmrun.sh <id> [timeout-seconds] < script
#
# Prints the tail of the output and exits with the script's status.
dir="$(cd "$(dirname "$0")/.." && pwd)/.bridge"
id="${1:?usage: vmrun.sh <id> [timeout] < script}"
timeout="${2:-110}"
mkdir -p "$dir"
rm -f "$dir/rc-$id" "$dir/out-$id.log"
cat > "$dir/cmd-$id.tmp"
mv "$dir/cmd-$id.tmp" "$dir/cmd-$id.sh"

end=$((SECONDS + timeout))
while [ ! -f "$dir/rc-$id" ]; do
  if [ "$SECONDS" -ge "$end" ]; then
    echo "vmrun: $id still running after ${timeout}s" >&2
    tail -n 15 "$dir/out-$id.log" 2>/dev/null
    exit 124
  fi
  read -r -t 1 _ < /dev/zero 2>/dev/null || ping -n 2 127.0.0.1 > /dev/null
done
tail -n "${VMRUN_TAIL:-40}" "$dir/out-$id.log"
exit "$(cat "$dir/rc-$id")"
