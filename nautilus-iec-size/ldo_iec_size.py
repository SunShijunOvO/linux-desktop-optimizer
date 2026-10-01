"""Nautilus list-view column using IEC (base 1024) file sizes."""

import locale
import logging
import weakref

import gi

gi.require_version("Nautilus", "4.1")
gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, GObject, Gtk, Nautilus


COLUMN = "Ldo::IecSize"
ATTRIBUTE = "ldo_iec_size"
UNAVAILABLE = "—"


class NativeSizeSortBridge:
    """Reuse each view's actual size sorter via GTK, without recreating it.

    Nautilus 50 uses GtkColumnView column IDs 'size' and COLUMN. This is a
    version-sensitive UI integration, not part of the Nautilus extension API.
    """

    def __init__(self):
        self._hook = None
        self._warned = False

    def start(self):
        if self._hook is not None:
            return
        # Force class initialization so the inherited map signal is registered.
        Gtk.Widget.list_properties()
        self._hook = GObject.add_emission_hook(Gtk.Widget, "map", self._mapped)

    def stop(self):
        if self._hook is not None:
            GObject.remove_emission_hook(Gtk.Widget, "map", self._hook)
            self._hook = None

    def _mapped(self, widget):
        if isinstance(widget, Gtk.ColumnView):
            self.attach(widget)
        return True

    def attach(self, view):
        columns = view.get_columns()
        native = None
        iec = None
        for index in range(columns.get_n_items()):
            column = columns.get_item(index)
            if column.get_id() == "size":
                native = column
            elif column.get_id() == COLUMN:
                iec = column
        if iec is None:
            return False
        sorter = native.get_sorter() if native is not None else None
        if sorter is None:
            # Do not silently offer incorrect lexicographic sorting on a UI
            # version whose native column cannot be located.
            iec.set_sorter(None)
            if not self._warned:
                logging.getLogger(__name__).warning(
                    "IEC size: native size sorter unavailable; column sorting disabled"
                )
                self._warned = True
            return False
        if iec.get_sorter() != sorter:
            iec.set_sorter(sorter)
        return True


def format_size(size):
    """Use GNOME's localized formatter with explicit IEC units."""
    return GLib.format_size_full(size, GLib.FormatSizeFlags.IEC_UNITS)


class IecSizeColumn(GObject.GObject, Nautilus.ColumnProvider, Nautilus.InfoProvider):
    def __init__(self):
        super().__init__()
        self._pending = {}
        self._directories = weakref.WeakKeyDictionary()
        self._sort_bridge = NativeSizeSortBridge()

    def get_columns(self):
        self._sort_bridge.start()
        language = locale.getlocale(locale.LC_MESSAGES)[0] or ""
        chinese = language.startswith("zh")
        return [Nautilus.Column(
            name=COLUMN,
            attribute=ATTRIBUTE,
            label="大小（IEC）" if chinese else "Size (IEC)",
            description=("以 KiB、MiB、GiB 等 1024 进制单位显示文件大小"
                         if chinese else "File size in base 1024: KiB, MiB, GiB, …"),
            xalign=1.0,
        )]

    def update_file_info_full(self, provider, handle, closure, file):
        # Never perform filesystem I/O on Nautilus's UI thread. GIO also handles
        # escaped names and remote locations without converting URIs to paths.
        file.add_string_attribute(ATTRIBUTE, UNAVAILABLE)
        if file.is_gone():
            return Nautilus.OperationResult.COMPLETE
        if file.is_directory():
            self._update_directory(file)
            return Nautilus.OperationResult.COMPLETE

        cancellable = Gio.Cancellable()
        self._pending[handle] = cancellable
        file.get_location().query_info_async(
            "standard::size,standard::type",
            Gio.FileQueryInfoFlags.NONE,
            GLib.PRIORITY_DEFAULT,
            cancellable,
            self._query_finished,
            (provider, handle, closure, file, cancellable),
        )
        return Nautilus.OperationResult.IN_PROGRESS

    def _update_directory(self, file):
        # Reuse Nautilus's count, translations and count/remote-location policy.
        # Counting independently would disagree about hidden files and refreshes.
        if file not in self._directories:
            state = {"value": None}
            self._directories[file] = state
            file.connect("changed", self._directory_changed, state)
        else:
            state = self._directories[file]
        value = file.get_string_attribute("size") or UNAVAILABLE
        state["value"] = value
        file.add_string_attribute(ATTRIBUTE, value)

    def _directory_changed(self, file, *args):
        state = args[-1]
        if file.is_gone() or not file.is_directory():
            return
        value = file.get_string_attribute("size") or UNAVAILABLE
        if value != state["value"]:
            # add_string_attribute itself emits changed; update the guard first.
            state["value"] = value
            file.add_string_attribute(ATTRIBUTE, value)

    def _query_finished(self, location, result, context):
        provider, handle, closure, file, cancellable = context
        try:
            info = location.query_info_finish(result)
        except GLib.Error:
            info = None

        # A cancelled request must not publish results or invoke its closure.
        # Identity also protects a newer request if a handle is reused.
        if self._pending.get(handle) is not cancellable:
            return
        del self._pending[handle]
        if not file.is_gone() and info is not None:
            if (info.get_file_type() == Gio.FileType.REGULAR
                    and info.has_attribute("standard::size")):
                file.add_string_attribute(ATTRIBUTE, format_size(info.get_size()))
        Nautilus.info_provider_update_complete_invoke(
            closure, provider, handle, Nautilus.OperationResult.COMPLETE,
        )

    def cancel_update(self, provider, handle):
        cancellable = self._pending.pop(handle, None)
        if cancellable is not None:
            cancellable.cancel()
