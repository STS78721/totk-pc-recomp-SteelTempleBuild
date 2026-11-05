# Dynamic Resolution Scaling (DRS) Implementation Plan

Priority feature roadmap for next week's engine development cycle.

See the architecture blueprint in the conversation artifacts or summary below:

- **Goal:** GPU-aware dynamic resolution scaling protecting target framerates (40 / 60 / 120 FPS).
- **Core modules to touch:**
  - `runtime/vk_headroom.c`: Precise GPU timestamp query pool.
  - `runtime/resolution.c`: PID controller with hysteresis to eliminate scale pumping.
  - `runtime/vk_dlaa.c`: Dynamic render subrect feed into NVIDIA DLSS / AMD FSR.
  - `launcher/TotKLauncher.py`: UI sliders for Target FPS, Min Scale %, Max Scale %, and Aggressiveness.
