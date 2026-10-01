import locale
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

EXTENSION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXTENSION_DIR))
import ldo_iec_size as extension
from gi.repository import Gio, GLib, Nautilus


class FileStub:
    """Only Nautilus-owned FileInfo is substituted; filesystem I/O is real."""
    def __init__(self, path, directory=False):
        self.location = Gio.File.new_for_path(str(path))
        self.directory = directory
        self.gone = False
        self.attributes = {}

    def get_location(self):
        return self.location

    def is_directory(self):
        return self.directory

    def is_gone(self):
        return self.gone

    def add_string_attribute(self, key, value):
        self.attributes[key] = value


class ExtensionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.provider = extension.IecSizeColumn()

    def query(self, file, cancel=False):
        loop = GLib.MainLoop()
        finished = []
        complete = []
        original = self.provider._query_finished

        def callback(*args):
            try:
                original(*args)
            finally:
                finished.append(True)
                loop.quit()

        self.provider._query_finished = callback
        handle = object()
        closure = object()
        timeout = GLib.timeout_add_seconds(5, lambda: (loop.quit(), False)[1])
        with patch.object(Nautilus, "info_provider_update_complete_invoke",
                          side_effect=lambda *args: complete.append(args)):
            status = self.provider.update_file_info_full(
                self.provider, handle, closure, file,
            )
            if cancel:
                self.provider.cancel_update(self.provider, handle)
            if status == Nautilus.OperationResult.IN_PROGRESS:
                loop.run()
                self.assertTrue(finished, "GIO did not complete before timeout")
            GLib.source_remove(timeout)
        self.assertEqual(self.provider._pending, {})
        expected = ([(closure, self.provider, handle, Nautilus.OperationResult.COMPLETE)]
                    if status == Nautilus.OperationResult.IN_PROGRESS and not cancel else [])
        self.assertEqual(complete, expected)
        return file.attributes[extension.ATTRIBUTE]

    def test_column_is_real_nautilus_object(self):
        column, = self.provider.get_columns()
        self.assertIsInstance(column, Nautilus.Column)
        self.assertEqual(column.props.attribute, extension.ATTRIBUTE)
        self.assertEqual(column.props.xalign, 1.0)

    def test_iec_boundaries(self):
        previous = locale.setlocale(locale.LC_ALL)
        self.addCleanup(locale.setlocale, locale.LC_ALL, previous)
        locale.setlocale(locale.LC_ALL, "C")
        cases = [(0, "0 bytes"), (1, "1 byte"), (1023, "1023 bytes"),
                 (1024, "1.0 KiB"), (1536, "1.5 KiB"),
                 (1024**2, "1.0 MiB"), (1024**3, "1.0 GiB"),
                 (1024**4, "1.0 TiB"), (1024**5, "1.0 PiB"),
                 (1024**6, "1.0 EiB")]
        for size, expected in cases:
            with self.subTest(size=size):
                self.assertEqual(" ".join(extension.format_size(size).split()), expected)

    def test_unicode_spaces_and_percent_in_name(self):
        path = self.root / "测试 100% # file"
        path.write_bytes(b"x" * 1536)
        self.assertEqual(self.query(FileStub(path)), extension.format_size(1536))

    def test_empty_file(self):
        path = self.root / "empty"
        path.touch()
        self.assertEqual(self.query(FileStub(path)), extension.format_size(0))

    def test_sparse_file_and_refresh(self):
        path = self.root / "sparse"
        with path.open("wb") as stream:
            stream.truncate(2 * 1024**3)
        file = FileStub(path)
        self.assertEqual(self.query(file), extension.format_size(2 * 1024**3))
        path.write_bytes(b"x" * 1024)
        self.assertEqual(self.query(file), extension.format_size(1024))

    def test_symlink_follows_target(self):
        target = self.root / "target"
        target.write_bytes(b"x" * 2048)
        link = self.root / "link"
        link.symlink_to(target)
        self.assertEqual(self.query(FileStub(link)), extension.format_size(2048))

    def test_missing_and_broken_link(self):
        missing = self.root / "missing"
        link = self.root / "broken"
        link.symlink_to(missing)
        for path in (missing, link):
            with self.subTest(path=path):
                self.assertEqual(self.query(FileStub(path)), extension.UNAVAILABLE)

    def test_directory_and_directory_link(self):
        self.assertEqual(self.query(FileStub(self.root, directory=True)), extension.UNAVAILABLE)
        link = self.root / "dir-link"
        link.symlink_to(self.root)
        self.assertEqual(self.query(FileStub(link)), extension.UNAVAILABLE)

    def test_fifo_does_not_open_content(self):
        path = self.root / "fifo"
        os.mkfifo(path)
        self.assertEqual(self.query(FileStub(path)), extension.UNAVAILABLE)

    def test_cancel_has_no_late_result_or_completion(self):
        path = self.root / "cancelled"
        path.write_bytes(b"x" * 1024)
        self.assertEqual(self.query(FileStub(path), cancel=True), extension.UNAVAILABLE)
        self.provider.cancel_update(self.provider, object())

    def test_gone_file_is_not_queried(self):
        file = FileStub(self.root / "gone")
        file.gone = True
        with patch.object(file, "get_location", side_effect=AssertionError("unexpected I/O")):
            self.assertEqual(self.query(file), extension.UNAVAILABLE)


class InstallerTests(unittest.TestCase):
    def test_install_update_uninstall_preserves_other_extensions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "nautilus-python/extensions"
            directory.mkdir(parents=True)
            unrelated = directory / "other.py"
            unrelated.write_text("# leave me alone\n")
            target = directory / "ldo_iec_size.py"

            def run(action):
                subprocess.run([sys.executable, str(EXTENSION_DIR / "install.py"),
                                action, "--data-home", str(root)],
                               check=True, capture_output=True, text=True)

            run("install")
            self.assertEqual(target.read_bytes(), (EXTENSION_DIR / target.name).read_bytes())
            target.write_text("# previous version\n")
            run("install")
            self.assertEqual(target.read_bytes(), (EXTENSION_DIR / target.name).read_bytes())
            run("uninstall")
            run("uninstall")
            self.assertFalse(target.exists())
            self.assertEqual(unrelated.read_text(), "# leave me alone\n")
            self.assertEqual(list(directory.iterdir()), [unrelated])


if __name__ == "__main__":
    unittest.main()
