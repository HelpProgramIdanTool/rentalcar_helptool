"""Run the web app and its disk-local backup scheduler under one supervisor."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def main():
    root = Path(__file__).resolve().parents[1]
    children = []
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        children.append(subprocess.Popen([
            sys.executable, '-m', 'gunicorn', 'config.wsgi:application',
            '--bind', '0.0.0.0:' + os.environ.get('PORT', '10000'), '--workers', '2',
        ], cwd=root))
        if os.environ.get('BACKUP_ENABLED') == '1':
            children.append(subprocess.Popen([sys.executable, str(root / 'scripts/render_backup.py'), '--loop'], cwd=root))
        while not stopping:
            if any(child.poll() is not None for child in children):
                raise RuntimeError('Web or backup scheduler exited; restarting service is required.')
            time.sleep(1)
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=25)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == '__main__':
    main()
