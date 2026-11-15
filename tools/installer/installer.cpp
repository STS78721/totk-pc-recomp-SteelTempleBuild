// SteelTemple's Tears of the Kingdom PC Recompiled - Native Windows Setup Wizard.
// Style matches MKW-THWOMP's SDL3 + Dear ImGui installer with a 60 FPS procedural animated
// Zonai / Triforce backdrop, standalone configuration + zstd payload extraction (`TOTKPKG1`).

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <windows.h>
#include <objbase.h>
#include <shlobj.h>
#include <shellapi.h>
#include <shobjidl.h>
#include <shlwapi.h>

#include <SDL3/SDL.h>
#include "imgui.h"
#include "backends/imgui_impl_sdl3.h"
#include "backends/imgui_impl_sdlrenderer3.h"
#include "zstd.h"
#include "roboto_font.h"

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace fs = std::filesystem;

#ifndef TOTK_SETUP_VERSION
#define TOTK_SETUP_VERSION "Beta 6.3"
#endif

static constexpr char kMagic[8] = {'T', 'O', 'T', 'K', 'P', 'K', 'G', '1'};
static constexpr wchar_t kAppDisplay[] = L"The Legend of Zelda - Tears of the Kingdom";
static constexpr wchar_t kUninstallKey[] = L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SteelTempleTotK";
static constexpr char kGuideText[] =
    "================================================================================\n"
    "  THE LEGEND OF ZELDA: TEARS OF THE KINGDOM (PC RECOMPILED)\n"
    "  IN-GAME SETTINGS OVERLAY & CONTROLLER NAVIGATION GUIDE\n"
    "================================================================================\n\n"
    "1. HOW TO OPEN / CLOSE THE IN-GAME SETTINGS MENU:\n"
    "   -----------------------------------------------------------------------------\n"
    "   * PLAYSTATION (PS5 DualSense / PS4 DualShock 4):\n"
    "     - Press the [Touchpad Click] directly to toggle the menu on or off!\n"
    "     - Or press [Create / Share] + [Options] together.\n"
    "   * XBOX / SWITCH / GENERIC CONTROLLER:\n"
    "     - Press [Select / View] + [Start / Menu] (or [Minus] + [Plus]) together.\n"
    "   * KEYBOARD:\n"
    "     - Press [F1] or [Esc] at any time.\n\n"
    "2. MENU THEMES & NAVIGATION:\n"
    "   -----------------------------------------------------------------------------\n"
    "   * Themes (Settings -> Menu -> Menu theme):\n"
    "     - Tears of the Kingdom (Zonai/Hylian), Dark, or Light.\n"
    "   * Switch Tabs:   [L1 / R1] / [LB / RB] or [Q / E]\n"
    "   * Navigate:      [D-Pad] or [Left Stick]\n"
    "   * Select / Edit: [A / Cross]  |  Back / Close: [B / Circle]\n\n"
    "3. PERFORMANCE OVERLAY & FULLSCREEN:\n"
    "   -----------------------------------------------------------------------------\n"
    "   * Perf Overlay:  Press [L3 + R3] (controller) or [F10] (keyboard)\n"
    "   * Fullscreen:    Press [F11] or [Alt + Enter]\n"
    "================================================================================\n";

// ---- UTF-8 / Wide helpers ----
static std::wstring to_wide(const std::string& s) {
    if (s.empty()) return {};
    int n = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), nullptr, 0);
    std::wstring w(n, L'\0');
    MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), w.data(), n);
    return w;
}

static std::string to_utf8(const std::wstring& w) {
    if (w.empty()) return {};
    int n = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), nullptr, 0, nullptr, nullptr);
    std::string s(n, '\0');
    WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), s.data(), n, nullptr, nullptr);
    return s;
}

static fs::path path_from_utf8(const std::string& s) { return fs::path(to_wide(s)); }
static std::string utf8_from_path(const fs::path& p) { return to_utf8(p.wstring()); }

static fs::path known_folder(REFKNOWNFOLDERID id) {
    PWSTR p = nullptr;
    fs::path out;
    if (SUCCEEDED(SHGetKnownFolderPath(id, 0, nullptr, &p)) && p) {
        out = fs::path(p);
        CoTaskMemFree(p);
    }
    return out;
}

static fs::path self_exe_path() {
    wchar_t buf[MAX_PATH] = {};
    DWORD n = GetModuleFileNameW(nullptr, buf, MAX_PATH);
    return fs::path(std::wstring(buf, n));
}

// ---- Optional embedded payload (`TOTKPKG1` format, compatible with build.py) ----
struct PayloadEntry {
    std::string rel_path;
    uint64_t comp_offset = 0;
    uint64_t comp_size = 0;
    uint64_t raw_size = 0;
};

struct Payload {
    bool present = false;
    std::vector<PayloadEntry> entries;
    uint64_t total_raw = 0;
};

static Payload inspect_payload() {
    Payload p;
    std::ifstream f(self_exe_path(), std::ios::binary | std::ios::ate);
    if (!f) return p;
    uint64_t file_size = (uint64_t)f.tellg();
    if (file_size < 16) return p;

    f.seekg((std::streamoff)(file_size - 16));
    uint64_t payload_offset = 0;
    char magic[8] = {};
    f.read((char*)&payload_offset, 8);
    f.read(magic, 8);
    if (std::memcmp(magic, kMagic, 8) != 0 || payload_offset >= file_size - 16) return p;

    f.seekg((std::streamoff)payload_offset);
    uint32_t count = 0;
    f.read((char*)&count, 4);
    if (!f || count > 200000) return p;

    p.entries.reserve(count);
    for (uint32_t i = 0; i < count; i++) {
        uint16_t len = 0;
        f.read((char*)&len, 2);
        if (!f || len == 0 || len > 4096) return Payload{};
        PayloadEntry e;
        e.rel_path.resize(len);
        f.read(e.rel_path.data(), len);
        f.read((char*)&e.comp_offset, 8);
        f.read((char*)&e.comp_size, 8);
        f.read((char*)&e.raw_size, 8);
        if (!f) return Payload{};
        p.total_raw += e.raw_size;
        p.entries.push_back(std::move(e));
    }
    p.present = true;
    return p;
}

// ---- Emulator save scanner ----
struct SaveCandidate {
    std::string label;
    std::string source;
    fs::path path;
    int slots = 1;
    uint64_t mtime = 0;
};

static uint64_t latest_sav_mtime(const fs::path& dir, int& slot_count) {
    uint64_t best = 0;
    slot_count = 0;
    std::error_code ec;
    for (const auto& entry : fs::recursive_directory_iterator(dir, ec)) {
        if (!entry.is_regular_file(ec)) continue;
        if (entry.path().extension() == L".sav") {
            if (entry.path().filename() == L"progress.sav") slot_count++;
            auto ft = entry.last_write_time(ec).time_since_epoch().count();
            if ((uint64_t)ft > best) best = (uint64_t)ft;
        }
    }
    if (slot_count == 0) slot_count = 1;
    return best;
}

static std::vector<SaveCandidate> scan_saves() {
    std::vector<SaveCandidate> out;
    fs::path appdata = known_folder(FOLDERID_RoamingAppData);
    if (appdata.empty()) return out;

    const char* yuzu_forks[] = {"yuzu", "eden", "sudachi", "suyu", "torzu", "citron"};
    std::error_code ec;
    for (const char* fork : yuzu_forks) {
        fs::path root = appdata / fork / "nand" / "user" / "save" / "0000000000000000";
        if (!fs::is_directory(root, ec)) continue;
        for (const auto& uid : fs::directory_iterator(root, ec)) {
            fs::path totk_dir = uid.path() / "0100F2C0115B6000";
            if (!fs::is_directory(totk_dir, ec)) continue;
            int slots = 0;
            uint64_t mt = latest_sav_mtime(totk_dir, slots);
            if (mt > 0) {
                SaveCandidate c;
                c.source = fork;
                c.source[0] = (char)toupper((unsigned char)c.source[0]);
                c.path = totk_dir;
                c.slots = slots;
                c.mtime = mt;
                c.label = "[" + c.source + "] " + std::to_string(slots) + " save slot(s)";
                out.push_back(std::move(c));
            }
        }
    }

    fs::path ryu = appdata / "Ryujinx" / "bis" / "user" / "save";
    if (fs::is_directory(ryu, ec)) {
        for (const auto& entry : fs::directory_iterator(ryu, ec)) {
            if (!entry.is_directory(ec)) continue;
            fs::path p0 = entry.path() / "0";
            if (fs::is_directory(p0, ec)) {
                int slots = 0;
                uint64_t mt = latest_sav_mtime(entry.path(), slots);
                if (mt > 0) {
                    SaveCandidate c;
                    c.source = "Ryujinx";
                    c.path = entry.path();
                    c.slots = slots;
                    c.mtime = mt;
                    c.label = "[Ryujinx] " + std::to_string(slots) + " save slot(s)";
                    out.push_back(std::move(c));
                }
            }
        }
    }

    std::sort(out.begin(), out.end(), [](const SaveCandidate& a, const SaveCandidate& b) {
        return a.mtime > b.mtime;
    });
    return out;
}

// ---- Win32 File / Folder Pickers & Key / Game Auto-Detection Helpers ----
static std::string browse_folder(SDL_Window* win, const std::string& initial, const wchar_t* title = L"Select Folder") {
    HWND owner = (HWND)SDL_GetPointerProperty(SDL_GetWindowProperties(win), SDL_PROP_WINDOW_WIN32_HWND_POINTER, nullptr);
    IFileDialog* dlg = nullptr;
    std::string result;
    if (SUCCEEDED(CoCreateInstance(CLSID_FileOpenDialog, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&dlg)))) {
        DWORD opts = 0;
        dlg->GetOptions(&opts);
        dlg->SetOptions(opts | FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM | FOS_PATHMUSTEXIST);
        dlg->SetTitle(title);
        fs::path initp = path_from_utf8(initial);
        std::error_code ec;
        while (!initp.empty() && !fs::exists(initp, ec)) initp = initp.parent_path();
        if (!initp.empty()) {
            IShellItem* item = nullptr;
            if (SUCCEEDED(SHCreateItemFromParsingName(initp.c_str(), nullptr, IID_PPV_ARGS(&item)))) {
                dlg->SetFolder(item);
                item->Release();
            }
        }
        if (SUCCEEDED(dlg->Show(owner))) {
            IShellItem* item = nullptr;
            if (SUCCEEDED(dlg->GetResult(&item))) {
                PWSTR path = nullptr;
                if (SUCCEEDED(item->GetDisplayName(SIGDN_FILESYSPATH, &path)) && path) {
                    result = to_utf8(path);
                    CoTaskMemFree(path);
                }
                item->Release();
            }
        }
        dlg->Release();
    }
    return result;
}

