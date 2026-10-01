"""Loaded only by run_nautilus_smoke.py in an isolated Nautilus process."""
import json
import os
from pathlib import Path
import traceback

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Nautilus", "4.1")
from gi.repository import Gio, GLib, GObject, Gtk, Nautilus


class IecSmokeProbe(GObject.GObject, Nautilus.ColumnProvider):
    def __init__(self):
        super().__init__()
        self.root = Path(os.environ["LDO_SMOKE_ROOT"])
        self.phase = 0
        self.report = {}
        Gio.Settings.new("org.gnome.nautilus.preferences").set_string(
            "default-folder-viewer", "list-view")
        Gio.Settings.new("org.gnome.nautilus.list-view").set_strv(
            "default-visible-columns", ["name", "Ldo::IecSize"])
        GLib.timeout_add_seconds(3, self.check)

    def get_columns(self):
        return []

    def views(self, widget):
        if isinstance(widget, Gtk.ColumnView):
            yield widget
            return
        child = widget.get_first_child()
        while child:
            yield from self.views(child)
            child = child.get_next_sibling()

    @staticmethod
    def files(view):
        model = view.get_model()
        return [model.get_item(i).get_item().get_property("file")
                for i in range(model.get_n_items())]

    def check(self):
        app = Gio.Application.get_default()
        try:
            view = next(v for w in app.get_windows() for v in self.views(w)
                        if any(c.get_id() == "Ldo::IecSize" for c in v.get_columns()))
            columns = {c.get_id(): c for c in view.get_columns()}
            assert columns["size"].get_sorter() == columns["Ldo::IecSize"].get_sorter()
            assert not columns["size"].get_visible()
            files = {f.get_name(): f for f in self.files(view)}
            assert len(files) == 8, list(files)
            for name in ("empty", "twelve", "dir-link"):
                file = files[name]
                assert file.get_string_attribute("size") == file.get_string_attribute("ldo_iec_size"), name
            for name, unit in (("kib", "KiB"), ("mib", "MiB"), ("gib", "GiB")):
                assert unit in files[name].get_string_attribute("ldo_iec_size"), name

            if self.phase == 0:
                assert files["empty"].get_string_attribute("size") == "0 items"
                assert files["twelve"].get_string_attribute("size") == "12 items"
                orders = {}
                settings = Gio.Settings.new("org.gtk.gtk4.Settings.FileChooser")
                for directories_first in (False, True):
                    settings.set_boolean("sort-directories-first", directories_first)
                    for order in (Gtk.SortType.ASCENDING, Gtk.SortType.DESCENDING):
                        view.sort_by_column(columns["size"], order)
                        expected = [f.get_name() for f in self.files(view)]
                        view.sort_by_column(columns["Ldo::IecSize"], order)
                        actual = [f.get_name() for f in self.files(view)]
                        assert actual == expected, (actual, expected)
                        orders[f"directories_first={directories_first},order={int(order)}"] = actual
                self.report["sort_orders"] = orders
                self.report["initial_counts"] = {
                    name: files[name].get_string_attribute("ldo_iec_size")
                    for name in ("empty", "twelve", "dir-link")}
                (self.root / "files/empty/new-item").touch()
                # Nautilus itself does not monitor every child directory's
                # contents. Exercise its normal F5 refresh after changing one.
                assert view.activate_action("slot.reload", None)
                self.phase = 1
                return True

            assert files["empty"].get_string_attribute("ldo_iec_size") == "1 item"
            self.report["updated_count"] = "1 item"
            self.report["ok"] = True
        except Exception:
            self.report["error"] = traceback.format_exc()
        (self.root / "result.json").write_text(json.dumps(self.report, indent=2))
        app.quit()
        return False
