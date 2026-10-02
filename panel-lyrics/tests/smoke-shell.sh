#!/usr/bin/env bash
# Runs an isolated headless Shell; never restarts the user's desktop.
set -euo pipefail
if [[ "${1:-}" != --inside ]]; then
    test_root="$(mktemp -d /tmp/panel-lyrics-shell.XXXXXX)"
    trap 'rm -rf -- "$test_root"' EXIT
    extension_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
    mkdir -p "$test_root/data/gnome-shell/extensions" "$test_root/config" "$test_root/cache" "$test_root/runtime"
    chmod 700 "$test_root/runtime"
    cp -r "$extension_root/panel-lyrics@linux-desktop-optimizer" "$test_root/data/gnome-shell/extensions/"
    cp -r "$extension_root/tests/probe" "$test_root/data/gnome-shell/extensions/panel-lyrics-test@local"
    cat >"$test_root/bus.conf" <<'BUS'
<busconfig>
  <type>session</type>
  <listen>unix:tmpdir=/tmp</listen>
  <policy context="default">
    <allow send_destination="*"/>
    <allow receive_sender="*"/>
    <allow own="*"/>
  </policy>
</busconfig>
BUS
    env XDG_DATA_HOME="$test_root/data" XDG_CONFIG_HOME="$test_root/config" \
        XDG_CACHE_HOME="$test_root/cache" XDG_RUNTIME_DIR="$test_root/runtime" \
        GSETTINGS_BACKEND=memory GIO_USE_VFS=local \
        dbus-run-session --config-file="$test_root/bus.conf" -- bash "$0" --inside
    exit
fi
shell_pid=''
trap 'if [[ -n "$shell_pid" ]]; then kill "$shell_pid" 2>/dev/null || true; wait "$shell_pid" 2>/dev/null || true; fi' EXIT
gnome-shell --headless --wayland --no-x11 --virtual-monitor=1280x720 \
    >"$XDG_CACHE_HOME/shell.log" 2>&1 &
shell_pid=$!
for attempt in {1..60}; do
    if gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell \
        --method org.gnome.Shell.Extensions.GetExtensionInfo panel-lyrics@linux-desktop-optimizer >"$XDG_CACHE_HOME/info" 2>/dev/null; then
        break
    fi
    if ! kill -0 "$shell_pid" 2>/dev/null; then
        cat "$XDG_CACHE_HOME/shell.log"
        exit 1
    fi
    sleep 0.5
done
gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell \
    --method org.gnome.Shell.Extensions.EnableExtension panel-lyrics@linux-desktop-optimizer
sleep 2
LC_ALL=C gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell \
        --method org.gnome.Shell.Extensions.GetExtensionInfo panel-lyrics@linux-desktop-optimizer >"$XDG_CACHE_HOME/info"
cat "$XDG_CACHE_HOME/info"
if ! grep -Eq "'state': <1.0>" "$XDG_CACHE_HOME/info"; then
    cat "$XDG_CACHE_HOME/shell.log"
    exit 1
fi
gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell \
    --method org.gnome.Shell.Extensions.EnableExtension panel-lyrics-test@local
for attempt in {1..20}; do
    if [[ -f "$XDG_CACHE_HOME/probe-result" ]]; then break; fi
    sleep 1
done
if [[ "$(cat "$XDG_CACHE_HOME/probe-result" 2>/dev/null)" != PASS ]]; then
    cat "$XDG_CACHE_HOME/probe-result" "$XDG_CACHE_HOME/shell.log"
    exit 1
fi
printf 'Panel text, local LRC, pause, seeking, reload and fallback passed\n'
gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell \
    --method org.gnome.Shell.Extensions.DisableExtension panel-lyrics-test@local
gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell \
    --method org.gnome.Shell.Extensions.DisableExtension panel-lyrics@linux-desktop-optimizer
gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell \
    --method org.gnome.Shell.Extensions.EnableExtension panel-lyrics@linux-desktop-optimizer
sleep 1
LC_ALL=C gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell \
        --method org.gnome.Shell.Extensions.GetExtensionInfo panel-lyrics@linux-desktop-optimizer >"$XDG_CACHE_HOME/info"
if ! grep -Eq "'state': <1.0>" "$XDG_CACHE_HOME/info"; then
    cat "$XDG_CACHE_HOME/shell.log"
    exit 1
fi
gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell \
    --method org.gnome.Shell.Extensions.DisableExtension panel-lyrics@linux-desktop-optimizer
if grep -E 'JS ERROR.*[Pp]anel|Extension panel-lyrics.*Error' "$XDG_CACHE_HOME/shell.log"; then
    cat "$XDG_CACHE_HOME/shell.log"
    exit 1
fi
printf 'GNOME Shell load, disable and re-enable passed\n'
