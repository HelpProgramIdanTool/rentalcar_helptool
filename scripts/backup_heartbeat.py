"""Signal only a completed, verified backup to independent monitoring."""
import os
import re
import time
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def heartbeat_success():
    url = os.environ.get('BACKUP_HEARTBEAT_URL', '').strip()
    if not url:
        return False
    if not re.fullmatch(r'https://hc-ping\.com/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', url):
        print('BACKUP MONITOR NOT NOTIFIED: invalid heartbeat URL configuration.', flush=True)
        return False
    for attempt in range(3):
        try:
            # No logs, credentials, record counts or customer information are sent.
            request = Request(url, data=b'', method='POST', headers={'User-Agent': 'RentalCar-Backup/1.0'})
            with build_opener(NoRedirect()).open(request, timeout=10) as response:
                if response.status != 200:
                    raise ValueError('Unexpected monitor response')
            print('BACKUP MONITOR: verified backup success reported.', flush=True)
            return True
        except Exception:
            if attempt < 2:
                time.sleep(1)
    # Monitoring failure must not change the result of an already verified backup.
    print('BACKUP MONITOR NOT NOTIFIED: delivery failed; external monitor may alert.', flush=True)
    return False
