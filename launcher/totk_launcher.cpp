#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <commdlg.h>
#include <dwmapi.h>
#include <mmsystem.h>
#include <shlobj.h>
#include <shellapi.h>
#include <tlhelp32.h>
#include <winhttp.h>

#define SDL_MAIN_HANDLED
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>
#include "imgui.h"
#include "imgui_impl_sdl3.h"
#include "imgui_impl_sdlrenderer3.h"
#include "launcher_assets.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <map>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

namespace fs = std::filesystem;

#ifndef TOTK_LAUNCHER_VERSION
#define TOTK_LAUNCHER_VERSION "Beta 6.3"
#endif

static constexpr int kWinW = 980;
static constexpr int kWinH = 620;

namespace {

std::wstring utf8_to_wide(const std::string& s) {
    if (s.empty()) return {};
    int n = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), nullptr, 0);
    std::wstring w(n, 0);
    MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), w.data(), n);
    return w;
}

std::string wide_to_utf8(const std::wstring& w) {
    if (w.empty()) return {};
    int n = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), nullptr, 0, nullptr, nullptr);
    std::string s(n, 0);
    WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), s.data(), n, nullptr, nullptr);
    return s;
}

std::string to_lower(std::string s) {
    for (char& c : s) {
        if (c >= 'A' && c <= 'Z') c = (char)(c - 'A' + 'a');
    }
    return s;
}

std::string trim(const std::string& s) {
    size_t a = s.find_first_not_of(" \t\r\n");
    if (a == std::string::npos) return {};
    size_t b = s.find_last_not_of(" \t\r\n");
    return s.substr(a, b - a + 1);
}

std::string quote_win(const std::string& arg) {
    std::string out = "\"";
    for (char c : arg) {
        if (c == '"') out += '\\';
        out += c;
    }
    out += '"';
    return out;
}

void open_in_shell(const std::wstring& target) {
    ShellExecuteW(nullptr, L"open", target.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
}

std::string browse_open_file(HWND owner, const wchar_t* title, const wchar_t* filter) {
    wchar_t buf[32768] = {};
    OPENFILENAMEW ofn{};
    ofn.lStructSize = sizeof(ofn);
    ofn.hwndOwner = owner;
    ofn.lpstrFilter = filter;
    ofn.lpstrFile = buf;
    ofn.nMaxFile = (DWORD)(sizeof(buf) / sizeof(buf[0]));
    ofn.lpstrTitle = title;
    ofn.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR;
    if (GetOpenFileNameW(&ofn)) return wide_to_utf8(buf);
    return {};
}

bool spawn_detached(const fs::path& exe, const std::vector<std::wstring>& args, const fs::path& cwd) {
    std::wstring cmd = L"\"" + exe.wstring() + L"\"";
    for (const auto& a : args) {
        cmd += L" \"" + a + L"\"";
    }
    STARTUPINFOW si{};
    si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};
    if (!CreateProcessW(nullptr, cmd.data(), nullptr, nullptr, FALSE,
                        CREATE_NEW_PROCESS_GROUP, nullptr, cwd.wstring().c_str(), &si, &pi)) {
        return false;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return true;
}

int run_hidden_process(const std::wstring& cmdline, const fs::path& cwd, std::string* captured_out = nullptr) {
    SECURITY_ATTRIBUTES sa{sizeof(sa), nullptr, TRUE};
    HANDLE rpipe = nullptr, wpipe = nullptr;
    if (captured_out && !CreatePipe(&rpipe, &wpipe, &sa, 0)) {
        return -1;
    }
    if (rpipe) SetHandleInformation(rpipe, HANDLE_FLAG_INHERIT, 0);

    STARTUPINFOW si{};
    si.cb = sizeof(si);
    if (captured_out) {
        si.dwFlags = STARTF_USESTDHANDLES;
        si.hStdOutput = wpipe;
        si.hStdError = wpipe;
    }
    std::wstring mut_cmd = cmdline;
    PROCESS_INFORMATION pi{};
    BOOL ok = CreateProcessW(nullptr, mut_cmd.data(), nullptr, nullptr, captured_out ? TRUE : FALSE,
                             CREATE_NO_WINDOW, nullptr, cwd.wstring().c_str(), &si, &pi);
    if (wpipe) CloseHandle(wpipe);
    if (!ok) {
        if (rpipe) CloseHandle(rpipe);
        return -1;
    }
    if (captured_out && rpipe) {
        char buf[4096];
        DWORD n = 0;
        while (ReadFile(rpipe, buf, sizeof(buf), &n, nullptr) && n > 0) {
            captured_out->append(buf, buf + n);
        }
        CloseHandle(rpipe);
    }
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD code = 1;
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return (int)code;
}

bool is_process_running(const wchar_t* exe_name) {
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snap == INVALID_HANDLE_VALUE) return false;
    PROCESSENTRY32W pe{};
    pe.dwSize = sizeof(pe);
    bool found = false;
    if (Process32FirstW(snap, &pe)) {
        do {
            if (_wcsicmp(pe.szExeFile, exe_name) == 0) {
                found = true;
                break;
            }
        } while (Process32NextW(snap, &pe));
    }
    CloseHandle(snap);
    return found;
}

struct MonitorInfoItem {
    std::string device;
    std::string label;
    int left = 0, top = 0, w = 1920, h = 1080, refresh = 60;
    bool primary = false;
};

static BOOL CALLBACK enum_monitor_cb(HMONITOR hmon, HDC, LPRECT, LPARAM lparam) {
    auto* list = reinterpret_cast<std::vector<MonitorInfoItem>*>(lparam);
    MONITORINFOEXW mi{};
    mi.cbSize = sizeof(mi);
    if (!GetMonitorInfoW(hmon, &mi)) return TRUE;
    DEVMODEW dm{};
    dm.dmSize = sizeof(dm);
    int w = mi.rcMonitor.right - mi.rcMonitor.left;
    int h = mi.rcMonitor.bottom - mi.rcMonitor.top;
    int hz = 60;
    if (EnumDisplaySettingsW(mi.szDevice, ENUM_CURRENT_SETTINGS, &dm)) {
        if (dm.dmPelsWidth && dm.dmPelsHeight) {
            w = (int)dm.dmPelsWidth;
            h = (int)dm.dmPelsHeight;
        }
        if (dm.dmDisplayFrequency > 1) hz = (int)dm.dmDisplayFrequency;
    }
    MonitorInfoItem item;
    item.device = wide_to_utf8(mi.szDevice);
    item.left = mi.rcMonitor.left;
    item.top = mi.rcMonitor.top;
    item.w = w;
    item.h = h;
    item.refresh = hz;
    item.primary = (mi.dwFlags & MONITORINFOF_PRIMARY) != 0;
    char buf[128];
    snprintf(buf, sizeof(buf), "Display %d: %dx%d @ %dHz%s",
             (int)list->size() + 1, w, h, hz, item.primary ? " (Primary)" : "");
    item.label = buf;
    list->push_back(std::move(item));
    return TRUE;
}

std::vector<MonitorInfoItem> enumerate_displays() {
    std::vector<MonitorInfoItem> list;
    EnumDisplayMonitors(nullptr, nullptr, enum_monitor_cb, reinterpret_cast<LPARAM>(&list));
    if (list.empty()) {
        list.push_back({"PRIMARY", "Display 1: 1920x1080 @ 60Hz (Primary)", 0, 0, 1920, 1080, 60, true});
    }
    return list;
}

std::string detect_gpu_short() {
    DISPLAY_DEVICEW dd{};
    dd.cb = sizeof(dd);
    std::string best;
    for (DWORD i = 0; EnumDisplayDevicesW(nullptr, i, &dd, 0); ++i) {
        if (dd.StateFlags & DISPLAY_DEVICE_MIRRORING_DRIVER) continue;
        std::string name = wide_to_utf8(dd.DeviceString);
        if (name.empty()) continue;
        std::string low = to_lower(name);
        if (low.find("nvidia") != std::string::npos || low.find("geforce") != std::string::npos ||
            low.find("radeon") != std::string::npos || low.find("amd") != std::string::npos) {
            return name;
        }
        if (best.empty()) best = name;
    }
    return best.empty() ? "Vulkan GPU" : best;
}

std::string detect_romfs_version(const fs::path& romfs_dir) {
    if (!fs::is_directory(romfs_dir)) return "unknown";
    if (fs::is_regular_file(romfs_dir / "System/Resource/ResourceSizeTable.Product.143.rsizetable.zs") ||
        fs::is_regular_file(romfs_dir / "UI/LayoutArchive/Common.Product.140.Nin_NX_NVN.blarc.zs")) {
        return "v143";
    }
    if (fs::is_regular_file(romfs_dir / "System/Resource/ResourceSizeTable.Product.121.rsizetable.zs")) {
        return "v121";
    }
    if (fs::is_regular_file(romfs_dir / "System/Resource/ResourceSizeTable.Product.110.rsizetable.zs")) {
        return "v110";
    }
    return "v143";
}

// ---------- Directory & Config I/O ----------

fs::path find_game_dir(const fs::path& exe_dir) {
    std::error_code ec;
    fs::path cwd = fs::current_path(ec);
    const fs::path candidates[] = {
        exe_dir,
        exe_dir.parent_path(),
        cwd,
        cwd / "GAME",
        exe_dir.parent_path() / "GAME",
    };
    for (const auto& c : candidates) {
        if (c.empty()) continue;
        if (fs::is_regular_file(c / "totk.exe", ec) || fs::is_regular_file(c / "totk.ini", ec)) {
            return c;
        }
    }
    return exe_dir;
}

struct LauncherConfig {
    bool show_launcher = true;
    std::string target_display;
    bool sound_effects = true;
};

static std::string json_extract_string(const std::string& json, const char* key) {
    std::string pat = std::string("\"") + key + "\"";
    size_t pos = json.find(pat);
    if (pos == std::string::npos) return {};
    pos = json.find(':', pos + pat.size());
    if (pos == std::string::npos) return {};
    size_t q1 = json.find('"', pos + 1);
    if (q1 == std::string::npos) return {};
    std::string out;
    for (size_t i = q1 + 1; i < json.size(); ++i) {
        if (json[i] == '\\' && i + 1 < json.size()) {
            out += json[i + 1];
            ++i;
        } else if (json[i] == '"') {
            return out;
        } else {
            out += json[i];
        }
    }
    return {};
}

static bool json_extract_bool(const std::string& json, const char* key, bool def) {
    std::string pat = std::string("\"") + key + "\"";
    size_t pos = json.find(pat);
    if (pos == std::string::npos) return def;
    pos = json.find(':', pos + pat.size());
    if (pos == std::string::npos) return def;
    std::string rest = trim(json.substr(pos + 1, 16));
    if (rest.rfind("true", 0) == 0) return true;
    if (rest.rfind("false", 0) == 0) return false;
    return def;
}

LauncherConfig load_launcher_config(const fs::path& game_dir) {
    LauncherConfig cfg;
    fs::path p = game_dir / "launcher_config.json";
    std::ifstream in(p, std::ios::binary);
    if (!in) return cfg;
    std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    cfg.show_launcher = json_extract_bool(content, "show_launcher", true);
    cfg.target_display = json_extract_string(content, "target_display");
    cfg.sound_effects = json_extract_bool(content, "launcher_sound_effects", true);
    return cfg;
}

void save_launcher_config(const fs::path& game_dir, const LauncherConfig& cfg) {
    std::string escaped_disp;
    for (char c : cfg.target_display) {
        if (c == '\\' || c == '"') escaped_disp += '\\';
        escaped_disp += c;
    }
    std::ofstream out(game_dir / "launcher_config.json", std::ios::binary | std::ios::trunc);
    if (!out) return;
    out << "{\n"
        << "  \"show_launcher\": " << (cfg.show_launcher ? "true" : "false") << ",\n"
        << "  \"target_display\": \"" << escaped_disp << "\",\n"
        << "  \"launcher_sound_effects\": " << (cfg.sound_effects ? "true" : "false") << "\n"
        << "}\n";
}

// Preserve comments & unknown lines in totk.ini while cleanly reading/updating active keys.
class IniStore {
public:
    std::map<std::string, std::string> values;
    std::vector<std::string> lines;

    void load_text(const std::string& text) {
        values.clear();
        lines.clear();
        std::istringstream ss(text);
        std::string line;
        while (std::getline(ss, line)) {
            if (!line.empty() && line.back() == '\r') line.pop_back();
            lines.push_back(line);
            std::string tr = trim(line);
            if (tr.empty() || tr[0] == '#' || tr[0] == ';' || tr[0] == '[') continue;
            size_t eq = tr.find('=');
            if (eq != std::string::npos) {
                std::string k = to_lower(trim(tr.substr(0, eq)));
                std::string v = trim(tr.substr(eq + 1));
                values[k] = v;
            }
        }
    }

    void load_file(const fs::path& ini_path) {
        std::ifstream in(ini_path, std::ios::binary);
        if (in) {
            std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
            load_text(text);
        } else {
            load_text(reinterpret_cast<const char*>(kDefaultTotkIni));
        }
    }

    std::string get(const std::string& key, const std::string& def = "") const {
        auto it = values.find(to_lower(key));
        return (it != values.end() && !it->second.empty()) ? it->second : def;
    }

    int get_int(const std::string& key, int def) const {
        std::string v = get(key);
        if (v.empty()) return def;
        try {
            return std::stoi(v);
        } catch (...) {
            return def;
        }
    }

    float get_float(const std::string& key, float def) const {
        std::string v = get(key);
        if (v.empty()) return def;
        try {
            return std::stof(v);
        } catch (...) {
            return def;
        }
    }

    bool get_bool(const std::string& key, bool def) const {
        std::string v = to_lower(get(key));
        if (v == "1" || v == "true" || v == "yes" || v == "on") return true;
        if (v == "0" || v == "false" || v == "no" || v == "off") return false;
        return def;
    }

    void set(const std::string& key, const std::string& val) {
        values[to_lower(key)] = val;
    }

