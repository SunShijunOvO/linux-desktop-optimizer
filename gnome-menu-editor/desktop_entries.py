"""User-scoped desktop entry editing; never execute an entry's command."""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import tempfile
import uuid

from gi.repository import GLib

GROUP = 'Desktop Entry'
FLAGS = GLib.KeyFileFlags.KEEP_COMMENTS | GLib.KeyFileFlags.KEEP_TRANSLATIONS


def read_keyfile(path):
    keyfile = GLib.KeyFile()
    keyfile.load_from_file(str(path), FLAGS)
    return keyfile


def get(keyfile, key, default='', localized=False):
    try:
        if localized:
            return keyfile.get_locale_string(GROUP, key, None)
        return keyfile.get_string(GROUP, key)
    except GLib.Error:
        return default


def boolean(keyfile, key):
    try:
        return keyfile.get_boolean(GROUP, key)
    except GLib.Error:
        return False


def command_tokens(command):
    """Token spans for desktop Exec double quoting, without shell expansion."""
    tokens = []
    start = None
    quoted = False
    escaped = False
    value = ''
    for i, char in enumerate(command):
        if start is None:
            if char.isspace():
                continue
            start = i
        if escaped:
            value += char
            escaped = False
        elif char == '\\':
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif char.isspace() and not quoted:
            tokens.append((value, start, i))
            start, value = None, ''
        else:
            value += char
    if quoted or escaped:
        raise ValueError('启动命令的引号或转义不完整。')
    if start is not None:
        tokens.append((value, start, len(command)))
    if not tokens:
        raise ValueError('请输入启动命令。')
    return tokens


def add_no_sandbox(command):
    tokens = command_tokens(command)
    # A shell command cannot be safely edited as a desktop-entry argument list.
    executable = Path(tokens[0][0]).name
    if executable in {'sh', 'bash', 'dash', 'zsh', 'fish'} or any(
        token[0] in {'-c', '-lc'} for token in tokens[1:]
    ):
        raise ValueError('此启动项使用 shell 脚本，请在启动命令中手动添加参数。')
    if any(token[0] == '--no-sandbox' for token in tokens[1:]):
        return command
    # Insert before file arguments and Flatpak file-forwarding delimiters.
    # For flatpak run this leaves the flag after the application ID.
    insertion = next((start for value, start, _ in tokens[1:]
                      if value in {'--', '@@', '@@u'} or re.search(r'%[fFuU]', value)), len(command))
    prefix, suffix = command[:insertion].rstrip(), command[insertion:]
    return prefix + ' --no-sandbox' + (' ' + suffix if suffix else '')


@dataclass
class Entry:
    desktop_id: str
    path: Path
    keyfile: GLib.KeyFile
    user: bool

    @property
    def name(self):
        return get(self.keyfile, 'Name', self.desktop_id, localized=True)

    @property
    def hidden(self):
        return boolean(self.keyfile, 'Hidden') or boolean(self.keyfile, 'NoDisplay')


class Store:
    def __init__(self, data_home=None, data_dirs=None):
        self.home = Path(data_home or os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
        roots = data_dirs if data_dirs is not None else (os.environ.get('XDG_DATA_DIRS') or '/usr/local/share:/usr/share').split(':')
        self.roots = [self.home] + [Path(root) for root in roots if Path(root).is_absolute() and Path(root) != self.home]
        self.errors = []

    def entries(self):
        found = {}
        self.errors = []
        for root in self.roots:
            directory = root / 'applications'
            for path in sorted(directory.rglob('*.desktop')):
                desktop_id = str(path.relative_to(directory)).replace(os.sep, '-')
                if desktop_id in found:
                    continue
                # Even an invalid higher-priority entry shadows the system file.
                found[desktop_id] = None
                try:
                    keyfile = read_keyfile(path)
                    if get(keyfile, 'Type') == 'Application':
                        found[desktop_id] = Entry(desktop_id, path, keyfile, root == self.home)
                except (GLib.Error, OSError) as error:
                    self.errors.append(f'{path}: {error}')
        return sorted((entry for entry in found.values() if entry), key=lambda entry: entry.name.casefold())

    def new(self):
        keyfile = GLib.KeyFile()
        for key, value in {'Type': 'Application', 'Name': '新应用', 'Exec': '', 'Icon': 'application-x-executable', 'Categories': 'Utility;'}.items():
            keyfile.set_string(GROUP, key, value)
        desktop_id = f'local-{uuid.uuid4().hex}.desktop'
        return Entry(desktop_id, self.home / 'applications' / desktop_id, keyfile, True)

    def save(self, entry, values):
        if not values['Name'].strip():
            raise ValueError('应用名称不能为空。')
        command_tokens(values['Exec'])
        # Clone so a failed write never changes the in-memory original.
        keyfile = GLib.KeyFile()
        data = entry.keyfile.to_data()[0]
        keyfile.load_from_data(data, len(data.encode('utf-8')), FLAGS)
        original_exec = get(keyfile, 'Exec')
        for key, value in values.items():
            if isinstance(value, bool):
                keyfile.set_boolean(GROUP, key, value)
            else:
                keyfile.set_string(GROUP, key, value.strip())
                if key in {'Name', 'Comment'}:
                    # Update the active translation without deleting other locales.
                    for locale in GLib.get_language_names():
                        if locale == 'C':
                            continue
                        if f'{key}[{locale}]' in keyfile.get_keys(GROUP)[0]:
                            keyfile.set_locale_string(GROUP, key, locale, value.strip())
        if values['Exec'].strip() != original_exec:
            keyfile.set_boolean(GROUP, 'DBusActivatable', False)
        if not values.get('NoDisplay', False):
            for key in ('Hidden', 'OnlyShowIn', 'NotShowIn'):
                if key in keyfile.get_keys(GROUP)[0]:
                    keyfile.remove_key(GROUP, key)
        directory = self.home / 'applications'
        directory.mkdir(parents=True, exist_ok=True)
        target = entry.path if entry.user else directory / entry.desktop_id
        # Replace symlinks instead of following them into system files.
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='.menu-editor-', dir=target.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write(keyfile.to_data()[0])
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o644)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return Entry(entry.desktop_id, target, keyfile, True)

    def remove_override(self, entry):
        if not entry.user:
            raise ValueError('系统启动项不能删除；可以关闭“显示在应用菜单中”。')
        entry.path.unlink()
