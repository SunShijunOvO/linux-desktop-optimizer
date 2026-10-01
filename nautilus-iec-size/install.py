#!/usr/bin/env python3
"""Install/remove only this extension in a user's XDG data directory."""

import argparse
import os
from pathlib import Path
import tempfile


FILENAME = "ldo_iec_size.py"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "uninstall"))
    parser.add_argument("--data-home", type=Path,
                        help="override XDG_DATA_HOME (also useful for staging)")
    args = parser.parse_args()
    data_home = args.data_home or Path(
        os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share"
    )
    if not data_home.is_absolute():
        parser.error("data directory must be an absolute path")
    destination = data_home / "nautilus-python/extensions" / FILENAME

    if args.action == "uninstall":
        destination.unlink(missing_ok=True)
        print(f"Removed: {destination}")
    else:
        # Preflight before changing any files; use the system Python interpreter.
        try:
            import gi
            gi.require_version("Nautilus", "4.1")
            gi.require_version("Gtk", "4.0")
            from gi.repository import Nautilus  # noqa: F401
            from gi.repository import Gtk
            if not hasattr(Gtk.ColumnViewColumn, "get_id"):
                raise ValueError("GTK ColumnViewColumn.get_id is required for native sorting")
        except (ImportError, ValueError) as error:
            parser.error(f"Nautilus 4.1 and compatible GTK 4 GI bindings required: {error}")
        source = Path(__file__).resolve().with_name(FILENAME)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination.parent,
                                             prefix=".ldo-iec-", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(source.read_bytes())
            temporary.chmod(0o644)
            temporary.replace(destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        print(f"Installed: {destination}")
    print("Restart Nautilus when file operations have finished: nautilus -q")


if __name__ == "__main__":
    main()