    void save_updates(const fs::path& ini_path, const std::map<std::string, std::string>& updates) {
        for (const auto& [k, v] : updates) {
            values[to_lower(k)] = v;
        }
        std::map<std::string, std::string> pending;
        for (const auto& [k, v] : updates) {
            pending[to_lower(k)] = v;
        }

        if (lines.empty()) {
            load_text(reinterpret_cast<const char*>(kDefaultTotkIni));
        }
        std::vector<std::string> out_lines = lines;
        for (std::string& line : out_lines) {
            std::string tr = trim(line);
            if (tr.empty() || tr[0] == '#' || tr[0] == ';' || tr[0] == '[') continue;
            size_t eq = tr.find('=');
            if (eq == std::string::npos) continue;
            std::string k = to_lower(trim(tr.substr(0, eq)));
            auto it = pending.find(k);
            if (it != pending.end()) {
                line = k + " = " + it->second;
                pending.erase(it);
            }
        }
        if (!pending.empty()) {
            if (!out_lines.empty() && !trim(out_lines.back()).empty()) out_lines.push_back("");
            for (const auto& [k, v] : pending) {
                out_lines.push_back(k + " = " + v);
            }
        }
        lines = std::move(out_lines);
        std::ofstream out(ini_path, std::ios::binary | std::ios::trunc);
        for (const std::string& l : lines) {
            out << l << "\r\n";
        }
    }
};

// Normalize legacy preset names to CNN / Transformer Gen 1 / Transformer Gen 2.
std::string normalize_dlss_preset(const std::string& raw) {
    std::string l = to_lower(trim(raw));
    if (l == "cnn" || l == "preset_c" || l == "preset_e") return "cnn";
    if (l == "transformer_gen2" || l == "preset_l" || l == "preset_m") return "transformer_gen2";
    return "transformer_gen1";
}

// ---------- Mods & Saves Helpers ----------

struct ModEntry {
    std::string name;
    fs::path path;
    bool enabled = true;
    bool is_4k = false;
};

static bool folder_has_4k_pack(const fs::path& dir) {
    std::error_code ec;
    for (auto it = fs::recursive_directory_iterator(dir, ec); it != fs::recursive_directory_iterator(); it.increment(ec)) {
        if (ec) break;
        std::string fname = to_lower(it->path().filename().string());
        if (fname.find("heapdef.byml.zs") != std::string::npos || fname.find("textogo") != std::string::npos) {
            return true;
        }
    }
    return false;
}

static std::vector<std::string> split_csv(const std::string& s) {
    std::vector<std::string> out;
    std::stringstream ss(s);
    std::string item;
    while (std::getline(ss, item, ',')) {
        std::string t = trim(item);
        if (!t.empty()) out.push_back(t);
    }
    return out;
}

static std::string join_csv(const std::vector<std::string>& list) {
    std::string out;
    for (size_t i = 0; i < list.size(); ++i) {
        if (i) out += ", ";
        out += list[i];
    }
    return out;
}

std::vector<ModEntry> scan_mods(const fs::path& game_dir, const IniStore& ini) {
    std::vector<ModEntry> out;
    fs::path mods_dir = game_dir / "mods";
    std::error_code ec;
    if (!fs::is_directory(mods_dir, ec)) return out;

    auto disabled_list = split_csv(ini.get("mods_disabled"));
    for (const auto& entry : fs::directory_iterator(mods_dir, ec)) {
        if (!entry.is_directory()) continue;
        std::string fname = entry.path().filename().string();
        if (fname.empty() || fname[0] == '.') continue;
        bool suffix_dis = fname.size() > 9 && to_lower(fname.substr(fname.size() - 9)) == ".disabled";
        std::string clean_name = suffix_dis ? fname.substr(0, fname.size() - 9) : fname;
        bool ini_dis = false;
        for (const auto& d : disabled_list) {
            if (_stricmp(d.c_str(), clean_name.c_str()) == 0 || _stricmp(d.c_str(), fname.c_str()) == 0) {
                ini_dis = true;
                break;
            }
        }
        ModEntry m;
        m.name = clean_name;
        m.path = entry.path();
        m.enabled = !(suffix_dis || ini_dis);
        m.is_4k = folder_has_4k_pack(entry.path());
        out.push_back(std::move(m));
    }
    std::sort(out.begin(), out.end(), [](const ModEntry& a, const ModEntry& b) {
        return to_lower(a.name) < to_lower(b.name);
    });
    return out;
}

struct SaveBackupItem {
    std::string name;
    fs::path path;
    std::string details;
};

static uint64_t folder_size_bytes(const fs::path& dir) {
    std::error_code ec;
    uint64_t total = 0;
    for (auto it = fs::recursive_directory_iterator(dir, ec); it != fs::recursive_directory_iterator(); it.increment(ec)) {
        if (!ec && it->is_regular_file(ec)) total += it->file_size(ec);
    }
    return total;
}

std::vector<SaveBackupItem> scan_save_backups(const fs::path& game_dir) {
    std::vector<SaveBackupItem> out;
    fs::path backups_dir = game_dir / "profile" / "backups";
    std::error_code ec;
    if (!fs::is_directory(backups_dir, ec)) return out;
    for (const auto& entry : fs::directory_iterator(backups_dir, ec)) {
        if (!entry.is_directory()) continue;
        SaveBackupItem item;
        item.name = entry.path().filename().string();
        item.path = entry.path();
        uint64_t bytes = folder_size_bytes(entry.path());
        char buf[64];
        snprintf(buf, sizeof(buf), "%.2f MB", bytes / (1024.0 * 1024.0));
        item.details = buf;
        out.push_back(std::move(item));
    }
    std::sort(out.begin(), out.end(), [](const SaveBackupItem& a, const SaveBackupItem& b) {
        return a.name > b.name;
    });
    return out;
}

std::string timestamp_now() {
    time_t t = time(nullptr);
    tm lt{};
    localtime_s(&lt, &t);
    char buf[32];
    strftime(buf, sizeof(buf), "%Y-%m-%d_%H-%M-%S", &lt);
    return buf;
}

// ---------- Procedural MKW-Style Zonai + Circumcenter Triforce Backdrop ----------

struct Particle {
    float x, y, vx, vy, r, alpha;
};

static std::vector<Particle> make_particles() {
    std::vector<Particle> out;
    out.reserve(46);
    uint32_t s = 0x5EED1234u;
    auto rnd = [&]() -> float {
        s = s * 1664525u + 1013904223u;
        return (s & 0xFFFF) / 65535.0f;
    };
    for (int i = 0; i < 46; ++i) {
        out.push_back({rnd(), rnd(), (rnd() - 0.5f) * 0.012f, -(0.008f + rnd() * 0.020f),
                       1.2f + rnd() * 2.2f, 0.14f + rnd() * 0.35f});
    }
    return out;
}

// Circumcenter-aligned Triforce so it always sits dead-center inside any enclosing circle.
static void draw_triforce(ImDrawList* dl, ImVec2 c, float radius, ImU32 fill_col, ImU32 glow_col) {
    float tri_h = radius * 0.90f;
    float half_w = tri_h / 1.7320508f;
    ImVec2 top(c.x, c.y - tri_h * (2.0f / 3.0f));
    ImVec2 bl(c.x - half_w, c.y + tri_h * (1.0f / 3.0f));
    ImVec2 br(c.x + half_w, c.y + tri_h * (1.0f / 3.0f));
    ImVec2 ml((top.x + bl.x) * 0.5f, (top.y + bl.y) * 0.5f);
    ImVec2 mr((top.x + br.x) * 0.5f, (top.y + br.y) * 0.5f);
    ImVec2 mb((bl.x + br.x) * 0.5f, (bl.y + br.y) * 0.5f);

    if ((glow_col >> 24) > 0) {
        dl->AddTriangleFilled(top, ml, mr, glow_col);
        dl->AddTriangleFilled(ml, bl, mb, glow_col);
        dl->AddTriangleFilled(mr, mb, br, glow_col);
    }
    dl->AddTriangleFilled(top, ml, mr, fill_col);
    dl->AddTriangleFilled(ml, bl, mb, fill_col);
    dl->AddTriangleFilled(mr, mb, br, fill_col);
}

static void draw_zonai_backdrop(ImDrawList* dl, ImVec2 vp, float t, std::vector<Particle>& pts, float ds, bool dim_for_subview) {
    // Deep obsidian sky gradient + subtle emerald/gold Zonai nebula on the right half
    dl->AddRectFilled(ImVec2(0, 0), vp, IM_COL32(10, 14, 20, 255));
    dl->AddRectFilledMultiColor(
        ImVec2(vp.x * 0.28f, 0.0f), vp,
        IM_COL32(10, 14, 20, 0), IM_COL32(18, 46, 44, dim_for_subview ? 55 : 130),
        IM_COL32(28, 34, 22, dim_for_subview ? 40 : 95), IM_COL32(10, 14, 20, 0));

    // Hero sacred Zonai astrolabe ring centered in the right art panel (as in MKW hero composition)
    ImVec2 hero(dim_for_subview ? vp.x * 0.78f : vp.x * 0.67f, vp.y * 0.48f);
    float base_r = (dim_for_subview ? 165.0f : 205.0f) * ds;
    float alpha_scale = dim_for_subview ? 0.34f : 1.0f;

    auto col_em = [&](int a) { return IM_COL32(26, 210, 163, (int)(a * alpha_scale)); };
    auto col_gd = [&](int a) { return IM_COL32(238, 198, 92, (int)(a * alpha_scale)); };

    // Outer ambient glow rings
    dl->AddCircleFilled(hero, base_r * 1.18f, col_em(12), 64);
    dl->AddCircleFilled(hero, base_r * 0.78f, col_gd(14), 64);
    dl->AddCircle(hero, base_r * 1.00f, col_em(52), 72, 1.5f * ds);
    dl->AddCircle(hero, base_r * 0.86f, col_gd(58), 72, 1.2f * ds);
    dl->AddCircle(hero, base_r * 0.54f, col_em(72), 64, 1.6f * ds);

    // Rotating Zonai arc ticks
    for (int i = 0; i < 24; ++i) {
        float ang = t * 0.14f + i * (6.2831853f / 24.0f);
        float r0 = base_r * 0.90f;
        float r1 = base_r * (i % 3 == 0 ? 0.99f : 0.95f);
        dl->AddLine(
            ImVec2(hero.x + cosf(ang) * r0, hero.y + sinf(ang) * r0),
            ImVec2(hero.x + cosf(ang) * r1, hero.y + sinf(ang) * r1),
            i % 3 == 0 ? col_gd(120) : col_em(75),
            (i % 3 == 0 ? 2.0f : 1.2f) * ds);
    }

    // Counter-rotating inner sacred segments
    for (int i = 0; i < 6; ++i) {
        float ang0 = -t * 0.22f + i * (6.2831853f / 6.0f);
        float ang1 = ang0 + 0.55f;
        dl->PathArcTo(hero, base_r * 0.68f, ang0, ang1, 16);
        dl->PathStroke(col_gd(90), 0, 2.2f * ds);
    }

    // Centered Triforce inside hero circle
    float pulse = 0.85f + 0.15f * sinf(t * 1.8f);
    draw_triforce(dl, hero, base_r * 0.42f,
                  col_gd((int)(195 * pulse)),
                  col_gd((int)(45 * pulse)));

    // Rising golden motes
    for (auto& p : pts) {
        p.x += p.vx * 0.016f;
        p.y += p.vy * 0.016f;
        if (p.y < -0.04f) { p.y = 1.04f; }
        if (p.x < -0.02f) { p.x = 1.02f; }
        if (p.x > 1.02f) { p.x = -0.02f; }
        dl->AddCircleFilled(
            ImVec2(p.x * vp.x, p.y * vp.y),
            p.r * ds,
            IM_COL32(238, 198, 92, (int)(p.alpha * 180.0f * alpha_scale)),
            12);
    }

    // Smooth dark fade into the left navigation column & footer (MKW composition signature)
    if (!dim_for_subview) {
        dl->AddRectFilledMultiColor(
            ImVec2(0, 0), ImVec2(vp.x * 0.42f, vp.y),
            IM_COL32(10, 14, 20, 245), IM_COL32(10, 14, 20, 0),
            IM_COL32(10, 14, 20, 0), IM_COL32(10, 14, 20, 245));
        dl->AddRectFilledMultiColor(
            ImVec2(0, vp.y * 0.80f), vp,
            IM_COL32(10, 14, 20, 0), IM_COL32(10, 14, 20, 0),
            IM_COL32(10, 14, 20, 235), IM_COL32(10, 14, 20, 235));
    } else {
        dl->AddRectFilled(ImVec2(0, 0), vp, IM_COL32(10, 14, 20, 165));
    }
}

// ---------- App State & Business Logic ----------

enum Screen {
    SCREEN_MAIN = 0,
    SCREEN_SETTINGS,
    SCREEN_MODS,
    SCREEN_SAVES,
    SCREEN_UPDATES,
    SCREEN_GUIDE,
};

struct SettingsDraft {
    // Display
    std::string target_display;
    bool fullscreen = true;
    std::string resolution = "1920x1080";
    std::string fps_limit = "60";
    std::string vk_present = "mailbox";
    std::string aspect = "fit";
    int fov = 100;

    // Upscaling & Frame Gen
    std::string upscaler = "fsr";
    std::string upscaler_preset = "native";
    std::string dlss_preset = "transformer_gen1";
    bool dlss_nr = false;
    std::string dlss_nr_preset = "preset_b";
    std::string fg_mode = "off";
    std::string fg_mult = "2x";
    std::string reflex = "on";
    std::string antilag2 = "on";
    std::string render_scale = "game";
    bool dynamic_res = false;
    int sharpness = 80;

