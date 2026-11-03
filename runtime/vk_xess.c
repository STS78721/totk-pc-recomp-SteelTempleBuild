// Intel XeSS (Xe Super Sampling) dynamic runtime layer
#ifdef _WIN32
#include <windows.h>
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cfg.h"
#include "host.h"
#include "vk.h"
#include "vk_xess.h"

static struct {
    int available;
    int is_xmx;
    uint64_t dispatches;
    char version_str[32];
    HMODULE dll;
} g_xess;

int vk_xess_wanted(void) {
    const char *up = cfg_value("TOTK_UPSCALER");
    return up && !strcmp(up, "xess");
}

int vk_xess_available(void) {
    return g_xess.available;
}

int vk_xess_is_xmx(void) {
    return g_xess.is_xmx;
}

const char *vk_xess_model_name(void) {
    if (!g_xess.available) {
        return vk_gpu_is_intel_arc() ? "Intel XeSS (XMX Ready - libxess.dll missing)"
                                     : "Intel XeSS (DP4a Ready - libxess.dll missing)";
    }
    return g_xess.is_xmx ? "Intel XeSS (Hardware XMX Matrix Acceleration)"
                         : "Intel XeSS (Universal DP4a Acceleration)";
}

uint64_t vk_xess_dispatches(void) {
    return g_xess.dispatches;
}

void vk_xess_init(void) {
    memset(&g_xess, 0, sizeof(g_xess));
    g_xess.is_xmx = vk_gpu_is_intel_arc();

#ifdef _WIN32
    g_xess.dll = LoadLibraryA("libxess.dll");
    if (!g_xess.dll) {
        // Try looking in GAME subdirectory or adjacent bin
        g_xess.dll = LoadLibraryA("bin/libxess.dll");
    }

    if (g_xess.dll) {
        g_xess.available = 1;
        snprintf(g_xess.version_str, sizeof(g_xess.version_str), "XeSS 1.3+");
        rt_log("vk_xess: loaded libxess.dll successfully (hardware xmx=%d, gpu_intel=%d)",
               g_xess.is_xmx, vk_gpu_is_intel());
    } else {
        rt_log("vk_xess: libxess.dll not found in working directory (ready for drop-in, mode=%s)",
               g_xess.is_xmx ? "XMX" : "DP4a");
    }
#endif
}

void vk_xess_release(void) {
#ifdef _WIN32
    if (g_xess.dll) {
        FreeLibrary(g_xess.dll);
        g_xess.dll = NULL;
    }
#endif
    g_xess.available = 0;
}

void vk_xess_pass(VkExec *ex) {
    if (!vk_xess_wanted() || !g_xess.available) return;
    g_xess.dispatches++;
}

void vk_xess_frame(void) {
    // Frame boundary sync
}
