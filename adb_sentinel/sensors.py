"""Sensor and system reads over ADB: battery, location, barometer, activity.

Everything here is read-only (dumpsys / settings get). No input injection,
no app launches, no permissions granted. The only "active" dependency is
Google Play Services' fused location provider, which already samples the
barometer in short bursts (~2 s every ~2 min) — we simply read the values
it leaves in the sensorservice ring buffer.
"""

from __future__ import annotations

import re
from typing import Optional

from .device import adb

PRESSURE_SENSOR_NAME = "lps22hh Pressure Sensor Non-wakeup"


def battery(serial: str) -> dict:
    """level %, temperature C, charging bool."""
    out = adb(["shell", "dumpsys", "battery"], serial=serial)
    lvl = re.search(r"level:\s*(\d+)", out)
    tmp = re.search(r"temperature:\s*(\d+)", out)
    status = re.search(r"status:\s*(\d+)", out)
    return {
        "level": int(lvl.group(1)) if lvl else None,
        "temp_c": round(int(tmp.group(1)) / 10, 1) if tmp else None,
        "charging": status is not None and status.group(1) in ("2", "5"),
    }


def location(serial: str) -> Optional[dict]:
    """Most recent last-known fix: provider, lat, lon, acc_m, age_min.

    Parses the ``last location=Location[...]`` cache lines from dumpsys
    location. Age comes from the ``et=`` field (elapsed time since fix).
    """
    out = adb(["shell", "dumpsys", "location"], serial=serial)
    best = None
    for line in out.splitlines():
        m = re.search(
            r"last location=Location\[(\w+)\s+([\d.]+),([-\d.]+)\s+hAcc=([\d.]+)(.*?)\]",
            line,
        )
        if not m:
            continue
        prov, lat, lon, acc, rest = m.groups()
        age = _parse_age(rest)
        if age is None:
            continue
        if best is None or age < best["age_min"]:
            best = {
                "provider": prov,
                "lat": float(lat),
                "lon": float(lon),
                "acc_m": float(acc),
                "age_min": age,
            }
    return best


def _parse_age(et_str: str) -> Optional[int]:
    m = re.search(r"et=\+?(\d+)d(\d+)h(\d+)m", et_str or "")
    if not m:
        return None
    return int(m.group(1)) * 1440 + int(m.group(2)) * 60 + int(m.group(3))


def pressure_hpa(serial: str) -> Optional[float]:
    """Latest barometer reading (hPa) from the sensorservice ring buffer.

    GMS samples the barometer in short bursts every ~2 min; the values are
    cached in the ``last N events`` ring buffer. We take the most recent
    numbered event. Returns None if the sensor is absent or never sampled.
    """
    out = adb(["shell", "dumpsys", "sensorservice"], serial=serial)
    # find the ring-buffer section for the pressure sensor, bounded by the
    # next sensor's "last N events" header so we don't read other sensors
    idx = out.find(PRESSURE_SENSOR_NAME + ": last")
    if idx == -1:
        return None
    end = out.find(": last", idx + len(PRESSURE_SENSOR_NAME) + 1)
    section = out[idx : end if end != -1 else idx + 20000]
    values = []
    for m in re.finditer(r"wall=([\d: .-]+)\)\s*([\d.]+),\s*0\.0", section):
        v = float(m.group(2))
        if 800.0 <= v <= 1100.0:  # sane barometric range; skips 0.0 padding
            values.append(v)
    return values[-1] if values else None


def activity(serial: str) -> Optional[dict]:
    """Last detected activity from GMS: type + confidence + age_min."""
    out = adb(
        ["shell", "dumpsys", "activity", "service", "com.google.android.location"],
        serial=serial,
        timeout=40,
    )
    m = re.search(r"last ar: DetectedActivity \[type=(\w+), confidence=(\d+)\] \((\d+)", out)
    if not m:
        return None
    return {
        "type": m.group(1),
        "confidence": int(m.group(2)),
        "age_s": int(m.group(3)),
    }


def wifi_connected_rssi(serial: str) -> Optional[int]:
    """RSSI (dBm) of the network the phone is currently connected to."""
    out = adb(["shell", "dumpsys", "wifi"], serial=serial)
    m = re.search(r"mWifiInfo.*?RSSI:\s*(-?\d+)", out, re.S)
    if m:
        return int(m.group(1))
    m = re.search(r"RSSI:\s*(-?\d+)", out)
    return int(m.group(1)) if m else None