    // Graphics & Lighting
    std::string shadow_res = "game";
    std::string shadow_scale = "1";
    int shadow_range = 100;
    int grass_range = 100;
    int pcss = 0;
    std::string ao_mode = "native";
    int contact_shadows = 0;
    std::string aniso = "16";
    std::string color_preset = "default";
    int color_brightness = 0;
    int color_contrast = 100;
    int color_saturation = 100;
    float color_gamma = 1.0f;
    bool pipe_prebuild = true;

    // Controls, Menu & Audio
    std::string menu_theme = "totk";
    bool touchpad_menu = true;
    std::string pad_layout = "auto";
    std::string prompts = "nintendo";
    bool dualsense = false;
    std::string mouse_mode = "direct";
    bool menu_cursor = true;
    bool map_click = true;
    bool dialogue_click = true;
    std::string audio_channels = "auto";
    bool sound_effects = true;
    bool show_launcher = true;
};

struct ReleaseInfo {
    bool checked = false;
    bool fetching = false;
    bool updating = false;
    bool update_available = false;
    std::string tag;
    std::string name;
    std::string zip_url;
    std::string body;
    std::string status_msg;
};

struct AppState {
    fs::path exe_dir;
    fs::path game_dir;
    bool has_totk_exe = false;
    bool has_game_files = false;
    std::string romfs_version = "v143";
    std::string gpu_name;
    std::vector<MonitorInfoItem> displays;

    Screen screen = SCREEN_MAIN;
    int settings_tab = 0;

    LauncherConfig launcher_cfg;
    IniStore ini;
    SettingsDraft draft;

    std::vector<ModEntry> mods;
    int selected_mod = -1;
    std::string mod_status;

    std::vector<SaveBackupItem> backups;
    int selected_backup = -1;
    char backup_tag[64] = "";
    std::string save_status;

    std::mutex bg_mtx;
    std::atomic<bool> patch_running{false};
    std::string patch_status;

    ReleaseInfo rel;

    std::string banner_msg;
    bool banner_is_error = false;
    double banner_until = 0.0;

    ImGuiID last_hovered_id = 0;
    HWND hwnd = nullptr;
};

void play_sound(const AppState& st, bool click) {
    if (!st.draft.sound_effects) return;
    const unsigned char* data = click ? kClickWav : kHoverWav;
    PlaySoundA(reinterpret_cast<LPCSTR>(data), nullptr, SND_MEMORY | SND_ASYNC | SND_NODEFAULT);
}

void set_banner(AppState& st, const std::string& msg, bool err = false) {
    st.banner_msg = msg;
    st.banner_is_error = err;
    st.banner_until = ImGui::GetTime() + 5.5;
}

void load_draft_from_disk(AppState& st) {
    st.launcher_cfg = load_launcher_config(st.game_dir);
    st.ini.load_file(st.game_dir / "totk.ini");

    auto& d = st.draft;
    d.target_display = st.launcher_cfg.target_display;
    if (d.target_display.empty() && !st.displays.empty()) {
        d.target_display = st.displays[0].device;
    }
    d.sound_effects = st.launcher_cfg.sound_effects;
    d.show_launcher = st.launcher_cfg.show_launcher;

    d.fullscreen = st.ini.get_bool("fullscreen", true);
    d.resolution = st.ini.get("output_res", st.ini.get("window_size", "1920x1080"));
    d.fps_limit = st.ini.get("fps_limit", "60");
    d.vk_present = to_lower(st.ini.get("vk_present", "mailbox"));
    d.aspect = to_lower(st.ini.get("aspect", "fit"));
    d.fov = st.ini.get_int("fov", 100);

    d.upscaler = to_lower(st.ini.get("upscaler", "fsr"));
    d.upscaler_preset = to_lower(st.ini.get("upscaler_preset", "native"));
    if (d.upscaler_preset == "dlaa") d.upscaler_preset = "native";
    d.dlss_preset = normalize_dlss_preset(st.ini.get("dlss_preset", "transformer_gen1"));
    d.dlss_nr = st.ini.get_bool("dlss_nr", false);
    d.dlss_nr_preset = to_lower(st.ini.get("dlss_nr_preset", "preset_b"));
    d.fg_mode = to_lower(st.ini.get("fg_mode", "off"));
    d.fg_mult = to_lower(st.ini.get("fg_mult", "2x"));
    d.reflex = to_lower(st.ini.get("reflex", "on"));
    d.antilag2 = to_lower(st.ini.get("antilag2", "on"));
    d.render_scale = to_lower(st.ini.get("render_scale", "game"));
    d.dynamic_res = st.ini.get_bool("dynamic_res", false);
    d.sharpness = st.ini.get_int("sharpness", 80);

    d.shadow_res = to_lower(st.ini.get("shadow_res", "game"));
    d.shadow_scale = st.ini.get("shadow_scale", "1");
    d.shadow_range = st.ini.get_int("shadow_range", 100);
    d.grass_range = st.ini.get_int("grass_range", 100);
    d.pcss = st.ini.get_int("pcss", 0);
    d.ao_mode = to_lower(st.ini.get("ao_mode", "native"));
    d.contact_shadows = st.ini.get_int("contact_shadows", 0);
    d.aniso = to_lower(st.ini.get("aniso", "16"));
    d.color_preset = to_lower(st.ini.get("color_preset", "default"));
    d.color_brightness = st.ini.get_int("color_brightness", 0);
    d.color_contrast = st.ini.get_int("color_contrast", 100);
    d.color_saturation = st.ini.get_int("color_saturation", 100);
    d.color_gamma = st.ini.get_float("color_gamma", 1.0f);
    d.pipe_prebuild = st.ini.get_bool("pipe_prebuild", true);

    d.menu_theme = to_lower(st.ini.get("menu_theme", "totk"));
    d.touchpad_menu = st.ini.get_bool("touchpad_menu", true);
    d.pad_layout = to_lower(st.ini.get("pad_layout", "auto"));
    d.prompts = to_lower(st.ini.get("prompts", "nintendo"));
    d.dualsense = st.ini.get_bool("dualsense", false);
    d.mouse_mode = to_lower(st.ini.get("mouse_mode", "direct"));
    d.menu_cursor = st.ini.get_bool("menu_cursor", true);
    d.map_click = st.ini.get_bool("map_click", true);
    d.dialogue_click = st.ini.get_bool("dialogue_click", true);
    d.audio_channels = to_lower(st.ini.get("audio_channels", "auto"));
}

// Resolve whether prompts folder needs '-label' (when pad_layout == auto|xbox) or base positional (nintendo).
std::string resolve_prompts_folder_style(const std::string& prompts, const std::string& pad_layout) {
    if (prompts == "xbox" || prompts == "dualsense" || prompts == "dualshock4") {
        return (pad_layout == "nintendo") ? prompts : (prompts + "-label");
    }
    return prompts;
}

fs::path find_patcher_exe(const AppState& st) {
    const fs::path cands[] = {
        st.exe_dir / "TotKPatcher.exe",
        st.game_dir / "TotKPatcher.exe",
    };
    for (const auto& c : cands) {
        if (fs::is_regular_file(c)) return c;
    }
    return {};
}

static std::pair<fs::path, fs::path> find_python_patcher_fallback(const fs::path& game_dir) {
    fs::path root = game_dir.parent_path();
    fs::path py = root / "python" / "python.exe";
    fs::path script = root / "tools" / "make_romfs_patches.py";
    if (fs::is_regular_file(py) && fs::is_regular_file(script)) return {py, script};
    return {};
}

void run_prompts_patcher_async(AppState& st, const std::string& style) {
    if (st.patch_running.exchange(true)) return;
    fs::path patcher = find_patcher_exe(st);
    auto py_fb = find_python_patcher_fallback(st.game_dir);
    fs::path romfs = st.game_dir / "romfs";
    fs::path out_dir = st.game_dir / ("romfs-patches-" + style);
    std::string ver = st.romfs_version;
    fs::path cwd = st.game_dir;

    {
        std::lock_guard<std::mutex> lk(st.bg_mtx);
        st.patch_status = "Building controller prompt overlay (" + style + ")...";
    }

    std::thread([&st, patcher, py_fb, style, ver, romfs, out_dir, cwd]() {
        std::string output;
        int rc = -1;
        if (!patcher.empty()) {
            std::wstring cmd = L"\"" + patcher.wstring() + L"\" --run-prompts-patcher \"" +
                               utf8_to_wide(style) + L"\" \"" + utf8_to_wide(ver) + L"\" \"" +
                               romfs.wstring() + L"\" \"" + out_dir.wstring() + L"\"";
            rc = run_hidden_process(cmd, cwd, &output);
        } else if (!py_fb.first.empty()) {
            std::wstring cmd = L"\"" + py_fb.first.wstring() + L"\" \"" + py_fb.second.wstring() +
                               L"\" --version \"" + utf8_to_wide(ver) + L"\" --romfs \"" +
                               romfs.wstring() + L"\" --out \"" + out_dir.wstring() +
                               L"\" --prompts \"" + utf8_to_wide(style) + L"\"";
            rc = run_hidden_process(cmd, cwd, &output);
        }
        {
            std::lock_guard<std::mutex> lk(st.bg_mtx);
            if (rc == 0) {
                st.patch_status = "Prompts overlay ready (" + style + ").";
            } else if (patcher.empty() && py_fb.first.empty()) {
                st.patch_status = "TotKPatcher.exe not found next to launcher — skipped overlay build.";
            } else {
                st.patch_status = "Prompt patcher finished with exit code " + std::to_string(rc) + ".";
            }
        }
        st.patch_running.store(false);
    }).detach();
}

void run_ultrawide_patcher_async(AppState& st, const std::string& res, bool restore_only) {
    if (st.patch_running.exchange(true)) return;
    fs::path patcher = find_patcher_exe(st);
    auto py_fb = find_python_patcher_fallback(st.game_dir);
    fs::path romfs = st.game_dir / "romfs";
    fs::path out_dir = st.game_dir / ("romfs-patches-" + res);
    std::string ver = st.romfs_version;
    fs::path cwd = st.game_dir;

    {
        std::lock_guard<std::mutex> lk(st.bg_mtx);
        st.patch_status = restore_only ? "Restoring 16:9 UI mod backups..." : ("Building Ultrawide HUD Fix (" + res + ")...");
    }

    std::thread([&st, patcher, py_fb, res, ver, romfs, out_dir, cwd, restore_only]() {
        std::string output;
        int rc = -1;
        if (!patcher.empty()) {
            std::wstring cmd = restore_only
                ? (L"\"" + patcher.wstring() + L"\" --restore-ui-mods \"" + cwd.wstring() + L"\"")
                : (L"\"" + patcher.wstring() + L"\" --run-ultrawide-patcher \"" + utf8_to_wide(res) +
                   L"\" \"" + utf8_to_wide(ver) + L"\" \"" + romfs.wstring() + L"\" \"" + out_dir.wstring() + L"\"");
            rc = run_hidden_process(cmd, cwd, &output);
        } else if (!restore_only && !py_fb.first.empty()) {
            std::wstring cmd = L"\"" + py_fb.first.wstring() + L"\" \"" + py_fb.second.wstring() +
                               L"\" --version \"" + utf8_to_wide(ver) + L"\" --romfs \"" +
                               romfs.wstring() + L"\" --out \"" + out_dir.wstring() +
                               L"\" --aspect \"" + utf8_to_wide(res) + L"\"";
            rc = run_hidden_process(cmd, cwd, &output);
        }
        {
            std::lock_guard<std::mutex> lk(st.bg_mtx);
            if (rc == 0) {
                st.patch_status = restore_only ? "16:9 HUD backups restored." : ("Ultrawide HUD Fix ready for " + res + ".");
            } else if (patcher.empty() && py_fb.first.empty()) {
                st.patch_status = "TotKPatcher.exe not found next to launcher.";
            } else {
                st.patch_status = "Ultrawide patcher returned exit code " + std::to_string(rc) + ".";
            }
        }
        st.patch_running.store(false);
    }).detach();
}

void disable_conflicting_prompt_mods(const fs::path& game_dir, IniStore& ini, std::map<std::string, std::string>& updates) {
    auto mods = scan_mods(game_dir, ini);
    auto disabled = split_csv(ini.get("mods_disabled"));
    bool changed = false;
    for (const auto& m : mods) {
        std::string low = to_lower(m.name);
        if (low.find("ps5 ui") != std::string::npos || low.find("xbox ui") != std::string::npos) {
            bool already = false;
            for (const auto& d : disabled) {
                if (_stricmp(d.c_str(), m.name.c_str()) == 0) { already = true; break; }
            }
            if (!already) {
                disabled.push_back(m.name);
                changed = true;
            }
        }
    }
    if (changed) {
        updates["mods_disabled"] = join_csv(disabled);
    }
}

