import platform
import subprocess
import os 
import datetime

class OsInfo():
    def __init__(self):
        self.os_info = self.detect_os()
        
    # cette fnct pour detecter quelle OS on a 
    def detect_os(self):
        system = platform.system().lower() 
        
        if system == 'windows':
            return self.get_windows_os_info()
        elif system == 'linux':
            return self.get_linux_os_info()
        elif system == 'darwin':
            return {"System": "macOS", "Name": "macOS", "Version": "unknown"}
        else:
            return {"System": "unknown", "Name": "unknown", "Version": "unknown"}
        
    def get_windows_os_info(self):
        import winreg
        from datetime import datetime
        
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
                product_name = winreg.QueryValueEx(key, "ProductName")[0]
                build_nb = winreg.QueryValueEx(key, "CurrentBuildNumber")[0]
                display_version = self.get_reg_value(key, "DisplayVersion", "")
                edition = self.get_reg_value(key, "EditionID", "")
                version_codename = self.get_reg_value(key, "ReleaseId", display_version)
                registered_owner = self.get_reg_value(key, "RegisteredOwner", "")
                
                install_date = ""
                install_timestamp = self.get_reg_value(key, "InstallDate", 0)
                
                if install_timestamp:
                    install_date = datetime.fromtimestamp(install_timestamp).strftime('%Y-%m-%d')
                
                product_type = self.get_reg_value(key, "ProductType", "Client")
                system_type = "Server" if product_type == "Server" else "Client"
                
                kernel_version =platform.version()
                activation_status =self.get_windows_activation_status()
                last_update = self.get_windows_last_update()
        except Exception as e:
            return self._get_generic_os_info()
        
        full_name = product_name
        if edition and edition not in full_name:
            full_name += f" {edition}"
        
        return {
            "System": "Windows",
            "Name": full_name,
            "Version": build_nb,
            "Display Version": display_version,
            "Edition": edition,
            "Type": system_type,
            "Build": build_nb,
            "Version Codename": version_codename,
            "Install date": install_date,
            "Owner": registered_owner,
            "Kernel": kernel_version,
            "Activation": activation_status,
            "Last Update": last_update
        }
        
    def get_windows_activation_status(self):
        try:
            result = subprocess.run(['cscript', '//Nologo', r'C:\Windows\System32\slmgr.vbs', '/dli'],
            capture_output=True, text=True, timeout=10)
            if "Licensed" in result.stdout or "Activé" in result.stdout:
                return "Activated"
            elif "License Status: Licensed" in result.stdout:
                return "Activated"
            else:
                return "Not Activated"
        except:
            try : 
                import winreg
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
                    product_status = winreg.QueryValueEx(key, "ProductStatus")[0]
                    return "Activated" if product_status == 1 else "Not Activated"
            except:
                return "Unknown"
    
    def get_windows_last_update(self):
        try:
            import re
            result = subprocess.run(
            ['powershell', 
             'Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 1 | Format-Table -HideTableHeaders'],
            capture_output=True, text=True, timeout=15
            )
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if re.match(r'\d{1,2}/\d{1,2}/\d{4}', line.strip()):
                        return line.strip()
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\Results\Install") as key:
                last_update = winreg.QueryValueEx(key, "LastSuccessTime")[0]
                if last_update:
                    return last_update.split('T')[0] 
        except:
            pass 
        
        return "Unknown"
    
    #info d'OS linux
    def get_linux_os_info(self):
        try:
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    lines = f.readlines()
                
                os_info = {}
                for line in lines:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        os_info[key] = value.strip('"')
                
                install_date = ""
                try:
                    install_timestamp = os.path.getctime('/etc/hostname')
                    install_date = datetime.datetime.fromtimestamp(install_timestamp).strftime('%Y-%m-%d')
                except:
                    pass
                
                return {
                    "System": os_info.get("NAME", "Linux"),
                    "Name": os_info.get("PRETTY_NAME", "Unknown Linux"),
                    "Version": os_info.get("VERSION_ID", "unknown"),
                    "Display Version": os_info.get("VERSION", ""),
                    "Edition": os_info.get("VARIANT", ""),
                    "Type": os_info.get("TYPE", "Desktop"),
                    "Build": os_info.get("BUILD_ID", platform.release()),
                    "Version Codename": os_info.get("VERSION_CODENAME", ""),
                    "Install date": install_date
                }
            else:
                return self.get_generic_os_info()
                
        except Exception as e:
            return self.get_generic_os_info()

    # methode qui aide a avoir les vals 
    def get_reg_value(self, key, value_name, default):
        import winreg
        try:
            return winreg.QueryValueEx(key, value_name)[0]
        except FileNotFoundError:
            return default

    # meth generique si la recuperation ne s'affectue pas 
    def get_generic_os_info(self):
        return {
            "System": platform.system(),
            "Name": platform.system(),
            "Version": platform.release(),
            "Display Version": "",
            "Edition": "",
            "Type": "Desktop",
            "Build": platform.release(),
            "Version Codename": "",
            "Install date": "",
            "Owner": ""
        }
        

if __name__ == "__main__":
    si = OsInfo()
    print(si.os_info)   