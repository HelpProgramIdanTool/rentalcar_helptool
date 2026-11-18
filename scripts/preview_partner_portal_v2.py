"""Serve the isolated, browser-based partner portal design and presentation.

No database, actual users, supplier rates, email transport or bookings are used.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8778)
    args = parser.parse_args()
    folder = Path(__file__).resolve().parents[1] / 'prototype' / 'partner-portal-v2'
    handler = partial(SimpleHTTPRequestHandler, directory=str(folder))
    # An old design preview may still be running; do not silently share its port.
    class PreviewServer(ThreadingHTTPServer):
        allow_reuse_address = False
    server = PreviewServer(('127.0.0.1', args.port), handler)
    print(f'Design: http://127.0.0.1:{args.port}/', flush=True)
    print(f'Presentation: http://127.0.0.1:{args.port}/?presentation=1', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
