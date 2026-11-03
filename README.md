# TotK Recomp — Next Gen STS Build

[![Latest Release](https://img.shields.io/github/v/release/STS78721/totk-pc-recomp-SteelTempleBuild?label=Latest%20Release&color=brightgreen)](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/latest)
[![Release Date](https://img.shields.io/github/release-date/STS78721/totk-pc-recomp-SteelTempleBuild?color=blue)](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/latest)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20x86--64-informational)](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild)
[![Vulkan](https://img.shields.io/badge/Renderer-Vulkan%201.3-red)](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild)

**TotK Recomp: Next Gen STS Build** is an enhanced, high-performance static recompilation fork of *The Legend of Zelda: Tears of the Kingdom* (Nintendo Switch, 2023) for native Windows and Linux x86-64.

> [!IMPORTANT]
> **No game files are included.** You need your own legally obtained copy of *Tears of the Kingdom*, dumped from your own console: the base game and update 1.1.0, 1.2.1, or 1.4.3. The game executable is built from your files on your machine. Do not share copyrighted assets.

---

## ⚡ What's New in Beta 3: Next Gen STS Build

The **Beta 3 Unified Release** (`v0.3.4-beta-3-steeltemple`) incorporates the full Intel rendering stack, advanced hardware awareness and gating for DLSS Neural Reconstruction, a zero-duplication grouped HUD overlay, 0.1% and 1% low frametime pacing metrics, industry-standard menu terminology, and architectural support for PS5 DualSense controllers:

### 🌟 Key Changes & Upgrades

1. **Full Intel Stack Integration (XeSS 2.0+, XeFG, XeLL)**
   - **Intel XeSS (Xe Super Sampling)**: High-performance AI upscaling with dedicated **XMX Matrix Hardware Acceleration** on Intel Arc GPUs and universal **DP4a** fallback vector acceleration across all vendors.
   - **Intel XeFG (Xe Frame Generation)**: Hardware-aware frame generation with `2x`, `3x`, and `4x` multipliers, dynamically synchronized with the presentation engine.
   - **Intel XeLL (Xe Low Latency)**: Real-time driver queue synchronization and frame pacing for Intel Arc and Iris Xe graphics.
   - **Official Intel DLLs Bundled**: Distributed with `libxess.dll` (v2.0.2), `libxess_fg.dll` (v1.3.1), `libxell.dll` (v1.3.2), and `libxess_dx11.dll` with a resilient multi-path dynamic runtime loader.

2. **DLSS Neural Reconstruction (DLSS-NR) Hardware Gating & Model Uncoupling**
   - **Complete Uncoupling**: DLSS-NR is now fully independent of DLSS Super Resolution models and presets (`TOTK_DLSS_PRESET` and `TOTK_DLSS_NR_PRESET` operate autonomously).
   - **Hardware Awareness & Safety Gating**: Automatically grays out DLSS-NR controls on non-NVIDIA GPUs or systems missing required DLLs (`nvngx_dlssnr.dll` / `sl.dlss_nr.dll`) with clear diagnostic badge explanations.
   - **Preset B Optimization**: NVIDIA's fastest neural reconstruction model (`NVSDK_NGX_DLSS_Hint_Render_Preset_B`) for razor-sharp image stability with minimal frame latency.

3. **Refined Zero-Duplication HUD Performance Overlay**
   - **Logical Technology Pipeline**: Grouped seamlessly on Line 2:
     `DLSS 4.5 · Preset M` &rarr; `[DLSS FG 6x]` (purple badge) &rarr; `[NR ACTIVE · Preset B]` (green badge) &rarr; `| 1080p -> 4K | Hybrid MV | Reflex`.
   - **Framerate & Frame Pacing Line**: Line 1 dedicated to clean performance numbers:
     `● 526 FPS  1% 41  0.1% 39  1.9 ms`.
   - **Zero Repetition**: Completely eliminated duplicate grey string suffixes so every technology pill badge appears exactly once with high contrast styling.

4. **0.1% and 1% Low Frametime Metrics**
   - Added real-time tracking of 1% low and 0.1% low frametimes to both the compact overlay and the comprehensive full performance analysis table (`F1` -> Overlay: Full).
   - Essential for detecting micro-stuttering, shader compilation hitches, and frame pacing variance.

5. **Strict Dynamic DLSS vs DLAA Detection**
   - Real-time resolution evaluation dynamically selects between **`DLSS 4.5`** (active upscaling from lower internal scene resolutions, e.g. 50% 1080p &rarr; 4K) and **`DLAA 4.5`** (native 100% resolution anti-aliasing), eliminating labeling confusion.

6. **Industry-Standard Graphics Settings Terminology**
   - Rephrased the graphics menu with intuitive, industry-standard options and clear explanations designed for average users while keeping full enthusiast control.

7. **PS5 DualSense Controller Architectural Blueprint**
   - Detailed architecture published for dynamic adaptive triggers (bow draw resistance and string snap release), 4-channel controller audio routing for archery sound effects, and automatic in-game button prompt detection (PlayStation vs Xbox vs Nintendo).

8. **Cave Entrance & Interior Black Screen Flicker Elimination (Hotfix)**
   - **Resolved Issue**: Fixed a bug where entering or approaching caves caused rapid in-and-out black screen flickering with upscalers active (both NVIDIA DLSS and AMD FSR) while the 2D HUD remained fully drawn at high framerates.
   - **Sub-Pass Isolation**: In dark environments, TotK dispatches a half-resolution (`960x540`) pass for volumetric fog and cave interior depth. The G-buffer registration now strictly enforces the configured scene resolution (`s[0]`), completely preventing sub-resolution passes from prematurely hijacking the upscaler pipeline.
   - **Output Target Verification**: Scaling passes are now strictly required to target output presentation resolution (`o[0]`), ensuring the final display target is never skipped or left unwritten.
   - **Skipped-Bloom Fallback**: Added in-place fallback evaluation for DLAA in deep caves where the engine dynamically skips the bloom downsampling chain.

9. **Physically Accurate Frame Generation Telemetry & Optical Flow Overhead Modeling**
   - Implemented dual-rate cadence telemetry (`● [Net FPS] (Base [Base FPS])`) on Line 1 of the HUD.
   - Replaced theoretical integer multipliers with real-world Optical Flow Accelerator (OFA) compute overhead modeling, matching NVIDIA FrameView, PresentMon, and RTSS.

---

<p align="center">
  <img src="https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/download/v0.3.4-beta-3-steeltemple/totk_overlay_beta3_grouped_hud.png" alt="Beta 3 Grouped HUD Overlay" width="90%">
</p>

---

## 🎮 Performance & Features Overview

| Feature | Supported Technologies | Key Benefits |
| :--- | :--- | :--- |
| **AI Upscaling** | NVIDIA DLSS 4 / 4.5 (Presets K, J, M, L, E, C), Intel XeSS 2.0+ (XMX & DP4a), AMD FSR 4.1.2 & FSR 1.0 | 4K crystal clarity from 1080p/1440p scene renders |
| **Frame Generation** | NVIDIA DLSS FG (2x, 4x, 6x MFG), Intel XeFG (2x, 3x, 4x), AMD FSR 3.1 & FSR 4 AI FG | Up to 6x framerate multiplication with ultra-smooth motion |
| **Neural Reconstruction** | OptiScaler-style DLSS-NR (Preset B Accelerated) | Temporal clarity, edge antialiasing, and AI radiance caching |
| **Low Latency** | NVIDIA Reflex (`VK_NV_low_latency2`), AMD Anti-Lag 2 (`VK_AMD_anti_lag`), Intel XeLL | Minimal input lag and synchronized frame queues |
| **Ambient Occlusion** | Intel XeGTAO, 24-Step Directional HBAO, SSAO, Native Switch AO | Realistic contact shadowing and atmospheric depth |
| **Motion Vectors** | Depth-Guided Analytical Hybrid Motion Vectors + Debug Visualizer | Zero ghosting on Link, weapons, enemies, and arrows |
| **HDR Calibration** | OLED HDR10 (Vivid, Clarity, Custom) with peak brightness and HUD balance | Full dynamic range on HDR monitors and OLED TVs |

---

## 🛠️ Quick Installation

### Portable Drop-in (Existing Installations)
1. Download **`TotK-Recomp-SteelTemple-v0.3.4-beta-3.zip`** from [Releases](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/latest).
2. Extract all files (`totk.exe`, `libtotkrt.a`, and the Intel DLLs) directly into your existing `GAME` folder, replacing older files.
3. Launch `totk.exe` and press **F1** to open the in-game settings menu!

### Full Installer (New Installations)
1. Download **`TotK-Setup-0.3.4-beta-3-steeltemple-windows.zip`** from [Releases](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/latest).
2. Run `TotK-Setup.exe` and point it to your legally dumped game files.
3. The setup will automatically build the game executable and configure all modern enhancements.

---

## 📜 Credits & Acknowledgments
- **valentderah** and the original [totk-pc-recomp](https://github.com/valentderah/totk-pc-recomp) team for the revolutionary static recompilation engine.
- **STS78721 (SteelTemple)** for lead development, Intel stack integration, DLSS-NR pipeline, hybrid motion vectors, and performance overlay architectures.
- **NVIDIA, AMD, and Intel** for DLSS/Reflex, FSR/Anti-Lag 2, and XeSS/XeFG/XeLL developer SDKs.