void save_draft_to_disk(AppState& st) {
    const auto& d = st.draft;
    st.launcher_cfg.target_display = d.target_display;
    st.launcher_cfg.sound_effects = d.sound_effects;
    st.launcher_cfg.show_launcher = d.show_launcher;
    save_launcher_config(st.game_dir, st.launcher_cfg);

    std::map<std::string, std::string> upd;
    upd["fullscreen"] = d.fullscreen ? "1" : "0";
    upd["window_size"] = d.resolution;
    upd["output_res"] = d.resolution;
    upd["fps_limit"] = d.fps_limit;
    if (d.fps_limit != "30") {
        upd["realtime"] = "1";
        upd["cloth_realtime"] = "1";
        upd["highfps_fix"] = "1";
        upd["climb_fix"] = "1";
    }
    upd["vk_present"] = d.vk_present;
    upd["aspect"] = d.aspect;
    upd["fov"] = std::to_string(d.fov);

    upd["upscaler"] = d.upscaler;
    upd["upscaler_preset"] = d.upscaler_preset;
    upd["dlss"] = (d.upscaler_preset == "native") ? "dlaa" : d.upscaler_preset;
    upd["dlaa"] = (d.upscaler == "dlss") ? "1" : "0";
    if (d.upscaler != "dlss") {
        if (d.upscaler_preset == "native") upd["render_scale"] = "100";
        else if (d.upscaler_preset == "quality") upd["render_scale"] = "67";
        else if (d.upscaler_preset == "balanced") upd["render_scale"] = "58";
        else if (d.upscaler_preset == "performance") upd["render_scale"] = "50";
        else if (d.upscaler_preset == "ultra_performance") upd["render_scale"] = "33";
    } else {
        upd["render_scale"] = d.render_scale;
    }
    upd["dlss_preset"] = d.dlss_preset;
    upd["dlss_nr"] = d.dlss_nr ? "1" : "0";
    upd["dlss_nr_preset"] = d.dlss_nr_preset;
    upd["fg_mode"] = d.fg_mode;
    upd["fg_mult"] = d.fg_mult;
    upd["reflex"] = d.reflex;
    upd["antilag2"] = d.antilag2;
    upd["dynamic_res"] = d.dynamic_res ? "1" : "0";
    upd["sharpness"] = std::to_string(d.sharpness);

    upd["shadow_res"] = d.shadow_res;
    upd["shadow_scale"] = d.shadow_scale;
    upd["shadow_range"] = std::to_string(d.shadow_range);
    upd["grass_range"] = std::to_string(d.grass_range);
    upd["pcss"] = std::to_string(d.pcss);
    upd["ao_mode"] = d.ao_mode;
    upd["contact_shadows"] = std::to_string(d.contact_shadows);
    upd["aniso"] = d.aniso;
    upd["color_preset"] = d.color_preset;
    upd["color_brightness"] = std::to_string(d.color_brightness);
    upd["color_contrast"] = std::to_string(d.color_contrast);
    upd["color_saturation"] = std::to_string(d.color_saturation);
    char gbuf[16];
    snprintf(gbuf, sizeof(gbuf), "%.2f", d.color_gamma);
    upd["color_gamma"] = gbuf;
    upd["pipe_prebuild"] = d.pipe_prebuild ? "1" : "0";

    upd["menu_theme"] = d.menu_theme;
    upd["touchpad_menu"] = d.touchpad_menu ? "1" : "0";
    upd["pad_layout"] = d.pad_layout;
    upd["prompts"] = d.prompts;
    upd["dualsense"] = d.dualsense ? "1" : "0";
    upd["mouse_mode"] = d.mouse_mode;
    upd["menu_cursor"] = d.menu_cursor ? "1" : "0";
    upd["map_click"] = d.map_click ? "1" : "0";
    upd["dialogue_click"] = d.dialogue_click ? "1" : "0";
    upd["audio_channels"] = d.audio_channels;

    if (d.prompts != "nintendo") {
        disable_conflicting_prompt_mods(st.game_dir, st.ini, upd);
    }

    st.ini.save_updates(st.game_dir / "totk.ini", upd);

    if (d.prompts != "nintendo") {
        std::string style = resolve_prompts_folder_style(d.prompts, d.pad_layout);
        fs::path prompt_dir = st.game_dir / ("romfs-patches-" + style);
        if (!fs::is_directory(prompt_dir) && fs::is_directory(st.game_dir / "romfs")) {
            run_prompts_patcher_async(st, style);
        }
    }
    set_banner(st, "Settings saved to totk.ini & launcher_config.json.");
}

void apply_quality_preset(AppState& st, const char* preset_name) {
    auto& d = st.draft;
    if (strcmp(preset_name, "max_fps") == 0) {
        d.upscaler = "fsr";
        d.upscaler_preset = "native";
        d.dlss_preset = "transformer_gen1";
        d.dlss_nr = false;
        d.fg_mode = "off";
        d.shadow_res = "game";
        d.shadow_scale = "1";
        d.shadow_range = 100;
        d.grass_range = 100;
        d.ao_mode = "native";
        d.contact_shadows = 0;
        d.pcss = 0;
        set_banner(st, "Max FPS (Default) preset selected — click Save & Apply.");
    } else if (strcmp(preset_name, "enhanced") == 0) {
        d.upscaler = "dlss";
        d.upscaler_preset = "quality";
        d.dlss_preset = "transformer_gen1";
        d.dlss_nr = false;
        d.shadow_res = "2048";
        d.shadow_scale = "2";
        d.shadow_range = 150;
        d.grass_range = 150;
        d.ao_mode = "xegtao";
        d.contact_shadows = 55;
        d.pcss = 40;
        set_banner(st, "Enhanced High preset selected — click Save & Apply.");
    } else if (strcmp(preset_name, "ultra") == 0) {
        d.upscaler = "dlss";
        d.upscaler_preset = "quality";
        d.dlss_preset = "transformer_gen2";
        d.dlss_nr = true;
        d.dlss_nr_preset = "preset_b";
        d.shadow_res = "2048";
        d.shadow_scale = "3";
        d.shadow_range = 250;
        d.grass_range = 250;
        d.ao_mode = "xegtao";
        d.contact_shadows = 80;
        d.pcss = 65;
        set_banner(st, "SteelTemple Ultra preset selected — click Save & Apply.");
    } else if (strcmp(preset_name, "handheld") == 0) {
        d.resolution = "1280x800";
        d.fullscreen = true;
        d.fps_limit = "45";
        d.upscaler = "fsr";
        d.upscaler_preset = "balanced";
        d.dlss_nr = false;
        d.fg_mode = "off";
        d.shadow_res = "768";
        d.shadow_scale = "1";
        d.shadow_range = 100;
        d.grass_range = 100;
        d.ao_mode = "native";
        d.contact_shadows = 0;
        d.pcss = 0;
        set_banner(st, "Handheld / 1280x800 preset selected — click Save & Apply.");
    }
}

void launch_game(const AppState& st, bool warm_only = false) {
    fs::path exe = st.game_dir / "totk.exe";
    if (!fs::is_regular_file(exe)) return;
    std::vector<std::wstring> args;
    if (warm_only) args.push_back(L"--warm-shaders");
    spawn_detached(exe, args, st.game_dir);
}

void create_desktop_shortcut(AppState& st) {
    fs::path self_exe = st.exe_dir / "TotKLauncher.exe";
    fs::path icon_exe = fs::is_regular_file(st.game_dir / "totk.exe") ? (st.game_dir / "totk.exe") : self_exe;
    std::wstring ps =
        L"powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command \""
        L"$w = New-Object -ComObject WScript.Shell; "
        L"$s = $w.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\\Tears of the Kingdom PC.lnk'); "
        L"$s.TargetPath = '" + self_exe.wstring() + L"'; "
        L"$s.Arguments = '--launcher'; "
        L"$s.WorkingDirectory = '" + st.game_dir.wstring() + L"'; "
        L"$s.IconLocation = '" + icon_exe.wstring() + L",0'; "
        L"$s.Save()\"";
    std::string out;
    int rc = run_hidden_process(ps, st.game_dir, &out);
    set_banner(st, rc == 0 ? "Desktop shortcut created." : "Failed to create desktop shortcut.", rc != 0);
}

// ---------- GitHub Release Check & Self-Update ----------

static std::string winhttp_get_text(const std::wstring& host, const std::wstring& path) {
    std::string body;
    HINTERNET ses = WinHttpOpen(L"TotK-Launcher/1.0", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, nullptr, nullptr, 0);
    if (!ses) return body;
    HINTERNET con = WinHttpConnect(ses, host.c_str(), INTERNET_DEFAULT_HTTPS_PORT, 0);
    if (con) {
        HINTERNET req = WinHttpOpenRequest(con, L"GET", path.c_str(), nullptr, WINHTTP_NO_REFERER,
                                           WINHTTP_DEFAULT_ACCEPT_TYPES, WINHTTP_FLAG_SECURE);
        if (req) {
            if (WinHttpSendRequest(req, nullptr, 0, nullptr, 0, 0, 0) && WinHttpReceiveResponse(req, nullptr)) {
                DWORD avail = 0;
                while (WinHttpQueryDataAvailable(req, &avail) && avail > 0) {
                    std::string chunk(avail, '\0');
                    DWORD read = 0;
                    if (WinHttpReadData(req, chunk.data(), avail, &read) && read > 0) {
                        body.append(chunk.data(), read);
                    }
                }
            }
            WinHttpCloseHandle(req);
        }
        WinHttpCloseHandle(con);
    }
    WinHttpCloseHandle(ses);
    return body;
}

static std::string normalize_release_ver(std::string s) {
    s = to_lower(trim(s));
    if (s.size() > 1 && s[0] == 'v' && (isdigit((unsigned char)s[1]) || s.rfind("vbeta", 0) == 0)) {
        s = s.substr(1);
    }
    std::string out;
    for (char c : s) {
        if (isalnum((unsigned char)c) || c == '.') out += c;
    }
    return out;
}

void check_updates_async(AppState& st) {
    if (st.rel.fetching) return;
    st.rel.fetching = true;
    {
        std::lock_guard<std::mutex> lk(st.bg_mtx);
        st.rel.status_msg = "Checking GitHub releases...";
    }
    std::thread([&st]() {
        std::string json = winhttp_get_text(L"api.github.com",
                                            L"/repos/STS78721/totk-pc-recomp-SteelTempleBuild/releases/latest");
        std::lock_guard<std::mutex> lk(st.bg_mtx);
        st.rel.fetching = false;
        st.rel.checked = true;
        if (json.empty()) {
            st.rel.status_msg = "Could not reach GitHub releases API.";
            return;
        }
        st.rel.tag = json_extract_string(json, "tag_name");
        st.rel.name = json_extract_string(json, "name");
        st.rel.body = json_extract_string(json, "body");
        // Find -Update.zip browser_download_url
        size_t pos = 0;
        st.rel.zip_url.clear();
        while ((pos = json.find("browser_download_url", pos)) != std::string::npos) {
            std::string url = json_extract_string(json.substr(pos, 512), "browser_download_url");
            if (!url.empty() && to_lower(url).find("update.zip") != std::string::npos) {
                st.rel.zip_url = url;
                break;
            }
            pos += 20;
        }
        std::string inst_norm = normalize_release_ver(TOTK_LAUNCHER_VERSION);
        std::string tag_norm = normalize_release_ver(st.rel.tag);
        std::string name_norm = normalize_release_ver(st.rel.name);
        bool matches_installed = (!tag_norm.empty() && tag_norm == inst_norm) ||
                                 (!name_norm.empty() && name_norm.find(inst_norm) != std::string::npos);
        st.rel.update_available = !st.rel.tag.empty() && !matches_installed;
        if (st.rel.tag.empty()) {
            st.rel.status_msg = "No release tag returned.";
        } else if (st.rel.update_available) {
            st.rel.status_msg = "New update available: " + st.rel.tag;
        } else {
            st.rel.status_msg = "You are on the latest build (" TOTK_LAUNCHER_VERSION ").";
        }
    }).detach();
}

void install_update_async(AppState& st) {
    if (st.rel.updating || st.rel.zip_url.empty()) return;
    st.rel.updating = true;
    std::string url = st.rel.zip_url;
    fs::path game_dir = st.game_dir;
    fs::path self_exe = st.exe_dir / "TotKLauncher.exe";
    DWORD self_pid = GetCurrentProcessId();
    {
        std::lock_guard<std::mutex> lk(st.bg_mtx);
        st.rel.status_msg = "Downloading & validating update package...";
    }
    std::thread([&st, url, game_dir, self_exe, self_pid]() {
        fs::path prep_ps1 = fs::temp_directory_path() / "totk_prep_update.ps1";
        fs::path swap_ps1 = fs::temp_directory_path() / "totk_swap_update.ps1";
        {
            std::ofstream ps(prep_ps1, std::ios::binary | std::ios::trunc);
            ps << "$ErrorActionPreference = 'Stop'\n"
               << "$zip = Join-Path $env:TEMP 'totk_update.zip'\n"
               << "$stage = Join-Path $env:TEMP 'totk_update_stage'\n"
               << "if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }\n"
               << "Invoke-WebRequest -Uri " << quote_win(url) << " -OutFile $zip -UseBasicParsing\n"
               << "Expand-Archive -Path $zip -DestinationPath $stage -Force\n"
               << "$gameExe = Join-Path $stage 'totk.exe'\n"
               << "if (Test-Path $gameExe) {\n"
               << "  & $gameExe --exefs (Join-Path " << quote_win(game_dir.string()) << " 'exefs') "
               << "--romfs (Join-Path " << quote_win(game_dir.string()) << " 'romfs') "
               << "--profile (Join-Path " << quote_win(game_dir.string()) << " 'profile') --probe-loader\n"
               << "  if ($LASTEXITCODE -ne 0) { throw 'Update loader probe failed; no game files changed.' }\n"
               << "}\n";
        }
        std::wstring cmd = L"powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"" + prep_ps1.wstring() + L"\"";
        std::string out;
        int rc = run_hidden_process(cmd, game_dir, &out);
        if (rc != 0) {
            std::lock_guard<std::mutex> lk(st.bg_mtx);
            st.rel.updating = false;
            st.rel.status_msg = "Update failed (exit " + std::to_string(rc) + "). No game files replaced.";
            return;
        }
        {
            std::ofstream sp(swap_ps1, std::ios::binary | std::ios::trunc);
            sp << "$ErrorActionPreference = 'Stop'\n"
               << "$stage = Join-Path $env:TEMP 'totk_update_stage'\n"
               << "Wait-Process -Id " << self_pid << " -ErrorAction SilentlyContinue\n"
               << "Start-Sleep -Milliseconds 350\n"
               << "Get-ChildItem $stage -File | ForEach-Object {\n"
               << "  if ($_.Name -ieq 'totk.ini') { return }\n"
               << "  Copy-Item $_.FullName (Join-Path " << quote_win(game_dir.string()) << " $_.Name) -Force\n"
               << "}\n"
               << "Start-Process -FilePath " << quote_win(self_exe.string()) << " -ArgumentList '--launcher' -WorkingDirectory " << quote_win(game_dir.string()) << "\n";
        }
        std::wstring swap_cmd = L"powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File \"" + swap_ps1.wstring() + L"\"";
        STARTUPINFOW si{};
        si.cb = sizeof(si);
        PROCESS_INFORMATION pi{};
        if (CreateProcessW(nullptr, swap_cmd.data(), nullptr, nullptr, FALSE,
                           CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP, nullptr, game_dir.wstring().c_str(), &si, &pi)) {
            CloseHandle(pi.hThread);
            CloseHandle(pi.hProcess);
            {
                std::lock_guard<std::mutex> lk(st.bg_mtx);
                st.rel.status_msg = "Update verified! Applying and restarting...";
            }
            if (st.hwnd) PostMessageW(st.hwnd, WM_CLOSE, 0, 0);
        } else {
            std::lock_guard<std::mutex> lk(st.bg_mtx);
            st.rel.updating = false;
            st.rel.status_msg = "Could not launch update swapper.";
        }
    }).detach();
}

