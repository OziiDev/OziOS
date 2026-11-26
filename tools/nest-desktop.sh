#!/bin/bash
# Run oziwm + ozi-shell from this checkout as a window inside the current
# desktop, with their own settings, for trying changes out.
#
#   tools/nest-desktop.sh start [DIR]   start; DIR (default: a new temp dir) keeps its state
#   tools/nest-desktop.sh ipc DIR JSON  send one request to THAT nested oziwm
#   tools/nest-desktop.sh shot DIR PNG  screenshot of the nested screen
#   tools/nest-desktop.sh stop DIR      end it
#
# It never touches the real desktop: it gets its own XDG_CONFIG_HOME (a copy of
# your desktop.json, never written back), and talks only to the socket it
# read from its own log, refusing the real desktop's $OZIWM_SOCKET.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
cmd=${1:-}

sock_of() {
    local s
    s=$(sed 's/\x1b\[[0-9;]*m//g' "$1/oziwm.log" | grep -o 'ipc=[^ ]*' | head -1 | cut -d= -f2 | tr -d '"')
    if [ -z "$s" ] || [ ! -S "$s" ]; then echo "no nested oziwm in $1" >&2; exit 1; fi
    if [ -n "${OZIWM_SOCKET:-}" ] && [ "$(realpath "$s")" = "$(realpath "$OZIWM_SOCKET")" ]; then
        echo "refusing: that is the real desktop's socket" >&2; exit 1
    fi
    echo "$s"
}

case "$cmd" in
start)
    dir=${2:-$(mktemp -d /tmp/ozi-nest.XXXXXX)}
    mkdir -p "$dir/config/ozios"
    real="${XDG_CONFIG_HOME:-$HOME/.config}/ozios/desktop.json"
    [ -f "$dir/config/ozios/desktop.json" ] || { [ -f "$real" ] && cp "$real" "$dir/config/ozios/desktop.json"; } || true
    bin="$here/oziwm/target/debug/oziwm"
    [ -x "$bin" ] || { echo "build first: cd $here/oziwm && cargo build" >&2; exit 1; }
    (
        export XDG_CONFIG_HOME="$dir/config"
        export PATH="$here/shell:$PATH"
        unset OZIWM_SOCKET QT_WAYLAND_SHELL_INTEGRATION
        export RUST_LOG=${RUST_LOG:-info} NO_COLOR=1
        setsid "$bin" --nested -c "$here/shell/ozi-shell" >"$dir/oziwm.log" 2>&1 &
        echo $! >"$dir/pid"
    )
    for _ in $(seq 50); do sed 's/\x1b\[[0-9;]*m//g' "$dir/oziwm.log" 2>/dev/null | grep -q 'ipc=' && break; sleep 0.2; done
    sock_of "$dir" >/dev/null
    echo "$dir"
    ;;
ipc)
    s=$(sock_of "$2")
    python3 -c 'import json,socket,sys
c=socket.socket(socket.AF_UNIX); c.settimeout(8); c.connect(sys.argv[1])
c.sendall((sys.argv[2].strip()+"\n").encode()); b=b""
while not b.endswith(b"\n"):
    d=c.recv(65536)
    if not d: break
    b+=d
print(b.decode().strip())' "$s" "$3"
    ;;
shot)
    "$0" ipc "$2" "{\"do\":\"screenshot\",\"path\":\"$(realpath -m "$3")\"}"
    ;;
stop)
    s=$(sock_of "$2") && "$0" ipc "$2" '{"do":"quit"}' >/dev/null 2>&1 || true
    [ -f "$2/pid" ] && kill "$(cat "$2/pid")" 2>/dev/null || true
    ;;
*)
    sed -n 2,12p "$0"; exit 2 ;;
esac
