# Changelog

All notable changes to the **SteelTempSaint ToTK Recomp** project will be documented in this file.

---

## [Beta 6.2] - 2026-11-11

### 🚀 Out-of-the-Box Performance & Benchmark Parity
- **Clean Max-FPS Baseline Configuration (`default_totk.ini`):**
  - Fresh `Portable-StandAlone.zip` installations now ship with clean, Switch-equivalent baseline rendering defaults (`shadow_res = game`, `shadow_scale = 1`, `shadow_range = 100`, `grass_range = 100`, `pcss = 0`, `ao_mode = native`, `contact_shadows = 0`, `dlss_nr = 0`, `fps_limit = 240`, `1920x1080`).
  - Eliminates the hidden 8192×8192 shadow cascade + 300% shadow range + PCSS + SSAO + DLSS-NR preset previously bundled in standalone builds, unlocking full native framerate parity on the Surface & Kakariko Village out of the box while keeping 1-click **Enhanced High** and **SteelTemple Ultra** presets ready in the Launcher!
  - Existing users upgrading via `Update.zip` or 1-Click Update retain all of their personalized `totk.ini` settings automatically.
- **Bundled `UltraCamVk.nvngx.dll`:** Included alongside `totk.exe` in both `Portable-StandAlone.zip` and `Update.zip` so NVIDIA DLSS Neural Rendering (`dlss_nr = 1`) works immediately whenever enabled.

### 🎮 Native PlayStation DualSense & DualShock 4 Button Prompts Fix
- **Fixed Inverted Gliding / Action-Diamond Prompts (`DoCommand_00.bflyt`):**
  - Added procedural vector PlayStation button prompt generation (`dualsense`, `dualsense-label`, `dualshock4`, `dualshock4-label`) to `tools/button_icons.py` and `tools/make_romfs_patches.py`, drawing crisp Cross (`✕`), Circle (`○`), Square (`□`), Triangle (`△`), `L1`, `R1`, `L2`, `R2`, Options, Create/Share, and D-Pad icons across `External.bfotf`, HUD masks (`__Combined.bntx`), `.bflyt` panes, and all 14 `Mals` languages.
  - Updated `runtime/input_map.c` and `runtime/romfs.c` so PlayStation prompts automatically match **both** `pad_layout = auto / xbox` (Western layout: Cross=Confirm, Circle=Cancel/Put Away, Square=Jump/Glide, Triangle=Attack with properly mirrored action-diamond positions) AND `pad_layout = nintendo` (Positional layout: Circle=Confirm, Cross=Cancel, Triangle=Jump/Glide, Square=Attack).
  - Removed the conflicting pre-enabled third-party `PS5 UI` mod override from fresh standalone packages so switching between Nintendo, Xbox, DualSense, DualShock 4, and PC prompts works cleanly.

### 🖥️ Standalone Launcher (`TotKLauncher.exe`) Enhancements & Fixes
- **1-Click Graphics & Performance Presets:** Added instant **Max FPS (Default)**, **Enhanced High**, **SteelTemple Ultra**, and **Steam Deck / Handheld** preset buttons in Settings.
- **Startup Shader Pre-Compilation Toggle (`pipe_prebuild`):** Added *"Precompile Shaders at Startup"* toggle right in the Graphics tab alongside 1-click Vulkan shader pre-warming.
- **Fixed Controls & Config Mapping:** Separated **Gamepad Button Layout (`pad_layout`)** from **On-Screen Button Prompts (`prompts`)**, fixed `audio_channels` (`auto` / `stereo` / `5.1`), `mouse_mode` (`direct` / `stick`), `upscaler` valid choices, restored `vk_present` / `aspect` / `fov` controls on the Display tab, and exposed `dlss_nr`, `shadow_scale`, `grass_range`, `dualsense`, `menu_cursor`, `map_click`, and `dialogue_click`.

---

## [Beta 6.1a] - 2026-11-11

