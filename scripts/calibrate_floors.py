#!/usr/bin/env python3
"""Interactive floor calibration walk.

Run it, then carry the phone through each location when prompted. Each step
samples the barometer for ~20 s and stores the mean pressure for that floor.
A full house (garage, basement, 1st floor, bedrooms) takes ~5 minutes.

    python3 scripts/calibrate_floors.py

Notes:
- Keep the phone on home Wi-Fi with wireless debugging active.
- Weather is stable enough during a short walk that the relative offsets are
  accurate; the self-healing anchor in floors.py tracks drift afterward.
- Re-run anytime; it updates the calibration file in place.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adb_sentinel import device, sensors  # noqa: E402

SAMPLE_SECONDS = 20
SAMPLE_INTERVAL = 2  # GMS refreshes the ring buffer ~every 2 min; resample often


def load_config():
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            return json.load(f)
    return {}


def sample_pressure(serial: str, seconds: int) -> list[float]:
    vals = []
    deadline = time.time() + seconds
    while time.time() < deadline:
        p = sensors.pressure_hpa(serial)
        if p is not None:
            vals.append(p)
        time.sleep(SAMPLE_INTERVAL)
    return vals


def main() -> int:
    cfg = load_config()
    state_file = os.path.expanduser(
        cfg.get("device", {}).get("state_file", "~/.adb-sentinel/device.state")
    )
    saved = cfg.get("device", {}).get("target", "")
    cal_path = os.path.expanduser(cfg.get("floors", {}).get("calibration_file", "data/calibration.json"))

    serial = device.find_phone(state_file, saved_target=saved or None)
    if not serial:
        print("⚠️  device unreachable — wireless debugging on? pairing done?")
        return 2
    print(f"📱 connected: {serial}\n")

    p0 = sensors.pressure_hpa(serial)
    if p0 is None:
        print("⚠️  no barometer readings yet — wait ~2 min for GMS to sample, or open an app that reads pressure.")
        return 2
    print(f"🌡️  current pressure: {p0:.2f} hPa — good, sensor is live.\n")

    from adb_sentinel.floors import FloorCalibration

    cal = FloorCalibration(cal_path)
    print(f"Existing calibration: {list(cal.floors().keys()) or 'none'}\n")

    print("Walk through your locations in any order. For each prompt:")
    print("  1. carry the phone to the location and keep it still")
    print("  2. press Enter  →  20 s of sampling  →  next location\n")

    while True:
        name = input("Location name (e.g. garage, basement, 1st_floor, bedrooms) or blank to finish: ").strip()
        if not name:
            break
        input(f"  Place phone in '{name}', then press Enter to sample 20 s...")
        vals = sample_pressure(serial, SAMPLE_SECONDS)
        if len(vals) < 3:
            print("  ⚠️  too few samples — try again.")
            continue
        mean = statistics.mean(vals)
        spread = max(vals) - min(vals)
        cal.set_floor(name, mean, len(vals))
        print(f"  ✅ {name}: {mean:.2f} hPa (n={len(vals)}, spread {spread:.2f} hPa)\n")

    print("\nSaved calibration:")
    for name, info in cal.floors().items():
        print(f"  {name}: {info['pressure']:.2f} hPa")
    print(f"\nWrote {cal_path}")
    print("Done. Run scripts/sample_once.py to see floor inference.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
