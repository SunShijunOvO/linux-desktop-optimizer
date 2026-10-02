#!/usr/bin/env bash
set -euo pipefail
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/jasmine-panel-lyrics@linux-desktop-optimizer"
output_dir="${1:-/tmp/jasmine-panel-lyrics-dist}"
mkdir -p -- "$output_dir"
gnome-extensions pack --force --extra-source=core --extra-source=players --extra-source=providers \
    --extra-source=transport --extra-source=ui \
    --out-dir="$output_dir" "$source_dir"
printf '扩展包：%s/jasmine-panel-lyrics@linux-desktop-optimizer.shell-extension.zip\n' "$output_dir"
