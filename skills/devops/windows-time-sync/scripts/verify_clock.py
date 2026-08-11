#!/usr/bin/env python3
"""
Direct NTP clock verification — ground truth for Windows time sync checks.
Queries pool.ntp.org and time.nist.gov via UDP 123 and compares against
the local system clock. HTTP time APIs are NOT reliable.

Usage:
    python verify_clock.py
    python verify_clock.py pool.ntp.org time.microsoft.com
"""
import socket, struct, time, datetime, sys

NTP_EPOCH = 2208988800

def ntp_time(host, timeout=5.0):
    try:
        req = b'\x1b' + 47 * b'\x00'
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        s.sendto(req, (host, 123))
        data, _ = s.recvfrom(512)
        s.close()
        secs, fracs = struct.unpack('!2I', data[16:24])
        return secs - NTP_EPOCH + fracs / (2**32)
    except Exception as e:
        print(f"  {host}: ERROR ({e})")
        return None

def main():
    hosts = sys.argv[1:] if len(sys.argv) > 1 else ['pool.ntp.org', 'time.nist.gov']
    local = time.time()
    print(f"Local: {datetime.datetime.fromtimestamp(local).strftime('%Y-%m-%d %H:%M:%S %Z')}\n")
    all_ok = True
    for h in hosts:
        nt = ntp_time(h)
        if nt is not None:
            diff = nt - local
            ok = abs(diff) < 2.0
            if not ok: all_ok = False
            print(f"  {h}: diff {diff:+.1f}s {'OK' if ok else 'SKEWED'}")
        else:
            all_ok = False
    print(f"\n{'SYNCED' if all_ok else 'DRIFT DETECTED'}")
    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())