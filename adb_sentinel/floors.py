"""Floor detection from barometric pressure.

Physics: air pressure drops ~0.12 hPa per meter of altitude. US home floors
are ~2.5-3 m apart, so adjacent floors differ by ~0.3-0.4 hPa — well within
the lps22hh barometer's ~0.01 hPa resolution.

The hard problem is *weather drift*: a passing front moves absolute pressure
by 3-5 hPa/day, which is 10x a floor. Two mitigations:

1. **Delta classification** — floors are stored as pressure *ranges* captured
   during a short calibration walk (weather is stable for those minutes), and
   inference picks the nearest range. Works for hours.
2. **Self-healing anchor** — when the phone is confirmed STILL (activity
   recognition) for consecutive readings, we re-anchor that floor's reference
   pressure to the current value. This tracks weather drift over days.

Inference is deliberately conservative: if the reading is far from every
calibrated floor (> tolerance), we report "uncalibrated/uncertain" instead of
a confident wrong answer.
"""

from __future__ import annotations

import json
import os
from typing import Optional

# Pa per meter is the same as hPa per 100 m; use hPa per meter:
HPA_PER_M = 0.12  # ~1 hPa per 8.4 m
DEFAULT_TOL_HPA = 0.6  # ±5 m band around a floor's reference


class FloorCalibration:
    def __init__(self, path: str):
        self.path = path
        self.data = self._load() if os.path.exists(path) else {"floors": {}}

    def _load(self) -> dict:
        with open(self.path) as f:
            return json.load(f)

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def set_floor(self, name: str, pressure_hpa: float, sample_count: int = 1) -> None:
        self.data["floors"][name] = {
            "pressure": round(pressure_hpa, 2),
            "samples": sample_count,
        }
        self.save()

    def reanchor(self, name: str, pressure_hpa: float) -> None:
        """Track weather drift: update a floor's reference to a confirmed reading."""
        if name in self.data["floors"]:
            self.data["floors"][name]["pressure"] = round(pressure_hpa, 2)
            self.save()

    def floors(self) -> dict:
        return self.data.get("floors", {})


def infer_floor(pressure: float, cal: FloorCalibration, tol_hpa: float = DEFAULT_TOL_HPA):
    """Return (name, delta_hpa, ok) for the nearest calibrated floor.

    ``ok`` is False when the reading is outside every tolerance band.
    """
    floors = cal.floors()
    if not floors:
        return None, 0.0, False
    best_name, best_delta, best_ok = None, None, False
    for name, info in floors.items():
        ref = info.get("pressure")
        if ref is None:
            continue
        delta = pressure - ref
        ok = abs(delta) <= tol_hpa
        if best_delta is None or abs(delta) < abs(best_delta):
            best_name, best_delta, best_ok = name, delta, ok
    return best_name, best_delta, best_ok
