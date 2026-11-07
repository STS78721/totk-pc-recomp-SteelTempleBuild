# Changelog

All notable changes to the **SteelTempSaint ToTK Recomp** project will be documented in this file.

---

## [Unreleased]
- Add a validated one-click GitHub update download/apply flow, a Vulkan shader pre-warm action, and a Save Backup Vault with pre-restore snapshots.
- Fix the Save Backup Vault process guard to match the installed game executable path and report its PID/path when blocking an operation.

---

## [Beta 5g] - 2026-11-07

### 🖥️ Synchronous Borderless Fullscreen Startup (Engine Fix)
- **Swapchain Race Condition Elimination:** Window creation now applies `WS_POPUP` borderless styling and physical monitor bounds (`rcMonitor`) synchronously *before* signaling surface acquisition. The Vulkan swapchain captures exact physical display dimensions on the first pass, preventing stretching or manual F11 toggle requirements on ultrawide displays (3440×1440, 2560×1080).

### 🎮 Ultrawide HUD Auto-Patcher for Custom UI & Controller Prompt Mods
- **Mod Layout Precedence Support:** Automatically detects when button prompt mods (e.g. PSX / DualSense / Xbox prompt mods) in `GAME/mods/` shadow the ultrawide HUD layout.
- **In-Place Ultrawide Mod Transformation:** Decompresses mod `Common.Product.*.blarc.zs` archives, transforms layout coordinates to matching ultrawide aspect ratios, and recompresses them—retaining 100% of custom button prompt textures while adapting the UI geometry to ultrawide!
- **Safe Revert Architecture:** Creates automatic `.bak_16_9` backups and automatically restores pristine 16:9 layouts if standard resolutions are selected.

---

## [Beta 5f] - 2026-11-07

### ⚡ Upstream v0.3.12 Engine Sync
- **Dynamic State Delta Recording:** Command buffer now tracks and records only states that changed since previous draws (`dyn_delta`), slashing command queue overhead and CPU draw time.
- **Inter-Pass Uniform Overlays:** Uniform updates between passes are batched as scratch overlays, eliminating redundant pipeline barriers.
- **HD Texture Pack Support:** Expanded texture heap via `tex_heap_extra_mb` preventing out-of-memory crashes on large 4K community texture packs (e.g. *The Second Quest*).
- **VRAM Pressure Auto-Management:** Released textures overwritten by newer assets are safely evicted when VRAM usage crosses threshold (`tex_vram_pressure`), preventing GPU paging stutter.
- **Ultra-Smooth Frame Queue:** Optional display-time image queue (`FRAME_QUEUE=1`) eliminating frame drops at target limits.
- **Native Direct Mouse Controls & In-Game Menu Pointer:** Full camera mouse control with native aim distance restoration, menu cursor support, and scroll wheel map zoom.
- **Movie Aspect Ratio Preservation:** Pre-rendered cutscenes maintain correct picture shape without stretching on non-16:9 displays.
- **Driver-Level Crash Diagnostics:** Crash reports now display driver stack frames, C++ exception types, and host function signatures.

