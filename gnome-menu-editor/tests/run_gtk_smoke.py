"""Start a private Broadway display and D-Bus session for the GTK smoke test."""
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time

with tempfile.TemporaryDirectory(prefix='menu-editor-gtk-') as directory:
    env = dict(os.environ, XDG_RUNTIME_DIR=directory, GDK_BACKEND='broadway',
               BROADWAY_DISPLAY=':37', GTK_A11Y='none', GSK_RENDERER='cairo')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    server = subprocess.Popen(['gtk4-broadwayd', '--address=127.0.0.1', f'--port={port}', ':37'], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 10
        while not (Path(directory) / 'broadway38.socket').exists():
            if server.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('Broadway failed to start')
            time.sleep(0.05)
        subprocess.run(['dbus-run-session', '--', '/usr/bin/python3', str(Path(__file__).with_name('smoke_gtk.py'))], env=env, check=True, timeout=30)
    finally:
        server.terminate()
        server.communicate(timeout=5)
