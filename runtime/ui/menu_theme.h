// Switch 2-inspired theme system for TotK Recompiled's in-game F1 menu (light, dark, and custom TOTK theme).
// Modeled after MKW-THWOMP's runtime/ui/menu/menu_theme.h & menu_look.cpp architecture while tailored for
// The Legend of Zelda: Tears of the Kingdom with bespoke Zonai/Hylian ImDrawList accents.
#pragma once
#include <math.h>
#include <string.h>

#include "imgui.h"

extern "C" {
#include "cfg.h"
}

namespace totk_theme {

enum MenuTheme {
    THEME_TOTK = 0,
    THEME_DARK = 1,
    THEME_LIGHT = 2,
};

inline MenuTheme g_active = THEME_TOTK;

inline ImU32 kBackdrop, kPanel, kHeader, kSidebar, kDivider;
inline ImU32 kText, kTextSoft, kTextDim, kTextOff;
inline ImU32 kAccent, kAccentAlt, kAccentSoft, kAccentText;
inline ImU32 kRowSel, kRowHover, kRowBorder, kWarn, kHelp;
inline ImU32 kButtonHover, kButtonActive, kScroll;
inline ImU32 kGoldBand, kJadeBand;

inline MenuTheme current_from_cfg() {
    const char *v = cfg_value("TOTK_MENU_THEME");
    if (!v || !*v || !strcmp(v, "totk")) return THEME_TOTK;
    if (!strcmp(v, "light")) return THEME_LIGHT;
    if (!strcmp(v, "dark")) return THEME_DARK;
    return THEME_TOTK;
}

inline void apply_palette(MenuTheme t) {
    g_active = t;
    if (t == THEME_LIGHT) {
        kBackdrop = IM_COL32(12, 16, 20, 150);
        kPanel = IM_COL32(240, 241, 244, 255);
        kHeader = IM_COL32(251, 251, 252, 255);
        kSidebar = IM_COL32(226, 228, 233, 255);
        kDivider = IM_COL32(202, 205, 212, 255);
        kText = IM_COL32(34, 36, 42, 255);
        kTextSoft = IM_COL32(84, 88, 98, 255);
        kTextDim = IM_COL32(128, 132, 142, 255);
        kTextOff = IM_COL32(168, 172, 180, 255);
        kAccent = IM_COL32(0, 174, 212, 255);
        kAccentAlt = IM_COL32(14, 154, 134, 255);
        kAccentSoft = IM_COL32(0, 174, 212, 65);
        kAccentText = IM_COL32(0, 122, 162, 255);
        kRowSel = IM_COL32(255, 255, 255, 255);
        kRowHover = IM_COL32(255, 255, 255, 175);
        kRowBorder = IM_COL32(206, 210, 218, 255);
        kWarn = IM_COL32(198, 86, 18, 255);
        kHelp = IM_COL32(251, 251, 252, 255);
        kButtonHover = IM_COL32(226, 246, 252, 255);
        kButtonActive = IM_COL32(194, 236, 247, 255);
        kScroll = IM_COL32(180, 184, 192, 255);
        kGoldBand = kAccentAlt;
        kJadeBand = kAccent;
    } else if (t == THEME_DARK) {
        kBackdrop = IM_COL32(0, 0, 0, 175);
        kPanel = IM_COL32(24, 25, 30, 255);
        kHeader = IM_COL32(32, 33, 39, 255);
        kSidebar = IM_COL32(17, 18, 22, 255);
        kDivider = IM_COL32(58, 60, 68, 255);
        kText = IM_COL32(238, 239, 243, 255);
        kTextSoft = IM_COL32(182, 185, 196, 255);
        kTextDim = IM_COL32(130, 134, 146, 255);
        kTextOff = IM_COL32(88, 90, 102, 255);
        kAccent = IM_COL32(232, 46, 56, 255);
        kAccentAlt = IM_COL32(236, 194, 84, 255);
        kAccentSoft = IM_COL32(232, 46, 56, 78);
        kAccentText = IM_COL32(255, 104, 110, 255);
        kRowSel = IM_COL32(44, 46, 54, 255);
        kRowHover = IM_COL32(39, 41, 48, 205);
        kRowBorder = IM_COL32(66, 68, 78, 255);
        kWarn = IM_COL32(255, 160, 68, 255);
        kHelp = IM_COL32(30, 31, 38, 255);
        kButtonHover = IM_COL32(68, 36, 42, 255);
        kButtonActive = IM_COL32(104, 34, 42, 255);
        kScroll = IM_COL32(82, 84, 96, 255);
        kGoldBand = kAccent;
        kJadeBand = kDivider;
    } else {
        // THEME_TOTK: Carved Zonai obsidian/forest slate, luminous Zonai teal & Sacred Hylian gold.
        kBackdrop = IM_COL32(5, 11, 10, 185);
        kPanel = IM_COL32(17, 27, 25, 255);
        kHeader = IM_COL32(22, 36, 33, 255);
        kSidebar = IM_COL32(12, 20, 18, 255);
        kDivider = IM_COL32(52, 86, 76, 255);
        kText = IM_COL32(240, 236, 224, 255);
        kTextSoft = IM_COL32(188, 198, 188, 255);
        kTextDim = IM_COL32(138, 158, 149, 255);
        kTextOff = IM_COL32(86, 104, 97, 255);
        kAccent = IM_COL32(46, 228, 178, 255);
        kAccentAlt = IM_COL32(236, 196, 86, 255);
        kAccentSoft = IM_COL32(46, 228, 178, 66);
        kAccentText = IM_COL32(236, 196, 86, 255);
        kRowSel = IM_COL32(27, 47, 42, 255);
        kRowHover = IM_COL32(23, 40, 36, 210);
        kRowBorder = IM_COL32(48, 82, 72, 255);
        kWarn = IM_COL32(242, 174, 82, 255);
        kHelp = IM_COL32(21, 35, 32, 255);
        kButtonHover = IM_COL32(32, 60, 52, 255);
        kButtonActive = IM_COL32(44, 84, 72, 255);
        kScroll = IM_COL32(66, 118, 102, 255);
        kGoldBand = IM_COL32(212, 172, 72, 215);
        kJadeBand = IM_COL32(30, 128, 102, 210);
    }
}

inline ImVec4 v4(ImU32 c) { return ImGui::ColorConvertU32ToFloat4(c); }

inline void fill_base_style(ImGuiStyle &s) {
    MenuTheme t = current_from_cfg();
    apply_palette(t);
    s = ImGuiStyle();
    s.WindowPadding = ImVec2(26, 20);
    s.FramePadding = ImVec2(16, 9);
    s.ItemSpacing = ImVec2(12, 8);
    s.ScrollbarSize = 10;
    s.WindowBorderSize = (t == THEME_TOTK) ? 1.5f : 1.0f;
    s.WindowRounding = (t == THEME_TOTK) ? 14.0f : 18.0f;
    s.ChildRounding = 10.0f;
    s.FrameRounding = (t == THEME_TOTK) ? 12.0f : 20.0f;
    s.PopupRounding = 12.0f;
    s.GrabRounding = 8.0f;
    s.ScrollbarRounding = 8.0f;

    ImVec4 *c = s.Colors;
    c[ImGuiCol_WindowBg] = v4(kPanel);
    c[ImGuiCol_PopupBg] = v4(kHeader);
    c[ImGuiCol_ChildBg] = ImVec4(0, 0, 0, 0);
    c[ImGuiCol_Border] = (t == THEME_TOTK) ? v4(IM_COL32(214, 176, 78, 120)) : v4(kDivider);
    c[ImGuiCol_Text] = v4(kText);
    c[ImGuiCol_TextDisabled] = v4(kTextDim);
    c[ImGuiCol_FrameBg] = v4(kSidebar);
    c[ImGuiCol_FrameBgHovered] = v4(kRowHover);
    c[ImGuiCol_FrameBgActive] = v4(kRowSel);
    c[ImGuiCol_SliderGrab] = v4(kAccent);
    c[ImGuiCol_SliderGrabActive] = v4(kAccentText);
    c[ImGuiCol_CheckMark] = v4(kAccent);
    c[ImGuiCol_Button] = v4(kHeader);
    c[ImGuiCol_ButtonHovered] = v4(kButtonHover);
    c[ImGuiCol_ButtonActive] = v4(kButtonActive);
    c[ImGuiCol_Header] = v4(kAccentSoft);
    c[ImGuiCol_HeaderHovered] = v4(kRowHover);
    c[ImGuiCol_HeaderActive] = v4(kButtonActive);
    c[ImGuiCol_ScrollbarBg] = ImVec4(0, 0, 0, 0);
    c[ImGuiCol_ScrollbarGrab] = v4(kScroll);
    c[ImGuiCol_ScrollbarGrabHovered] = v4(kTextDim);
    c[ImGuiCol_ScrollbarGrabActive] = v4(kTextSoft);
    c[ImGuiCol_NavCursor] = v4(kAccent);
    c[ImGuiCol_ModalWindowDimBg] = v4(kBackdrop);
    c[ImGuiCol_Separator] = v4(kDivider);
}

// Button circle hint ("A", "B") drawn procedurally so Roboto needs no special icon glyphs.
inline void hint_glyph(ImDrawList *dl, ImVec2 c, float rad, const char *letter) {
    dl->AddCircleFilled(c, rad, kText);
    ImFont *font = ImGui::GetFont();
    float fs = rad * 1.25f;
    ImVec2 ts = font->CalcTextSizeA(fs, FLT_MAX, 0, letter);
    dl->AddText(font, fs, ImVec2(c.x - ts.x * 0.5f, c.y - ts.y * 0.5f), kHeader, letter);
}

// Pill key/shoulder hint ("L", "R") drawn procedurally.
inline float hint_pill(ImDrawList *dl, ImVec2 p, float h, const char *letter) {
    ImFont *font = ImGui::GetFont();
    float fs = h * 0.62f;
    ImVec2 ts = font->CalcTextSizeA(fs, FLT_MAX, 0, letter);
    float w = ts.x + h * 0.9f;
    dl->AddRectFilled(p, ImVec2(p.x + w, p.y + h), kText, h * 0.5f);
    dl->AddText(font, fs, ImVec2(p.x + (w - ts.x) * 0.5f, p.y + (h - ts.y) * 0.5f), kHeader, letter);
    return w;
}

// Custom TOTK UI emblem: Sacred Triforce centered inside an engraved Zonai energy ring with cardinal diamond ticks.
inline void draw_totk_crest(ImDrawList *dl, ImVec2 c, float r, double t_sec) {
    ImU32 gold = kAccentAlt;
    ImU32 teal = kAccent;
    ImU32 ring_bg = IM_COL32(10, 22, 19, 200);
    dl->AddCircleFilled(c, r * 1.05f, ring_bg, 32);
    dl->AddCircle(c, r, teal, 32, fmaxf(1.5f, r * 0.11f));
    dl->AddCircle(c, r * 0.78f, IM_COL32(236, 196, 86, 130), 24, fmaxf(1.0f, r * 0.06f));

    // Slowly orbiting subtle cardinal ticks along the Zonai ring
    float spin = (float)fmod(t_sec * 0.35, 6.2831853);
    for (int i = 0; i < 4; i++) {
        float a = spin + i * 1.5707963f;
        float ca = cosf(a), sa = sinf(a);
        ImVec2 p0(c.x + ca * (r * 0.88f), c.y + sa * (r * 0.88f));
        ImVec2 p1(c.x + ca * (r * 1.15f), c.y + sa * (r * 1.15f));
        dl->AddLine(p0, p1, teal, fmaxf(1.5f, r * 0.10f));
    }

    // Triforce centered cleanly by circumcenter inside the inner circle
    float tri_h = r * 0.90f;
    float half_w = tri_h * 0.57735f;
    ImVec2 top(c.x, c.y - tri_h * (2.0f / 3.0f));
    ImVec2 mid_l(c.x - half_w * 0.5f, top.y + tri_h * 0.5f);
    ImVec2 mid_r(c.x + half_w * 0.5f, top.y + tri_h * 0.5f);
    ImVec2 bot_l(c.x - half_w, top.y + tri_h);
    ImVec2 bot_m(c.x, top.y + tri_h);
    ImVec2 bot_r(c.x + half_w, top.y + tri_h);
    dl->AddTriangleFilled(top, mid_r, mid_l, gold);
    dl->AddTriangleFilled(mid_l, bot_m, bot_l, gold);
    dl->AddTriangleFilled(mid_r, bot_r, bot_m, gold);
}

// Custom TOTK UI frieze: interlocking Zonai geometric diamond & rune pattern bordered by a luminous Zonai teal edge.
inline void draw_zonai_band(ImDrawList *dl, float x0, float x1, float y, float band_h, float edge, bool accent_below) {
    float span = x1 - x0;
    if (span <= 8.0f) return;
    dl->AddRectFilled(ImVec2(x0, y), ImVec2(x1, y + band_h), IM_COL32(10, 18, 16, 235));
    float cy = y + band_h * 0.5f;
    float step = fmaxf(band_h * 2.2f, 16.0f);
    int count = (int)(span / step);
    float xs = x0 + (span - count * step) * 0.5f;
    float dr = band_h * 0.34f;
    for (int i = 0; i < count; i++) {
        float cx = xs + (i + 0.5f) * step;
        // Outer Zonai diamond
        ImVec2 p0(cx, cy - dr), p1(cx + dr * 1.15f, cy), p2(cx, cy + dr), p3(cx - dr * 1.15f, cy);
        bool major = (i % 4) == 0;
        dl->AddQuadFilled(p0, p1, p2, p3, major ? kAccent : kJadeBand);
        if (major) {
            float ir = dr * 0.45f;
            dl->AddQuadFilled(ImVec2(cx, cy - ir), ImVec2(cx + ir, cy), ImVec2(cx, cy + ir), ImVec2(cx - ir, cy),
                              kGoldBand);
        } else {
            dl->AddLine(ImVec2(cx - step * 0.36f, cy), ImVec2(cx - dr * 1.25f, cy), kGoldBand, 1.0f);
            dl->AddLine(ImVec2(cx + dr * 1.25f, cy), ImVec2(cx + step * 0.36f, cy), kGoldBand, 1.0f);
        }
    }
    float ly = accent_below ? (y + band_h) : (y - edge);
    dl->AddRectFilled(ImVec2(x0, ly), ImVec2(x1, ly + edge), kAccent);
}

// Carved gold Zonai corner filigree brackets for the TOTK custom theme.
inline void draw_totk_corners(ImDrawList *dl, ImVec2 a, ImVec2 b, float len, float thick) {
    ImU32 col = kAccentAlt;
    // Top-left
    dl->AddRectFilled(ImVec2(a.x, a.y), ImVec2(a.x + len, a.y + thick), col);
    dl->AddRectFilled(ImVec2(a.x, a.y), ImVec2(a.x + thick, a.y + len), col);
    // Top-right
    dl->AddRectFilled(ImVec2(b.x - len, a.y), ImVec2(b.x, a.y + thick), col);
    dl->AddRectFilled(ImVec2(b.x - thick, a.y), ImVec2(b.x, a.y + len), col);
    // Bottom-left
    dl->AddRectFilled(ImVec2(a.x, b.y - thick), ImVec2(a.x + len, b.y), col);
    dl->AddRectFilled(ImVec2(a.x, b.y - len), ImVec2(a.x + thick, b.y), col);
    // Bottom-right
    dl->AddRectFilled(ImVec2(b.x - len, b.y - thick), ImVec2(b.x, b.y), col);
    dl->AddRectFilled(ImVec2(b.x - thick, b.y - len), ImVec2(b.x, b.y), col);
}

}   // namespace totk_theme
