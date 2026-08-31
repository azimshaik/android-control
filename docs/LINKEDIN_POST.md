# LinkedIn post — "Your Android phone will tell you everything (over ADB)"

Engineer-credible tone, no hype. Post when the repo is public; swap the
`[repo link]` placeholder.

---

**Your Android phone will tell you almost everything — if you ask it over ADB.**

No root. No apps. No Google account. Just the developer interface your phone
already ships with, over Wi-Fi, after a one-time pairing.

I spent an evening reading my own phone through `adb shell dumpsys`, and the
data that comes back is remarkable:

• **Battery health you can actually see** — charge level, temperature, and
  Samsung's internal wear figure (ASOC), not the marketing "battery health".
• **Floor-level indoor location from the barometer.** Air pressure drops
  ~0.12 hPa per meter. Adjacent floors are ~0.3–0.4 hPa apart, and the
  phone's barometer resolves 0.01 hPa. Even better: Google Play Services
  samples the barometer every ~2 minutes for its own altitude model, and the
  values sit in a readable ring buffer. Free floor detection, no beacons.
• **Where it is** — GPS/network/fused fixes with accuracy and age, labeled
  AT HOME / AWAY.
• **What it's doing** — Google's activity recognition (STILL / WALKING /
  IN_VEHICLE), readable without any API key.
• **Wi-Fi signal** for room-level fingerprinting.

**Legit uses:** battery-degradation tracking on a phone you keep for years,
finding a misplaced device, knowing a parent's phone is charged and at home,
home-automation triggers, building your own telemetry dashboards.

**Now the part that should worry you:** ADB is a dual-use interface. The same
channel that reads all of this can, in the wrong hands:

• Read SMS, WhatsApp, photos, and app data
• Inject input — type into banking/UPI apps, tap buttons, approve dialogs
• Exfiltrate files and recordings
• Persist via APK installs (past the prompts, with input injection)

That's why: disable wireless debugging when you're not using it, don't plug
into random USB cables with debugging on, and check `adb devices` actually
says `device` (authorized) — not `unauthorized`.

This level of control is a feature when the device is yours, and a liability
when it isn't. I open-sourced the scripts — read-only, stdlib-only Python,
no data leaves your machine: [repo link]

#Android #ADB #Privacy #Security #HomeAutomation
