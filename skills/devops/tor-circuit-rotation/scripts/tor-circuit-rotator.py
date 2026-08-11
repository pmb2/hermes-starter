#!/usr/bin/env python3
"""
tor-circuit-rotator.py — Standalone Tor circuit rotation via stem control protocol.

Fallback for when the tor-browser-mcp MCP server is not running/connected in the
current Hermes session. Connects directly to the Tor control port (default 9251),
sends NEWNYM, optionally closes existing circuits, and verifies the exit node changed.

Usage:
    python tor-circuit-rotator.py [--port PORT] [--wait SECONDS] [--close] [--check]

Options:
    --port PORT     Tor control port (default: 9251)
    --wait SECONDS  Seconds to wait after NEWNYM for circuit rebuild (default: 30)
    --close         Explicitly close all BUILT circuits before NEWNYM (stronger rotation)
    --check         Only check status, don't rotate
"""

import stem.control
import stem
import argparse
import time
import sys


def get_tor_status(ctrl):
    """Read tor daemon state."""
    info = {}
    for key in ("version", "uptime", "traffic/read", "traffic/written"):
        try:
            info[key] = ctrl.get_info(key)
        except Exception:
            info[key] = "N/A"
    circuits = ctrl.get_circuits()
    built = [c for c in circuits if c.status == "BUILT"]
    pending = [c for c in circuits if c.status != "BUILT"]
    info["circuits_total"] = len(circuits)
    info["circuits_built"] = len(built)
    info["circuits_pending"] = len(pending)
    info["circuits"] = built
    return info


def format_circuit_path(circ):
    """Format a circuit's relay path for display."""
    parts = []
    for hop in circ.path:
        nick = hop[1] if len(hop) > 1 and hop[1] else hop[0][:10]
        parts.append(nick)
    return " -> ".join(parts)


def print_status(ctrl, label="Status"):
    """Print formatted tor status with circuit listing."""
    info = get_tor_status(ctrl)
    print(f"=== {label} ===")
    print(f"Tor {info['version']}  |  Uptime: {info['uptime']}s")
    print(f"Traffic: {info['traffic/read']}B read / {info['traffic/written']}B written")
    print(f"Circuits: {info['circuits_built']} BUILT, {info['circuits_pending']} pending "
          f"({info['circuits_total']} total)")

    # Show 3-hop circuits with exit info
    three_hop = [c for c in info["circuits"] if len(c.path) >= 3]
    for i, circ in enumerate(three_hop[:6], 1):
        print(f"  Circuit {circ.id}: {format_circuit_path(circ)}")

    if three_hop:
        exit_fp = three_hop[0].path[-1][0]
        exit_nick = three_hop[0].path[-1][1] if len(three_hop[0].path[-1]) > 1 else exit_fp[:10]
        print(f"\nPrimary exit: {exit_nick} ({exit_fp[:10]}...)")
        return exit_fp, exit_nick

    if info["circuits_built"] == 0:
        print("\nNo BUILT circuits yet.")
    return None, None


def rotate_identity(ctrl, close_existing=False, wait=30):
    """
    Rotate Tor identity by sending NEWNYM.
    Optionally close existing circuits first for stronger rotation.
    Returns (changed, old_exit, new_exit).
    """
    # Before snapshot
    old_fp, old_nick = print_status(ctrl, "Before Rotation")
    rotation_start = time.time()

    # Optionally close existing circuits
    if close_existing:
        circuits = ctrl.get_circuits()
        closed = 0
        for c in circuits:
            if c.status == "BUILT":
                try:
                    ctrl.close_circuit(c.id)
                    closed += 1
                except Exception:
                    pass
        print(f"\nClosed {closed} existing circuits.")

    # Send NEWNYM
    print("\nSending NEWNYM signal...")
    ctrl.signal(stem.Signal.NEWNYM)
    print(f"NEWNYM sent. Waiting {wait}s for circuits to rebuild...")
    time.sleep(wait)

    # After snapshot
    new_fp, new_nick = print_status(ctrl, "After Rotation")
    elapsed = time.time() - rotation_start

    # Comparison
    print(f"\n--- Rotation Result ({elapsed:.0f}s) ---")
    if old_fp and new_fp:
        changed = old_fp != new_fp
        if changed:
            print(f"✅ Exit CHANGED: {old_nick} -> {new_nick}")
        else:
            print(f"⚠️  Exit UNCHANGED: still {old_nick}")
            print("   (Try --close flag for stronger rotation)")
        return changed, (old_fp, old_nick), (new_fp, new_nick)
    else:
        print("⚠️  Could not compare exits (insufficient circuit data)")
        return None, (old_fp, old_nick), (new_fp, new_nick)


def main():
    parser = argparse.ArgumentParser(
        description="Tor circuit rotation via stem control protocol"
    )
    parser.add_argument("--port", type=int, default=9251,
                        help="Tor control port (default: 9251)")
    parser.add_argument("--wait", type=int, default=30,
                        help="Seconds to wait after NEWNYM (default: 30)")
    parser.add_argument("--close", action="store_true",
                        help="Close all BUILT circuits before NEWNYM")
    parser.add_argument("--check", action="store_true",
                        help="Check status only, don't rotate")
    args = parser.parse_args()

    try:
        with stem.control.Controller.from_port(port=args.port) as ctrl:
            ctrl.authenticate()

            if args.check:
                print_status(ctrl, "Tor Status")
            else:
                rotate_identity(ctrl,
                                close_existing=args.close,
                                wait=args.wait)

    except stem.SocketError as e:
        print(f"❌ Cannot connect to Tor control port {args.port}: {e}")
        print("   Is tor.exe running? Check: netstat -ano | grep LISTENING | grep <port>")
        sys.exit(1)
    except stem.connection.AuthenticationFailure as e:
        print(f"❌ Authentication failed on port {args.port}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
