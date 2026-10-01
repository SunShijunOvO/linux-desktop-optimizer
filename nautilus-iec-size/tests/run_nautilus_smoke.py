#!/usr/bin/env python3
"""Exercise the installed Nautilus/GTK in a temporary, private desktop session."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


def main():
    tests = Path(__file__).resolve().parent
    for command in ("gtk4-broadwayd", "dbus-run-session", "nautilus"):
        if shutil.which(command) is None:
            raise SystemExit(f"Required command missing: {command}")
    with tempfile.TemporaryDirectory(prefix="ldo-nautilus-test-") as temporary:
        root = Path(temporary)
        env = os.environ.copy()
        for variable, directory in (("XDG_RUNTIME_DIR", "runtime"), ("XDG_DATA_HOME", "data"),
                                    ("XDG_CONFIG_HOME", "config"), ("XDG_CACHE_HOME", "cache")):
            path = root / directory
            path.mkdir(mode=0o700)
            env[variable] = str(path)
        env.update(GDK_BACKEND="broadway", BROADWAY_DISPLAY=":1", GSETTINGS_BACKEND="memory",
                   LDO_SMOKE_ROOT=str(root), LC_ALL="C.UTF-8", GIO_USE_VFS="local",
                   GIO_USE_VOLUME_MONITOR="unix")
        extensions = root / "data/nautilus-python/extensions"
        extensions.mkdir(parents=True)
        shutil.copy2(tests.parent / "ldo_iec_size.py", extensions)
        shutil.copy2(tests / "nautilus_probe.py", extensions)
        files = root / "files"
        (files / "empty").mkdir(parents=True)
        (files / "twelve").mkdir()
        (files / "dir-link").symlink_to(files / "twelve")
        for i in range(12):
            (files / "twelve" / str(i)).touch()
        for name, size in (("ten", 10), ("kib", 1024), ("same", 1024),
                           ("mib", 1024**2), ("gib", 1024**3)):
            with (files / name).open("wb") as stream:
                stream.truncate(size)
        with (root / "broadway.log").open("w+") as log:
            display = subprocess.Popen(["gtk4-broadwayd", ":1", "-a", "127.0.0.1", "-p", "0"],
                                       env=env, stdout=log, stderr=log)
            try:
                for _ in range(100):
                    if (root / "runtime/broadway2.socket").exists():
                        break
                    if display.poll() is not None:
                        log.seek(0)
                        raise RuntimeError(log.read())
                    time.sleep(0.05)
                run = subprocess.run(["dbus-run-session", "--", "nautilus", "--new-window", str(files)],
                                     env=env, capture_output=True, text=True, timeout=30)
                result = root / "result.json"
                if not result.exists():
                    raise RuntimeError(f"Nautilus probe failed ({run.returncode}):\n{run.stdout}\n{run.stderr}")
                report = json.loads(result.read_text())
                print(json.dumps(report, indent=2))
                if not report.get("ok"):
                    raise SystemExit(1)
            finally:
                display.terminate()
                display.wait(timeout=5)


if __name__ == "__main__":
    main()