// ---------- UI Widgets ----------

void apply_mkw_style(float ds) {
    ImGuiStyle& st = ImGui::GetStyle();
    st = ImGuiStyle();
    st.WindowPadding = ImVec2(24 * ds, 20 * ds);
    st.FramePadding = ImVec2(12 * ds, 7 * ds);
    st.ItemSpacing = ImVec2(10 * ds, 8 * ds);
    st.WindowRounding = 0.0f;
    st.ChildRounding = 8.0f * ds;
    st.FrameRounding = 7.0f * ds;
    st.GrabRounding = 6.0f * ds;
    st.PopupRounding = 7.0f * ds;
    st.ScrollbarSize = 11.0f * ds;

    ImVec4* c = st.Colors;
    c[ImGuiCol_WindowBg] = ImVec4(0.039f, 0.055f, 0.078f, 0.0f);
    c[ImGuiCol_ChildBg] = ImVec4(0.065f, 0.090f, 0.125f, 0.86f);
    c[ImGuiCol_PopupBg] = ImVec4(0.075f, 0.105f, 0.145f, 0.98f);
    c[ImGuiCol_Border] = ImVec4(0.18f, 0.25f, 0.34f, 0.72f);
    c[ImGuiCol_Text] = ImVec4(0.95f, 0.97f, 0.99f, 1.0f);
    c[ImGuiCol_TextDisabled] = ImVec4(0.56f, 0.62f, 0.70f, 1.0f);
    c[ImGuiCol_FrameBg] = ImVec4(0.11f, 0.15f, 0.21f, 0.95f);
    c[ImGuiCol_FrameBgHovered] = ImVec4(0.15f, 0.21f, 0.29f, 1.0f);
    c[ImGuiCol_FrameBgActive] = ImVec4(0.18f, 0.26f, 0.35f, 1.0f);
    c[ImGuiCol_Button] = ImVec4(0.12f, 0.16f, 0.22f, 0.90f);
    c[ImGuiCol_ButtonHovered] = ImVec4(0.17f, 0.24f, 0.33f, 0.98f);
    c[ImGuiCol_ButtonActive] = ImVec4(0.13f, 0.56f, 0.45f, 1.0f);
    c[ImGuiCol_CheckMark] = ImVec4(0.10f, 0.82f, 0.64f, 1.0f);
    c[ImGuiCol_SliderGrab] = ImVec4(0.10f, 0.82f, 0.64f, 1.0f);
    c[ImGuiCol_SliderGrabActive] = ImVec4(0.24f, 0.92f, 0.73f, 1.0f);
    c[ImGuiCol_Header] = ImVec4(0.10f, 0.82f, 0.64f, 0.24f);
    c[ImGuiCol_HeaderHovered] = ImVec4(0.10f, 0.82f, 0.64f, 0.38f);
    c[ImGuiCol_HeaderActive] = ImVec4(0.10f, 0.82f, 0.64f, 0.52f);
}

bool emerald_button(AppState& st, const char* label, ImVec2 sz) {
    ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0.102f, 0.824f, 0.639f, 1.0f));
    ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(0.239f, 0.902f, 0.722f, 1.0f));
    ImGui::PushStyleColor(ImGuiCol_ButtonActive, ImVec4(0.075f, 0.700f, 0.540f, 1.0f));
    ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.024f, 0.141f, 0.110f, 1.0f));
    bool clicked = ImGui::Button(label, sz);
    ImGui::PopStyleColor(4);
    if (ImGui::IsItemHovered() && st.last_hovered_id != ImGui::GetItemID()) {
        st.last_hovered_id = ImGui::GetItemID();
        play_sound(st, false);
    }
    if (clicked) play_sound(st, true);
    return clicked;
}

bool nav_button(AppState& st, const char* label, float w, float h, bool active = false) {
    if (active) {
        ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0.11f, 0.28f, 0.25f, 0.95f));
        ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(0.14f, 0.35f, 0.31f, 1.0f));
    } else {
        ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0.10f, 0.14f, 0.19f, 0.72f));
        ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(0.16f, 0.22f, 0.30f, 0.94f));
    }
    ImGui::PushStyleColor(ImGuiCol_ButtonActive, ImVec4(0.10f, 0.82f, 0.64f, 0.35f));
    bool clicked = ImGui::Button(label, ImVec2(w, h));
    ImGui::PopStyleColor(3);
    if (ImGui::IsItemHovered() && st.last_hovered_id != ImGui::GetItemID()) {
        st.last_hovered_id = ImGui::GetItemID();
        play_sound(st, false);
    }
    if (clicked) play_sound(st, true);
    return clicked;
}

bool combo_strings(const char* label, std::string& val,
                   const std::vector<std::pair<std::string, std::string>>& items, float width = 260.0f) {
    std::string preview = val;
    for (const auto& [k, lbl] : items) {
        if (k == val) { preview = lbl; break; }
    }
    bool changed = false;
    ImGui::SetNextItemWidth(width);
    if (ImGui::BeginCombo(label, preview.c_str())) {
        for (const auto& [k, lbl] : items) {
            bool sel = (k == val);
            if (ImGui::Selectable(lbl.c_str(), sel)) {
                val = k;
                changed = true;
            }
            if (sel) ImGui::SetItemDefaultFocus();
        }
        ImGui::EndCombo();
    }
    return changed;
}

void draw_setting_desc(const char* desc, float ds) {
    ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.58f, 0.65f, 0.73f, 1.0f));
    ImGui::Indent(4.0f * ds);
    ImGui::TextWrapped("%s", desc);
    ImGui::Unindent(4.0f * ds);
    ImGui::PopStyleColor();
    ImGui::Spacing();
}

// ---------- Screens ----------

void render_main_screen(AppState& st, float ds, ImVec2 vp, ImFont* title_font) {
    ImDrawList* dl = ImGui::GetWindowDrawList();
    const float rail_x = 26.0f * ds;
    const float rail_w = 248.0f * ds;
    float y = 38.0f * ds;

    // Crest + Game Title header in left rail
    ImVec2 crest_c(rail_x + 18.0f * ds, y + 18.0f * ds);
    dl->AddCircleFilled(crest_c, 18.0f * ds, IM_COL32(20, 44, 42, 230), 36);
    dl->AddCircle(crest_c, 18.0f * ds, IM_COL32(26, 210, 163, 210), 36, 1.5f * ds);
    draw_triforce(dl, crest_c, 15.0f * ds, IM_COL32(240, 200, 92, 255), 0);

    ImGui::SetCursorPos(ImVec2(rail_x + 44.0f * ds, y + 1.0f * ds));
    if (title_font) ImGui::PushFont(title_font);
    ImGui::TextUnformatted("Tears of the Kingdom");
    if (title_font) ImGui::PopFont();
    ImGui::SetCursorPos(ImVec2(rail_x + 44.0f * ds, y + 23.0f * ds));
    ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.60f, 0.67f, 0.75f, 1.0f));
    ImGui::TextUnformatted("PC Recompiled · SteelTemple");
    ImGui::PopStyleColor();

    y += 66.0f * ds;
    ImGui::SetCursorPos(ImVec2(rail_x, y));
    if (!st.has_totk_exe || !st.has_game_files) ImGui::BeginDisabled();
    if (emerald_button(st, "Play", ImVec2(rail_w, 42.0f * ds))) {
        launch_game(st, false);
        if (st.hwnd) PostMessageW(st.hwnd, WM_CLOSE, 0, 0);
    }
    if (!st.has_totk_exe || !st.has_game_files) ImGui::EndDisabled();

    y += 54.0f * ds;
    const float nh = 34.0f * ds;
    const float gap = 6.0f * ds;

    auto item = [&](const char* lbl) {
        ImGui::SetCursorPos(ImVec2(rail_x, y));
        y += nh + gap;
        return nav_button(st, lbl, rail_w, nh, false);
    };

    bool upd_avail = false;
    std::string upd_tag;
    {
        std::lock_guard<std::mutex> lk(st.bg_mtx);
        upd_avail = st.rel.update_available;
        upd_tag = st.rel.tag;
    }

    if (item("Settings")) { st.screen = SCREEN_SETTINGS; }
    if (item("Mods")) { st.mods = scan_mods(st.game_dir, st.ini); st.screen = SCREEN_MODS; }
    if (item("Save Vault")) { st.backups = scan_save_backups(st.game_dir); st.screen = SCREEN_SAVES; }
    {
        std::string upd_lbl = upd_avail ? ("Updates  [NEW: " + upd_tag + "]") : "Updates";
        ImGui::SetCursorPos(ImVec2(rail_x, y));
        y += nh + gap;
        bool upd_clicked = upd_avail
            ? emerald_button(st, upd_lbl.c_str(), ImVec2(rail_w, nh))
            : nav_button(st, upd_lbl.c_str(), rail_w, nh, false);
        if (upd_clicked) {
            st.screen = SCREEN_UPDATES;
            if (!st.rel.checked) check_updates_async(st);
        }
    }
    if (item("Controller Guide")) { st.screen = SCREEN_GUIDE; }
    if (item("Desktop shortcut")) { create_desktop_shortcut(st); }
    if (item("Open folder")) { open_in_shell(st.game_dir.wstring()); }
    if (item("Quit")) {
        if (st.hwnd) PostMessageW(st.hwnd, WM_CLOSE, 0, 0);
    }

    // Bottom status + disclaimer bar
    const float foot_y = vp.y - 34.0f * ds;
    ImVec2 dot_c(rail_x + 5.0f * ds, foot_y + 8.0f * ds);
    bool ready = st.has_totk_exe && st.has_game_files;
    dl->AddCircleFilled(dot_c, 4.5f * ds,
                        upd_avail ? IM_COL32(26, 210, 163, 255)
                                  : (ready ? IM_COL32(26, 210, 163, 255) : IM_COL32(245, 184, 46, 255)),
                        16);
    ImGui::SetCursorPos(ImVec2(rail_x + 16.0f * ds, foot_y));
    std::string status = upd_avail
        ? ("Update available: " + upd_tag + " — open Updates to install")
        : (ready ? ("Ready · " + st.romfs_version + " · " + st.gpu_name)
                 : "Missing totk.exe / exefs / romfs — run Setup Wizard");
    ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.76f, 0.82f, 0.88f, 1.0f));
    ImGui::TextUnformatted(status.c_str());

    const char* right_txt = "Your own copy of the game · No game data included · " TOTK_LAUNCHER_VERSION;
    float rw = ImGui::CalcTextSize(right_txt).x;
    ImGui::SetCursorPos(ImVec2(vp.x - 24.0f * ds - rw, foot_y));
    ImGui::PopStyleColor();
    ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.52f, 0.59f, 0.67f, 1.0f));
    ImGui::TextUnformatted(right_txt);
    ImGui::PopStyleColor();
}

