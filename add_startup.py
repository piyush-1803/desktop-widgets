import winreg
import sys

exe = sys.executable
script = "C:\\DesktopWidgets\\widget_host.py"
cmd = f'"{exe}" "{script}"'

key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                     r"Software\Microsoft\Windows\CurrentVersion\Run",
                     0, winreg.KEY_SET_VALUE)
winreg.SetValueEx(key, "DesktopWidgets", 0, winreg.REG_SZ, cmd)
winreg.CloseKey(key)
print("Startup entry added successfully!")
print("Command:", cmd)
