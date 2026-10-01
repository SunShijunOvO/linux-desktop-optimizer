"""Nautilus list-view column using IEC (base 1024) file sizes."""

import locale

import gi

gi.require_version("Nautilus", "4.1")
from gi.repository import Gio, GLib, GObject, Nautilus


COLUMN = "Ldo::IecSize"
ATTRIBUTE = "ldo_iec_size"
UNAVAILABLE = "—"


def format_size(size):
    """Use GNOME's localized formatter with explicit IEC units."""
    return GLib.format_size_full(size, GLib.FormatSizeFlags.IEC_UNITS)


class IecSizeColumn(GObject.GObject, Nautilus.ColumnProvider, Nautilus.InfoProvider):
    def __init__(self):
        super().__init__()
        self._pending = {}

    def get_columns(self):
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
        if file.is_gone() or file.is_directory():
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