void render_settings_screen(AppState& st, float ds, ImVec2 vp, ImFont* title_font) {
    const float m = 24.0f * ds;
    ImGui::SetCursorPos(ImVec2(m, 18.0f * ds));
    if (nav_button(st, "< Back", 84.0f * ds, 32.0f * ds)) {
        st.screen = SCREEN_MAIN;
    }
    ImGui::SameLine(0, 14.0f * ds);
    if (title_font) ImGui::PushFont(title_font);
    ImGui::TextUnformatted("Settings");
    if (title_font) ImGui::PopFont();

    // Right-aligned Save & Reset in top bar
    float act_x = vp.x - m - 252.0f * ds;
    ImGui::SameLine(act_x);
    if (nav_button(st, "Reset Defaults", 122.0f * ds, 32.0f * ds)) {
        st.ini.load_text(reinterpret_cast<const char*>(kDefaultTotkIni));
        st.ini.set("dlss_preset", "transformer_gen1");
        st.ini.set("menu_theme", "totk");
        st.ini.set("touchpad_menu", "1");
        st.ini.save_updates(st.game_dir / "totk.ini", st.ini.values);
        load_draft_from_disk(st);
        set_banner(st, "Reset totk.ini to hardware-agnostic defaults.");
    }
    ImGui::SameLine(0, 8.0f * ds);
    if (emerald_button(st, "Save & Apply", ImVec2(122.0f * ds, 32.0f * ds))) {
        save_draft_to_disk(st);
    }

    // 1-Click Presets Row
    ImGui::SetCursorPos(ImVec2(m, 60.0f * ds));
    float pw = (vp.x - m * 2.0f - 24.0f * ds) * 0.25f;
    if (nav_button(st, "Max FPS (Default)", pw, 30.0f * ds)) apply_quality_preset(st, "max_fps");
    ImGui::SameLine(0, 8.0f * ds);
    if (nav_button(st, "Enhanced High", pw, 30.0f * ds)) apply_quality_preset(st, "enhanced");
    ImGui::SameLine(0, 8.0f * ds);
    if (nav_button(st, "SteelTemple Ultra", pw, 30.0f * ds)) apply_quality_preset(st, "ultra");
    ImGui::SameLine(0, 8.0f * ds);
    if (nav_button(st, "Handheld (800p)", pw, 30.0f * ds)) apply_quality_preset(st, "handheld");

    // Category tabs
    ImGui::SetCursorPos(ImVec2(m, 98.0f * ds));
    const char* tabs[] = {"Display & Window", "Upscaling & Frame Gen", "Graphics & Shaders", "Controls, Menu & Audio"};
    float tw = (vp.x - m * 2.0f - 24.0f * ds) * 0.25f;
    for (int i = 0; i < 4; ++i) {
        if (i) ImGui::SameLine(0, 8.0f * ds);
        if (nav_button(st, tabs[i], tw, 32.0f * ds, st.settings_tab == i)) {
            st.settings_tab = i;
        }
    }

    // Scrollable settings body
    ImGui::SetCursorPos(ImVec2(m, 140.0f * ds));
    float body_h = vp.y - 166.0f * ds;
    ImGui::BeginChild("settings_body", ImVec2(vp.x - m * 2.0f, body_h), ImGuiChildFlags_Borders);
    auto& d = st.draft;
    const float cw = 320.0f * ds;

    if (st.settings_tab == 0) {
        std::vector<std::pair<std::string, std::string>> disp_items;
        for (const auto& mon : st.displays) disp_items.push_back({mon.device, mon.label});
        combo_strings("Target Display", d.target_display, disp_items, cw);
        draw_setting_desc("Monitor where the launcher centers itself and the game opens.", ds);

        ImGui::Checkbox("Borderless / Fullscreen Mode", &d.fullscreen);
        draw_setting_desc("Uncheck for a resizable desktop window.", ds);

        std::string native_res = std::to_string(st.displays[0].w) + "x" + std::to_string(st.displays[0].h);
        combo_strings("Resolution", d.resolution, {
            {native_res, native_res + " (Display Native)"},
            {"1280x720", "1280x720 (720p)"},
            {"1280x800", "1280x800 (Handheld 16:10)"},
            {"1600x900", "1600x900 (900p)"},
            {"1920x1080", "1920x1080 (1080p)"},
            {"2560x1080", "2560x1080 (21:9 Ultrawide)"},
            {"2560x1440", "2560x1440 (1440p)"},
            {"3440x1440", "3440x1440 (21:9 UWQHD)"},
            {"3840x1600", "3840x1600 (21:9 38\")"},
            {"3840x2160", "3840x2160 (4K UHD)"},
            {"5120x1440", "5120x1440 (32:9 Superwide)"},
        }, cw);
        draw_setting_desc("Sets both window_size and output_res in totk.ini.", ds);

        combo_strings("Frame Rate Limit", d.fps_limit, {
            {"30", "30 FPS (Console)"}, {"40", "40 FPS"}, {"45", "45 FPS"}, {"60", "60 FPS"},
            {"90", "90 FPS"}, {"120", "120 FPS"}, {"144", "144 FPS"}, {"180", "180 FPS"},
            {"240", "240 FPS"}, {"display", "Display Refresh Rate"},
        }, cw);
        draw_setting_desc("Above 30 automatically enables realtime simulation, cloth and climb fixes.", ds);

        combo_strings("VSync / Presentation Mode", d.vk_present, {
            {"mailbox", "Mailbox (FastSync / Low Latency)"},
            {"fifo", "FIFO (Strict VSync)"},
            {"immediate", "Immediate (Uncapped / VRR)"},
        }, cw);
        combo_strings("Aspect Ratio Scaling", d.aspect, {
            {"fit", "Fit (Preserve Aspect)"},
            {"stretch", "Stretch (Fill Screen)"},
        }, cw);
        ImGui::SetNextItemWidth(cw);
        ImGui::SliderInt("Camera FOV (%)", &d.fov, 70, 140);
        draw_setting_desc("Game version 1.4.3 camera field of view multiplier (default 100%).", ds);

        // Ultrawide HUD Fix button
        {
            int rw = 1920, rh = 1080;
            if (sscanf(d.resolution.c_str(), "%dx%d", &rw, &rh) == 2 && rh > 0) {
                float asp = (float)rw / (float)rh;
                bool is_non_169 = std::fabs(asp - (16.0f / 9.0f)) > 0.05f;
                if (st.patch_running.load()) ImGui::BeginDisabled();
                if (is_non_169) {
                    std::string btxt = "Build Ultrawide HUD Fix (" + d.resolution + ")";
                    if (emerald_button(st, btxt.c_str(), ImVec2(290.0f * ds, 32.0f * ds))) {
                        save_draft_to_disk(st);
                        run_ultrawide_patcher_async(st, d.resolution, false);
                    }
                } else {
                    if (nav_button(st, "Restore 16:9 UI Mod Backups", 250.0f * ds, 32.0f * ds)) {
                        run_ultrawide_patcher_async(st, "1920x1080", true);
                    }
                }
                if (st.patch_running.load()) ImGui::EndDisabled();
            }
        }
    } else if (st.settings_tab == 1) {
        combo_strings("Upscaler Backend", d.upscaler, {
            {"dlss", "NVIDIA DLSS (RTX Only)"},
            {"fsr4", "AMD FSR 4 / FidelityFX"},
            {"xess", "Intel XeSS"},
            {"fsr", "AMD FSR 1.0 (Universal)"},
            {"bilinear", "Bilinear (Sharp Native)"},
        }, cw);
        draw_setting_desc("Active spatial or neural upscaler (gates DLSS-specific controls cleanly).", ds);

        combo_strings("Quality / Scale Preset", d.upscaler_preset, {
            {"native", "Native / DLAA (100%)"},
            {"quality", "Quality (67%)"},
            {"balanced", "Balanced (58%)"},
            {"performance", "Performance (50%)"},
            {"ultra_performance", "Ultra Performance (33%)"},
        }, cw);

        bool dlss_on = (d.upscaler == "dlss");
        if (!dlss_on) ImGui::BeginDisabled();
        combo_strings("DLSS Model Generation", d.dlss_preset, {
            {"cnn", "CNN Model (Classic)"},
            {"transformer_gen1", "Transformer Gen 1 (Presets J / K)"},
            {"transformer_gen2", "Transformer Gen 2 (Presets L / M)"},
        }, cw);
        draw_setting_desc("Selects CNN vs Transformer Gen 1 vs Gen 2; uses NVIDIA's recommended preset for your chosen scale.", ds);

        ImGui::Checkbox("Enable DLSS Neural Radiance (DLSS-NR)", &d.dlss_nr);
        if (!d.dlss_nr) ImGui::BeginDisabled();
        combo_strings("DLSS-NR Preset", d.dlss_nr_preset, {
            {"preset_a", "Preset A"}, {"preset_b", "Preset B"},
            {"preset_c", "Preset C"}, {"preset_d", "Preset D"}, {"preset_e", "Preset E"},
        }, cw);
        if (!d.dlss_nr) ImGui::EndDisabled();
        if (!dlss_on) ImGui::EndDisabled();

        ImGui::Spacing();
        combo_strings("Frame Generation", d.fg_mode, {
            {"off", "Off"}, {"dlss_fg", "NVIDIA DLSS Frame Gen"},
            {"fsr3_fg", "AMD FSR 3.1 Frame Gen"}, {"fsr4_fg", "AMD FSR 4 Frame Gen"}, {"xefg", "Intel XeFG"},
        }, cw);
        if (d.fg_mode != "dlss_fg") ImGui::BeginDisabled();
        combo_strings("Frame Gen Multiplier", d.fg_mult, {{"2x", "2x"}, {"4x", "4x"}, {"6x", "6x"}}, cw);
        if (d.fg_mode != "dlss_fg") ImGui::EndDisabled();

        combo_strings("NVIDIA Reflex", d.reflex, {{"off", "Off"}, {"on", "On"}, {"boost", "On + Boost"}}, cw);
        combo_strings("AMD Anti-Lag 2", d.antilag2, {{"off", "Off"}, {"on", "On"}}, cw);

        ImGui::Checkbox("Dynamic Resolution Scaling (game)", &d.dynamic_res);
        ImGui::SetNextItemWidth(cw);
        ImGui::SliderInt("Upscaler Sharpness", &d.sharpness, 0, 100);
    } else if (st.settings_tab == 2) {
        combo_strings("Sun Shadow Map Resolution", d.shadow_res, {
            {"game", "Game Default (Dynamic)"}, {"256", "256"}, {"512", "512"},
            {"768", "768"}, {"1024", "1024"}, {"1536", "1536"}, {"2048", "2048"},
        }, cw);
        combo_strings("Shadow Cascade Scale", d.shadow_scale, {
            {"1", "1x (960)"}, {"2", "2x (1920)"}, {"3", "3x (2880)"}, {"4", "4x (3840)"},
        }, cw);
        ImGui::SetNextItemWidth(cw);
        ImGui::SliderInt("Shadow Draw Distance (%)", &d.shadow_range, 50, 400);
        ImGui::SetNextItemWidth(cw);
        ImGui::SliderInt("Grass Draw Distance (%)", &d.grass_range, 50, 400);
        ImGui::SetNextItemWidth(cw);
        ImGui::SliderInt("PCSS Soft Shadows (%)", &d.pcss, 0, 200);
        combo_strings("Ambient Occlusion", d.ao_mode, {
            {"native", "Native"}, {"xegtao", "Intel XeGTAO"}, {"hbao", "HBAO"}, {"ssao", "Enhanced SSAO"}, {"off", "Off"},
        }, cw);
        ImGui::SetNextItemWidth(cw);
        ImGui::SliderInt("Contact Shadows (%)", &d.contact_shadows, 0, 100);
        combo_strings("Anisotropic Filtering", d.aniso, {
            {"game", "Game"}, {"2", "2x"}, {"4", "4x"}, {"8", "8x"}, {"16", "16x"},
        }, cw);
        combo_strings("Color Profile", d.color_preset, {
            {"default", "Default"}, {"vivid", "Vivid"}, {"clarity", "Clarity"}, {"custom", "Custom"},
        }, cw);
        ImGui::SetNextItemWidth(cw);
        ImGui::SliderInt("Brightness", &d.color_brightness, -30, 30);
        ImGui::SetNextItemWidth(cw);
        ImGui::SliderInt("Contrast (%)", &d.color_contrast, 70, 150);
        ImGui::SetNextItemWidth(cw);
        ImGui::SliderInt("Saturation (%)", &d.color_saturation, 50, 200);
        ImGui::SetNextItemWidth(cw);
        ImGui::SliderFloat("Gamma", &d.color_gamma, 0.80f, 1.20f, "%.2f");
        ImGui::Checkbox("Prebuild Known Vulkan Pipelines at Startup", &d.pipe_prebuild);
        if (!st.has_totk_exe) ImGui::BeginDisabled();
        if (nav_button(st, "Pre-Warm Vulkan Shaders", 220.0f * ds, 32.0f * ds)) {
            launch_game(st, true);
            set_banner(st, "Launched totk.exe --warm-shaders.");
        }
        if (!st.has_totk_exe) ImGui::EndDisabled();
    } else if (st.settings_tab == 3) {
        combo_strings("In-Game F1 Menu Theme", d.menu_theme, {
            {"totk", "TOTK Zonai & Gold"}, {"dark", "Dark Slate"}, {"light", "Clean Light"},
        }, cw);
        ImGui::Checkbox("PS4 / PS5 Touchpad Toggles In-Game Menu", &d.touchpad_menu);
        combo_strings("Gamepad Button Layout", d.pad_layout, {
            {"auto", "Auto (Follows Controller / Xbox Standard)"},
            {"xbox", "Xbox / Label-Match"},
            {"nintendo", "Nintendo Positional (Swap A/B & X/Y)"},
        }, cw);
        combo_strings("On-Screen Button Prompts", d.prompts, {
            {"nintendo", "Switch / Nintendo"},
            {"dualsense", "PlayStation 5 (DualSense)"},
            {"dualshock4", "PlayStation 4 (DualShock 4)"},
            {"xbox", "Xbox"},
            {"pc", "Keyboard & Mouse (PC)"},
        }, cw);
        draw_setting_desc("Prompts follow your controller layout accurately (e.g. Triangle glides, Square attacks). Saving builds the overlay if needed.", ds);

        ImGui::Checkbox("DualSense Adaptive Triggers & Haptics", &d.dualsense);
        combo_strings("Mouse Look Mode", d.mouse_mode, {{"direct", "Direct Aim / Camera"}, {"stick", "Virtual Right Stick"}}, cw);
        ImGui::Checkbox("Mouse Cursor in Menus", &d.menu_cursor);
        ImGui::Checkbox("Click Map Pins with Mouse", &d.map_click);
        ImGui::Checkbox("Advance Dialogue with Mouse Click", &d.dialogue_click);
        combo_strings("Audio Channel Layout", d.audio_channels, {{"auto", "Auto"}, {"stereo", "Stereo"}, {"5.1", "5.1 Surround"}}, cw);
        ImGui::Checkbox("Launcher UI Sound Effects", &d.sound_effects);
        ImGui::Checkbox("Always Show Launcher Before Starting Game", &d.show_launcher);
        draw_setting_desc("If unchecked, double-clicking launches totk.exe directly unless Shift is held.", ds);
    }

    {
        std::lock_guard<std::mutex> lk(st.bg_mtx);
        if (!st.patch_status.empty()) {
            ImGui::Spacing();
            ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.10f, 0.82f, 0.64f, 1.0f));
            ImGui::TextWrapped("%s", st.patch_status.c_str());
            ImGui::PopStyleColor();
        }
    }
    ImGui::EndChild();
}

void toggle_mod_entry(AppState& st, ModEntry& m) {
    m.enabled = !m.enabled;
    auto disabled = split_csv(st.ini.get("mods_disabled"));
    disabled.erase(std::remove_if(disabled.begin(), disabled.end(), [&](const std::string& s) {
        return _stricmp(s.c_str(), m.name.c_str()) == 0;
    }), disabled.end());

    // If physically renamed .disabled, rename back to clean folder name so ini controls cleanly.
    std::string fname = m.path.filename().string();
    if (fname.size() > 9 && to_lower(fname.substr(fname.size() - 9)) == ".disabled") {
        fs::path target = m.path.parent_path() / m.name;
        std::error_code ec;
        if (!fs::exists(target, ec)) {
            fs::rename(m.path, target, ec);
            if (!ec) m.path = target;
        }
    }
    if (!m.enabled) disabled.push_back(m.name);
    st.ini.save_updates(st.game_dir / "totk.ini", {{"mods_disabled", join_csv(disabled)}});
}

