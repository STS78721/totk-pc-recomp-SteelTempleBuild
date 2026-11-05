# Changelog

## Unreleased

- Add a Steam Deck / handheld launcher preset for 1280x800, 40 FPS, FSR balanced, and reduced shadow settings, with safe Linux/SteamOS launcher platform handling.
- Show SDL-reported gamepad battery and charging status in the compact performance overlay; DualSense uses its active SDL HID report.
- Add an asynchronous launcher action to generate and install an aspect-specific ultrawide HUD patch from the installed RomFS.
- Bundle and install `TotKLauncher.exe` from the standalone setup wizard before its optional desktop shortcut step.
- Add a standalone launcher Mod Manager with a live scan of `GAME/mods/`, one-click folder toggles, refresh, and an
  Open Mods Folder action.
- Treat the launcher's `.disabled` folder suffix as an inactive mod in the runtime scanner.
