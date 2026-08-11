#!/usr/bin/env python3
"""
Post-rotation verification for Tor circuit rotation cron jobs.
Performs three checks in one script: xul.dll stealth patch, circuit
inspection via raw socket control protocol, and orphan process audit.

Usage:
    python ${USER_HOME}/tor-post-rotation-check.py

Output: machine-parseable lines prefixed with XUL_PATCH:, CIRCUITS:, ORPHANS:
"""

import socket, time, glob, os, subprocess

# ======== 1. xul.dll Patch Verification ========
dll = r'${USER_HOME}\TorBrowser\Browser\xul.dll'
with open(dll, 'rb') as f:
    data = f.read()
    wd = data.count(b'webdriver')
    wb = data.count(b'WEBDRIVER_BIDI')
patched = (wd == 0 and wb == 0)
print(f"XUL_PATCH:PATCHED={patched} (webdriver:{wd}, WEBDRIVER_BIDI:{wb})")

# ======== 2. Circuit Inspection via Control Port ========
cookie_files = glob.glob(
    r'${USER_HOME}\AppData\Local\Temp\torbrowser-driver-*\tor-data\control_auth_cookie'
)
cookie_files.sort(key=os.path.getmtime, reverse=True)
if not cookie_files:
    # Probe control port with PROTOCOLINFO even without cookie
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(8)
        s.connect(('127.0.0.1', 9251))
        s.sendall(b'PROTOCOLINFO\r\n')
        time.sleep(0.5)
        resp = s.recv(4096).decode(errors='replace')
        if '250-PROTOCOLINFO' in resp:
            auth = 'unknown'
            version = 'unknown'
            for line in resp.split('\r\n'):
                if 'AUTH METHODS=' in line:
                    auth = line.split('AUTH METHODS=')[1].split('\r')[0]
                if 'VERSION Tor=' in line:
                    version = line.split('VERSION Tor=')[1].split('\r')[0].strip('"')
            print(f"CIRCUITS:NO_COOKIE_PORT_ALIVE (auth={auth}, version={version})")
        else:
            print(f"CIRCUITS:NO_COOKIE_PORT_UNRESPONSIVE:{resp[:100]}")
    except socket.timeout:
        print("CIRCUITS:NO_COOKIE_PORT_TIMEOUT")
    except ConnectionRefusedError:
        print("CIRCUITS:NO_COOKIE_PORT_REFUSED")
    except Exception as e:
        print(f"CIRCUITS:NO_COOKIE_PORT_ERROR:{e}")
    else:
        s.close()
else:
    cookie_path = cookie_files[0]
    with open(cookie_path, 'rb') as f:
        cookie_hex = f.read().hex()

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(8)
        s.connect(('127.0.0.1', 9251))
        s.sendall(b'PROTOCOLINFO\r\n')
        time.sleep(0.3)
        s.recv(4096)
        s.sendall(f'AUTHENTICATE {cookie_hex}\r\n'.encode())
        time.sleep(0.3)
        resp = s.recv(4096)
        if b'250' not in resp:
            print(f"CIRCUITS:AUTH_FAIL:{resp.decode(errors='replace')[:100]}")
            s.close()
        else:
            s.sendall(b'GETINFO circuit-status\r\n')
            time.sleep(0.5)
            resp = s.recv(16384).decode(errors='replace')
            s.close()

            lines = resp.split('\r\n')
            built_circuits = [l for l in lines if ' BUILT ' in l and 'ONEHOP_TUNNEL' not in l]
            total_built = [l for l in lines if ' BUILT ' in l]

            print(f"CIRCUITS:GENERAL_PURPOSE_BUILT={len(built_circuits)}")
            print(f"CIRCUITS:TOTAL_BUILT={len(total_built)}")
            for l in built_circuits:
                print(f"CIRCUIT_PATH:{l[:200]}")
    except socket.timeout:
        print("CIRCUITS:CONTROL_PORT_TIMEOUT")
    except ConnectionRefusedError:
        print("CIRCUITS:CONTROL_PORT_REFUSED")
    except Exception as e:
        print(f"CIRCUITS:ERROR:{e}")
    finally:
        try:
            s.close()
        except:
            pass

# ======== 3. Orphan Firefox/Geckodriver Check (via PowerShell) ========
try:
    result = subprocess.run(
        ['powershell.exe', '-Command',
         '@(Get-Process firefox -ErrorAction SilentlyContinue).Count; '
         '@(Get-Process geckodriver -ErrorAction SilentlyContinue).Count'],
        capture_output=True, text=True, timeout=15
    )
    counts = result.stdout.strip().split('\n')
    ff_count = int(counts[0]) if len(counts) > 0 else 0
    gk_count = int(counts[1]) if len(counts) > 1 else 0
    print(f"ORPHANS:FIREFOX={ff_count},GECKODRIVER={gk_count}")
except Exception as e:
    print(f"ORPHANS:ERROR:{e}")

print("CHECK_COMPLETE")
