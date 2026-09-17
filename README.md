# adb-sentinel

Read-only telemetry from an Android phone over **wireless ADB** — no root, no
app installs, no Google account, no data leaving your machine.

Everything is read from the phone's existing `dumpsys` interfaces: battery
(including wear/health), per-component temperatures, GPS/network/fused
location, **barometric floor detection**, Google's activity recognition, and
Wi-Fi signal. It is designed to run headless on a cron timer and report to
Telegram/anywhere a script can print.

```text
📱 192.168.1.50:5555        ← your device's wireless-debugging target
🔋 87% · 31.2°C · charging
📍 40.7128,-74.0060 · fused ±20m · fix 2h old   (example output)
🌡️ 990.45 hPa → floor: 1st_floor (Δ+0.00 hPa)
🚶 STILL (100%)
📶 Wi-Fi RSSI -17 dBm
```

## Why this exists

Android devices are *designed* to be controlled over ADB — that's how
developers debug them. The interesting part is that after a **one-time
wireless pairing** (Settings → Developer options → Wireless debugging), you
have the same interface remotely, forever. That unlocks genuinely useful
things for a device you own:

- **Battery health over time** — level, temperature, and Samsung's ASOC wear
  figure, logged every few hours to spot degradation.
- **Floor-level location** — the phone's barometer (lps22hh) is
  sampled in short bursts by Google Play Services every ~2 minutes; the values
  sit in the sensorservice ring buffer, free to read. ~0.12 hPa per meter ⇒
  adjacent floors (~3 m) are easy to tell apart.
- **"Is it home?"** — GPS/network fix + distance from home point, labeled
  AT HOME / NEAR HOME / AWAY.
- **Movement context** — Google's activity recognition (STILL/WALKING/
  IN_VEHICLE) without using any API key.
- **Room detection (roadmap)** — Wi-Fi RSSI fingerprints per room.

## Requirements

- macOS or Linux with `adb` (Android platform-tools)
- Python 3.9+ (stdlib only — no pip installs)
- An Android phone with **Developer options → Wireless debugging** enabled
- One-time pairing: run `adb pair <ip>:<pair_port>` and enter the 6-digit code
  shown on the phone (or accept the USB-debugging prompt over USB once)

## Quick start

```bash
git clone <this repo> && cd adb-sentinel
cp config.example.json config.json   # then edit: home coords, saved target

# discover/connect (saved target → subnet scan fallback) and sample once
python3 scripts/sample_once.py

# interactive floor calibration (~5 min walk around the house)
python3 scripts/calibrate_floors.py

# full report (battery + location + floor + activity)
python3 scripts/report.py
```

`config.json` is gitignored — home coordinates and device targets stay local.

## How a query flows

```
You (Telegram, anywhere) → Hermes (your machine) → adb-sentinel → your phone (wireless ADB)
```

Ask "what's the battery?" from Telegram and watch it travel end to end —
[full annotated sequence diagram](docs/QUERY_FLOW.md).

## How floor detection works

Air pressure drops ~0.12 hPa per meter of altitude; US home floors are
~2.5–3 m apart, so floors differ by ~0.3–0.4 hPa, far above the barometer's
~0.01 hPa resolution. The catch is **weather drift**: a front moves absolute
pressure by 3–5 hPa/day — 10× a floor. Two mitigations:

1. **Delta classification** — floors are stored as pressure ranges captured
   during a short calibration walk; inference picks the nearest range.
2. **Self-healing anchor** — when activity says STILL and a reading falls
   inside a floor's band, that floor's reference is re-anchored to the current
   value, tracking weather drift over days.

Inference is deliberately conservative: readings outside every tolerance band
report as uncertain rather than confidently wrong.

## Scheduling

Cron (macOS/Linux):

```cron
0 */4 * * *  cd /path/to/adb-sentinel && python3 scripts/report.py >> ~/.adb-sentinel/history.log 2>&1
```

The report also appends a CSV row (time, level, temp, lat, lon, fix age,
pressure, floor) to `~/.adb-sentinel/history.csv` for trend analysis.

## What's read vs. what's written

**Read-only:** `dumpsys battery|location|sensorservice|wifi`, GMS activity
service dumps, `settings get`. No input injection, no app launches, no
permission grants, no screen interaction.

**One write (self-heal):** updating the local calibration JSON. That's it.

## Ethics & security

You should only monitor **your own device** (or one you have explicit
permission to monitor). ADB is a powerful, dual-use interface — see
[SECURITY.md](SECURITY.md) for what an attacker with ADB access can do and how
to protect yourself.

## Roadmap

- [ ] Room-level Wi-Fi RSSI fingerprinting
- [ ] Alert rules (battery < 20%, phone left home, floor changed while away)
- [ ] Home-automation triggers (arrival / room events → lights, alerts)
- [ ] Historical charts from the CSV log

## License

MIT — see [LICENSE](LICENSE).
