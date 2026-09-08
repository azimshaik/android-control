#!/usr/bin/env python3
"""Deployed cron watcher (no_agent mode): battery + location + floor report.

This is the script referenced by the Hermes cron job "S23 status check"
(every 4 h). It prints one short report to stdout, which the cron scheduler
delivers verbatim to Telegram. Exit 0 always (a readable message is printed
even when the phone is unreachable); non-zero would raise a scheduler alert.

State/history defaults live outside the repo (~/.adb-sentinel/) so no
personal data is ever committed. Override via config.json (see repo).
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from adb_sentinel import device, floors, sensors  # noqa: E402
from adb_sentinel.report import build_report, haversine_km  # noqa: E402


def load_config():
    cfg_path = os.path.join(PROJECT_DIR, "config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            return json.load(f)
    return {}


def main() -> int:
    cfg = load_config()
    state_file = os.path.expanduser(
        cfg.get("device", {}).get("state_file", "~/.adb-sentinel/device.state")
    )
    hist_file = os.path.expanduser(
        cfg.get("history", {}).get("csv", "~/.adb-sentinel/history.csv")
    )
    saved = cfg.get("device", {}).get("target", "")
    home_lat = float(cfg.get("home", {}).get("lat", 0.0))
    home_lon = float(cfg.get("home", {}).get("lon", 0.0))

    serial = device.find_phone(state_file, saved_target=saved or None)
    if not serial:
        print(
            "⚠️  S23 unreachable — wireless debugging likely off or the phone rebooted.\n"
            "Re-enable it (Settings → Developer options → Wireless debugging) or plug in via USB."
        )
        return 0

    report = build_report(serial, home_lat, home_lon)

    # floor inference + self-heal anchor (weather drift compensation)
    cal_path = os.path.expanduser(cfg.get("floors", {}).get("calibration_file", "data/calibration.json"))
    cal = floors.FloorCalibration(cal_path)
    p = sensors.pressure_hpa(serial)
    act = sensors.activity(serial)
    if p is not None:
        name, delta, ok = floors.infer_floor(p, cal)
        if name:
            report += f"\n🏠 floor: {name} (Δ{delta:+.2f} hPa, {'confident' if ok else 'uncertain'})"
            # self-heal: phone confirmed still + reading within band -> re-anchor
            if ok and act and act["type"] == "STILL" and act["confidence"] >= 90:
                cal.reanchor(name, p)
        else:
            report += f"\n🏠 floor: uncalibrated ({p:.2f} hPa)"

    print(report)

    # append history
    try:
        loc = sensors.location(serial)
        os.makedirs(os.path.dirname(hist_file), exist_ok=True)
        with open(hist_file, "a", newline="") as f:
            row = [datetime.now(timezone.utc).isoformat()]
            b = sensors.battery(serial)
            row += [b.get("level"), b.get("temp_c")]
            if loc:
                row += [f"{loc['lat']:.6f}", f"{loc['lon']:.6f}", loc["age_min"]]
            else:
                row += ["", "", ""]
            row += [p, name if name else ""]
            csv.writer(f).writerow(row)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
