#!/usr/bin/env bash
set -euo pipefail
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/panel-lyrics@linux-desktop-optimizer"
output_dir="${1:-/tmp/panel-lyrics-dist}"
mkdir -p -- "$output_dir"
gnome-extensions pack --force --extra-source=lyrics.js --extra-source=player.js \
    --out-dir="$output_dir" "$source_dir"
printf '扩展包：%s/panel-lyrics@linux-desktop-optimizer.shell-extension.zip\n' "$output_dir"
