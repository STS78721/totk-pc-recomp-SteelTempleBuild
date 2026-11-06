# 🗡️ SteelTempSaint's ToTK Recomp 🎮⚡
### *Transforming Tears of the Kingdom into a Flagship Modern PC Experience*

[![Latest Release](https://img.shields.io/github/v/release/STS78721/totk-pc-recomp-SteelTempleBuild?label=Latest%20Release&color=brightgreen)](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/latest)
[![Release Date](https://img.shields.io/github/release-date/STS78721/totk-pc-recomp-SteelTempleBuild?color=blue)](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/latest)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20x86--64-informational)](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild)
[![Renderer](https://img.shields.io/badge/Renderer-Vulkan%201.3-red)](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild)
[![DualSense](https://img.shields.io/badge/Controller-PS5%20DualSense%20Native-blueviolet)](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild)
[![Community Feedback](https://img.shields.io/badge/Community-Feedback%20Welcome-orange)](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/issues)

> [!IMPORTANT]
> **No copyrighted game files are included.** You need your own legally obtained copy of *The Legend of Zelda: Tears of the Kingdom*, dumped from your console: base game and update **v1.4.3** (`ExeFS` / `RomFS`). The executable is compiled and linked on your local machine.

---

## 🌟 Our Vision: What We Want to Achieve

**SteelTempSaint's ToTK Recomp** is an enthusiast-driven, high-performance static recompilation fork of *The Legend of Zelda: Tears of the Kingdom* (Nintendo Switch) for native Windows and Linux x86-64.

Our goal is not just to run the game on PC—it is to **elevate *Tears of the Kingdom* into a native, flagship PC title** that leverages the full power of modern hardware:
- **Next-Gen Immersion:** Bridging the physical gap between player and world with native PS5 DualSense 4-channel audio streaming, dynamic adaptive trigger resistance, and voice-coil tactile feedback.
- **State-of-the-Art Rendering:** Combining deep neural reconstruction, multi-vendor AI upscaling, and low-latency presentation pipelines for razor-sharp 4K/8K presentation at ultra-high framerates.
- **Future-Forward Graphics:** Actively pioneering real-time lighting advancements (RTGI, Path Tracing, and modern PBR pipelines) to realize Hyrule in its most breathtaking form.
- **A Completely Community-Guided Project:** Built for players, with players. Every design choice, trigger curve, audio filter, and visual toggle is driven by user testing, discussion, and direct feedback.

---

## 🕹️ What Has Been Implemented

### 1. 🖥️ Standalone PlayStation / Nixxes-Style PC Launcher (`TotKLauncher.exe`)

<p align="center">
  <img src="https://raw.githubusercontent.com/STS78721/totk-pc-recomp-SteelTempleBuild/main/launcher/launcher_showcase.png" alt="SteelTemple Standalone PC Launcher" width="90%">
</p>

*Modeled directly after modern AAA Sony/Nixxes PC ports (Horizon Forbidden West, Ghost of Tsushima, Spider-Man):*
- **Pre-Game Configuration Hub:** Dial in your graphics, display resolution, and performance settings *before* launching the game.
- **Troubleshoot & Prevent Crashes:** If an unsupported resolution or display mode ever causes an out-of-range monitor error or black screen, fix it externally without editing raw config files.
- **Zero In-Game Stuttering:** Pre-configure DLSS 4.5, AMD FSR 4.1.2, Intel XeSS, Frame Generation, and NVIDIA Reflex Boost so your game boots perfectly dialed in with optimal Vulkan pipeline pre-building.
- **Digital Extras One-Click Directory Hub:** Direct 1-click access to the `mods/` directory, save file location (`profile/save/`), `amiibo/` dumps, and the In-Game Controller Overlay Guide.
- **Standalone Mod Manager:** Open Digital Extras → Mod Manager to scan installed mods, enable or disable them with one checkbox, and open `GAME/mods/` to add more. Disabled folders use a `.disabled` suffix and are skipped by the game.
- **Interactive High-Contrast Controls:** Custom-engineered `SonySlider` widgets with active gold progress fills, glowing thumb indicators, and high-visibility digital readouts.
- **Startup Flexibility:** Includes a `[✓] SHOW LAUNCHER` toggle (boot directly to `totk.exe` or hold `Shift` on launch to bring it back), plus an optional desktop shortcut pointing straight to the launcher.
- **Direct GitHub Community Integration:** Built-in 1-click button connecting players straight to our repository for updates and community discussions.
- **Controller Battery Overlay:** The compact performance HUD shows the active controller's reported battery level or charging state when available.
- **Ultrawide HUD Patcher:** The launcher offers an asynchronous 21:9/32:9 layout patch generated from the installed RomFS.
- **Steam Deck / Handheld Preset:** Apply 1280x800, a 40 FPS cap, FSR balanced upscaling, and reduced shadow settings from Display settings; Proton/Wine launches use native platform fallbacks when available.
- **One-Click Update:** Download and validate the matching GitHub update ZIP, preserve existing `totk.ini` values while merging new defaults, then replace the included game and launcher files with rollback copies.
- **Vulkan Shader Pre-Warm:** Run the renderer's shader pipeline cache pre-warm from Graphics settings and see completion or failure status.
- **Save Backup Vault:** Snapshot `profile/save/`, restore a selected snapshot with confirmation, and automatically snapshot the current save before restore. The game-running safeguard checks the installed `GAME/totk.exe` path and reports the blocking PID/path, so the launcher itself is not mistaken for the game.

---

### 2. 🎮 Native PlayStation 5 DualSense Next-Gen Immersion

<p align="center">
  <img src="https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/download/v0.3.4-beta-4-steeltemple/totk_zonai_dualsense_theme.png" alt="TotK SteelTemple Next-Gen Immersion" width="85%">
</p>

*A whole new way to play TotK on PC with full physical and auditory tactile integration:*
- **4-Channel Audio Streaming & Controller Speaker:** Tapped straight into the game's 48 kHz audio mixer. Sound effects are high-pass filtered and routed directly to the controller's built-in speaker.
- **Smart Interactive Audio Gating:** The speaker stays silent during peaceful exploration—music and ambient wind remain purely on your TV/display. The controller speaker fires only during Link's actions (bow draws, arrow flight, shield parries, melee clashes, explosions, chest fanfares).
- **Studio Dynamics (+18.6 dB Gain + Analog Limiter):** High-headroom digital amplification with a continuous tape-saturation curve (`tanhf`) so subtle bowstring creaks are crisp and loud without digital clipping.
- **Adaptive Triggers:** Progressive bowstring tension builds on Right Trigger (ZR) as you draw; when releasing, the trigger fires a mechanical recoil hammer pulse (Force 8/8) paired with 100% max dual-motor rumble and a 65 Hz voice-coil palm shockwave.
- **Shield Parry Kickback:** When an enemy strikes Link's shield, the Left Trigger (ZL) violently hammers back with maximum force for 350 ms, physically pushing your finger off the trigger.
- **Luminous Zonai Teal-Green Lightbar (`#20F8B8`):** Glows in Link's iconic Ultrahand magic color and gracefully restores to standard system lighting when exiting the game.

### 3. 🚀 Comprehensive AI Upscaler & Neural Reconstruction Hub
- **Universal Multi-Vendor Upscaling:** NVIDIA DLSS 4 / 4.5 (Presets K, J, M, L, E, C), Intel XeSS 2.0+ (Hardware XMX & universal DP4a), AMD FSR 4.1.2 & FSR 1.0 (EASU + RCAS).
- **DLSS Neural Reconstruction (DLSS-NR):** OptiScaler-style neural radiance reconstruction running on Preset B for temporal stability and fine detail. Fully uncoupled from super-resolution presets with hardware auto-gating.
- **Accurate Dynamic Resolution:** Proper 66.7% internal scene scaling in DLSS Quality mode, strictly separated from native 100% DLAA anti-aliasing.
- **Zero Foliage Haloing:** Eliminated unwanted forced sharpening passes on native frames, keeping grass and leaves pristine.

### 4. ⚡ Multi-Vendor Frame Generation & Low Latency
- **Frame Multiplication:** Hardware-aware frame generation support across vendors (NVIDIA DLSS-G, Intel XeFG up to 4x, and AMD FSR 3.1 / FSR 4 AI FG).
- **Minimal Input Lag:** Synchronized queue pacing with NVIDIA Reflex (`VK_NV_low_latency2`), AMD Anti-Lag 2 (`VK_AMD_anti_lag`), and Intel XeLL.

### 5. 🎨 Ambient Occlusion, HDR & Visual Stability
- **Contact Shadowing:** In-engine ambient occlusion choices including Intel XeGTAO, 24-step Directional HBAO, SSAO, and native Switch AO.
- **Cave & Dark Area Flicker Elimination:** Isolated half-resolution sub-passes so volumetric cave fog never hijacks or flickers the upscaler pipeline.
- **OLED HDR10 Calibration:** Dedicated HDR profiles (Vivid, Clarity, Custom) with peak nits and HUD brightness balancing.
- **Clean Grouped HUD:** Two-line high-contrast performance overlay with 0.1% and 1% low frametime hitch tracking and zero repetitive wording.

### 6. 🛠️ Upstream v0.3.10 Engine Improvements & Fixes
- **Falling Rain & Waterfall Splashes Fix (#91, #528):** Implemented Vulkan storage buffer write-back merge to resolve white rain flicker and disappearing waterfall splash effects.
- **VRAM Memory Leak Elimination (#670):** Properly releases pinned texture memory copies, reducing long-session memory leakage from 44 MiB/min to <1 MiB/min.
- **Grass Fire Spread Fix (#132):** Fixed the fire propagation flag (*officially credited to STS78721 in upstream v0.3.10 release notes*).
- **Reduced PCIe Bandwidth & Copying Overhead (#698):** Drastically cuts discrete GPU upload pressure (e.g. Kakariko Village texture uploads reduced from 473 MiB down to 126 MiB).
- **Direct PC Mouse Camera & In-Game Menu Cursor (#558, #605):** Fluid mouse look without analog deadzones on 1.4.3, plus interactive mouse pointer support in native game menus (inventory, shops, dialogue).
- **PC Button Prompts (#585):** Native keyboard & mouse prompts displayed directly in-game.
- **DLSS Stationary Jitter Fix (#701):** Removed conflicting motion patch and added character class bias masks to eliminate DLSS camera shimmer.

---

## 🗺️ The Horizon: Future Tech Roadmap 🔭

We are actively exploring and prototyping new technologies to push the fidelity of *Tears of the Kingdom* even further:
- **🌟 Real-Time Global Illumination (RTGI) & Path Tracing:** Exploring real-time ray-traced bounce lighting, accurate indirect shadows, and dynamic sky illumination across Hyrule's surface, sky islands, and depths.
- **🔮 NVIDIA RTX Remix & Modern PBR Pipelines:** Researching spatial lighting pipelines, enhanced texture materials, and next-gen surface reflectance models.
- **🏹 Expanded Weapon Haptics:** Building out bespoke adaptive trigger curves and voice-coil profiles for heavy two-handed crushers, rapid spear thrusts, and Zonai beam emitters.
- **📡 Wireless DualSense Haptic Streaming:** Exploring custom low-latency wireless Bluetooth audio/haptic pipelines on PC.

---

## 💬 Community Feedback is Crucial — Any & All Ideas Welcome! 🤝

This build exists because of the community, and **your feedback is the single most important factor shaping its development**.

We want to hear from you:
- How do the adaptive triggers feel? Too stiff, too light, or just right?
- How is the controller speaker balance on your setup?
- What visual features, lighting tweaks, or upscaler options would you like to see next?
- Encountered a bug, frametime spike, or edge case?

👉 **Share your thoughts, request features, or report issues directly on the [GitHub Issues tab](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/issues).**
Every idea is welcome, whether you're a casual player enjoying Hyrule on your couch or an enthusiast pushing 4K 120 FPS!

---

## 📥 Quick Start & Downloads

Grab the latest prebuilt packages from our **[Latest Release (Beta 5e)](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/tag/Beta-5e)**:

### 🎮 1. New Players (Fresh Standalone Setup)
👉 **Download: [`SteelTemple-TotK-Beta5e-Portable-StandAlone.zip`](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/download/Beta-5e/SteelTemple-TotK-Beta5e-Portable-StandAlone.zip)** (505 MB)
1. Extract the archive into your chosen game folder (e.g. `C:\Games\Tears of the Kingdom PC\GAME`).
   - *Includes the pre-compiled `TotKLauncher.exe`, `totk.exe`, `SDL3.dll`, all multi-vendor AI upscalers (DLSS 4.5 / XeSS / FSR), controller configs, and aspect ratio patches.*
2. Copy **both** your dumped **`exefs`** and **`romfs`** folders (from your legally owned 1.4.3 game dump) directly into this folder.
   Your game directory should look like this:
   ```text
   GAME/
   ├── totk.exe
   ├── TotKLauncher.exe
   ├── SDL3.dll, libopus-0.dll, etc.
   ├── exefs/            <-- Contains main.npdm, main, sdk, subsdk0 (from 1.4.3 update)
   ├── romfs/            <-- Contains game assets (or romfs.bin)
   └── ...
   ```
3. Launch **`TotKLauncher.exe`** to configure graphics, pre-warm shaders, apply Ultrawide HUD fixes if needed, and hit **Play**!

---

### ⚡ 2. Upgrading / Moving from Another Recomp (Zero Recompiling Needed)
👉 **Download: [`SteelTemple-TotK-Beta5e-Update.zip`](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/download/Beta-5e/SteelTemple-TotK-Beta5e-Update.zip)** (117 MB)
1. If you already have a working game folder or are switching from upstream recomp:
2. Extract and replace **`totk.exe`**, **`TotKLauncher.exe`**, and updated configs directly into your existing game directory.
3. Launch **`TotKLauncher.exe`** to dial in your settings and hit Play, or start **`totk.exe`** directly! Your existing save games, settings, and RomFS will work seamlessly.

---

### 🛠️ 3. Setup & Configuration Wizard (Companion Tool)
👉 **Download: [`SteelTemple-TotK-Beta5e-Full-Setup-Wizard.exe`](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/download/Beta-5e/SteelTemple-TotK-Beta5e-Full-Setup-Wizard.exe)** (64 MB)
- This optional utility runs on top of your game directory to:
  - Automatically detect and migrate your saves from Yuzu, Ryujinx, Sudachi, or previous recomp builds into `profile/save/`.
  - Install custom Controller UI prompt themes (PlayStation 5 DualSense, DualShock 4, Xbox) to `mods/`.
  - Create a 1-click Desktop shortcut pointing directly to `TotKLauncher.exe`.
  - Configure vendor AI upscaler packages (DLSS 4.5, DLSS-NR, Intel XeSS).

---

*Thank you to all contributors, testers, and players building the ultimate Tears of the Kingdom experience!* 🗡️🛡️
