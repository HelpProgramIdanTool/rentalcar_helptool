"""Local design with a read-only calculator using an isolated SQLite copy."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import json
import sys
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8782)
    args = parser.parse_args()
    folder = Path(__file__).resolve().parents[1] / 'prototype' / 'partner-portal-v2'
    from partner_design_prices import initialise, calculate
    source_updated=initialise()
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,directory=str(folder),**kwargs)
        def json_response(self,code,data):
            body=json.dumps(data,ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def do_POST(self):
            if self.path!='/api/prices':return self.json_response(404,{'error':'Not found'})
            origin=self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{args.port}',f'http://localhost:{args.port}'):
                return self.json_response(403,{'error':'Local same-origin requests only'})
            if self.headers.get_content_type()!='application/json':
                return self.json_response(415,{'error':'JSON required'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=16384:raise ValueError('Invalid request size')
                data=json.loads(self.rfile.read(length))
                if not isinstance(data,dict):raise ValueError('Invalid data')
                result=calculate(data)
                result['source_updated']=source_updated
                self.json_response(200,result)
            except (ValueError,KeyError) as error:
                self.json_response(400,{'error':str(error)})
            except Exception as error:
                # Do not disclose DB/customer details or tracebacks to the page.
                self.json_response(422,{'error':'המסלול דורש בדיקה אישית של עידן או שלא נמצא מחיר מלא.'})
            finally:
                from django.db import connections
                connections.close_all()
    # An old design preview may still be running; do not silently share its port.
    class PreviewServer(ThreadingHTTPServer):
        allow_reuse_address = False
        request_queue_size = 64
    server = PreviewServer(('127.0.0.1', args.port), Handler)
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