void install_mod_archive_flow(AppState& st) {
    std::string path = browse_open_file(
        st.hwnd, L"Select Mod Archive (.zip, .7z, .rar)",
        L"Archives (*.zip;*.7z;*.rar)\0*.zip;*.7z;*.rar\0All Files (*.*)\0*.*\0");
    if (path.empty()) return;

    fs::path archive(path);
    fs::path mods_dir = st.game_dir / "mods";
    fs::create_directories(mods_dir);
    fs::path temp = fs::temp_directory_path() / ("totk_mod_" + std::to_string(GetTickCount64()));
    fs::create_directories(temp);

    std::string low = to_lower(archive.extension().string());
    std::string out;
    int rc = -1;
    if (low == ".zip") {
        std::wstring cmd = L"powershell.exe -NoProfile -NonInteractive -Command \"Expand-Archive -Path '" +
                           archive.wstring() + L"' -DestinationPath '" + temp.wstring() + L"' -Force\"";
        rc = run_hidden_process(cmd, st.game_dir, &out);
    } else {
        const wchar_t* tools[] = {L"C:\\Program Files\\7-Zip\\7z.exe", L"C:\\Program Files\\WinRAR\\WinRAR.exe"};
        for (const auto* t : tools) {
            if (fs::is_regular_file(t)) {
                std::wstring cmd = std::wstring(L"\"") + t + L"\" x -y \"" + archive.wstring() + L"\" -o\"" + temp.wstring() + L"\"";
                rc = run_hidden_process(cmd, st.game_dir, &out);
                break;
            }
        }
    }
    if (rc != 0) {
        std::error_code ec;
        fs::remove_all(temp, ec);
        st.mod_status = "Extraction failed (install 7-Zip for .7z/.rar, or use .zip).";
        return;
    }

    std::vector<fs::path> entries;
    for (const auto& e : fs::directory_iterator(temp)) {
        std::string n = e.path().filename().string();
        if (n != "__MACOSX" && n != ".DS_Store" && n != "Thumbs.db") entries.push_back(e.path());
    }
    std::string mod_name = (entries.size() == 1 && fs::is_directory(entries[0]))
        ? entries[0].filename().string()
        : archive.stem().string();
    fs::path src = (entries.size() == 1 && fs::is_directory(entries[0])) ? entries[0] : temp;
    fs::path dst = mods_dir / mod_name;
    std::error_code ec;
    fs::remove_all(dst, ec);
    fs::copy(src, dst, fs::copy_options::recursive | fs::copy_options::overwrite_existing, ec);
    fs::remove_all(temp, ec);

    if (folder_has_4k_pack(dst)) {
        auto order = split_csv(st.ini.get("mods_order"));
        if (std::find_if(order.begin(), order.end(), [&](const std::string& x) {
                return _stricmp(x.c_str(), mod_name.c_str()) == 0;
            }) == order.end()) {
            order.push_back(mod_name);
        }
        st.ini.save_updates(st.game_dir / "totk.ini", {
            {"mods_order", join_csv(order)},
            {"tex_heap_extra_mb", "1024"},
        });
        st.mod_status = "Installed 4K Texture Pack '" + mod_name + "' and set tex_heap_extra_mb = 1024.";
    } else {
        st.mod_status = "Installed mod '" + mod_name + "'.";
    }
    st.mods = scan_mods(st.game_dir, st.ini);
}

void render_mods_screen(AppState& st, float ds, ImVec2 vp, ImFont* title_font) {
    const float m = 24.0f * ds;
    ImGui::SetCursorPos(ImVec2(m, 18.0f * ds));
    if (nav_button(st, "< Back", 84.0f * ds, 32.0f * ds)) st.screen = SCREEN_MAIN;
    ImGui::SameLine(0, 14.0f * ds);
    if (title_font) ImGui::PushFont(title_font);
    ImGui::TextUnformatted("Mods Manager");
    if (title_font) ImGui::PopFont();

    ImGui::SetCursorPos(ImVec2(m, 62.0f * ds));
    if (emerald_button(st, "Install Archive (.zip / .7z / .rar)", ImVec2(240.0f * ds, 34.0f * ds))) {
        install_mod_archive_flow(st);
    }
    ImGui::SameLine(0, 8.0f * ds);
    if (nav_button(st, "Open Mods Folder", 150.0f * ds, 34.0f * ds)) {
        fs::create_directories(st.game_dir / "mods");
        open_in_shell((st.game_dir / "mods").wstring());
    }
    ImGui::SameLine(0, 8.0f * ds);
    if (nav_button(st, "Refresh", 100.0f * ds, 34.0f * ds)) {
        st.mods = scan_mods(st.game_dir, st.ini);
    }

    ImGui::SetCursorPos(ImVec2(m, 106.0f * ds));
    ImGui::BeginChild("mods_list", ImVec2(vp.x - m * 2.0f, vp.y - 166.0f * ds), ImGuiChildFlags_Borders);
    if (st.mods.empty()) {
        ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.60f, 0.67f, 0.75f, 1.0f));
        ImGui::TextWrapped("No mods found in mods/. Click 'Install Archive' or open the mods folder to add mods.");
        ImGui::PopStyleColor();
    } else {
        for (size_t i = 0; i < st.mods.size(); ++i) {
            auto& mod = st.mods[i];
            ImGui::PushID((int)i);
            bool en = mod.enabled;
            if (ImGui::Checkbox(mod.name.c_str(), &en)) {
                toggle_mod_entry(st, mod);
            }
            ImGui::SameLine(vp.x - m * 2.0f - 265.0f * ds);
            ImGui::TextColored(
                mod.enabled ? ImVec4(0.10f, 0.82f, 0.64f, 1.0f) : ImVec4(0.95f, 0.72f, 0.25f, 1.0f),
                "%s%s", mod.enabled ? "ENABLED" : "DISABLED", mod.is_4k ? "  [4K PACK]" : "");
            ImGui::SameLine(vp.x - m * 2.0f - 95.0f * ds);
            if (nav_button(st, "Remove", 72.0f * ds, 26.0f * ds)) {
                std::error_code ec;
                fs::remove_all(mod.path, ec);
                st.mod_status = "Removed mod '" + mod.name + "'.";
                st.mods = scan_mods(st.game_dir, st.ini);
                ImGui::PopID();
                break;
            }
            ImGui::PopID();
        }
    }
    ImGui::EndChild();

    ImGui::SetCursorPos(ImVec2(m, vp.y - 46.0f * ds));
    ImGui::TextUnformatted(st.mod_status.empty() ? "Toggle mods or install archives cleanly." : st.mod_status.c_str());
}

void render_saves_screen(AppState& st, float ds, ImVec2 vp, ImFont* title_font) {
    const float m = 24.0f * ds;
    ImGui::SetCursorPos(ImVec2(m, 18.0f * ds));
    if (nav_button(st, "< Back", 84.0f * ds, 32.0f * ds)) st.screen = SCREEN_MAIN;
    ImGui::SameLine(0, 14.0f * ds);
    if (title_font) ImGui::PushFont(title_font);
    ImGui::TextUnformatted("Save Backup Vault");
    if (title_font) ImGui::PopFont();

    ImGui::SetCursorPos(ImVec2(m, 62.0f * ds));
    ImGui::SetNextItemWidth(200.0f * ds);
    ImGui::InputTextWithHint("##tag", "Optional snapshot tag...", st.backup_tag, sizeof(st.backup_tag));
    ImGui::SameLine(0, 8.0f * ds);
    if (emerald_button(st, "Create Snapshot", ImVec2(150.0f * ds, 34.0f * ds))) {
        fs::path save_dir = st.game_dir / "profile" / "save";
        if (!fs::is_directory(save_dir)) {
            st.save_status = "No active profile/save directory found yet.";
        } else {
            std::string tag = trim(st.backup_tag);
            for (char& c : tag) if (!isalnum((unsigned char)c) && c != '-' && c != '_') c = '_';
            std::string name = "save_" + timestamp_now() + (tag.empty() ? "" : ("_" + tag));
            fs::path dst = st.game_dir / "profile" / "backups" / name;
            fs::create_directories(dst.parent_path());
            std::error_code ec;
            fs::copy(save_dir, dst, fs::copy_options::recursive | fs::copy_options::overwrite_existing, ec);
            st.save_status = ec ? "Snapshot failed." : ("Created snapshot: " + name);
            st.backup_tag[0] = '\0';
            st.backups = scan_save_backups(st.game_dir);
        }
    }
    ImGui::SameLine(0, 8.0f * ds);
    if (nav_button(st, "Open Backups Folder", 170.0f * ds, 34.0f * ds)) {
        fs::create_directories(st.game_dir / "profile" / "backups");
        open_in_shell((st.game_dir / "profile" / "backups").wstring());
    }

    ImGui::SetCursorPos(ImVec2(m, 106.0f * ds));
    ImGui::BeginChild("saves_list", ImVec2(vp.x - m * 2.0f, vp.y - 166.0f * ds), ImGuiChildFlags_Borders);
    if (st.backups.empty()) {
        ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.60f, 0.67f, 0.75f, 1.0f));
        ImGui::TextWrapped("No save snapshots yet. Click 'Create Snapshot' above to safely back up profile/save.");
        ImGui::PopStyleColor();
    } else {
        for (size_t i = 0; i < st.backups.size(); ++i) {
            const auto& bk = st.backups[i];
            ImGui::PushID((int)i);
            ImGui::Text("%s  (%s)", bk.name.c_str(), bk.details.c_str());
            ImGui::SameLine(vp.x - m * 2.0f - 180.0f * ds);
            if (nav_button(st, "Restore", 80.0f * ds, 26.0f * ds)) {
                if (is_process_running(L"totk.exe")) {
                    st.save_status = "Close totk.exe before restoring a save backup.";
                } else {
                    fs::path save_dir = st.game_dir / "profile" / "save";
                    std::error_code ec;
                    if (fs::is_directory(save_dir, ec)) {
                        fs::path safety = st.game_dir / "profile" / "backups" / ("save_" + timestamp_now() + "_before-restore");
                        fs::copy(save_dir, safety, fs::copy_options::recursive | fs::copy_options::overwrite_existing, ec);
                        fs::remove_all(save_dir, ec);
                    }
                    fs::create_directories(save_dir);
                    fs::copy(bk.path, save_dir, fs::copy_options::recursive | fs::copy_options::overwrite_existing, ec);
                    st.save_status = ec ? "Restore failed." : ("Restored '" + bk.name + "' cleanly.");
                    st.backups = scan_save_backups(st.game_dir);
                    ImGui::PopID();
                    break;
                }
            }
            ImGui::SameLine(0, 6.0f * ds);
            if (nav_button(st, "Delete", 74.0f * ds, 26.0f * ds)) {
                std::error_code ec;
                fs::remove_all(bk.path, ec);
                st.save_status = "Deleted snapshot '" + bk.name + "'.";
                st.backups = scan_save_backups(st.game_dir);
                ImGui::PopID();
                break;
            }
            ImGui::PopID();
        }
    }
    ImGui::EndChild();

    ImGui::SetCursorPos(ImVec2(m, vp.y - 46.0f * ds));
    ImGui::TextUnformatted(st.save_status.empty() ? "Backups protect profile/save before modding or updates." : st.save_status.c_str());
}

void render_updates_screen(AppState& st, float ds, ImVec2 vp, ImFont* title_font) {
    const float m = 24.0f * ds;
    ImGui::SetCursorPos(ImVec2(m, 18.0f * ds));
    if (nav_button(st, "< Back", 84.0f * ds, 32.0f * ds)) st.screen = SCREEN_MAIN;
    ImGui::SameLine(0, 14.0f * ds);
    if (title_font) ImGui::PushFont(title_font);
    ImGui::TextUnformatted("Updates");
    if (title_font) ImGui::PopFont();

    std::string tag, name, url, body, status;
    bool fetching, updating, checked, avail;
    {
        std::lock_guard<std::mutex> lk(st.bg_mtx);
        tag = st.rel.tag;
        name = st.rel.name;
        url = st.rel.zip_url;
        body = st.rel.body;
        status = st.rel.status_msg;
        fetching = st.rel.fetching;
        updating = st.rel.updating;
        checked = st.rel.checked;
        avail = st.rel.update_available;
    }

    ImGui::SetCursorPos(ImVec2(m, 64.0f * ds));
    if (fetching || updating) ImGui::BeginDisabled();
    if (nav_button(st, "Check GitHub Releases", 190.0f * ds, 34.0f * ds)) {
        check_updates_async(st);
    }
    if (!url.empty()) {
        ImGui::SameLine(0, 10.0f * ds);
        std::string btn_lbl = avail ? ("Download & Install " + tag) : "Reinstall Latest Update";
        if (emerald_button(st, btn_lbl.c_str(), ImVec2(240.0f * ds, 34.0f * ds))) {
            install_update_async(st);
        }
    }
    if (fetching || updating) ImGui::EndDisabled();

    ImGui::SetCursorPos(ImVec2(m, 110.0f * ds));
    ImGui::BeginChild("updates_box", ImVec2(vp.x - m * 2.0f, vp.y - 168.0f * ds), ImGuiChildFlags_Borders);
    ImGui::Text("Installed Build:  %s", TOTK_LAUNCHER_VERSION);
    if (checked && avail) {
        ImGui::TextColored(ImVec4(0.10f, 0.82f, 0.64f, 1.0f), "Update Status:  NEW UPDATE AVAILABLE (%s)", tag.c_str());
    } else if (checked && !tag.empty()) {
        ImGui::TextColored(ImVec4(0.10f, 0.82f, 0.64f, 1.0f), "Update Status:  %s", status.c_str());
    } else {
        ImGui::Text("Status:  %s", status.empty() ? "Idle" : status.c_str());
    }
    if (!tag.empty()) ImGui::Text("Latest Release:  %s  %s", tag.c_str(), name.c_str());
    ImGui::Separator();
    ImGui::Spacing();
    if (!body.empty()) {
        ImGui::TextWrapped("%s", body.c_str());
    } else {
        ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.60f, 0.67f, 0.75f, 1.0f));
        ImGui::TextWrapped("Updates preserve your game extraction, saves, mods, and totk.ini settings.");
        ImGui::PopStyleColor();
    }
    ImGui::EndChild();
}

