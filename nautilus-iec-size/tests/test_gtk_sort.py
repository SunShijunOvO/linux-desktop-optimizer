"""Real GTK tests; run with a display (including GTK's Broadway backend)."""
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ldo_iec_size as extension
from gi.repository import Gio, GLib, GObject, Gtk


@unittest.skipUnless(os.environ.get("LDO_TEST_GTK") == "1", "set LDO_TEST_GTK=1 with a GTK display")
class NativeSortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not Gtk.init_check():
            raise RuntimeError("LDO_TEST_GTK=1 requires a working GTK display")

    def setUp(self):
        self.bridge = extension.NativeSizeSortBridge()
        self.addCleanup(self.bridge.stop)
        self.view = Gtk.ColumnView()
        self.native = Gtk.ColumnViewColumn(title="Size")
        self.native.set_id("size")
        self.iec = Gtk.ColumnViewColumn(title="IEC")
        self.iec.set_id(extension.COLUMN)
        self.native_sorter = Gtk.CustomSorter.new(lambda a, b, *_: (a.value > b.value) - (a.value < b.value))
        self.native.set_sorter(self.native_sorter)
        self.iec.set_sorter(Gtk.CustomSorter.new(lambda *_: 0))
        self.view.append_column(self.native)
        self.view.append_column(self.iec)

    def test_shares_exact_native_sorter_even_when_native_column_hidden(self):
        self.native.set_visible(False)
        self.assertTrue(self.bridge.attach(self.view))
        self.assertEqual(self.iec.get_sorter(), self.native_sorter)
        self.assertTrue(self.bridge.attach(self.view))

    def test_ascending_and_descending_match_native_with_mixed_units_and_ties(self):
        store = Gio.ListStore.new(GObject.Object)
        for size in (1024**3, 1024, 10, 2 * 1024**2, 1024, 0):
            item = GObject.Object()
            item.value = size
            store.append(item)
        self.bridge.attach(self.view)
        model = Gtk.SortListModel.new(store, self.view.get_sorter())
        for order in (Gtk.SortType.ASCENDING, Gtk.SortType.DESCENDING):
            self.view.sort_by_column(self.native, order)
            expected = [model.get_item(i) for i in range(model.get_n_items())]
            self.view.sort_by_column(self.iec, order)
            self.assertEqual([model.get_item(i) for i in range(model.get_n_items())], expected)

    def test_missing_native_sorter_disables_incorrect_text_sort(self):
        self.view.remove_column(self.native)
        with self.assertLogs(extension.__name__, level="WARNING"):
            self.assertFalse(self.bridge.attach(self.view))
        self.assertIsNone(self.iec.get_sorter())

    def test_map_hook_attaches_new_views_without_polling(self):
        self.bridge.start()
        window = Gtk.Window()
        self.addCleanup(window.destroy)
        window.set_child(self.view)
        window.present()
        context = GLib.MainContext.default()
        while context.pending():
            context.iteration(False)
        self.assertTrue(self.view.get_mapped())
        self.assertEqual(self.iec.get_sorter(), self.native_sorter)
        window.set_visible(False)
        window.present()
        self.assertEqual(self.iec.get_sorter(), self.native_sorter)