static std::string browse_file(SDL_Window* win, const std::string& initial, const wchar_t* title,
                               const COMDLG_FILTERSPEC* filters, UINT filter_count) {
    HWND owner = (HWND)SDL_GetPointerProperty(SDL_GetWindowProperties(win), SDL_PROP_WINDOW_WIN32_HWND_POINTER, nullptr);
    IFileDialog* dlg = nullptr;
    std::string result;
    if (SUCCEEDED(CoCreateInstance(CLSID_FileOpenDialog, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&dlg)))) {
        DWORD opts = 0;
        dlg->GetOptions(&opts);
        dlg->SetOptions(opts | FOS_FORCEFILESYSTEM | FOS_FILEMUSTEXIST);
        dlg->SetTitle(title);
        if (filters && filter_count > 0) dlg->SetFileTypes(filter_count, filters);
        fs::path initp = path_from_utf8(initial);
        std::error_code ec;
        if (fs::is_regular_file(initp, ec)) initp = initp.parent_path();
        while (!initp.empty() && !fs::exists(initp, ec)) initp = initp.parent_path();
        if (!initp.empty()) {
            IShellItem* item = nullptr;
            if (SUCCEEDED(SHCreateItemFromParsingName(initp.c_str(), nullptr, IID_PPV_ARGS(&item)))) {
                dlg->SetFolder(item);
                item->Release();
            }
        }
        if (SUCCEEDED(dlg->Show(owner))) {
            IShellItem* item = nullptr;
            if (SUCCEEDED(dlg->GetResult(&item))) {
                PWSTR path = nullptr;
                if (SUCCEEDED(item->GetDisplayName(SIGDN_FILESYSPATH, &path)) && path) {
                    result = to_utf8(path);
                    CoTaskMemFree(path);
                }
                item->Release();
            }
        }
        dlg->Release();
    }
    return result;
}

static bool validate_prod_keys(const std::string& path_utf8, std::string& out_msg) {
    if (path_utf8.empty()) {
        out_msg = "Required: select your Switch prod.keys file.";
        return false;
    }
    std::error_code ec;
    fs::path p = path_from_utf8(path_utf8);
    if (!fs::is_regular_file(p, ec)) {
        out_msg = "prod.keys file does not exist.";
        return false;
    }
    std::ifstream f(p, std::ios::binary);
    if (!f) {
        out_msg = "Cannot read prod.keys.";
        return false;
    }
    bool has_header_key = false;
    int key_count = 0;
    std::string line;
    while (std::getline(f, line)) {
        auto hash = line.find('#');
        if (hash != std::string::npos) line.resize(hash);
        auto eq = line.find('=');
        if (eq == std::string::npos) continue;
        std::string k = line.substr(0, eq);
        std::string v = line.substr(eq + 1);
        auto trim = [](std::string& s) {
            size_t a = s.find_first_not_of(" \t\r\n");
            size_t b = s.find_last_not_of(" \t\r\n");
            s = (a == std::string::npos) ? std::string() : s.substr(a, b - a + 1);
        };
        trim(k);
        trim(v);
        if (k.empty() || v.size() < 16) continue;
        for (char& ch : k) ch = (char)tolower((unsigned char)ch);
        if (k == "header_key") has_header_key = true;
        key_count++;
    }
    if (!has_header_key || key_count < 4) {
        out_msg = "Invalid prod.keys (missing header_key for Switch 1 NCA extraction).";
        return false;
    }
    out_msg = "Valid prod.keys (" + std::to_string(key_count) + " keys loaded).";
    return true;
}

static std::string auto_find_keys() {
    std::error_code ec;
    std::vector<fs::path> candidates;
    fs::path self_dir = self_exe_path().parent_path();
    candidates.push_back(self_dir / "prod.keys");
    candidates.push_back(self_dir / "keys" / "prod.keys");
    fs::path appdata = known_folder(FOLDERID_RoamingAppData);
    if (!appdata.empty()) {
        for (const char* fork : {"yuzu", "eden", "sudachi", "suyu", "torzu", "citron"}) {
            candidates.push_back(appdata / fork / "keys" / "prod.keys");
        }
        candidates.push_back(appdata / "Ryujinx" / "system" / "prod.keys");
    }
    fs::path dl = known_folder(FOLDERID_Downloads);
    if (!dl.empty()) candidates.push_back(dl / "prod.keys");
    fs::path desk = known_folder(FOLDERID_Desktop);
    if (!desk.empty()) candidates.push_back(desk / "prod.keys");

    for (const auto& c : candidates) {
        std::string s = utf8_from_path(c);
        std::string msg;
        if (fs::is_regular_file(c, ec) && validate_prod_keys(s, msg)) return s;
    }
    return {};
}

static std::string auto_find_game_file(bool want_update) {
    std::error_code ec;
    std::vector<fs::path> dirs;
    fs::path self_dir = self_exe_path().parent_path();
    dirs.push_back(self_dir);
    fs::path dl = known_folder(FOLDERID_Downloads);
    if (!dl.empty()) dirs.push_back(dl);
    fs::path desk = known_folder(FOLDERID_Desktop);
    if (!desk.empty()) dirs.push_back(desk);
    fs::path docs = known_folder(FOLDERID_Documents);
    if (!docs.empty()) dirs.push_back(docs);

    for (const auto& d : dirs) {
        if (!fs::is_directory(d, ec)) continue;
        for (const auto& ent : fs::directory_iterator(d, ec)) {
            if (!ent.is_regular_file(ec)) continue;
            std::string ext = utf8_from_path(ent.path().extension());
            std::string fn = utf8_from_path(ent.path().filename());
            for (char& ch : ext) ch = (char)tolower((unsigned char)ch);
            for (char& ch : fn) ch = (char)tolower((unsigned char)ch);
            bool ok_ext = want_update ? (ext == ".nsp" || ext == ".nsz")
                                      : (ext == ".xci" || ext == ".nsp" || ext == ".xcz" || ext == ".nsz");
            if (!ok_ext) continue;
            bool is_upd_name = (fn.find("update") != std::string::npos || fn.find("upd") != std::string::npos ||
                                fn.find("1.4.3") != std::string::npos || fn.find("1.2.1") != std::string::npos ||
                                fn.find("1.1.0") != std::string::npos || fn.find("0100f2c0115b6800") != std::string::npos);
            bool is_base_name = (fn.find("totk") != std::string::npos || fn.find("tears") != std::string::npos ||
                                 fn.find("zelda") != std::string::npos || fn.find("0100f2c0115b6000") != std::string::npos);
            if (want_update && is_upd_name && is_base_name) return utf8_from_path(ent.path());
            if (!want_update && is_base_name && !is_upd_name) return utf8_from_path(ent.path());
        }
    }
    return {};
}

static bool create_shortcut(const fs::path& lnk_path, const fs::path& target, const fs::path& workdir,
                            const fs::path& icon, const wchar_t* desc) {
    IShellLinkW* link = nullptr;
    if (FAILED(CoCreateInstance(CLSID_ShellLink, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&link)))) return false;
    link->SetPath(target.c_str());
    link->SetWorkingDirectory(workdir.c_str());
    link->SetIconLocation(icon.c_str(), 0);
    link->SetDescription(desc);
    IPersistFile* pf = nullptr;
    bool ok = false;
    if (SUCCEEDED(link->QueryInterface(IID_PPV_ARGS(&pf)))) {
        std::error_code ec;
        fs::create_directories(lnk_path.parent_path(), ec);
        ok = SUCCEEDED(pf->Save(lnk_path.c_str(), TRUE));
        pf->Release();
    }
    link->Release();
    return ok;
}

static void write_ini_kv(const fs::path& ini_path, const std::vector<std::pair<std::string, std::string>>& kvs) {
    std::vector<std::string> lines;
    {
        std::ifstream in(ini_path);
        std::string line;
        while (std::getline(in, line)) {
            if (!line.empty() && line.back() == '\r') line.pop_back();
            lines.push_back(line);
        }
    }
    auto trim = [](const std::string& s) {
        size_t a = s.find_first_not_of(" \t");
        if (a == std::string::npos) return std::string();
        size_t b = s.find_last_not_of(" \t");
        return s.substr(a, b - a + 1);
    };
    auto ieq = [](const std::string& a, const std::string& b) {
        if (a.size() != b.size()) return false;
        for (size_t i = 0; i < a.size(); i++)
            if (tolower((unsigned char)a[i]) != tolower((unsigned char)b[i])) return false;
        return true;
    };
    for (const auto& [key, val] : kvs) {
        bool replaced = false;
        for (auto& ln : lines) {
            std::string t = trim(ln);
            if (t.empty()) continue;
            bool commented = (t[0] == '#' || t[0] == ';');
            std::string body = commented ? trim(t.substr(1)) : t;
            size_t eq = body.find('=');
            if (eq == std::string::npos) continue;
            std::string k = trim(body.substr(0, eq));
            if (ieq(k, key)) {
                ln = key + " = " + val;
                replaced = true;
                break;
            }
        }
        if (!replaced) lines.push_back(key + " = " + val);
    }
    std::ofstream out(ini_path, std::ios::binary | std::ios::trunc);
    for (const auto& ln : lines) {
        out << ln << "\r\n";
    }
}

static void register_uninstall(const fs::path& dir, uint64_t bytes) {
    HKEY key = nullptr;
    if (RegCreateKeyExW(HKEY_CURRENT_USER, kUninstallKey, 0, nullptr, 0, KEY_WRITE, nullptr, &key, nullptr) !=
        ERROR_SUCCESS)
        return;
    auto set_s = [&](const wchar_t* name, const std::wstring& v) {
        RegSetValueExW(key, name, 0, REG_SZ, (const BYTE*)v.c_str(), (DWORD)((v.size() + 1) * sizeof(wchar_t)));
    };
    fs::path exe = fs::exists(dir / "totk.exe") ? (dir / "totk.exe") : (dir / "TotKLauncher.exe");
    fs::path uninst = dir / "unins000.exe";
    set_s(L"DisplayName", kAppDisplay);
    set_s(L"DisplayVersion", to_wide(TOTK_SETUP_VERSION));
    set_s(L"Publisher", L"SteelTemple");
    set_s(L"InstallLocation", dir.wstring());
    set_s(L"DisplayIcon", exe.wstring() + L",0");
    if (fs::exists(uninst)) set_s(L"UninstallString", L"\"" + uninst.wstring() + L"\" --uninstall");
    DWORD kb = (DWORD)std::max<uint64_t>(1, bytes / 1024);
    DWORD one = 1;
    RegSetValueExW(key, L"EstimatedSize", 0, REG_DWORD, (const BYTE*)&kb, sizeof(kb));
    RegSetValueExW(key, L"NoModify", 0, REG_DWORD, (const BYTE*)&one, sizeof(one));
    RegSetValueExW(key, L"NoRepair", 0, REG_DWORD, (const BYTE*)&one, sizeof(one));
    RegCloseKey(key);
}

// ---- App State ----
enum Page { PAGE_WELCOME, PAGE_FILES, PAGE_OPTIONS, PAGE_INSTALL, PAGE_UNINSTALL, PAGE_DONE };

struct Switch1Inputs {
    fs::path base_path;
    fs::path update_path;
    fs::path keys_path;
    fs::path firmware_path;
    std::string lang = "en-US";
};

struct JobState {
    std::mutex mu;
    std::atomic<bool> done{false};
    std::atomic<bool> ok{false};
    std::atomic<float> progress{0.0f};
    std::string phase = "Preparing...";
    std::string detail;
    uint64_t bytes_done = 0;
    uint64_t bytes_total = 0;
    uint32_t files_done = 0;
    uint32_t files_total = 0;
    std::string error;

