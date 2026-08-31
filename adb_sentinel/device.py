"""ADB device discovery and connection management (wireless, no root).

Handles the two real-world annoyances of wireless ADB:
  1. The adb server restarts and forgets the connection -> reconnect by target.
  2. The phone's DHCP lease can change -> subnet scan for the wireless-debugging
     port (5555) and retry the saved port number on the new IP.

A connection is "authorized" when `adb devices` lists it in `device` state
(not `unauthorized` / `offline`). One-time pairing still requires the user to
accept the pairing code dialog on the phone; after that the host key is trusted.
"""

from __future__ import annotations

import concurrent.futures
import os
import re
import socket
import subprocess
from typing import Optional

ADB_WIRELESS_PORT = 5555


def adb(args: list[str], serial: Optional[str] = None, timeout: int = 25) -> str:
    """Run an adb command; returns stdout ("" on any failure)."""
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout
    except Exception:
        return ""


def devices() -> str:
    return adb(["devices"])


def authorized_serial() -> Optional[str]:
    """First serial currently in `device` state, or None."""
    for line in devices().splitlines():
        m = re.match(r"(\S+)\s+(\S+)", line.strip())
        if m and m.group(2) == "device":
            return m.group(1)
    return None


def _local_ip() -> Optional[str]:
    for iface in ("en0", "en1"):
        try:
            r = subprocess.run(
                ["ipconfig", "getifaddr", iface], capture_output=True, text=True, timeout=5
            )
            ip = r.stdout.strip()
            if ip:
                return ip
        except Exception:
            pass
    return None


def _scan_port_on_subnet(port: int, timeout_s: float = 0.3, workers: int = 64):
    """Yield IPs on the local /24 with `port` open."""
    ip = _local_ip()
    if not ip:
        return
    base = ".".join(ip.split(".")[:3])

    def check(i: int) -> Optional[str]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout_s)
        try:
            s.connect((f"{base}.{i}", port))
            return f"{base}.{i}"
        except Exception:
            return None
        finally:
            s.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for hit in ex.map(check, range(1, 255)):
            if hit:
                yield hit


def find_phone(state_file: str, saved_target: Optional[str] = None) -> Optional[str]:
    """Return an authorized serial, trying, in order:

    1. the saved ``ip:port`` target (works across adb server restarts),
    2. the saved port number on a fresh IP found via subnet scan (DHCP change).

    Updates ``state_file`` with the working serial. Returns None if unreachable.
    """
    candidates: list[str] = []
    if saved_target:
        candidates.append(saved_target)
    try:
        if os.path.exists(state_file):
            candidates.append(open(state_file).read().strip())
    except Exception:
        pass

    saved_port = None
    for c in candidates:
        if ":" in c:
            saved_port = c.rsplit(":", 1)[1]
            break

    # fresh IP guess: scan for the wireless-debugging port
    for ip in _scan_port_on_subnet(ADB_WIRELESS_PORT):
        if saved_port:
            candidates.append(f"{ip}:{saved_port}")

    for target in dict.fromkeys(candidates):  # dedupe, keep order
        adb(["connect", target], timeout=15)
        serial = authorized_serial()
        if serial:
            try:
                os.makedirs(os.path.dirname(state_file), exist_ok=True)
                open(state_file, "w").write(serial)
            except Exception:
                pass
            return serial
    return None
