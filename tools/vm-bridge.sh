#!/usr/bin/env bash
# Runs inside a test VM, as root. Runs command files dropped into .bridge/
# on the shared folder and leaves their output and exit status next to them,
# so the VM can be driven from the host without a network login.
dir="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)/.bridge"
mkdir -p "$dir"
rm -f "$dir"/cmd-*.sh "$dir"/rc-* 2>/dev/null
date -Is > "$dir/ready"
echo "bridge: watching $dir"

while :; do
  for cmd in "$dir"/cmd-*.sh; do
    [ -e "$cmd" ] || continue
    id="${cmd##*/cmd-}"
    id="${id%.sh}"
    tr -d '\r' < "$cmd" > /tmp/bridge-cmd.sh
    rm -f "$cmd"
    echo "bridge: running $id"
    bash /tmp/bridge-cmd.sh > "$dir/out-$id.log" 2>&1
    echo $? > "$dir/rc-$id"
  done
  sleep 1
done