    void set(float p, const std::string& ph, const std::string& det) {
        std::lock_guard<std::mutex> g(mu);
        progress = p;
        phase = ph;
        detail = det;
    }
};

static const char* kThemeIds[] = {"totk", "dark", "light"};
static const char* kThemeNames[] = {"Tears of the Kingdom (Zonai)", "Dark Theme", "Light Theme"};
static const char* kPromptIds[] = {"dualsense", "dualshock4", "xbox", "pc", "nintendo"};
static const char* kPromptNames[] = {
    "PlayStation 5 DualSense",
    "PlayStation 4 DualShock 4",
    "Xbox Series / One",
    "PC Keyboard & Mouse",
    "Nintendo Switch (Original)",
};
static const char* kLangCodes[] = {
    "en-US", "en-GB", "ja", "fr", "fr-CA", "de", "es", "es-419", "it", "nl", "ru", "ko", "zh-Hans", "zh-Hant",
};
static const char* kLangNames[] = {
    "English (US) [en-US]", "English (UK) [en-GB]", "Japanese [ja]", "French [fr]", "French (Canada) [fr-CA]",
    "German [de]", "Spanish [es]", "Spanish (Latin America) [es-419]", "Italian [it]", "Dutch [nl]",
    "Russian [ru]", "Korean [ko]", "Simplified Chinese [zh-Hans]", "Traditional Chinese [zh-Hant]",
};

// ---- 60 FPS Animated TOTK Procedural Backdrop ----
static ImU32 lerp_col(ImU32 a, ImU32 b, float t) {
    t = std::clamp(t, 0.0f, 1.0f);
    int r = (int)((a & 0xFF) + ((int)(b & 0xFF) - (int)(a & 0xFF)) * t);
    int g = (int)(((a >> 8) & 0xFF) + ((int)((b >> 8) & 0xFF) - (int)((a >> 8) & 0xFF)) * t);
    int bl = (int)(((a >> 16) & 0xFF) + ((int)((b >> 16) & 0xFF) - (int)((a >> 16) & 0xFF)) * t);
    int al = (int)(((a >> 24) & 0xFF) + ((int)((b >> 24) & 0xFF) - (int)((a >> 24) & 0xFF)) * t);
    return IM_COL32(r, g, bl, al);
}

static void draw_filled_triangle(ImDrawList* dl, ImVec2 cx, float r, float rot, ImU32 col) {
    ImVec2 p[3];
    for (int i = 0; i < 3; i++) {
        float a = rot - 1.5707963f + i * 2.0943951f;
        p[i] = ImVec2(cx.x + cosf(a) * r, cx.y + sinf(a) * r);
    }
    dl->AddTriangleFilled(p[0], p[1], p[2], col);
}

static void draw_triforce(ImDrawList* dl, ImVec2 center, float size, ImU32 gold, ImU32 glow) {
    float h = size * 0.8660254f;
    float s2 = size * 0.5f;
    // Place circumcenter at `center` so all 3 outer corners stay equidistant inside any concentric circle.
    float top_y = center.y - h * (2.0f / 3.0f);
    float mid_y = top_y + h * 0.5f;
    float bot_y = top_y + h;
    ImVec2 top(center.x, top_y);
    ImVec2 ml(center.x - s2 * 0.5f, mid_y);
    ImVec2 mr(center.x + s2 * 0.5f, mid_y);
    ImVec2 bl(center.x - s2, bot_y);
    ImVec2 bm(center.x, bot_y);
    ImVec2 br(center.x + s2, bot_y);

    // Subtle soft glow underneath
    dl->AddCircleFilled(center, size * 0.65f, glow, 36);
    dl->AddTriangleFilled(top, mr, ml, gold);
    dl->AddTriangleFilled(ml, bm, bl, gold);
    dl->AddTriangleFilled(mr, br, bm, gold);
}

static void draw_totk_backdrop(ImDrawList* dl, float W, float H, float s, float t) {
    // Base full-window deep obsidian fill
    dl->AddRectFilled(ImVec2(0, 0), ImVec2(W, H), IM_COL32(16, 21, 27, 255));

    // Right scene viewport starts around 36% so fade under panel reads smoothly
    float x0 = W * 0.34f;
    float scene_w = W - x0;
    ImVec2 hub(x0 + scene_w * 0.56f, H * 0.50f);

    // Twilight Sky Island sky gradient
    dl->AddRectFilledMultiColor(
        ImVec2(x0, 0), ImVec2(W, H * 0.55f),
        IM_COL32(10, 22, 26, 255), IM_COL32(14, 38, 36, 255),
        IM_COL32(17, 50, 44, 255), IM_COL32(12, 30, 30, 255));
    dl->AddRectFilledMultiColor(
        ImVec2(x0, H * 0.55f), ImVec2(W, H),
        IM_COL32(12, 30, 30, 255), IM_COL32(17, 50, 44, 255),
        IM_COL32(12, 26, 24, 255), IM_COL32(9, 16, 20, 255));

    // Soft radial Zonai glow behind crest
    for (int i = 5; i >= 1; i--) {
        float frac = (float)i / 5.0f;
        float rad = H * (0.14f + frac * 0.40f) * (1.0f + 0.025f * sinf(t * 1.4f));
        int alpha = (int)((1.0f - frac * 0.78f) * 28.0f);
        dl->AddCircleFilled(hub, rad, IM_COL32(34, 211, 160, alpha), 64);
    }

    // Floating distant Sky Island silhouettes gently bobbing
    auto draw_island = [&](float rx, float ry, float iw, float ih, float phase, ImU32 col) {
        float bob = sinf(t * 0.55f + phase) * 8.0f * s;
        float px = x0 + scene_w * rx;
        float py = H * ry + bob;
        ImVec2 pts[6] = {
            ImVec2(px - iw * 0.55f, py),
            ImVec2(px - iw * 0.35f, py - ih * 0.25f),
            ImVec2(px + iw * 0.40f, py - ih * 0.22f),
            ImVec2(px + iw * 0.55f, py + ih * 0.04f),
            ImVec2(px + iw * 0.12f, py + ih),
            ImVec2(px - iw * 0.26f, py + ih * 0.78f),
        };
        dl->AddConvexPolyFilled(pts, 6, col);
        dl->AddLine(pts[1], pts[2], IM_COL32(118, 224, 186, 48), 1.5f * s);
    };
    draw_island(0.22f, 0.26f, 130.0f * s, 54.0f * s, 0.0f, IM_COL32(13, 30, 32, 180));
    draw_island(0.83f, 0.20f, 160.0f * s, 68.0f * s, 1.7f, IM_COL32(11, 26, 28, 195));
    draw_island(0.80f, 0.76f, 180.0f * s, 64.0f * s, 3.1f, IM_COL32(10, 22, 24, 210));
    draw_island(0.25f, 0.78f, 115.0f * s, 46.0f * s, 4.4f, IM_COL32(12, 27, 28, 175));

    // Rotating concentric Zonai glyph rings (outer clockwise, middle counter-clockwise, inner clockwise)
    auto draw_dashed_ring = [&](float radius, float rot, int segs, float duty, float thick, ImU32 col) {
        const float two_pi = 6.2831853f;
        for (int i = 0; i < segs; i++) {
            float a0 = rot + two_pi * ((float)i / segs);
            float a1 = a0 + two_pi * (duty / segs);
            dl->PathArcTo(hub, radius, a0, a1, 6);
            dl->PathStroke(col, 0, thick);
        }
    };

    float r_outer = H * 0.37f;
    float r_mid = H * 0.295f;
    float r_inner = H * 0.215f;

    dl->AddCircle(hub, r_outer, IM_COL32(34, 211, 160, 42), 96, 1.5f * s);
    draw_dashed_ring(r_outer + 7.0f * s, t * 0.14f, 18, 0.56f, 2.6f * s, IM_COL32(34, 211, 160, 115));
    draw_dashed_ring(r_mid, -t * 0.24f, 12, 0.62f, 2.2f * s, IM_COL32(220, 188, 102, 130));
    draw_dashed_ring(r_mid - 9.0f * s, -t * 0.24f + 0.25f, 24, 0.35f, 1.5f * s, IM_COL32(34, 211, 160, 75));
    dl->AddCircle(hub, r_inner, IM_COL32(220, 188, 102, 85), 64, 1.4f * s);
    draw_dashed_ring(r_inner - 7.0f * s, t * 0.38f, 8, 0.55f, 2.0f * s, IM_COL32(34, 211, 160, 145));

    // Orbiting Zonai diamond nodes on outer and middle rings
    for (int i = 0; i < 6; i++) {
        float a = t * 0.14f + i * (6.2831853f / 6.0f);
        ImVec2 p(hub.x + cosf(a) * r_outer, hub.y + sinf(a) * r_outer);
        float d = 5.0f * s;
        ImVec2 pts[4] = {ImVec2(p.x, p.y - d), ImVec2(p.x + d, p.y), ImVec2(p.x, p.y + d), ImVec2(p.x - d, p.y)};
        dl->AddQuadFilled(pts[0], pts[1], pts[2], pts[3], IM_COL32(220, 188, 102, 190));
    }
    for (int i = 0; i < 4; i++) {
        float a = -t * 0.24f + i * (6.2831853f / 4.0f);
        ImVec2 p(hub.x + cosf(a) * r_mid, hub.y + sinf(a) * r_mid);
        draw_filled_triangle(dl, p, 6.0f * s, a + 1.57f, IM_COL32(34, 211, 160, 210));
    }

    // Center pulsing Triforce
    float tri_pulse = 0.85f + 0.15f * sinf(t * 2.1f);
    ImU32 gold_col = lerp_col(IM_COL32(204, 169, 82, 235), IM_COL32(246, 220, 134, 255), tri_pulse);
    draw_triforce(dl, hub, H * 0.145f, gold_col, IM_COL32(236, 198, 96, (int)(32 * tri_pulse)));

    // Rising emerald Zonai wisps & golden sunlight motes (deterministic seeded particles)
    for (int i = 0; i < 30; i++) {
        float seed = (float)i * 1.6180339f;
        float speed = 0.045f + fmodf(seed * 0.37f, 0.065f);
        float life = fmodf(t * speed + fmodf(seed * 0.73f, 1.0f), 1.0f);
        float px = x0 + scene_w * (0.08f + 0.86f * fmodf(seed * 0.43f, 1.0f)) +
                   sinf(t * 1.3f + seed * 3.0f) * 14.0f * s;
        float py = H * (1.03f - life * 1.06f);
        float fade = sinf(life * 3.1415926f);
        bool is_gold = (i % 3 == 0);
        float rad = (is_gold ? 2.6f : 3.2f) * s * (0.65f + 0.35f * sinf(t * 2.5f + seed));
        int a = (int)(fade * (is_gold ? 185.0f : 155.0f));
        ImU32 pcol = is_gold ? IM_COL32(238, 200, 102, a) : IM_COL32(52, 232, 180, a);
        dl->AddCircleFilled(ImVec2(px, py), rad * 2.2f, IM_COL32(is_gold ? 238 : 52, is_gold ? 200 : 232, is_gold ? 102 : 180, a / 4), 12);
        dl->AddCircleFilled(ImVec2(px, py), rad, pcol, 12);
    }

    // Subtle Zonai diamond horizon accent lines top and bottom of backdrop
    for (float bx = x0 + 20.0f * s; bx < W - 20.0f * s; bx += 22.0f * s) {
        float d = 2.5f * s;
        float y_top = 18.0f * s;
        float y_bot = H - 18.0f * s;
        dl->AddQuadFilled(ImVec2(bx, y_top - d), ImVec2(bx + d, y_top), ImVec2(bx, y_top + d), ImVec2(bx - d, y_top),
                          IM_COL32(34, 211, 160, 45));
        dl->AddQuadFilled(ImVec2(bx, y_bot - d), ImVec2(bx + d, y_bot), ImVec2(bx, y_bot + d), ImVec2(bx - d, y_bot),
                          IM_COL32(220, 188, 102, 45));
    }

    // Smooth gradient fade melting backdrop cleanly into left panel (#10151B)
    float panel_w = W * 0.45f;
    dl->AddRectFilled(ImVec2(0, 0), ImVec2(panel_w, H), IM_COL32(16, 21, 27, 255));
    dl->AddRectFilledMultiColor(
        ImVec2(panel_w, 0), ImVec2(panel_w + 150.0f * s, H),
        IM_COL32(16, 21, 27, 255), IM_COL32(16, 21, 27, 0),
        IM_COL32(16, 21, 27, 0), IM_COL32(16, 21, 27, 255));
}