void render_guide_screen(AppState& st, float ds, ImVec2 vp, ImFont* title_font) {
    const float m = 24.0f * ds;
    ImGui::SetCursorPos(ImVec2(m, 18.0f * ds));
    if (nav_button(st, "< Back", 84.0f * ds, 32.0f * ds)) st.screen = SCREEN_MAIN;
    ImGui::SameLine(0, 14.0f * ds);
    if (title_font) ImGui::PushFont(title_font);
    ImGui::TextUnformatted("Controller & Shortcuts Guide");
    if (title_font) ImGui::PopFont();

    fs::path guide_file = st.game_dir / "CONTROLLER_GUIDE.txt";
    if (fs::is_regular_file(guide_file)) {
        ImGui::SameLine(vp.x - m - 190.0f * ds);
        if (nav_button(st, "Open CONTROLLER_GUIDE.txt", 190.0f * ds, 32.0f * ds)) {
            open_in_shell(guide_file.wstring());
        }
    }

    ImGui::SetCursorPos(ImVec2(m, 64.0f * ds));
    ImGui::BeginChild("guide_box", ImVec2(vp.x - m * 2.0f, vp.y - 96.0f * ds), ImGuiChildFlags_Borders);
    ImGui::TextColored(ImVec4(0.10f, 0.82f, 0.64f, 1.0f), "IN-GAME OVERLAY & HOTKEYS");
    ImGui::BulletText("Open / Close Settings Menu: F1, Select + Start, or PS4/PS5 Touchpad");
    ImGui::BulletText("Fullscreen Toggle: F11 / Alt+Enter");
    ImGui::Spacing();
    ImGui::TextColored(ImVec4(0.10f, 0.82f, 0.64f, 1.0f), "FACE BUTTONS & PROMPTS");
    ImGui::BulletText("Auto / Xbox layout matches face labels (Bottom = Jump/B, Right = Confirm/Interact/Sprint, Top = Glide/X, Left = Attack/Y).");
    ImGui::BulletText("PlayStation DualSense / DualShock 4 with Auto or Xbox layout shows Triangle for Glide, Square for Attack, Cross for Jump, Circle for Interact.");
    ImGui::BulletText("Nintendo Positional layout matches Switch physical button positions.");
    ImGui::Spacing();
    ImGui::TextColored(ImVec4(0.10f, 0.82f, 0.64f, 1.0f), "KEYBOARD & MOUSE DEFAULTS");
    ImGui::BulletText("Move: WASD   |   Walk: Left Shift   |   Camera: Mouse (Direct Aim)");
    ImGui::BulletText("Attack: Left Click   |   Interact / Pick Up: E   |   Sprint / Cancel: Right Click");
    ImGui::BulletText("Jump / Glide: Space   |   Ability Wheel: Q   |   Throw / Aim: R");
    ImGui::EndChild();
}

}  // namespace

static int app_main(int argc, char** argv) {
    AppState st;
    wchar_t self_buf[MAX_PATH] = {};
    GetModuleFileNameW(nullptr, self_buf, MAX_PATH);
    st.exe_dir = fs::path(self_buf).parent_path();
    st.game_dir = find_game_dir(st.exe_dir);
    st.has_totk_exe = fs::is_regular_file(st.game_dir / "totk.exe");
    st.has_game_files = fs::is_directory(st.game_dir / "romfs") && fs::is_directory(st.game_dir / "exefs");
    st.romfs_version = detect_romfs_version(st.game_dir / "romfs");
    st.displays = enumerate_displays();
    st.gpu_name = detect_gpu_short();

    bool force_launcher = false;
    std::string shot_dir;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--launcher") force_launcher = true;
        else if (a == "--shot" && i + 1 < argc) { shot_dir = argv[++i]; force_launcher = true; }
        else if ((a == "--run-ultrawide-patcher" || a == "--run-prompts-patcher") && i + 4 < argc) {
            fs::path patcher = find_patcher_exe(st);
            if (patcher.empty()) return 2;
            std::wstring cmd = L"\"" + patcher.wstring() + L"\"";
            for (int j = 1; j < argc; ++j) cmd += L" \"" + utf8_to_wide(argv[j]) + L"\"";
            return run_hidden_process(cmd, st.game_dir, nullptr);
        }
    }

    load_draft_from_disk(st);

    // Direct play skip unless --launcher or Shift held
    bool shift_held = (GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0;
    if (!force_launcher && !st.launcher_cfg.show_launcher && !shift_held && st.has_totk_exe && st.has_game_files) {
        launch_game(st, false);
        return 0;
    }

    SDL_SetMainReady();
    if (!SDL_Init(SDL_INIT_VIDEO)) return 1;

    float ds = SDL_GetDisplayContentScale(SDL_GetPrimaryDisplay());
    if (ds <= 0.0f) ds = 1.0f;

    int win_w = (int)std::lround(kWinW * ds);
    int win_h = (int)std::lround(kWinH * ds);
    SDL_Window* window = SDL_CreateWindow("The Legend of Zelda: Tears of the Kingdom — Launcher",
                                          win_w, win_h, SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY);
    if (!window) { SDL_Quit(); return 1; }
    SDL_SetWindowMinimumSize(window, (int)(860 * ds), (int)(540 * ds));

    // Place centered on preferred monitor
    for (const auto& mon : st.displays) {
        if (mon.device == st.launcher_cfg.target_display || (st.launcher_cfg.target_display.empty() && mon.primary)) {
            int cx = mon.left + std::max(0, (mon.w - win_w) / 2);
            int cy = mon.top + std::max(0, (mon.h - win_h) / 2);
            SDL_SetWindowPosition(window, cx, cy);
            break;
        }
    }

    HWND hwnd = (HWND)SDL_GetPointerProperty(SDL_GetWindowProperties(window), SDL_PROP_WINDOW_WIN32_HWND_POINTER, nullptr);
    st.hwnd = hwnd;
    if (hwnd) {
        BOOL dark = TRUE;
        DwmSetWindowAttribute(hwnd, 20 /* DWMWA_USE_IMMERSIVE_DARK_MODE */, &dark, sizeof(dark));
    }

    SDL_Renderer* renderer = SDL_CreateRenderer(window, nullptr);
    if (!renderer) { SDL_DestroyWindow(window); SDL_Quit(); return 1; }
    SDL_SetRenderVSync(renderer, 1);

    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.IniFilename = nullptr;
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;

    ImFontConfig fc{};
    fc.FontDataOwnedByAtlas = false;
    ImFont* body_font = io.Fonts->AddFontFromMemoryTTF(const_cast<unsigned char*>(kRobotoMediumTtf),
                                                       (int)kRobotoMediumTtfLen, 15.5f * ds, &fc);
    ImFont* title_font = io.Fonts->AddFontFromMemoryTTF(const_cast<unsigned char*>(kRobotoMediumTtf),
                                                        (int)kRobotoMediumTtfLen, 21.0f * ds, &fc);
    io.FontDefault = body_font;

    apply_mkw_style(ds);
    ImGui_ImplSDL3_InitForSDLRenderer(window, renderer);
    ImGui_ImplSDLRenderer3_Init(renderer);

    std::vector<Particle> particles = make_particles();
    auto t0 = std::chrono::steady_clock::now();

    auto save_png_bmp_shot = [&](const fs::path& out_path) {
        int pw = 0, ph = 0;
        SDL_GetWindowSizeInPixels(window, &pw, &ph);
        SDL_Surface* surf = SDL_RenderReadPixels(renderer, nullptr);
        if (surf) {
            fs::create_directories(out_path.parent_path());
            SDL_SavePNG(surf, out_path.string().c_str());
            SDL_DestroySurface(surf);
        }
    };

    auto draw_one_frame = [&](float sim_t) {
        ImGui_ImplSDLRenderer3_NewFrame();
        ImGui_ImplSDL3_NewFrame();
        ImGui::NewFrame();

        ImVec2 vp = io.DisplaySize;
        ImGui::SetNextWindowPos(ImVec2(0, 0));
        ImGui::SetNextWindowSize(vp);
        ImGui::Begin("##root", nullptr,
                     ImGuiWindowFlags_NoDecoration | ImGuiWindowFlags_NoMove |
                     ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoSavedSettings |
                     ImGuiWindowFlags_NoBringToFrontOnFocus);

        draw_zonai_backdrop(ImGui::GetWindowDrawList(), vp, sim_t, particles, ds, st.screen != SCREEN_MAIN);

        switch (st.screen) {
            case SCREEN_MAIN:     render_main_screen(st, ds, vp, title_font); break;
            case SCREEN_SETTINGS: render_settings_screen(st, ds, vp, title_font); break;
            case SCREEN_MODS:     render_mods_screen(st, ds, vp, title_font); break;
            case SCREEN_SAVES:    render_saves_screen(st, ds, vp, title_font); break;
            case SCREEN_UPDATES:  render_updates_screen(st, ds, vp, title_font); break;
            case SCREEN_GUIDE:    render_guide_screen(st, ds, vp, title_font); break;
        }

        if (!st.banner_msg.empty() && ImGui::GetTime() < st.banner_until) {
            float bw = std::min(vp.x * 0.55f, ImGui::CalcTextSize(st.banner_msg.c_str()).x + 36.0f * ds);
            float bx = (vp.x - bw) * 0.5f;
            float by = 14.0f * ds;
            ImDrawList* fdl = ImGui::GetForegroundDrawList();
            fdl->AddRectFilled(ImVec2(bx, by), ImVec2(bx + bw, by + 32.0f * ds),
                               st.banner_is_error ? IM_COL32(140, 32, 32, 235) : IM_COL32(18, 62, 52, 235), 7.0f * ds);
            fdl->AddRect(ImVec2(bx, by), ImVec2(bx + bw, by + 32.0f * ds),
                         st.banner_is_error ? IM_COL32(235, 95, 95, 255) : IM_COL32(26, 210, 163, 255), 7.0f * ds);
            fdl->AddText(ImVec2(bx + 18.0f * ds, by + 7.5f * ds), IM_COL32(245, 248, 252, 255), st.banner_msg.c_str());
        }

        ImGui::End();
        ImGui::Render();

        SDL_SetRenderDrawColor(renderer, 10, 14, 20, 255);
        SDL_RenderClear(renderer);
        ImGui_ImplSDLRenderer3_RenderDrawData(ImGui::GetDrawData(), renderer);
        SDL_RenderPresent(renderer);
    };

    if (!shot_dir.empty()) {
        fs::path sdir(shot_dir);
        struct ShotSpec { Screen scr; int tab; const char* fname; float t; };
        const ShotSpec specs[] = {
            {SCREEN_MAIN,     0, "01_main.png",              1.5f},
            {SCREEN_SETTINGS, 0, "02_settings_display.png",  2.0f},
            {SCREEN_SETTINGS, 1, "03_settings_upscale.png",  2.2f},
            {SCREEN_SETTINGS, 2, "04_settings_graphics.png", 2.4f},
            {SCREEN_SETTINGS, 3, "05_settings_controls.png", 2.6f},
            {SCREEN_MODS,     0, "06_mods.png",              2.8f},
            {SCREEN_SAVES,    0, "07_saves.png",             3.0f},
            {SCREEN_UPDATES,  0, "08_updates.png",           3.2f},
            {SCREEN_GUIDE,    0, "09_guide.png",             3.4f},
        };
        st.mods = scan_mods(st.game_dir, st.ini);
        st.backups = scan_save_backups(st.game_dir);
        for (const auto& sp : specs) {
            st.screen = sp.scr;
            st.settings_tab = sp.tab;
            for (int f = 0; f < 3; ++f) {
                SDL_PumpEvents();
                draw_one_frame(sp.t);
            }
            save_png_bmp_shot(sdir / sp.fname);
        }
    } else {
        check_updates_async(st);
        bool running = true;
        while (running) {
            SDL_Event ev;
            while (SDL_PollEvent(&ev)) {
                ImGui_ImplSDL3_ProcessEvent(&ev);
                if (ev.type == SDL_EVENT_QUIT) running = false;
                if (ev.type == SDL_EVENT_WINDOW_CLOSE_REQUESTED &&
                    ev.window.windowID == SDL_GetWindowID(window)) {
                    running = false;
                }
                if (ev.type == SDL_EVENT_KEY_DOWN && ev.key.key == SDLK_ESCAPE && st.screen != SCREEN_MAIN) {
                    st.screen = SCREEN_MAIN;
                }
            }
            float sim_t = std::chrono::duration<float>(std::chrono::steady_clock::now() - t0).count();
            draw_one_frame(sim_t);
        }
    }

    ImGui_ImplSDLRenderer3_Shutdown();
    ImGui_ImplSDL3_Shutdown();
    ImGui::DestroyContext();
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}

int WINAPI WinMain(HINSTANCE, HINSTANCE, LPSTR, int) {
    int wargc = 0;
    wchar_t** wargv = CommandLineToArgvW(GetCommandLineW(), &wargc);
    std::vector<std::string> utf8_args;
    std::vector<char*> c_args;
    for (int i = 0; i < wargc; ++i) {
        utf8_args.push_back(wide_to_utf8(wargv[i]));
    }
    if (wargv) LocalFree(wargv);
    for (auto& s : utf8_args) c_args.push_back(s.data());
    return app_main((int)c_args.size(), c_args.data());
}
