#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bundle_dir="$(mktemp -d /tmp/jasmine-panel-lyrics-install.XXXXXX)"
trap 'rm -rf -- "$bundle_dir"' EXIT
uuid='jasmine-panel-lyrics@linux-desktop-optimizer'
legacy_uuid='panel-lyrics@linux-desktop-optimizer'
bash "$project_dir/package.sh" "$bundle_dir"
gnome-extensions install --force "$bundle_dir/$uuid.shell-extension.zip"
# Retire the old identity only after the new package has installed successfully.
legacy_dir="${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/$legacy_uuid"
if [[ -d "$legacy_dir" ]]; then
    gnome-extensions disable "$legacy_uuid" 2>/dev/null || true
    if ! gnome-extensions uninstall "$legacy_uuid"; then
        # A newly installed extension may not yet be registered in this Shell.
        # Preserve its files outside the scanned directory instead of deleting them.
        python3 - "$legacy_dir/metadata.json" "$legacy_uuid" <<'PY'
import json
import sys
with open(sys.argv[1]) as source:
    if json.load(source).get('uuid') != sys.argv[2]:
        raise SystemExit('旧目录 UUID 不匹配，保留原目录，请手动检查。')
PY
        backup_root="${XDG_STATE_HOME:-$HOME/.local/state}/jasmine-panel-lyrics"
        mkdir -p -- "$backup_root"
        backup_dir="$(mktemp -d "$backup_root/legacy.XXXXXX")"
        mv -- "$legacy_dir" "$backup_dir/$legacy_uuid"
        printf '旧版本已移至备份：%s\n' "$backup_dir/$legacy_uuid"
    fi
fi
if gnome-extensions enable "$uuid"; then
    printf '已安装并请求启用 jasmine-panel-lyrics。\n'
else
    printf '已安装。请保存工作、注销并重新登录，然后运行：\n  gnome-extensions enable %s\n' "$uuid"
fi