### 🔧 Critical Hotfix (`Beta 6.1a`)
- **Fixed Game v1.4.3 Launch (`main.npdm` Hash Verification):** Corrected `totk.exe` target build version from `v121` to `v143` (`expected-v1.4.3.json`), resolving the startup `main.npdm` SHA-256 mismatch error introduced in the initial `Beta 6.1` build.
- **Freshly Re-Lifted v1.4.3 Recompilation Modules:** Re-generated all lifted C modules (`main`, `subsdk0`, `sdk`) against the updated `recomp/patches-v143.txt` so the new `grass_range` (`grass` patch set) and `climb_fix` (`climb` patch set) work natively out of the box.
- **Portable Profile Fallback Hardening:** Portable installs launched before `profile/` exists now automatically create `profile/` beside `totk.exe` when the build-time fallback path is absent.

### 🌿 Upstream Synchronization (valentderah/totk-pc-recomp dev v0.4.0+)
- **NVIDIA Reflex Officially Upstreamed:**
  - Upstream officially merged our NVIDIA Reflex low latency implementation into the core project (`#913`, `#638` by STS78721, carried by itaskaev2).
  - Cleaned up front-end declarations and optimized frame ID queries without present lock contention.
- **DLSS 1.2.1 Post-Scaling Fix:**
  - Skips the game's internal 1.2.1 scaling draw after DLSS instead of re-feeding DLSS output back into the engine blitter (`#1112` by itaskaev2, `#1106`). Resolves double-scaling artifacts when running game version 1.2.1.
- **Grass Range Setting (`grass_range`):**
  - Added new graphic setting `grass_range = 50..400` in both config and in-game menu (`F1` -> Screen / Shadows & Lighting).
  - Scales how far around Link grass renders (from 31 m at 50% to 250 m at 400%, default 62.5 m at 100%).
- **Mouse & Keyboard Controls Overhaul:**
  - **Purah Pad Map Click (`map_click = 1`):** Left mouse click selects pins and points of interest directly on the map.
  - **Dialogue Mouse Click (`dialogue_click = 1`):** Left click advances dialogue (B) and right click confirms (A).
  - **Mouse Wheel Scroll:** Scroll wheel navigation across inventory grids, item strips, and quick-menus.
  - **Purah Pad Scope Zoom:** Mouse wheel smoothly zooms the camera scope and binoculars.
  - **Native Keyboard Glyph Prompts:** Dynamic `T` key icon prompt and cleaner PC key prompts throughout the HUD.
- **Version-Agnostic Mod File Serving:**
  - Mod loader now transparently serves files named for different game versions under their matching internal names, fixing multi-version audio, voice, and soundtrack mods.
- **Dynamic DLSS Preset Slot Invalidation:**
  - Cleanly reclaims all DLSS resolution slots when changing presets at runtime to eliminate VRAM fragmentation.

### 🛡️ Preserved SteelTemple Custom Architecture
- **NVIDIA DLSS Neural Rendering (DLSS-NR Preset B):** Full Pre-SR multipass AI surface reconstruction (`dlss_nr_passes = 1|2|3|4`, `dlss_nr_scale`, `dlss_nr_color`).
- **Hardened Multi-Frame Generation:** DLSS FG 2x/4x/6x (with Blackwell RTX 50 Series support), AMD FSR 3.1 & FSR 4 AI FG, and Intel XeFG.
- **Ultra-Low Latency Ecosystem:** NVIDIA Reflex + Boost, AMD Anti-Lag 2 (`VK_AMD_anti_lag`), and Intel XeLL.
- **Custom Ambient Occlusion Suite:** Intel XeGTAO (Ground Truth AO), HBAO, and SSAO alongside native lighting.
- **Sony / Nixxes Standalone Launcher:** High-DPI Zonai UI with Mod Manager, GameBanana 1-click browser, Save Backup Vault, and Profile Manager.
- **DualSense Controller Suite:** 4-channel haptics and hardware adaptive triggers.

