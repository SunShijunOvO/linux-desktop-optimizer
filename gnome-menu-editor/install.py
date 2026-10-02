#!/usr/bin/python3
"""Install a private copy for the current user; no root required."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

APP_ID = 'io.github.linux_desktop_optimizer.MenuEditor'
FILES = ('menu_editor.py', 'desktop_entries.py')


def main():
    parser = argparse.ArgumentParser(description='安装或卸载 GNOME 应用菜单编辑器')
    parser.add_argument('action', choices=['install', 'uninstall'])
    parser.add_argument('--data-home', type=Path, default=Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share'))
    args = parser.parse_args()
    home = args.data_home.expanduser().absolute()
    destination = home / 'linux-desktop-optimizer' / 'menu-editor'
    launcher = home / 'applications' / (APP_ID + '.desktop')
    if args.action == 'install':
        import gi
        gi.require_version('Gtk', '4.0')
        gi.require_version('Adw', '1')
        from gi.repository import Adw
        if (Adw.get_major_version(), Adw.get_minor_version()) < (1, 5):
            parser.error('需要 libadwaita 1.5 或更新版本')
        destination.mkdir(parents=True, exist_ok=True)
        for name in FILES:
            shutil.copy2(Path(__file__).parent / name, destination / name)
        launcher.parent.mkdir(parents=True, exist_ok=True)
        # Desktop Exec quoting has a second escape layer in KeyFile strings.
        from gi.repository import GLib
        path = str(destination / 'menu_editor.py')
        quoted = '"' + ''.join('\\' + c if c in '\\"`$' else c for c in path).replace('%', '%%') + '"'
        keyfile = GLib.KeyFile()
        for key, value in {'Type': 'Application', 'Name': '应用菜单编辑器', 'Comment': '编辑 GNOME 应用启动项与菜单', 'Exec': '/usr/bin/python3 ' + quoted, 'Icon': 'applications-system-symbolic', 'Categories': 'Settings;', 'Keywords': 'menu;desktop;Alacarte;菜单;启动项;', 'StartupWMClass': APP_ID}.items():
            keyfile.set_string('Desktop Entry', key, value)
        launcher.write_text(keyfile.to_data()[0], encoding='utf-8')
        print(f'已安装：{launcher}')
    else:
        launcher.unlink(missing_ok=True)
        for name in FILES:
            (destination / name).unlink(missing_ok=True)
        # Leave any unrelated files and user-edited application entries intact.
        if destination.exists() and not any(destination.iterdir()):
            destination.rmdir()
        print('已卸载编辑器；你编辑的应用启动项予以保留。')
    updater = shutil.which('update-desktop-database')
    if updater and launcher.parent.exists():
        subprocess.run([updater, str(launcher.parent)], check=False)


if __name__ == '__main__':
    main()
