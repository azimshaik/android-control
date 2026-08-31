#!/usr/bin/env python3
"""One-shot telemetry sample. Usage:

    python3 scripts/sample_once.py [--json]

Prints battery, location, barometric pressure, activity, and (if calibrated)
the inferred floor. Exit code 0 even on partial data; 2 if the phone is
unreachable.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adb_sentinel import device, floors, sensors  # noqa: E402


def load_config():
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            return json.load(f)
    return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    state_file = os.path.expanduser(
        cfg.get("device", {}).get("state_file", "~/.adb-sentinel/device.state")
    )
    saved = cfg.get("device", {}).get("target", "")

    serial = device.find_phone(state_file, saved_target=saved or None)
    if not serial:
        print("⚠️  device unreachable — is wireless debugging on? (one-time pairing required)")
        return 2

    out = {
        "serial": serial,
        "battery": sensors.battery(serial),
        "location": sensors.location(serial),
        "pressure_hpa": sensors.pressure_hpa(serial),
        "activity": sensors.activity(serial),
        "wifi_rssi": sensors.wifi_connected_rssi(serial),
    }

    cal_path = os.path.expanduser(cfg.get("floors", {}).get("calibration_file", "data/calibration.json"))
    cal = floors.FloorCalibration(cal_path)
    if out["pressure_hpa"] is not None:
        name, delta, ok = floors.infer_floor(out["pressure_hpa"], cal)
        out["floor"] = {"name": name, "delta_hpa": round(delta, 2), "confident": ok}

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        b = out["battery"]
        print(f"📱 {serial}")
        print(f"🔋 {b['level']}% · {b['temp_c']}°C · {'charging' if b['charging'] else 'not charging'}")
        loc = out["location"]
        if loc:
            print(f"📍 {loc['lat']:.5f},{loc['lon']:.5f} · {loc['provider']} ±{loc['acc_m']:.0f}m, {loc['age_min']}m old")
        if out["pressure_hpa"]:
            f = out["floor"]
            line = f"🌡️ {out['pressure_hpa']:.2f} hPa"
            if f and f["name"]:
                line += f" → floor: {f['name']} (Δ{f['delta_hpa']:+.2f} hPa, {'confident' if f['confident'] else 'uncertain'})"
            else:
                line += " → uncalibrated"
            print(line)
        if out["activity"]:
            a = out["activity"]
            print(f"🚶 {a['type']} ({a['confidence']}%)")
        if out["wifi_rssi"] is not None:
            print(f"📶 Wi-Fi RSSI {out['wifi_rssi']} dBm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
