import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_entries import Store, add_no_sandbox, get, boolean, read_keyfile


class Commands(unittest.TestCase):
    def test_placeholder_and_quotes(self):
        self.assertEqual(add_no_sandbox('"/opt/My App/app" --profile="a b" %U'), '"/opt/My App/app" --profile="a b" --no-sandbox %U')

    def test_flatpak(self):
        self.assertEqual(add_no_sandbox('flatpak run --branch=stable --file-forwarding org.example.App @@u %U @@'), 'flatpak run --branch=stable --file-forwarding org.example.App --no-sandbox @@u %U @@')

    def test_idempotence(self):
        for command in ['app --no-sandbox %U', 'app "--no-sandbox"', 'env X=1 app --no-sandbox']:
            self.assertEqual(add_no_sandbox(command), command)
        self.assertEqual(add_no_sandbox('app --no-sandbox-other'), 'app --no-sandbox-other --no-sandbox')

    def test_separator(self):
        self.assertEqual(add_no_sandbox('app -- %F'), 'app --no-sandbox -- %F')

    def test_invalid_and_shell(self):
        for command in ['', 'app "oops', 'app \\', 'sh -c "app %U"']:
            with self.assertRaises(ValueError):
                add_no_sandbox(command)


class Files(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'user'
        self.system = self.root / 'system'
        self.folder = self.system / 'applications' / 'nested'
        self.folder.mkdir(parents=True)
        self.original = self.folder / 'app.desktop'
        self.content = '# preserved comment\n[Desktop Entry]\nType=Application\nName=Original\nName[fr]=Original français\nExec=app %U\nDBusActivatable=true\nOnlyShowIn=KDE;\nX-Custom=keep\nActions=New;\n\n[Desktop Action New]\nName=New\nExec=app --new\n'
        self.original.write_text(self.content)
        self.store = Store(self.home, [self.system])

    def values(self, **changes):
        result = dict(Name='Edited', Exec='app --no-sandbox %U', NoDisplay=False)
        result.update(changes)
        return result

    def test_override_preserves_system_actions_locales(self):
        entry = self.store.entries()[0]
        self.assertEqual(entry.desktop_id, 'nested-app.desktop')
        saved = self.store.save(entry, self.values())
        self.assertEqual(self.original.read_text(), self.content)
        self.assertTrue(saved.user)
        self.assertFalse(boolean(saved.keyfile, 'DBusActivatable'))
        self.assertEqual(get(saved.keyfile, 'OnlyShowIn'), '')
        self.assertEqual(get(saved.keyfile, 'X-Custom'), 'keep')
        self.assertEqual(saved.keyfile.get_string('Desktop Action New', 'Exec'), 'app --new')
        self.assertIn('Name[fr]=', saved.path.read_text())
        self.assertIn('# preserved comment', saved.path.read_text())
        self.assertEqual(len(self.store.entries()), 1)
        self.store.remove_override(saved)
        self.assertEqual(self.store.entries()[0].name, 'Original')

    def test_hidden_override_and_restore(self):
        saved = self.store.save(self.store.entries()[0], self.values(NoDisplay=True))
        self.assertTrue(self.store.entries()[0].hidden)
        self.assertEqual(get(saved.keyfile, 'OnlyShowIn'), 'KDE;')
        self.store.remove_override(saved)
        self.assertFalse(self.store.entries()[0].hidden)

    def test_new_and_validation(self):
        entry = self.store.new()
        with self.assertRaises(ValueError):
            self.store.save(entry, self.values(Name=''))
        self.assertFalse(entry.path.exists())
        self.store.save(entry, self.values())
        self.assertTrue(entry.path.exists())

    def test_same_exec_keeps_dbus(self):
        saved = self.store.save(self.store.entries()[0], self.values(Exec='app %U'))
        self.assertTrue(boolean(saved.keyfile, 'DBusActivatable'))

    def test_symlink_is_replaced_not_followed(self):
        directory = self.home / 'applications'
        directory.mkdir(parents=True)
        (directory / 'nested-app.desktop').symlink_to(self.original)
        saved = self.store.save(self.store.entries()[0], self.values())
        self.assertFalse(saved.path.is_symlink())
        self.assertEqual(self.original.read_text(), self.content)

    def test_system_delete_refused(self):
        with self.assertRaises(ValueError):
            self.store.remove_override(self.store.entries()[0])


if __name__ == '__main__':
    unittest.main()