### 🚀 Upstream Parity NVIDIA Reflex (`VK_NV_low_latency2`)
- **Full Upstream Merge Validation (PR #638):** Fully rebased and compliant with official upstream review requirements.
- **Clean Restarts & Fallbacks:** Gated cleanly on `reflex != off` as a `RESTART` setting, preserving vanilla device/swapchain paths for non-Reflex players.
- **Graceful Unsupported Hardware Handling:** Explicitly logs non-NVIDIA GPU fallback notice (`Reflex: VK_NV_low_latency2 not available`) with zero validation errors.
- **Multilingual Support:** Complete translations in English, Russian, Brazilian Portuguese, and Simplified Chinese.

### 📦 Standalone Distribution & Packaging
- **Streamlined Distribution Architecture:**
  - `SteelTemple-TotK-Beta5f-Portable-StandAlone.zip` (~505 MB) — Complete standalone zero-install environment.
  - `SteelTemple-TotK-Beta5f-Update.zip` (~117 MB) — Drop-in delta update preserving existing player configurations.
  - `SteelTemple-TotK-Beta5f-Full-Setup-Wizard.exe` (~64 MB) — Interactive installer with 1-click Desktop shortcut creation.
- **ExeFS Startup Integrity Protection:** `TotKLauncher.exe` pre-flight dialog prevents silent launch crashes if `exefs/` or `romfs/` are missing.

---

## [Beta 5e Hotfix] - 2026-11-05

### 🎮 In-Game Overlay & Controller Features
- **DualSense & Gamepad Battery Level Indicator:** Integrated battery percentage and charging status (`[🔋 XX%]` / `[⚡ Charging]`) directly into the compact two-line performance overlay next to the controller prompt icon.
  - Queries active SDL HID reports for Sony DualSense controllers with zero latency impact.
  - Falls back to `SDL_GetGamepadPowerInfo()` for standard Xbox, Switch Pro, and third-party gamepads.

### 🖥️ Standalone Sony-Style PC Launcher (`TotKLauncher.exe`)
- **Steam Deck & Handheld Preset:** One-click preset in the Display tab configuring native 1280×800 16:10 resolution, 40 FPS target limiter, AMD FSR Balanced upscaling, and optimized shadow geometry for battery efficiency.
- **Linux & SteamOS Compatibility:** Added native platform fallbacks for Steam Deck / SteamOS (Proton / Wine launch paths, X11/Wayland display resolution detection, and Linux file manager open actions).
- **Ultrawide HUD Auto-Patcher:** Automatically detects 21:9 (2560×1080, 3440×1440, 3840×1600) and 32:9 (5120×1440) resolutions, offering a 1-click async fix to patch RomFS layout archives and eliminate stretched UI elements.
- **1-Click Mod Manager:** Built-in mod manager in *Digital Extras* that scans `GAME/mods/`, allows one-click mod enabling/disabling via `.disabled` suffixes, and directly opens the mod folder.
- **Tactile Audio & UI Polish:** Zonai stone-carving audio cues on button clicks and hover states, custom high-contrast sliders with live numeric badges, and primary GPU auto-detection.

### 📦 Setup Wizard & Engine Packaging
- **Unified Release Package Architecture:** Adopted clean, distinct distribution package names:
  - `SteelTemple-TotK-Beta5e-Update.zip` (~117 MB) — In-place update for existing Beta 5x installs.
  - `SteelTemple-TotK-Beta5e-Portable-StandAlone.zip` (~505 MB) — Recommended zero-install complete environment.
  - `SteelTemple-TotK-Beta5e-Full-Setup-Wizard.exe` (~64 MB) — Interactive Windows installer with shortcut creation.
- **ExeFS & RomFS Startup Validation:** `TotKLauncher.exe` now verifies that required `exefs/` (v1.4.3 `main.npdm`) and `romfs/` folders exist before launching, displaying an intuitive troubleshooting dialog instead of allowing a silent exit.
- **Game Version 1.4.3 Build System:** Updated build pipelines to fully support ExeFS v1.4.3 hashes, ensuring zero startup integrity errors.
- **Developer Tools:** Added `tools/post_issue_comment.py` to automate authenticated GitHub issue communication using local git credential helpers.

---

## [Beta 5d] - 2026-11-04
- Upstream sync with v0.3.10 codebase.
- Master toggle for DLSS / DLAA with preset string configuration (`preset_k`, `preset_m`, `preset_l`).
- Fixed fullscreen windowed startup glitch in `runtime/gfx_window_win.c`.
- Fixed contact shadow duplicate ID bug in in-game menu.

---

## [Beta 5c] - 2026-11-03
- Multi-vendor AI upscaler support (NVIDIA DLSS 4.5, AMD FSR 4.1.2, Intel XeSS).
- Low latency Reflex integration (`VK_NV_low_latency2`).
- 4-channel DualSense haptic streaming and adaptive trigger profiles.
