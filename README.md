# TotK Recomp — Next Gen STS Build

[![Latest Release](https://img.shields.io/github/v/release/STS78721/totk-pc-recomp-SteelTempleBuild?label=Latest%20Release&color=brightgreen)](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/latest)
[![Release Date](https://img.shields.io/github/release-date/STS78721/totk-pc-recomp-SteelTempleBuild?color=blue)](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/latest)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20x86--64-informational)](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild)
[![Vulkan](https://img.shields.io/badge/Renderer-Vulkan%201.3-red)](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild)

**TotK Recomp: Next Gen STS Build** is an enhanced, high-performance static recompilation fork of *The Legend of Zelda: Tears of the Kingdom* (Nintendo Switch, 2023) for native Windows and Linux x86-64.

> [!IMPORTANT]
> **No game files are included.** You need your own legally obtained copy of *Tears of the Kingdom*, dumped from your own console: the base game and update 1.1.0, 1.2.1, or 1.4.3. The game executable is built from your files on your machine. Do not share copyrighted assets.

---

## ⚡ What's New in Beta 2: Next Gen STS Build

The **Beta 2 Unified Release** (`v0.3.4-beta-2-steeltemple`) consolidates all experimental and cutting-edge features developed across previous alpha/beta iterations into a rock-solid, production-ready build:

### 🌟 Key Changes & Upgrades

1. **Clean Removal of Experimental RTGI & Ray Reconstruction**
   - Stripped unpolished screen-space/BVH ray-traced global illumination shaders and ray reconstruction denoisers.
   - Eliminates temporal ghosting, firefly noise, edge boiling, and frame pacing stutter.
   - Provides pure, pristine image fidelity and flawless frame consistency across all GPU architectures.

2. **Intel XeGTAO (Ground Truth Ambient Occlusion)**
   - Integrated full Intel XeGTAO high-performance ground-truth ambient occlusion alongside SSAO, HBAO, and Native Switch AO.
   - Micro-shadowing depth and contact shadow realism with negligible GPU overhead.

3. **Depth-Guided Hybrid Motion Vectors & Live Visualizer**
   - **Per-Object Velocity Tracking**: Hybrid motion vector engine combining 100% exact analytical camera reprojection for static scenery with depth-guided temporal disocclusion tracking for dynamic actors (Link running, swinging weapons, charging enemies, flying arrows).
   - **Eliminates Ghosting**: Supplies NVIDIA DLSS with complete character-level motion vectors, completely eliminating the temporal ghosting, smearing, and trailing typical of camera-only implementations.
   - **Live Motion Vector Visualizer**: Built-in debug renderer (`TOTK_MV_DEBUG=1` or menu switch) mapping 2D velocities to standard diagnostic RGB colors (neutral grey stationary, vivid red/green/cyan directional vectors) to visually verify character tracking in real time.

4. **NVIDIA DLSS-NR Integration with Forced Preset B**
   - **Streamline DLSS-NR (`sl.dlss_nr.dll`)**: Dedicated in-game menu tab with neural reconstruction, real-time AI radiance caching, and micro-contrast sliders.
   - **Forced Preset B**: Automatically engages NVIDIA's fast neural model (`NVSDK_NGX_DLSS_Hint_Render_Preset_B`), providing a substantial frame time reduction and higher frame rates compared to previous model iterations without compromising clarity.

5. **Unified Guided Upscaler Engine**
   - **NVIDIA DLSS 4 / 4.5**: Next-generation Transformer neural network models (Presets `K`, `J`, `M`, `L`) and DLSS 3 CNN models (Presets `E`, `C`) with DLAA support.
   - **AMD FidelityFX Super Resolution**: Modern FSR 4.1.2 context-aware neural pipeline and FSR 1.0 spatial upscaler for universal hardware support.

6. **Multi-Frame Generation Hub**
   - **NVIDIA DLSS Frame Generation**: Full optical flow and motion-vector frame interpolation (`2x`), with Multi-Frame Generation (`4x` and `6x` MFG) hardware-gated to RTX 50-series GPUs.
   - **AMD FSR 3.1 & FSR 4 AI Frame Generation**: High-performance frame interpolation optimized across modern Radeon cards (including RX 9070 XT, RX 7900 XTX, and RDNA 3/4).

7. **Ultra-Low Latency Synchronization**
   - **NVIDIA Reflex** native integration (`VK_NV_low_latency2`): `Off`, `On`, and `On + Boost`.
   - **AMD Anti-Lag 2** native pipeline (`VK_AMD_anti_lag`): In-engine frame pacing and driver queue synchronization to eliminate input lag during frame generation.

8. **Next Gen STS Interface & Tab Overhaul**
   - Rebranded header: `TotK Recomp 0.3.4-beta-2 (Next Gen STS Build)`.
   - Dedicated **Graphics Settings** tab (formerly Screen tab) organizing resolution, upscaling, ambient occlusion, and display options.
   - Dedicated **DLSS NR** tab previewing DLSS 5 Neural Rendering controls and Preset B acceleration.
   - Full OLED HDR10 calibration (`Vivid`, `Clarity`, `Custom`) with dynamic peak brightness, game exposure, and HUD white point sliders.

---

## 📦 Download & Installation

Visit the **[Latest Beta 2 Release Page](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/latest)** to download:

- **`TotK-Setup-0.3.4-beta-2-steeltemple-windows.zip`**: Full automated graphical installer with Vulkan shader pre-compilation.
- **`TotK-Recomp-SteelTemple-v0.3.4-beta-2.zip`**: Drop-in archive containing `totk.exe`, `totk-rt.dll`, configurations, and DLL loaders.
- **`totk_recomp_beta_2_unified.patch`**: Full developer patch for building from source.

### 🔌 DLL Guide for DLSS & FSR Features

To activate hardware-accelerated NVIDIA DLSS / Reflex / Frame Generation and AMD FSR, place the official vendor libraries directly in the game folder next to `totk.exe`:

#### NVIDIA Streamline DLLs
- Download from NVIDIA's official repository: [NVIDIA Streamline GitHub](https://github.com/NVIDIAGameWorks/Streamline/releases)
- Required files in root game folder:
  ```text
  sl.interposer.dll   (Streamline Interposer)
  sl.dlss.dll         (DLSS 4 / 4.5 Super Resolution)
  sl.dlss_g.dll       (DLSS Frame Generation)
  sl.reflex.dll       (NVIDIA Reflex Low Latency)
  sl.dlss_nr.dll      (DLSS Neural Rendering preview)
  ```

#### AMD FidelityFX DLLs
- Download from GPUOpen: [GPUOpen FidelityFX SDK](https://github.com/GPUOpen-LibrariesAndSDKs/FidelityFX-SDK/releases)
- Required files in root game folder:
  ```text
  amd_fidelityfx_dx12.dll / amd_fidelityfx_vk.dll
  fsr4_upscaler.dll
  ```

> [!NOTE]
> Detailed extraction instructions, directory hierarchy, and checksums are provided in our [DLL Installation Guide](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/releases/tag/v0.3.4-beta-2-steeltemple).

---

## 🔬 Testing & Roadmap

> [!NOTE]
> **Active Beta Mode**: This release is actively being benchmarked across diverse hardware platforms (Intel, AMD, NVIDIA, handhelds, and desktops) 24/7. Feedback, bug reports, and performance logs are welcome in the [Issues tab](https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild/issues).

### Coming Soon:
- **DLSS 5 Neural Rendering (DLSS-NR)**: Full radiance cache reconstruction and transformer-driven lighting stability.
- **Intel Xe Suite**: Dynamic runtime support for Intel XeSS upscaling (`libxess.dll`), XeLL (Xe Low Latency), and XeFG (Xe Frame Generation).
- **VRR Enhancement**: Adaptive sync frame pacing optimization for high-refresh G-Sync and FreeSync panels.

---

## 🛠️ Credits & Attribution

- **valentderah** and the **TotK Recomp Community**: For the foundational static recompilation engine and Vulkan graphics backend.
- **STS78721**: Next Gen STS Build fork engineering, DLSS/FSR pipeline integration, XeGTAO implementation, and UI development.
- **Nintendo**: Creators of *The Legend of Zelda: Tears of the Kingdom*. All game copyrights belong to Nintendo.
