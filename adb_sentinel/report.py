"""Message formatting for the Telegram/CLI status report."""

from __future__ import annotations

from datetime import datetime

from . import sensors


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    R = 6371.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


def fmt_age(minutes: int) -> str:
    if minutes >= 1440:
        return f"{minutes // 1440}d {(minutes % 1440) // 60}h"
    if minutes >= 60:
        return f"{minutes // 60}h{minutes % 60}m"
    return f"{minutes}m"


def build_report(serial: str, home_lat: float, home_lon: float) -> str:
    lines = [f"📱 {serial} · {datetime.now().strftime('%a %H:%M')}"]

    bat = sensors.battery(serial)
    if bat["level"] is not None:
        state = "charging" if bat["charging"] else "not charging"
        lines.append(f"🔋 {bat['level']}% · {bat['temp_c']}°C · {state}")

    loc = sensors.location(serial)
    if loc:
        km = haversine_km(loc["lat"], loc["lon"], home_lat, home_lon)
        place = "AT HOME" if km < 1.0 else ("NEAR HOME" if km < 3.0 else "AWAY FROM HOME")
        if km >= 1.0:
            place += f" ({km:.1f} km)"
        lines.append(
            f"📍 {loc['lat']:.5f},{loc['lon']:.5f} · {place} · "
            f"{loc['provider']}, ±{loc['acc_m']:.0f}m, fix {fmt_age(loc['age_min'])} old"
        )
    else:
        lines.append("📍 no location fix")

    act = sensors.activity(serial)
    if act:
        lines.append(f"🚶 {act['type']} ({act['confidence']}%)")

    return "\n".join(lines)