// ---- Minimal JSON field extractors & Switch 1 extraction runner ----
static std::string json_get_str(const std::string& line, const std::string& key) {
    std::string pat = "\"" + key + "\"";
    size_t pos = line.find(pat);
    if (pos == std::string::npos) return {};
    pos = line.find(':', pos + pat.size());
    if (pos == std::string::npos) return {};
    pos = line.find_first_not_of(" \t", pos + 1);
    if (pos == std::string::npos || line[pos] != '"') return {};
    pos++;
    std::string out;
    while (pos < line.size() && line[pos] != '"') {
        if (line[pos] == '\\' && pos + 1 < line.size()) pos++;
        out.push_back(line[pos++]);
    }
    return out;
}

static double json_get_num(const std::string& line, const std::string& key, double fallback = -1.0) {
    std::string pat = "\"" + key + "\"";
    size_t pos = line.find(pat);
    if (pos == std::string::npos) return fallback;
    pos = line.find(':', pos + pat.size());
    if (pos == std::string::npos) return fallback;
    pos = line.find_first_not_of(" \t", pos + 1);
    if (pos == std::string::npos) return fallback;
    char* endp = nullptr;
    double v = strtod(line.c_str() + pos, &endp);
    return (endp == line.c_str() + pos) ? fallback : v;
}

static float step_base_progress(const std::string& step) {
    if (step == "check") return 0.04f;
    if (step == "fonts") return 0.09f;
    if (step == "extract") return 0.14f;
    if (step == "lift") return 0.34f;
    if (step == "compile") return 0.50f;
    if (step == "prepare") return 0.64f;
    if (step == "pc_prompts") return 0.68f;
    if (step == "dlss") return 0.70f;
    if (step == "cleanup") return 0.72f;
    return 0.10f;
}

static std::string step_label(const std::string& step) {
    if (step == "check") return "Verifying Switch 1 files & prod.keys...";
    if (step == "fonts") return "Extracting Switch shared fonts...";
    if (step == "extract") return "Decrypting & extracting Switch 1 RomFS / ExeFS...";
    if (step == "lift") return "Recompiling Switch 1 executable to C...";
    if (step == "compile") return "Compiling native totk.exe...";
    if (step == "prepare") return "Pre-translating shaders & pipelines...";
    if (step == "pc_prompts") return "Preparing prompt resources...";
    if (step == "dlss") return "Configuring DLSS runtime...";
    if (step == "cleanup") return "Cleaning temporary build files...";
    return "Running Switch 1 extraction...";
}

static bool find_switch1_toolchain(fs::path& out_root, fs::path& out_python) {
    std::error_code ec;
    fs::path cur = self_exe_path().parent_path();
    for (int depth = 0; depth < 4 && !cur.empty(); depth++) {
        if (fs::exists(cur / "installer" / "__main__.py", ec)) {
            out_root = cur;
            fs::path emb1 = cur / "python" / "python.exe";
            fs::path emb2 = cur / "build" / "py314-embed" / "py" / "python.exe";
            if (fs::is_regular_file(emb1, ec)) {
                out_python = emb1;
                return true;
            }
            if (fs::is_regular_file(emb2, ec)) {
                out_python = emb2;
                return true;
            }
            wchar_t found[MAX_PATH] = {};
            if (SearchPathW(nullptr, L"python.exe", nullptr, MAX_PATH, found, nullptr) > 0) {
                out_python = fs::path(found);
                return true;
            }
        }
        cur = cur.parent_path();
    }
    return false;
}

static bool run_switch1_extractor(JobState* job, const fs::path& root_dir, const fs::path& py_exe,
                                  const Switch1Inputs& sw1, const fs::path& dst, bool with_dlss,
                                  std::string& out_error) {
    std::wstring cmd = L"\"" + py_exe.wstring() + L"\" -u -m installer --dest \"" + dst.wstring() + L"\" --root \"" +
                       root_dir.wstring() + L"\" --keys \"" + sw1.keys_path.wstring() + L"\" --lang " +
                       to_wide(sw1.lang);
    if (!sw1.base_path.empty()) cmd += L" --base \"" + sw1.base_path.wstring() + L"\"";
    if (!sw1.update_path.empty()) cmd += L" --update \"" + sw1.update_path.wstring() + L"\"";
    if (!sw1.firmware_path.empty()) cmd += L" --firmware \"" + sw1.firmware_path.wstring() + L"\"";
    if (with_dlss) cmd += L" --dlss";

    SECURITY_ATTRIBUTES sa{sizeof(sa), nullptr, TRUE};
    HANDLE read_h = nullptr, write_h = nullptr;
    if (!CreatePipe(&read_h, &write_h, &sa, 0)) {
        out_error = "Failed to create pipe for Switch 1 extractor.";
        return false;
    }
    SetHandleInformation(read_h, HANDLE_FLAG_INHERIT, 0);

    STARTUPINFOW si{sizeof(si)};
    si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    si.hStdOutput = write_h;
    si.hStdError = write_h;
    PROCESS_INFORMATION pi{};
    if (!CreateProcessW(nullptr, cmd.data(), nullptr, nullptr, TRUE, CREATE_NO_WINDOW, nullptr, root_dir.c_str(), &si,
                        &pi)) {
        CloseHandle(read_h);
        CloseHandle(write_h);
        out_error = "Failed to start python -m installer.";
        return false;
    }
    CloseHandle(write_h);

    std::string buf, last_err;
    char tmp[2048];
    DWORD nread = 0;
    while (ReadFile(read_h, tmp, sizeof(tmp) - 1, &nread, nullptr) && nread > 0) {
        buf.append(tmp, nread);
        size_t nl = 0;
        while ((nl = buf.find('\n')) != std::string::npos) {
            std::string line = buf.substr(0, nl);
            buf.erase(0, nl + 1);
            if (!line.empty() && line.back() == '\r') line.pop_back();
            if (line.empty() || line[0] != '{') continue;
            std::string typ = json_get_str(line, "type");
            std::string step = json_get_str(line, "step");
            if (typ == "step") {
                job->set(step_base_progress(step), step_label(step), "Stage: " + step);
            } else if (typ == "progress") {
                std::string ph = json_get_str(line, "phase");
                double done_v = json_get_num(line, "done", 0.0);
                double tot_v = json_get_num(line, "total", 0.0);
                std::string unit = json_get_str(line, "unit");
                float b = step_base_progress(step);
                float frac = (tot_v > 0.0) ? (float)std::clamp(done_v / tot_v, 0.0, 1.0) : 0.2f;
                char det[160];
                if (tot_v > 0.0) {
                    snprintf(det, sizeof(det), "%s: %.0f / %.0f %s", ph.c_str(), done_v, tot_v, unit.c_str());
                } else {
                    snprintf(det, sizeof(det), "%s", ph.c_str());
                }
                job->set(std::min(0.72f, b + frac * 0.12f), step_label(step), det);
            } else if (typ == "error") {
                std::string eid = json_get_str(line, "id");
                std::string edet = json_get_str(line, "detail");
                last_err = edet.empty() ? ("Installer error: " + eid) : (eid + " (" + edet + ")");
            }
        }
    }
    CloseHandle(read_h);
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD code = 1;
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    if (code != 0) {
        out_error = last_err.empty() ? ("Switch 1 extraction exited with code " + std::to_string(code)) : last_err;
        return false;
    }
    return true;
}

