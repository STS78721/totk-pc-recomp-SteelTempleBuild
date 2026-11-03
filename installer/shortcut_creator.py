"""Desktop shortcut creator for TOTK PC Recompiled."""

import os
import subprocess

def create_desktop_shortcut(game_dir: str, shortcut_name: str = "The Legend of Zelda - Tears of the Kingdom") -> bool:
    """Creates a Windows desktop shortcut pointing to totk.exe in game_dir."""
    try:
        desktop_dir = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
        if not os.path.exists(desktop_dir):
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")

        shortcut_path = os.path.join(desktop_dir, f"{shortcut_name}.lnk")
        exe_path = os.path.join(game_dir, "totk.exe")
        icon_path = os.path.join(game_dir, "totk.exe")

        # Use PowerShell to create the shell link cleanly
        ps_script = f"""
        $ws = New-Object -ComObject WScript.Shell
        $s = $ws.CreateShortcut('{shortcut_path}')
        $s.TargetPath = '{exe_path}'
        $s.WorkingDirectory = '{game_dir}'
        $s.IconLocation = '{icon_path},0'
        $s.Description = 'Play The Legend of Zelda: Tears of the Kingdom (PC Recompiled)'
        $s.Save()
        """

        res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                             capture_output=True, text=True, timeout=10)
        return res.returncode == 0 and os.path.exists(shortcut_path)
    except Exception as e:
        print(f"Error creating shortcut: {e}")
        return False
