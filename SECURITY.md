# Security — what ADB access really means

ADB is a **dual-use interface**. Everything in this project is read-only and
runs against a device you own. This document is the other half of the story:
what the same interface looks like in the wrong hands, and how to stay safe.

## What an attacker with ADB access can do

Once a device is paired and authorized (state `device` in `adb devices`), the
interface is effectively root-lite for many purposes:

- **Read data**: SMS, WhatsApp (via backup + key extraction), photos, files,
  app data on debuggable apps, notifications, clipboard.
- **Inject input**: type anything into any app (banking, UPI, messaging),
  tap buttons, approve dialogs — the PhonePe/PIN flows people script are
  exactly what an attacker would script.
- **Exfiltrate**: `adb pull` any accessible file; screen-record and
  screencap protected screens on some devices.
- **Interact with sensors**: trigger camera/recorder UIs, read sensors,
  request locations.
- **Persist**: install APKs (with user-visible prompts on modern Android,
  but social engineering + input injection can navigate those prompts).

This is **not** a vulnerability — it's the designed developer interface.
The danger is leaving it enabled and reachable.

## Attack surface specific to wireless ADB

1. **Network exposure** — wireless debugging listens on a TCP port (commonly
   5555 or a dynamic port) on your Wi-Fi. Anyone on the same network can
   *attempt* pairing; an authorized host key is still required, but see below.
2. **Pairing codes** — `adb pair` codes are short-lived (single use), but a
   code shown on the phone screen is guessable only if the attacker can see
   your screen. The bigger risk is a **previously paired host** whose key is
   still trusted.
3. **Unauthorized ≠ safe** — a device in `unauthorized` state has *not*
   accepted your key; it's an old or revoked pairing. Don't treat a raw
   `adb connect` success as authorization — check `adb devices` state.
4. **Screenshots of secure screens** — some builds blank screencaps of
   PIN/bank screens; that's a *protection*, not a guarantee. UI dumps
   (`uiautomator dump`) can still expose text content.

## Mitigations

- **Disable wireless debugging when you're not actively using it.** This is
  the single most effective control. Re-enable + re-pair when needed (pairing
  takes 20 seconds).
- **Never leave USB debugging on for random public charging cables** — a
  "charging only" cable is a lie; a cable can be an ADB implant.
- **Keep the phone on your own trusted Wi-Fi** — hotel/airport networks put
  the ADB port on a shared L2 segment.
- **Firewall the ADB port** if your router supports it (allowlist the
  management host's IP).
- **Check `adb devices` state after every connect** — `device` is authorized;
  `unauthorized`/`offline` is not.
- **Use the pairing code flow, not a raw RSA accept** — you see exactly which
  host is being trusted.
- **Don't store phone unlock PINs in scripts** — this project never needs
  one; if your own tooling does, keep it out of repos (gitignored, chmod 600).
- **Google Play Protect + lock screen** stay enabled; ADB doesn't bypass
  those, and they're your defense if input injection happens.

## Consent

Monitor only devices you own or have explicit permission to monitor. Laws
about device monitoring vary by jurisdiction; this project is a tool, not
legal advice.

## Reporting

This project makes no changes to the device; there is no firmware or
exploit surface of its own. If you find a bug in the scripts, open an issue.