static void run_prompt_gen(const fs::path& dst, const std::string& style, const std::wstring& ver) {
    std::error_code ec;
    fs::path out_dir = dst / ("romfs-patches-" + style);
    if (fs::exists(out_dir / "manifest.tsv", ec)) return;
    fs::path launcher = dst / "TotKLauncher.exe";
    if (!fs::exists(launcher, ec)) return;
    std::wstring cmd = L"\"" + launcher.wstring() + L"\" --run-prompts-patcher " + to_wide(style) + L" " + ver +
                       L" \"" + (dst / "romfs").wstring() + L"\" \"" + out_dir.wstring() + L"\"";
    STARTUPINFOW si{sizeof(si)};
    PROCESS_INFORMATION pi{};
    if (CreateProcessW(nullptr, cmd.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW, nullptr, dst.c_str(), &si, &pi)) {
        WaitForSingleObject(pi.hProcess, 180000);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
}

// ---- Actual Install / Configure Worker ----
static void run_install_worker(JobState* job, const Payload* payload, Switch1Inputs sw1, fs::path dst, int theme_idx,
                               int prompt_idx, bool copy_sdks, bool import_save, fs::path save_src,
                               bool make_shortcuts, bool write_guide) {
    std::error_code ec;
    fs::create_directories(dst, ec);
    if (ec) {
        job->error = "Cannot create destination folder: " + ec.message();
        job->done = true;
        return;
    }

    // 0. Switch 1 prod.keys MUST always be validated before installing
    std::string key_err;
    if (!validate_prod_keys(utf8_from_path(sw1.keys_path), key_err)) {
        job->error = key_err;
        job->done = true;
        return;
    }

    fs::path sw_root, sw_python;
    bool has_sw_toolchain = find_switch1_toolchain(sw_root, sw_python);

    // 1. Extract payload if bundled (`TOTKPKG1`), otherwise run the Switch 1 extractor (`python -m installer`)
    if (payload && payload->present && !payload->entries.empty()) {
        job->files_total = (uint32_t)payload->entries.size();
        job->bytes_total = payload->total_raw;
        std::ifstream in(self_exe_path(), std::ios::binary);
        ZSTD_DCtx* dctx = ZSTD_createDCtx();
        std::vector<char> cbuf;
        std::vector<char> rbuf;

        for (size_t i = 0; i < payload->entries.size(); i++) {
            const auto& e = payload->entries[i];
            {
                std::lock_guard<std::mutex> g(job->mu);
                job->phase = "Installing game files...";
                job->detail = e.rel_path;
                job->files_done = (uint32_t)i;
                job->progress = payload->total_raw ? 0.65f * ((float)job->bytes_done / (float)payload->total_raw) : 0.3f;
            }
            fs::path out_p = dst / path_from_utf8(e.rel_path);
            fs::create_directories(out_p.parent_path(), ec);
            cbuf.resize((size_t)e.comp_size);
            rbuf.resize((size_t)e.raw_size);
            in.seekg((std::streamoff)e.comp_offset);
            in.read(cbuf.data(), (std::streamsize)e.comp_size);
            size_t dec = ZSTD_decompressDCtx(dctx, rbuf.data(), rbuf.size(), cbuf.data(), cbuf.size());
            if (ZSTD_isError(dec)) {
                ZSTD_freeDCtx(dctx);
                job->error = "Corrupt payload entry: " + e.rel_path;
                job->done = true;
                return;
            }
            std::ofstream out(out_p, std::ios::binary | std::ios::trunc);
            out.write(rbuf.data(), (std::streamsize)dec);
            if (!out) {
                ZSTD_freeDCtx(dctx);
                job->error = "Cannot write file (is totk.exe running?): " + e.rel_path;
                job->done = true;
                return;
            }
            std::lock_guard<std::mutex> g(job->mu);
            job->bytes_done += e.raw_size;
            job->files_done = (uint32_t)(i + 1);
        }
        ZSTD_freeDCtx(dctx);

        fs::copy_file(self_exe_path(), dst / "unins000.exe", fs::copy_options::overwrite_existing, ec);
    } else if (!fs::exists(dst / "totk.exe", ec) || !fs::exists(dst / "romfs" / "romfs.bin", ec) ||
               (!sw1.base_path.empty() && !sw1.update_path.empty())) {
        if (sw1.base_path.empty() || !fs::is_regular_file(sw1.base_path, ec) ||
            sw1.update_path.empty() || !fs::is_regular_file(sw1.update_path, ec)) {
            if (!fs::exists(dst / "totk.exe", ec) || !fs::exists(dst / "romfs" / "romfs.bin", ec)) {
                job->error = "Base Game (.xci/.nsp) and Update (.nsp/.nsz) are required for Switch 1 extraction.";
                job->done = true;
                return;
            }
        } else {
            if (!has_sw_toolchain) {
                job->error = "Switch 1 extraction toolchain (python/ and installer/) was not found next to Setup.";
                job->done = true;
                return;
            }
            std::string ext_err;
            job->set(0.03f, "Starting Switch 1 extractor...", utf8_from_path(sw1.base_path.filename()));
            if (!run_switch1_extractor(job, sw_root, sw_python, sw1, dst, copy_sdks, ext_err)) {
                job->error = ext_err;
                job->done = true;
                return;
            }
        }
    }

    // 1b. Deploy TotKLauncher.exe & TotKPatcher.exe if available next to setup or in repo assets
    fs::path self_dir = self_exe_path().parent_path();
    const std::pair<const char*, fs::path> helper_bins[] = {
        {"TotKLauncher.exe", sw_root / "launcher" / "dist" / "TotKLauncher.exe"},
        {"TotKPatcher.exe", sw_root / "launcher" / "dist" / "TotKPatcher.exe"},
    };
    for (const auto& [hname, sw_cand] : helper_bins) {
        fs::path cands[] = {
            self_dir / hname,
            self_dir / "assets" / hname,
            sw_cand,
        };
        for (const auto& lc : cands) {
            if (!lc.empty() && fs::is_regular_file(lc, ec) && !fs::exists(dst / hname, ec)) {
                fs::copy_file(lc, dst / hname, fs::copy_options::overwrite_existing, ec);
                break;
            }
        }
    }

    // 1c. Remove/disable conflicting third-party prompt UI mods so native prompts match on-screen buttons
    fs::path mods_dir = dst / "mods";
    if (fs::is_directory(mods_dir, ec)) {
        for (const auto& entry : fs::directory_iterator(mods_dir, ec)) {
            if (!entry.is_directory(ec)) continue;
            std::string nm = utf8_from_path(entry.path().filename());
            for (char& ch : nm) ch = (char)tolower((unsigned char)ch);
            if (nm.find("ps5 ui") != std::string::npos || nm.find("xbox ui") != std::string::npos) {
                fs::remove_all(entry.path(), ec);
            }
        }
    }

    // 2. Write / update clean totk.ini settings (never hardcoding personal paths!)
    job->set(0.74f, "Configuring F1 menu theme & controller layout...", "Writing totk.ini");
    fs::path ini = dst / "totk.ini";
    if (!fs::exists(ini, ec) && fs::exists(dst / "totk.ini.example", ec)) {
        fs::copy_file(dst / "totk.ini.example", ini, fs::copy_options::none, ec);
    }
    write_ini_kv(ini, {
        {"menu_theme", kThemeIds[std::clamp(theme_idx, 0, 2)]},
        {"touchpad_menu", "1"},
        {"pad_layout", "auto"},
        {"prompts", kPromptIds[std::clamp(prompt_idx, 0, 4)]},
    });

    // Build controller prompts RomFS overlays (both positional and -label variants) if RomFS + TotKLauncher.exe exist
    if (prompt_idx != 4 && fs::exists(dst / "romfs" / "romfs.bin", ec) && fs::exists(dst / "TotKLauncher.exe", ec)) {
        job->set(0.78f, "Generating controller button prompts overlay...", kPromptIds[prompt_idx]);
        std::wstring ver = fs::exists(dst / "exefs" / "1.4.3", ec) ? L"v143" : L"v121";
        std::ifstream idx(dst / "romfs" / "index.json", std::ios::binary);
        if (idx) {
            std::string chunk(65536, '\0');
            while (idx.read(chunk.data(), chunk.size()) || idx.gcount() > 0) {
                chunk.resize((size_t)idx.gcount());
                if (chunk.find("Product.140.") != std::string::npos) {
                    ver = L"v143";
                    break;
                }
                chunk.resize(65536);
            }
        }
        if (prompt_idx == 3) {
            run_prompt_gen(dst, "pc", ver);
        } else {
            run_prompt_gen(dst, kPromptIds[prompt_idx], ver);
            run_prompt_gen(dst, std::string(kPromptIds[prompt_idx]) + "-label", ver);
        }
    }

    // 3. Copy vendor DLLs from installer's adjacent folder if requested & missing
    if (copy_sdks) {
        job->set(0.84f, "Checking upscaler SDK DLLs...", "DLSS / DLSS-NR / XeSS");
        const char* sdk_dlls[] = {"nvngx_dlss.dll", "nvngx_dlssg.dll", "nvngx_dlssnr.dll", "libxess.dll",
                                  "libxess_fg.dll", "libxell.dll", "sl.interposer.dll", "sl.common.dll",
                                  "sl.dlss.dll", "sl.dlss_g.dll", "sl.dlss_nr.dll", "sl.reflex.dll"};
        fs::path src_dir = self_exe_path().parent_path();
        for (const char* dll : sdk_dlls) {
            if (!fs::exists(dst / dll, ec) && fs::exists(src_dir / dll, ec)) {
                fs::copy_file(src_dir / dll, dst / dll, fs::copy_options::overwrite_existing, ec);
            }
        }
    }

    // 4. Import emulator save if selected
    if (import_save && !save_src.empty() && fs::exists(save_src, ec)) {
        job->set(0.89f, "Importing save game data...", utf8_from_path(save_src));
        fs::path dest_save = dst / "profile" / "user" / "save";
        bool has_direct_sav = false;
        for (const auto& it : fs::directory_iterator(save_src, ec)) {
            if (it.is_regular_file(ec) && it.path().extension() == L".sav") {
                has_direct_sav = true;
                break;
            }
        }
        fs::path target_root = has_direct_sav ? (dest_save / "0") : dest_save;
        fs::create_directories(target_root, ec);
        fs::copy(save_src, target_root, fs::copy_options::recursive | fs::copy_options::overwrite_existing, ec);
    }

    // 5. Write CONTROLLER_GUIDE.txt
    if (write_guide) {
        job->set(0.93f, "Writing Controller Guide...", "CONTROLLER_GUIDE.txt");
        std::ofstream g1(dst / "CONTROLLER_GUIDE.txt", std::ios::binary | std::ios::trunc);
        g1.write(kGuideText, sizeof(kGuideText) - 1);
    }

    // 6. Desktop & Start Menu shortcuts
    if (make_shortcuts) {
        job->set(0.96f, "Creating Windows shortcuts...", utf8_from_path(dst));
        fs::path target_exe = fs::exists(dst / "TotKLauncher.exe", ec) ? (dst / "TotKLauncher.exe") : (dst / "totk.exe");
        if (fs::exists(target_exe, ec)) {
            fs::path desk = known_folder(FOLDERID_Desktop);
            fs::path sm = known_folder(FOLDERID_Programs);
            if (!desk.empty())
                create_shortcut(desk / (std::wstring(kAppDisplay) + L".lnk"), target_exe, dst, target_exe,
                                L"The Legend of Zelda: Tears of the Kingdom (PC Recompiled)");
            if (!sm.empty())
                create_shortcut(sm / kAppDisplay / (std::wstring(kAppDisplay) + L".lnk"), target_exe, dst, target_exe,
                                L"The Legend of Zelda: Tears of the Kingdom (PC Recompiled)");
        }
    }

    if (payload && payload->present) register_uninstall(dst, payload->total_raw);
    job->set(1.0f, "Setup complete!", utf8_from_path(dst));
    job->ok = true;
    job->done = true;
}

static void run_uninstall_worker(JobState* job, fs::path dst) {
    std::error_code ec;
    job->set(0.25f, "Removing shortcuts...", "");
    fs::path desk = known_folder(FOLDERID_Desktop);
    fs::path sm = known_folder(FOLDERID_Programs);
    if (!desk.empty()) fs::remove(desk / (std::wstring(kAppDisplay) + L".lnk"), ec);
    if (!sm.empty()) fs::remove_all(sm / kAppDisplay, ec);

    job->set(0.60f, "Removing game binaries (keeping saves)...", utf8_from_path(dst));
    const char* bin_files[] = {"totk.exe", "TotKLauncher.exe", "TotKPatcher.exe", "totk_xlate.exe", "SDL3.dll", "libopus-0.dll"};
    for (const char* f : bin_files) fs::remove(dst / f, ec);
    RegDeleteTreeW(HKEY_CURRENT_USER, kUninstallKey);
    job->set(1.0f, "Uninstall complete (saves in profile/ were kept).", utf8_from_path(dst));
    job->ok = true;
    job->done = true;
}

// ---- Headless screenshot capture helper (`--shot` or `TOTK_SETUP_SHOT`) ----
static void save_shot(SDL_Renderer* r, const fs::path& path) {
    SDL_Surface* surf = SDL_RenderReadPixels(r, nullptr);
    if (!surf) return;
    std::error_code ec;
    fs::create_directories(path.parent_path(), ec);
    SDL_SavePNG(surf, utf8_from_path(path).c_str());
    SDL_DestroySurface(surf);
}

// ---- Main UI ----
int WINAPI WinMain(HINSTANCE, HINSTANCE, LPSTR, int) {
    CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE);

    // Parse args (`--uninstall`, `--shot DIR`) and `TOTK_SETUP_SHOT`
    int argc = 0;
    LPWSTR* argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    bool uninstall_mode = false;
    fs::path shot_dir;
    if (const char* e = std::getenv("TOTK_SETUP_SHOT")) {
        if (*e) shot_dir = path_from_utf8(e);
    }
    for (int i = 1; i < argc; i++) {
        if (wcscmp(argv[i], L"--uninstall") == 0) uninstall_mode = true;
        else if (wcscmp(argv[i], L"--shot") == 0 && i + 1 < argc) shot_dir = fs::path(argv[++i]);
    }
    if (argv) LocalFree(argv);

    Payload payload = inspect_payload();
    std::vector<SaveCandidate> saves = scan_saves();

    // Clean hardware-agnostic default path (`%LOCALAPPDATA%\Programs\Tears of the Kingdom`),
    // or the installer's folder itself if totk.exe already lives next to the installer.
    fs::path default_dir = known_folder(FOLDERID_LocalAppData) / "Programs" / "Tears of the Kingdom";
    if (fs::exists(self_exe_path().parent_path() / "totk.exe")) {
        default_dir = self_exe_path().parent_path();
    } else if (fs::exists(self_exe_path().parent_path() / "GAME" / "totk.exe")) {
        default_dir = self_exe_path().parent_path() / "GAME";
    }

    if (!SDL_Init(SDL_INIT_VIDEO)) {
        CoUninitialize();
        return 1;
    }

    float init_scale = 1.0f;
    if (SDL_DisplayID did = SDL_GetPrimaryDisplay()) {
        float ds = SDL_GetDisplayContentScale(did);
        if (ds > 0.5f && ds < 4.0f) init_scale = ds;
    }
    int win_w = (int)roundf(1240.0f * init_scale);
    int win_h = (int)roundf(760.0f * init_scale);
    SDL_WindowFlags wflags = SDL_WINDOW_HIGH_PIXEL_DENSITY;
    if (!shot_dir.empty()) wflags |= SDL_WINDOW_HIDDEN;
    SDL_Window* win = SDL_CreateWindow("Tears of the Kingdom - Setup", win_w, win_h, wflags);
    if (!win) {
        SDL_Quit();
        CoUninitialize();
        return 1;
    }
    SDL_Renderer* ren = SDL_CreateRenderer(win, nullptr);
    if (!ren) {
        SDL_DestroyWindow(win);
        SDL_Quit();
        CoUninitialize();
        return 1;
    }
    SDL_SetRenderVSync(ren, 1);

    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.IniFilename = nullptr;

    ImGui_ImplSDL3_InitForSDLRenderer(win, ren);
    ImGui_ImplSDLRenderer3_Init(ren);

    float ds = SDL_GetWindowDisplayScale(win);
    if (ds <= 0.1f) ds = init_scale;

    ImFontConfig fc;
    fc.FontDataOwnedByAtlas = false;
    io.Fonts->AddFontFromMemoryTTF((void*)kRobotoMediumTtf, (int)kRobotoMediumTtfLen, floorf(16.5f * ds), &fc);

    // Style setup matching MKW cards with TOTK emerald + gold palette
    ImGuiStyle& st = ImGui::GetStyle();
    st.WindowBorderSize = 0.0f;
    st.FrameBorderSize = 1.0f;
    st.ChildBorderSize = 1.0f;
    st.FrameRounding = 8.0f * ds;
    st.GrabRounding = 8.0f * ds;
    st.ChildRounding = 10.0f * ds;
    st.WindowPadding = ImVec2(0, 0);
    st.FramePadding = ImVec2(11.0f * ds, 7.0f * ds);
    st.ItemSpacing = ImVec2(10.0f * ds, 8.0f * ds);

    auto& c = st.Colors;
    c[ImGuiCol_WindowBg] = ImVec4(0.06f, 0.08f, 0.11f, 0.0f);
    c[ImGuiCol_ChildBg] = ImVec4(0.09f, 0.12f, 0.15f, 0.92f);
    c[ImGuiCol_Border] = ImVec4(0.16f, 0.25f, 0.24f, 0.85f);
    c[ImGuiCol_Text] = ImVec4(0.95f, 0.96f, 0.96f, 1.0f);
    c[ImGuiCol_TextDisabled] = ImVec4(0.56f, 0.62f, 0.63f, 1.0f);
    c[ImGuiCol_FrameBg] = ImVec4(0.08f, 0.11f, 0.14f, 1.0f);
    c[ImGuiCol_FrameBgHovered] = ImVec4(0.11f, 0.17f, 0.19f, 1.0f);
    c[ImGuiCol_FrameBgActive] = ImVec4(0.13f, 0.22f, 0.21f, 1.0f);
    c[ImGuiCol_Button] = ImVec4(0.13f, 0.18f, 0.21f, 1.0f);
    c[ImGuiCol_ButtonHovered] = ImVec4(0.18f, 0.26f, 0.28f, 1.0f);
    c[ImGuiCol_ButtonActive] = ImVec4(0.12f, 0.20f, 0.22f, 1.0f);
    c[ImGuiCol_CheckMark] = ImVec4(0.13f, 0.83f, 0.63f, 1.0f);
    c[ImGuiCol_PlotHistogram] = ImVec4(0.13f, 0.83f, 0.63f, 1.0f);
    c[ImGuiCol_PopupBg] = ImVec4(0.08f, 0.11f, 0.14f, 0.98f);
    c[ImGuiCol_Header] = ImVec4(0.13f, 0.55f, 0.44f, 0.45f);
    c[ImGuiCol_HeaderHovered] = ImVec4(0.13f, 0.68f, 0.52f, 0.55f);

    // Interactive state + Switch 1 game/key auto-detection
    Page page = uninstall_mode ? PAGE_UNINSTALL : PAGE_WELCOME;
    char dir_buf[1024] = {};
    char base_buf[1024] = {};
    char upd_buf[1024] = {};
    char keys_buf[1024] = {};
    char fw_buf[1024] = {};
    snprintf(dir_buf, sizeof(dir_buf), "%s", utf8_from_path(default_dir).c_str());
    snprintf(base_buf, sizeof(base_buf), "%s", auto_find_game_file(false).c_str());
    snprintf(upd_buf, sizeof(upd_buf), "%s", auto_find_game_file(true).c_str());
    snprintf(keys_buf, sizeof(keys_buf), "%s", auto_find_keys().c_str());
    int lang_idx = 0;    // en-US default
    int theme_idx = 0;   // Tears of the Kingdom default
    int prompt_idx = 0;  // PS5 DualSense default
    int save_idx = 0;
    bool opt_import_save = !saves.empty();
    bool opt_sdks = true;
    bool opt_shortcuts = true;
    bool opt_guide = true;

    JobState job;
    std::thread worker;
    bool launched_uninstall = false;

    const ImVec4 kZonaiGreen(0.13f, 0.83f, 0.63f, 1.0f);
    const ImVec4 kZonaiGreenHov(0.18f, 0.90f, 0.70f, 1.0f);
    const ImVec4 kGold(0.88f, 0.75f, 0.40f, 1.0f);
    const ImVec4 kErrRed(1.0f, 0.42f, 0.42f, 1.0f);
    const ImU32 kAccentU = IM_COL32(34, 211, 160, 255);
    const ImU32 kGoldU = IM_COL32(224, 192, 102, 255);
    const ImU32 kDimU = IM_COL32(146, 160, 162, 255);

    auto draw_primary_btn = [&](const char* label, float bw, float bh) -> bool {
        ImGui::PushStyleColor(ImGuiCol_Button, kZonaiGreen);
        ImGui::PushStyleColor(ImGuiCol_ButtonHovered, kZonaiGreenHov);
        ImGui::PushStyleColor(ImGuiCol_ButtonActive, ImVec4(0.09f, 0.68f, 0.50f, 1.0f));
        ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.04f, 0.08f, 0.08f, 1.0f));
        bool clicked = ImGui::Button(label, ImVec2(bw, bh));
        ImGui::PopStyleColor(4);
        return clicked;
    };

    auto draw_feature_card = [&](const char* title, const char* desc, ImU32 bar_col) {
        ImDrawList* dl = ImGui::GetWindowDrawList();
        ImVec2 p0 = ImGui::GetCursorScreenPos();
        float cw = ImGui::GetContentRegionAvail().x;
        float ch = 66.0f * ds;
        dl->AddRectFilled(p0, ImVec2(p0.x + cw, p0.y + ch), IM_COL32(22, 30, 36, 235), 8.0f * ds);
        dl->AddRect(p0, ImVec2(p0.x + cw, p0.y + ch), IM_COL32(42, 62, 62, 190), 8.0f * ds, 0, 1.0f * ds);
        dl->AddRectFilled(ImVec2(p0.x + 8.0f * ds, p0.y + 12.0f * ds),
                          ImVec2(p0.x + 12.0f * ds, p0.y + ch - 12.0f * ds), bar_col, 2.0f * ds);
        ImFont* fnt = ImGui::GetFont();
        dl->AddText(fnt, 16.0f * ds, ImVec2(p0.x + 22.0f * ds, p0.y + 10.0f * ds), IM_COL32(244, 248, 247, 255), title);
        dl->AddText(fnt, 13.0f * ds, ImVec2(p0.x + 22.0f * ds, p0.y + 34.0f * ds), kDimU, desc, nullptr,
                    cw - 32.0f * ds);
        ImGui::Dummy(ImVec2(cw, ch));
    };

    auto render_frame = [&](float anim_t) {
        ImGui_ImplSDLRenderer3_NewFrame();
        ImGui_ImplSDL3_NewFrame();
        ImGui::NewFrame();

        int rw = 0, rh = 0;
        SDL_GetWindowSizeInPixels(win, &rw, &rh);
        float W = (float)rw, H = (float)rh;

        ImGui::SetNextWindowPos(ImVec2(0, 0));
        ImGui::SetNextWindowSize(ImVec2(W, H));
        ImGui::Begin("##setup_root", nullptr,
                     ImGuiWindowFlags_NoDecoration | ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoSavedSettings |
                         ImGuiWindowFlags_NoBringToFrontOnFocus | ImGuiWindowFlags_NoBackground);

        ImDrawList* bg_dl = ImGui::GetWindowDrawList();
        draw_totk_backdrop(bg_dl, W, H, ds, anim_t);

        // Left interactive panel (48% width)
        float pad = 30.0f * ds;
        float panel_w = W * 0.48f;
        ImGui::SetCursorPos(ImVec2(pad, pad * 0.80f));
        ImGui::BeginChild("##left_panel", ImVec2(panel_w - pad * 1.15f, H - pad * 1.60f), ImGuiChildFlags_None,
                          ImGuiWindowFlags_NoBackground | ImGuiWindowFlags_NoScrollbar);

        // Branded top header with concentric centered Triforce crest
        ImDrawList* dl = ImGui::GetWindowDrawList();
        ImVec2 hp = ImGui::GetCursorScreenPos();
        float cr = 18.0f * ds;
        ImVec2 hc(hp.x + cr, hp.y + cr);
        dl->AddCircleFilled(hc, cr, IM_COL32(18, 42, 36, 255), 36);
        dl->AddCircle(hc, cr, kAccentU, 36, 1.5f * ds);
        draw_triforce(dl, hc, 20.0f * ds, kGoldU, IM_COL32(230, 194, 90, 35));
        ImFont* fnt = ImGui::GetFont();
        dl->AddText(fnt, 18.0f * ds, ImVec2(hp.x + cr * 2.0f + 12.0f * ds, hp.y + 1.0f * ds), kGoldU,
                    "TEARS OF THE KINGDOM");
        char sub[128];
        snprintf(sub, sizeof(sub), "SteelTemple PC Recompiled  |  Switch 1 Edition  |  %s", TOTK_SETUP_VERSION);
        dl->AddText(fnt, 13.0f * ds, ImVec2(hp.x + cr * 2.0f + 12.0f * ds, hp.y + 21.0f * ds), kDimU, sub);
        ImGui::Dummy(ImVec2(0, cr * 2.0f + 12.0f * ds));

        // Reserve generous footer height so bottom rounded corners are never clipped
        float foot_h = 74.0f * ds;
        float body_h = std::max(120.0f * ds, ImGui::GetContentRegionAvail().y - foot_h);
        ImGui::BeginChild("##body", ImVec2(0, body_h), ImGuiChildFlags_None, ImGuiWindowFlags_NoBackground);

        std::error_code ec;
        std::string keys_msg;
        bool keys_valid = validate_prod_keys(keys_buf, keys_msg);
        fs::path target_p = path_from_utf8(dir_buf);
        bool has_existing = fs::exists(target_p / "totk.exe", ec) && fs::exists(target_p / "romfs" / "romfs.bin", ec);
        bool base_ok = fs::is_regular_file(path_from_utf8(base_buf), ec);
        bool upd_ok = fs::is_regular_file(path_from_utf8(upd_buf), ec);
        bool need_sw1_dumps = !payload.present && !has_existing;
        bool files_ready = keys_valid && (!need_sw1_dumps || (base_ok && upd_ok));

        if (page == PAGE_WELCOME) {
            ImGui::SetWindowFontScale(1.38f);
            ImGui::TextWrapped("Native Windows Edition (Switch 1)");
            ImGui::SetWindowFontScale(1.0f);
            ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.70f, 0.76f, 0.76f, 1.0f));
            ImGui::TextWrapped(payload.present
                                   ? "One-step Switch 1 setup: verifies your prod.keys, installs the native Vulkan PC port, F1 menu themes, controller prompts, and emulator saves."
                                   : "One-step Switch 1 setup: extracts your Switch 1 Base Game + Update using prod.keys, compiles the native Vulkan port, and configures themes, prompts & saves.");
            ImGui::PopStyleColor();
            ImGui::Dummy(ImVec2(0, 8.0f * ds));

            draw_feature_card("In-Game F1 Overlay & TOTK Themes",
                              "TOTK Zonai, Dark & Light themes - open via F1, Select+Start, or PS4/PS5 Touchpad",
                              kAccentU);
            ImGui::Dummy(ImVec2(0, 2.0f * ds));
            draw_feature_card("Native 60+ FPS Vulkan, DLSS & XeSS",
                              "Hardware-accelerated upscaling, DLSS-NR, adaptive triggers & per-game shaders",
                              kGoldU);
            ImGui::Dummy(ImVec2(0, 2.0f * ds));
            draw_feature_card("Switch 1 Extraction, Prompts & Saves",
                              "Requires Switch 1 prod.keys & game dumps; auto-detects DualSense/Xbox/Ryujinx saves",
                              IM_COL32(72, 186, 232, 255));
        } else if (page == PAGE_FILES) {
            float browse_w = 92.0f * ds;
            float avail_w = ImGui::GetContentRegionAvail().x;
            float in_w = avail_w - browse_w - 8.0f * ds;

            ImGui::PushStyleColor(ImGuiCol_Text, kGold);
            ImGui::TextUnformatted("Switch 1 Game Files & Required Decryption Keys");
            ImGui::PopStyleColor();

            ImGui::TextUnformatted("Base Game (.xci / .nsp / .xcz / .nsz)");
            ImGui::SetNextItemWidth(in_w);
            ImGui::InputText("##base_game", base_buf, sizeof(base_buf));
            ImGui::SameLine();
            if (ImGui::Button("Browse##base", ImVec2(browse_w, 0))) {
                const COMDLG_FILTERSPEC f[] = {{L"Switch Game Files (*.xci;*.nsp;*.xcz;*.nsz)", L"*.xci;*.nsp;*.xcz;*.nsz"},
                                               {L"All Files (*.*)", L"*.*"}};
                std::string p = browse_file(win, base_buf, L"Select Tears of the Kingdom Base Game", f, 2);
                if (!p.empty()) snprintf(base_buf, sizeof(base_buf), "%s", p.c_str());
            }

            ImGui::TextUnformatted("Game Update (.nsp / .nsz - 1.1.0 / 1.2.1 / 1.4.3)");
            ImGui::SetNextItemWidth(in_w);
            ImGui::InputText("##upd_nsp", upd_buf, sizeof(upd_buf));
            ImGui::SameLine();
            if (ImGui::Button("Browse##upd", ImVec2(browse_w, 0))) {
                const COMDLG_FILTERSPEC f[] = {{L"Switch Update Files (*.nsp;*.nsz)", L"*.nsp;*.nsz"},
                                               {L"All Files (*.*)", L"*.*"}};
                std::string p = browse_file(win, upd_buf, L"Select Tears of the Kingdom Update", f, 2);
                if (!p.empty()) snprintf(upd_buf, sizeof(upd_buf), "%s", p.c_str());
            }

            ImGui::PushStyleColor(ImGuiCol_Text, keys_valid ? kZonaiGreen : kErrRed);
            ImGui::Text("Switch prod.keys (Required)  -  %s", keys_msg.c_str());
            ImGui::PopStyleColor();
            ImGui::SetNextItemWidth(in_w);
            ImGui::InputText("##prod_keys", keys_buf, sizeof(keys_buf));
            ImGui::SameLine();
            if (ImGui::Button("Browse##keys", ImVec2(browse_w, 0))) {
                const COMDLG_FILTERSPEC f[] = {{L"Switch Keys (prod.keys)", L"*.keys;prod.keys"},
                                               {L"All Files (*.*)", L"*.*"}};
                std::string p = browse_file(win, keys_buf, L"Select Switch 1 prod.keys", f, 2);
                if (!p.empty()) snprintf(keys_buf, sizeof(keys_buf), "%s", p.c_str());
            }

            ImGui::TextUnformatted("Firmware Folder (Optional - for Chinese/Korean fonts)");
            ImGui::SetNextItemWidth(in_w);
            ImGui::InputText("##fw_dir", fw_buf, sizeof(fw_buf));
            ImGui::SameLine();
            if (ImGui::Button("Browse##fw", ImVec2(browse_w, 0))) {
                std::string p = browse_folder(win, fw_buf, L"Select Switch Firmware Folder (Contents/registered)");
                if (!p.empty()) snprintf(fw_buf, sizeof(fw_buf), "%s", p.c_str());
            }

            ImGui::TextUnformatted("Game Language & Install Folder");
            ImGui::SetNextItemWidth(avail_w * 0.44f);
            ImGui::Combo("##game_lang", &lang_idx, kLangNames, (int)(sizeof(kLangNames) / sizeof(kLangNames[0])));
            ImGui::SameLine();
            ImGui::SetNextItemWidth(avail_w * 0.56f - browse_w - 16.0f * ds);
            ImGui::InputText("##dir", dir_buf, sizeof(dir_buf));
            ImGui::SameLine();
            if (ImGui::Button("Browse##dir", ImVec2(browse_w, 0))) {
                std::string p = browse_folder(win, dir_buf, L"Select Tears of the Kingdom Installation Folder");
                if (!p.empty()) snprintf(dir_buf, sizeof(dir_buf), "%s", p.c_str());
            }

            ULARGE_INTEGER free_bytes{};
            std::string free_str;
            fs::path probe_p = target_p;
            while (!probe_p.empty() && !fs::exists(probe_p, ec)) probe_p = probe_p.parent_path();
            if (!probe_p.empty() && GetDiskFreeSpaceExW(probe_p.c_str(), &free_bytes, nullptr, nullptr)) {
                char fb[64];
                snprintf(fb, sizeof(fb), "%.1f GB free", (double)free_bytes.QuadPart / (1024.0 * 1024.0 * 1024.0));
                free_str = fb;
            }
            ImGui::PushStyleColor(ImGuiCol_Text, has_existing ? kZonaiGreen : ImVec4(0.65f, 0.72f, 0.73f, 1.0f));
            ImGui::Text("%s  %s", has_existing ? "Existing TOTK install detected" : "Target install folder",
                        free_str.c_str());
            ImGui::PopStyleColor();
        } else if (page == PAGE_OPTIONS) {
            ImGui::PushStyleColor(ImGuiCol_Text, kGold);
            ImGui::TextUnformatted("F1 Menu Theme & Controller Button Prompts");
            ImGui::PopStyleColor();

            ImGui::SetNextItemWidth(ImGui::GetContentRegionAvail().x * 0.48f);
            ImGui::Combo("##theme", &theme_idx, kThemeNames, 3);
            ImGui::SameLine();
            ImGui::SetNextItemWidth(ImGui::GetContentRegionAvail().x);
            ImGui::Combo("##prompts", &prompt_idx, kPromptNames, 5);

            ImGui::Dummy(ImVec2(0, 6.0f * ds));
            ImGui::PushStyleColor(ImGuiCol_Text, kGold);
            ImGui::TextUnformatted("Optional Components");
            ImGui::PopStyleColor();

            ImGui::Checkbox("Verify / configure upscaler SDKs (DLSS / DLSS-NR / XeSS)", &opt_sdks);
            ImGui::Checkbox("Create Desktop & Start Menu shortcuts", &opt_shortcuts);
            ImGui::Checkbox("Write CONTROLLER_GUIDE.txt (Touchpad + F1 tips)", &opt_guide);

            ImGui::Dummy(ImVec2(0, 6.0f * ds));
            ImGui::PushStyleColor(ImGuiCol_Text, kGold);
            ImGui::TextUnformatted("Emulator Save Game Importer");
            ImGui::PopStyleColor();

            float sb_w = 124.0f * ds;
            ImGui::Checkbox("Import existing save to profile/user/save", &opt_import_save);
            if (!saves.empty() && opt_import_save) {
                ImGui::SetNextItemWidth(ImGui::GetContentRegionAvail().x - sb_w - 8.0f * ds);
                if (ImGui::BeginCombo("##save_src", saves[save_idx].label.c_str())) {
                    for (int i = 0; i < (int)saves.size(); i++) {
                        bool sel = (i == save_idx);
                        if (ImGui::Selectable(saves[i].label.c_str(), sel)) save_idx = i;
                    }
                    ImGui::EndCombo();
                }
                ImGui::SameLine();
            } else {
                ImGui::TextDisabled(saves.empty() ? "No Yuzu/Eden/Ryujinx saves auto-detected." : "Save import disabled.");
                ImGui::SameLine();
            }
            if (ImGui::Button("Browse Save...", ImVec2(sb_w, 0))) {
                std::string p = browse_folder(win, "", L"Select TOTK Save Folder");
                if (!p.empty()) {
                    SaveCandidate sc;
                    sc.source = "Custom";
                    sc.path = path_from_utf8(p);
                    sc.label = "[Custom] " + utf8_from_path(sc.path.filename());
                    saves.insert(saves.begin(), std::move(sc));
                    save_idx = 0;
                    opt_import_save = true;
                }
            }
        } else if (page == PAGE_INSTALL || page == PAGE_UNINSTALL) {
            if (page == PAGE_UNINSTALL && !launched_uninstall) {
                launched_uninstall = true;
                fs::path dst = fs::exists(self_exe_path().parent_path() / "totk.exe")
                                   ? self_exe_path().parent_path()
                                   : path_from_utf8(dir_buf);
                worker = std::thread(run_uninstall_worker, &job, dst);
            }

            std::string ph, det, err;
            float p = job.progress.load();
            uint64_t bd = 0, bt = 0;
            uint32_t fd = 0, ft = 0;
            {
                std::lock_guard<std::mutex> g(job.mu);
                ph = job.phase;
                det = job.detail;
                err = job.error;
                bd = job.bytes_done;
                bt = job.bytes_total;
                fd = job.files_done;
                ft = job.files_total;
            }
            if (!shot_dir.empty()) {
                p = 0.42f;
                ph = "Decrypting & extracting Switch 1 RomFS / ExeFS...";
                det = "extract: 6842 / 16384 MB";
            }

            ImGui::SetWindowFontScale(1.30f);
            ImGui::TextUnformatted(page == PAGE_UNINSTALL ? "Uninstalling..." : "Installing Tears of the Kingdom...");
            ImGui::SetWindowFontScale(1.0f);
            ImGui::Dummy(ImVec2(0, 12.0f * ds));

            char ov[64];
            snprintf(ov, sizeof(ov), "%d%%", (int)roundf(p * 100.0f));
            ImGui::ProgressBar(p, ImVec2(ImGui::GetContentRegionAvail().x, 28.0f * ds), ov);
            ImGui::Dummy(ImVec2(0, 6.0f * ds));

            ImGui::PushStyleColor(ImGuiCol_ChildBg, ImVec4(0.08f, 0.11f, 0.14f, 0.95f));
            ImGui::BeginChild("##status_card", ImVec2(0, 130.0f * ds), ImGuiChildFlags_Borders);
            ImGui::SetCursorPos(ImVec2(14.0f * ds, 12.0f * ds));
            ImGui::BeginGroup();
            ImGui::PushStyleColor(ImGuiCol_Text, kZonaiGreen);
            ImGui::TextUnformatted(ph.c_str());
            ImGui::PopStyleColor();
            ImGui::TextDisabled("%s", det.empty() ? "Working..." : det.c_str());
            if (ft > 0) {
                ImGui::Dummy(ImVec2(0, 6.0f * ds));
                ImGui::Text("%u / %u files  (%.1f / %.1f MB)", fd, ft, (double)bd / 1048576.0, (double)bt / 1048576.0);
            }
            if (!err.empty()) {
                ImGui::PushStyleColor(ImGuiCol_Text, kErrRed);
                ImGui::TextWrapped("Error: %s", err.c_str());
                ImGui::PopStyleColor();
            }
            ImGui::EndGroup();
            ImGui::EndChild();
            ImGui::PopStyleColor();

            if (job.done.load() && job.ok.load() && shot_dir.empty()) page = PAGE_DONE;
        } else if (page == PAGE_DONE) {
            ImGui::SetWindowFontScale(1.35f);
            ImGui::PushStyleColor(ImGuiCol_Text, kZonaiGreen);
            ImGui::TextUnformatted(uninstall_mode ? "Uninstall Complete" : "Ready to Play!");
            ImGui::PopStyleColor();
            ImGui::SetWindowFontScale(1.0f);
            ImGui::Dummy(ImVec2(0, 4.0f * ds));
            ImGui::TextWrapped("Folder: %s", dir_buf);
            ImGui::Dummy(ImVec2(0, 8.0f * ds));

            draw_feature_card("Quick Controls Cheat-Sheet",
                              "F1 / Select+Start / PS4-PS5 Touchpad = Settings Menu\nL1/R1 or Q/E = Switch Tabs  |  F10 or L3+R3 = FPS Overlay  |  F11 = Fullscreen",
                              kAccentU);
            ImGui::Dummy(ImVec2(0, 4.0f * ds));
            draw_feature_card("Theme Applied",
                              theme_idx == 0 ? "Tears of the Kingdom (Custom Zonai & Triforce styling active)"
                                             : (theme_idx == 1 ? "Dark Theme active" : "Light Theme active"),
                              kGoldU);
        }

        ImGui::EndChild();

        // Bottom wizard action bar (57*ds height inside 74*ds reserved footer -> zero clipping!)
        ImGui::Separator();
        ImGui::Dummy(ImVec2(0, 4.0f * ds));
        float btn_h = 36.0f * ds;
        float btn_w = 132.0f * ds;

        if (page == PAGE_WELCOME) {
            if (ImGui::Button("Cancel", ImVec2(105.0f * ds, btn_h))) {
                SDL_Event ev{SDL_EVENT_QUIT};
                SDL_PushEvent(&ev);
            }
            ImGui::SameLine(ImGui::GetContentRegionAvail().x - btn_w * 1.15f);
            if (draw_primary_btn("Continue  >", btn_w * 1.15f, btn_h)) page = PAGE_FILES;
        } else if (page == PAGE_FILES) {
            if (ImGui::Button("<  Back", ImVec2(105.0f * ds, btn_h))) page = PAGE_WELCOME;
            ImGui::SameLine(ImGui::GetContentRegionAvail().x - btn_w * 1.15f);
            if (!files_ready && shot_dir.empty()) ImGui::BeginDisabled();
            if (draw_primary_btn("Continue  >", btn_w * 1.15f, btn_h)) page = PAGE_OPTIONS;
            if (!files_ready && shot_dir.empty()) ImGui::EndDisabled();
        } else if (page == PAGE_OPTIONS) {
            if (ImGui::Button("<  Back", ImVec2(105.0f * ds, btn_h))) page = PAGE_FILES;
            ImGui::SameLine(ImGui::GetContentRegionAvail().x - btn_w * 1.25f);
            if (!keys_valid && shot_dir.empty()) ImGui::BeginDisabled();
            if (draw_primary_btn("Install Now", btn_w * 1.25f, btn_h)) {
                page = PAGE_INSTALL;
                fs::path dst = path_from_utf8(dir_buf);
                fs::path ssrc = (!saves.empty() && opt_import_save) ? saves[save_idx].path : fs::path();
                Switch1Inputs sw1;
                sw1.base_path = path_from_utf8(base_buf);
                sw1.update_path = path_from_utf8(upd_buf);
                sw1.keys_path = path_from_utf8(keys_buf);
                sw1.firmware_path = path_from_utf8(fw_buf);
                sw1.lang = kLangCodes[std::clamp(lang_idx, 0, (int)(sizeof(kLangCodes) / sizeof(kLangCodes[0])) - 1)];
                if (worker.joinable()) worker.join();
                worker = std::thread(run_install_worker, &job, &payload, sw1, dst, theme_idx, prompt_idx, opt_sdks,
                                     opt_import_save, ssrc, opt_shortcuts, opt_guide);
            }
            if (!keys_valid && shot_dir.empty()) ImGui::EndDisabled();
        } else if (page == PAGE_INSTALL || page == PAGE_UNINSTALL) {
            if (job.done.load() && !job.ok.load()) {
                if (ImGui::Button("<  Back", ImVec2(105.0f * ds, btn_h))) {
                    job.done = false;
                    job.error.clear();
                    page = PAGE_FILES;
                }
            } else {
                ImGui::BeginDisabled();
                ImGui::Button("Working...", ImVec2(btn_w, btn_h));
                ImGui::EndDisabled();
            }
        } else if (page == PAGE_DONE) {
            if (ImGui::Button("Open Folder", ImVec2(124.0f * ds, btn_h))) {
                ShellExecuteW(nullptr, L"open", path_from_utf8(dir_buf).c_str(), nullptr, nullptr, SW_SHOWNORMAL);
            }
            ImGui::SameLine();
            if (ImGui::Button("Close", ImVec2(96.0f * ds, btn_h))) {
                SDL_Event ev{SDL_EVENT_QUIT};
                SDL_PushEvent(&ev);
            }
            fs::path launch_p = fs::exists(target_p / "TotKLauncher.exe", ec) ? (target_p / "TotKLauncher.exe")
                              : (fs::exists(target_p / "totk.exe", ec) ? (target_p / "totk.exe") : fs::path());
            if (!launch_p.empty()) {
                ImGui::SameLine(ImGui::GetContentRegionAvail().x - btn_w * 1.15f);
                if (draw_primary_btn("Launch Game", btn_w * 1.15f, btn_h)) {
                    ShellExecuteW(nullptr, L"open", launch_p.c_str(), nullptr, target_p.c_str(), SW_SHOWNORMAL);
                    SDL_Event ev{SDL_EVENT_QUIT};
                    SDL_PushEvent(&ev);
                }
            }
        }

        ImGui::EndChild();
        ImGui::End();

        ImGui::Render();
        SDL_SetRenderDrawColor(ren, 16, 21, 27, 255);
        SDL_RenderClear(ren);
        ImGui_ImplSDLRenderer3_RenderDrawData(ImGui::GetDrawData(), ren);
        SDL_RenderPresent(ren);
    };

    // Headless automated visual check (`--shot` / `TOTK_SETUP_SHOT`)
    if (!shot_dir.empty()) {
        auto snap = [&](Page p, float t, const char* name) {
            page = p;
            render_frame(t);
            render_frame(t);
            save_shot(ren, shot_dir / name);
        };
        snap(PAGE_WELCOME, 0.5f, "01_welcome_t0.png");
        snap(PAGE_WELCOME, 2.8f, "01_welcome_t1.png");
        snap(PAGE_FILES, 1.0f, "02_files.png");
        snap(PAGE_OPTIONS, 1.8f, "03_options.png");
        snap(PAGE_INSTALL, 2.4f, "04_installing.png");
        snap(PAGE_DONE, 3.2f, "05_done.png");
    } else {
        uint64_t t0 = SDL_GetTicks();
        bool running = true;
        while (running) {
            SDL_Event ev;
            while (SDL_PollEvent(&ev)) {
                ImGui_ImplSDL3_ProcessEvent(&ev);
                if (ev.type == SDL_EVENT_QUIT) running = false;
            }
            float anim_t = (float)(SDL_GetTicks() - t0) * 0.001f;
            render_frame(anim_t);
        }
    }

    if (worker.joinable()) worker.join();
    ImGui_ImplSDLRenderer3_Shutdown();
    ImGui_ImplSDL3_Shutdown();
    ImGui::DestroyContext();
    SDL_DestroyRenderer(ren);
    SDL_DestroyWindow(win);
    SDL_Quit();
    CoUninitialize();
    return 0;
}
