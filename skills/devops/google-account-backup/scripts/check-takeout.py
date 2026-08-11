#!/usr/bin/env python3
"""
Check Google Takeout status via Camofox browser and download archives when ready.
Run this as a cron job every 4 hours after starting a Takeout export.

Requires Camofox to be running on localhost:9377 with Google auth cookies.
"""
import json, urllib.request, time, os, sys
from datetime import datetime

BASE = 'http://localhost:9377'
BACKUP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAKEOUT_DIR = os.path.join(BACKUP_DIR, 'takeout')
os.makedirs(TAKEOUT_DIR, exist_ok=True)
STATUS_FILE = os.path.join(TAKEOUT_DIR, 'takeout_status.json')
DOWNLOAD_LOG = os.path.join(TAKEOUT_DIR, 'download_log.txt')

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    with open(DOWNLOAD_LOG, 'a') as f:
        f.write(line + '\n')

# Check Camofox is running
try:
    h = json.loads(urllib.request.urlopen(f'{BASE}/health', timeout=5).read())
    if not h.get('ok'):
        log('Camofox not healthy')
        sys.exit(0)
except Exception as e:
    log(f'Camofox unreachable: {e}')
    sys.exit(0)

# Create tab for Takeout manage page
try:
    req = urllib.request.Request(
        f'{BASE}/tabs',
        data=json.dumps({'userId': 'the operator', 'sessionKey': 'takeout-check',
                         'url': 'https://takeout.google.com/manage'}).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
    tab_id = resp.get('tabId')
    log(f'Tab created: {tab_id}')
    time.sleep(5)
except Exception as e:
    log(f'Error creating tab: {e}')
    sys.exit(1)

# Check status
try:
    snap = json.loads(urllib.request.urlopen(
        f'{BASE}/tabs/{tab_id}/snapshot?userId=the operator', timeout=30
    ).read())
    snap_text = snap.get('snapshot', '')

    if 'Export in progress' in snap_text:
        log('Takeout still processing')
        with open(STATUS_FILE, 'w') as f:
            json.dump({'status': 'processing', 'checked_at': datetime.now().isoformat()}, f)
    elif 'No completed exports' in snap_text:
        log('Takeout still processing (no completed exports yet)')
        with open(STATUS_FILE, 'w') as f:
            json.dump({'status': 'processing', 'checked_at': datetime.now().isoformat()}, f)
    elif 'Download' in snap_text:
        log('TAKEOUT ARCHIVE AVAILABLE!')
        with open(STATUS_FILE, 'w') as f:
            json.dump({'status': 'ready', 'checked_at': datetime.now().isoformat()}, f)
        # Try to find download URLs via JavaScript
        try:
            js_resp = json.loads(urllib.request.urlopen(
                urllib.request.Request(
                    f'{BASE}/tabs/{tab_id}/evaluate',
                    data=json.dumps({
                        'userId': 'the operator',
                        'expression': '''
                        (function(){
                            var links = document.querySelectorAll('a');
                            var dlLinks = [];
                            for(var i=0;i<links.length;i++){
                                var t = (links[i].textContent||'').toLowerCase();
                                if(t.indexOf('download') !== -1 && links[i].href){
                                    dlLinks.push({text:links[i].textContent.trim(), href:links[i].href});
                                }
                            }
                            return JSON.stringify(dlLinks);
                        })()
                        '''
                    }).encode(),
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                ), timeout=15).read())
            result = js_resp.get('result', '[]')
            log(f'Download links found: {result[:500]}')
        except Exception as e:
            log(f'Error extracting download URLs: {e}')
        print('ALERT: Takeout archives are ready for download!')
    else:
        log(f'Unknown state (snapshot: {len(snap_text)} chars)')
        with open(STATUS_FILE, 'w') as f:
            json.dump({'status': 'unknown', 'checked_at': datetime.now().isoformat()}, f)
except Exception as e:
    log(f'Error checking: {e}')

# Cleanup
try:
    urllib.request.urlopen(urllib.request.Request(
        f'{BASE}/tabs/{tab_id}?userId=the operator', method='DELETE'), timeout=5)
except:
    pass

log('Check complete')
