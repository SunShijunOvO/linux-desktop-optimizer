"""Run inside a display session with isolated application data."""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from menu_editor import Application, Window
from desktop_entries import Store, get, boolean
from gi.repository import GLib


def drain():
    context = GLib.MainContext.default()
    while context.pending():
        context.iteration(False)


with tempfile.TemporaryDirectory() as directory:
    app = Application()
    app.register(None)
    store = Store(Path(directory), [])
    window = Window(app, store)
    window.present()
    drain()
    window.new_entry()
    window.fields['Name'].set_text('界面测试')
    window.fields['Exec'].set_text('example %U')
    window.no_sandbox()
    assert window.fields['Exec'].get_text() == 'example --no-sandbox %U'
    assert window.dirty
    assert window.save()
    drain()
    assert window.current.name == '界面测试'
    assert not window.dirty
    assert len(window.rows) == 1
    window.current.keyfile.set_boolean('Desktop Entry', 'DBusActivatable', True)
    window.no_sandbox()
    assert window.dirty
    assert window.save()
    assert not boolean(window.current.keyfile, 'DBusActivatable')
    window.visible.set_active(False)
    assert window.save()
    assert store.entries()[0].hidden
    window.search.set_text('找不到')
    window.filter_rows()
    assert not window.rows[0].get_visible()
    window.search.set_text('界面')
    window.filter_rows()
    assert window.rows[0].get_visible()
    store.remove_override(window.current)
    window.reload()
    assert len(window.rows) == 0
    window.close()
    drain()
    print('GTK smoke passed: new, edit, no-sandbox, save, hide, search, delete')