---

## [Beta 6] - 2026-11-08

### 🌟 NVIDIA DLSS Neural Rendering (DLSS-NR Preset B) & Pre-SR Multipass
- **Apology & Technical Transparency:** First and foremost, we owe you an apology. In earlier test builds, DLSS-NR was not behaving visually as it should have—plagued by black-screen parameter mismatches (`0xbad00005`), shadow cascade flickering caused by camera viewport jitter, and simple blit scaling that bypassed the upscaler. We stepped back, listened, and completely rebuilt the neural pipeline natively into the engine so it works exactly as envisioned.
- **OptiScaler-Inspired Pre-SR Multipass Architecture:**
  - **Stage 1 (Pre-SR Neural Reconstruction):** DLSS-NR (Preset B) evaluates directly at native render resolution (e.g. 1080p) across sequential neural passes (`1x`, `2x`, `3x`, or `4x`). The neural network resolves complex specular reflections, fine geometry, and lighting details right on your GPU's Tensor Cores before scaling occurs.
  - **Stage 2 (DLSS Super Resolution AI Upscaling):** The reconstructed neural frame is passed directly into DLSS Super Resolution (Feature 1, Preset M), cleanly upscaling to full 4K (`3840x2160`) with razor-sharp edges and zero blurriness.
- **Shadow Cascade Flickering Eliminated:** Zeroed viewport camera jitter specifically during DLSS-NR execution, completely fixing shadow cascade jumping while preserving pristine temporal clarity.
- **In-Engine Controls & INI Configuration:** Full support for `dlss_nr = 1`, `dlss_nr_preset = preset_b`, and `dlss_nr_passes = 1|2|3|4` in both `totk.ini` and the in-game Settings menu (`F1` -> Screen / Upscaler tab).
- **💡 Real-World Hardware & Tensor Core Performance Note:**
  - DLSS Neural Rendering (DLSS 5 generation tech) is genuinely advanced and computationally demanding. Running multiple sequential passes (`3x` or `4x`) invokes deep neural inference per frame directly on your Tensor Cores.
  - While high-end cards like the GeForce RTX 5070 Ti, 4080, and 4090 have ample Tensor compute, multipass *can be taxing* on GPU resources and frame times. We recommend starting with `1x` or `2x` passes for the sweet spot of pristine image quality and rock-solid performance!

---

### ⚡ Hardware-Aware Frame Generation & Reflex Low Latency
- **Multi-Frame Generation (MFG) Hardened:**
  - Hardware-gated multipliers (`2x`, `3x`, `4x`, `6x`) with full Blackwell RTX 50 Series support for 4x and 6x Multi-Frame Gen.
  - Multiplier parsing hardened across the presentation pipeline with zero fallback clamping on RTX 50 series hardware.
- **Vulkan Synchronization2 Hardening:**
  - Added explicit transfer read barriers (`VK_ACCESS_2_TRANSFER_READ_BIT`) to presentation history buffers, preventing swapchain queue stalls or presentation jitter.
- **NVIDIA Reflex (`VK_NV_low_latency2`):**
  - Complete 6-point latency marker loop (`SIMULATION_START`, `SIMULATION_END`, `RENDERSUBMIT_START`, `RENDERSUBMIT_END`, `PRESENT_START`, `PRESENT_END`) with Boost mode pinned GPU clocks.
- **Telemetry & HUD Redesign:**
  - Compact two-line HUD displays net generated frame rate alongside true base rendering rate: `240 FPS (Base 120)` with 1% and 0.1% low percentiles.
  - Integrated sleek pill badges: `[DLSS 4K]`, `[FG 2x / 4x / 6x]`, and `[NR Active B]`.

---

## [Beta 5h] - 2026-11-07
- Add 1-click mod archive installer (.zip/.rar/.7z) and GameBanana mod browser integration to launcher.
- Upstream dev sync (v0.3.13): GPU texture deswizzling, memory defer fixes.

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
