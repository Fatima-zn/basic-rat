import platform
import subprocess
import os

class PrivilegesInfo():
    def __init__(self):
        self.get_privileges = self.get_privileges_info()
        
    def get_privileges_info(self):
        system = platform.system().lower()
        
        if system == 'windows':
            return self.get_windows_privileges()
        elif system == 'linux':
            return self.get_linux_privileges()
        else:
            return self.get_genenric_privileges()
        
    def get_windows_privileges(self):
        try:
            import winreg
            import subprocess
            
            privileges ={
                "Current privileges": self.get_windows_token_privilges(),
                "Escalation methods": self.find_windows_escalation_methods(),
                "System weaknesses": self.find_windows_weaknesses(),
                "Integrity level": self.get_windows_integrity_level()
            }
            return {"Privileges": privileges}
        except Exception as e:
            return {"Privileges": {"Error": str(e)}}
    
    def get_windows_token_privilges(self):
        privileges =[]
        try:
            result = subprocess.run(['whoami', '/priv'], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Enabled' in line and line.startswith('Se'):
                        privilege = line.split()[0].strip()
                        privileges.append(privilege)
        except:
            pass
        return privileges if privileges else ["SeChangeNotifyPrivilge"]
    
    def find_windows_escalation_methods(self):
        methods = []
        if self.is_uac_bypass_possible():
            methods.append("uac_bypass")
        if self.has_vulnerable_services():
            methods.append("service_abuse")
        if self.has_writable_scheduled_tasks():
            methods.append("sheduled_task_hijack")
        
        return methods
    
    def find_windows_weaknesses(self):
        weaknesses = []
    
        if self.check_always_install_elevated():
            weaknesses.append("always_install_elevated")
        if self.has_unquoted_service_paths():
            weaknesses.append("unquoted_service_paths")
        if self.check_sticky_keys():
            weaknesses.append("sticky_keys_backdoor")
    
        return weaknesses
    
    def get_windows_integrity_level(self):
        try:
            import ctypes
            if ctypes.windll.shell32.IsUserAnAdmin():
                return "Hight"
            else:
                return "Medium"
        except:
            return "Uknown"
        
    def is_uac_bypass_possible(self):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System") as key:
                uac_value = winreg.QueryValueEx(key, "ConsentPromptBehaviorAdmin")[0]
                return uac_value in [0, 2]
        except:
            return False
        
    def has_vulnerable_services(self):
        vulnerable_services =[]
        try:
            result = subprocess.run(['sc', 'query'], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                current_service = ""
                for line in lines:
                    line = line.strip()
                    if line.startswith('SERVICE_NAME:'):
                        current_service = line.split(':')[1].strip()
                    elif current_service and 'WIN32_OWN_PROCESS' in line :
                        perm = subprocess.run(['sc', 'qc'], capture_output=True, text=True, timeout=5)
                        if perm.returncode == 0:
                            service_config = perm.stdout
                            if any(indicator in service_config for indicator in ['INTERACTIVE', 'LocalSystem', 'NULL SESSION']):
                                vulnerable_services.append(current_service)
            return len(vulnerable_services) >0
        except Exception as e:
            return False
    
    def has_writable_scheduled_tasks(self):
        try:
            task_paths = [r'C:\Windows\System32\Tasks', 
                          r'C:\Windows\Tasks', 
                          os.path.join(os.environ.get('ProgramData', ''), 'Microsoft', 'Windows', 'TaskScheduler')
                    ]
            for Tpath in task_paths:
                if os.path.exists(Tpath):
                    try:
                        test = os.path.join(Tpath, 'test.map')
                        with open(test, 'w') as f:
                            f.write('test')
                        os.remove(test)
                    except:
                        continue
            result = subprocess.run(['schtasks', '/query', '/fo', 'LIST'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                tasks = result.stdout.count('TaskName:')
                return tasks > 0
            return False
        except Exception as e:
            return False
    
    def check_always_install_elevated(self):
        try: 
            import winreg 
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Installer")as key:
                lm_value = winreg.QueryValueEx(key, "AlwaysInstallElevated")[0]
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Policies\Microsoft\Windows\Installer") as key:
                cu_value = winreg.QueryValueEx(key, "AlwaysInstallElevated")[0]
                
            return lm_value == 1 and cu_value == 1
        except : 
            return False
        
    def check_sticky_keys(self):
        try:
            result = subprocess.run(['reg', 'query', 
            'HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Accessibility', 
            '/v', 'Configuration'], capture_output=True, text=True)
            
            return result.returncode == 0
        except:
            return False
        
    def has_unquoted_service_paths(self):
        try:
            import winreg 
            unquoted_services = []
            
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services") as services_key:
                i =0
                while True:
                    try:
                        service_name = winreg.EnumKey(services_key, i)
                        i += 1
                        try:
                             with winreg.OpenKey(services_key, service_name) as service_key:
                                try:
                                    image_path = winreg.QueryValueEx(service_key, "ImagePath")[0]
                                    
                                    if (isinstance(image_path, str) and ' ' in image_path and not image_path.startswith('"') and'.exe' in image_path.lower()):
                                        if not image_path.startswith('\\SystemRoot') and 'system32\\drivers' not in image_path.lower():
                                            unquoted_services.append(service_name)
                                except FileNotFoundError:
                                    pass
                        except:
                            continue
                    except OSError:
                        break
                return len(unquoted_services) > 0
        except Exception as e :
            return False
        
    # maintanant je passe au cotee linux 
    def get_linux_privileges(self):
        try:
            import grp 
            privilges = {
                "Current privileges": self.get_linux_capabilities(),
                "Escalation methods": self.find_linux_escalation_methods(),
                "System weaknesses": self.find_linux_weaknesses(),
                "Integrity level": "root" if os.geteuid() ==0 else "user"
            }
            return {"Privileges": privilges}
        except Exception as e :
            return { " Privileges": str(e)}
            
    
    def get_linux_privileges_info(self):
        """Retourne toutes les informations de privilèges SANS mot de passe"""
        return {
            "Current privileges": self.get_linux_capabilities(),
            "Escalation methods": self.find_linux_escalation_methods(),
            "System weaknesses": self.find_linux_weaknesses(),
            "Integrity level": "root" if os.geteuid() == 0 else "user"
        }
    
    def get_linux_capabilities(self):
        """Récupère les capabilities SANS commandes externes"""
        try:
            # Lecture directe depuis /proc sans subprocess
            with open('/proc/self/status', 'r') as f:
                for line in f:
                    if line.startswith('Cap'):
                        return line.strip()
            return "No capabilities"
        except:
            return "Unknown capabilities"
    
    def find_linux_escalation_methods(self):
        """Trouve les méthodes d'escalade SANS sudo ni mot de passe"""
        methods = []
        
        # 1. Vérifier si déjà root
        if os.geteuid() == 0:
            methods.append("already_root")
            return methods
        
        # 2. Vérifier les SUID dans le HOME directory seulement
        try:
            home_dir = os.path.expanduser("~")
            for root, dirs, files in os.walk(home_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        if os.stat(file_path).st_mode & 0o4000:  # SUID bit
                            methods.append("suid_in_home")
                            break
                    except:
                        continue
                if "suid_in_home" in methods:
                    break
        except:
            pass
        
        # 3. Vérifier l'appartenance aux groupes (SANS mot de passe)
        try:
            groups = os.getgroups()
            group_names = []
            try:
                import grp
                for gid in groups:
                    try:
                        group_names.append(grp.getgrgid(gid).gr_name)
                    except:
                        pass
            except:
                pass
            
            privileged_groups = ["docker", "lxd", "sudo", "wheel", "adm"]
            for group in privileged_groups:
                if group in group_names:
                    methods.append(f"privileged_group_{group}")
        except:
            pass
        
        # 4. Vérifier les variables d'environnement dangereuses
        dangerous_env_vars = ["LD_PRELOAD", "LD_LIBRARY_PATH", "PYTHONPATH"]
        for env_var in dangerous_env_vars:
            if env_var in os.environ:
                methods.append(f"dangerous_env_{env_var}")
        
        # 5. Vérifier les fichiers avec capabilities (méthode manuelle)
        try:
            user_paths = os.environ.get('PATH', '').split(':')
            for path_dir in user_paths:
                if os.path.exists(path_dir):
                    for binary in os.listdir(path_dir):
                        binary_path = os.path.join(path_dir, binary)
                        if os.path.isfile(binary_path):
                            try:
                                # Vérifier si le fichier a des capabilities via getcap
                                # Mais sans l'exécuter pour éviter le mot de passe
                                if os.access(binary_path, os.X_OK):
                                    # On suppose que les binaires courants avec capabilities sont dangereux
                                    dangerous_binaries = ["ping", "mount", "umount", "su"]
                                    if binary in dangerous_binaries:
                                        methods.append(f"potential_capability_{binary}")
                            except:
                                pass
        except:
            pass
        
        return methods
    
    def find_linux_weaknesses(self):
        """Trouve les faiblesses SANS sudo ni mot de passe"""
        weaknesses = []
        
        try:
            # A) Fichiers personnels modifiables
            user_configs = [
                os.path.expanduser("~/.bashrc"),
                os.path.expanduser("~/.bash_profile"),
                os.path.expanduser("~/.profile"),
                os.path.expanduser("~/.zshrc"),
                os.path.expanduser("~/.ssh/authorized_keys"),
                os.path.expanduser("~/.ssh/config"),
            ]
            
            for config in user_configs:
                if os.path.exists(config):
                    if os.access(config, os.W_OK):
                        weaknesses.append(f"writable_{os.path.basename(config)}")
            
            # B) Répertoires personnels modifiables
            user_dirs = [
                os.path.expanduser("~/.config/systemd/user"),
                os.path.expanduser("~/.local/bin"),
                os.path.expanduser("~/bin"),
            ]
            
            for directory in user_dirs:
                if os.path.exists(directory):
                    if os.access(directory, os.W_OK):
                        weaknesses.append(f"writable_{os.path.basename(directory)}")
            
            # C) Variables d'environnement dangereuses
            dangerous_env = ["LD_PRELOAD", "LD_LIBRARY_PATH", "PYTHONPATH", "PERLLIB", "RUBYLIB"]
            for env_var in dangerous_env:
                if env_var in os.environ:
                    weaknesses.append(f"dangerous_env_{env_var}")
            
            # D) Vérifier l'accès en écriture à /tmp
            try:
                test_file = "/tmp/test_no_password_123"
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                weaknesses.append("writable_tmp")
            except:
                pass
            
            # E) Vérifier les scripts exécutables par tous dans le home
            try:
                home_dir = os.path.expanduser("~")
                for root, dirs, files in os.walk(home_dir):
                    for file in files:
                        if file.endswith('.sh') or file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            try:
                                if os.stat(file_path).st_mode & 0o001:  # Exécutable par others
                                    weaknesses.append("world_executable_scripts")
                                    break
                            except:
                                continue
                    if "world_executable_scripts" in weaknesses:
                        break
            except:
                pass
            
            # F) Vérifier les clés SSH avec permissions faibles
            try:
                ssh_dir = os.path.expanduser("~/.ssh")
                if os.path.exists(ssh_dir):
                    for file in os.listdir(ssh_dir):
                        if file.startswith('id_'):
                            file_path = os.path.join(ssh_dir, file)
                            try:
                                if os.stat(file_path).st_mode & 0o004:  # Lisible par others
                                    weaknesses.append("world_readable_ssh_key")
                                    break
                            except:
                                continue
            except:
                pass
            
            # G) Vérifier l'appartenance au groupe docker (SANS mot de passe)
            try:
                groups = os.getgroups()
                group_names = []
                try:
                    import grp
                    for gid in groups:
                        try:
                            group_names.append(grp.getgrgid(gid).gr_name)
                        except:
                            pass
                except:
                    pass
                
                if "docker" in group_names:
                    weaknesses.append("docker_group_member")
            except:
                pass
            
            # H) Vérifier si des services systemd utilisateur existent
            try:
                user_systemd = os.path.expanduser("~/.config/systemd/user")
                if os.path.exists(user_systemd):
                    weaknesses.append("user_systemd_services")
            except:
                pass
            
            # I) Vérifier le crontab utilisateur
            try:
                # Vérifier si le fichier crontab existe sans l'exécuter
                from crontab import CronTab  # Si la librairie est disponible
                cron = CronTab(user=True)
                if len(list(cron)) > 0:
                    weaknesses.append("user_crontab_exists")
            except:
                # Fallback: vérifier le fichier directement
                cron_files = [
                    f"/var/spool/cron/crontabs/{os.getlogin()}",
                    os.path.expanduser("~/.crontab")
                ]
                for cron_file in cron_files:
                    if os.path.exists(cron_file):
                        weaknesses.append("user_crontab_exists")
                        break
            
            return weaknesses
            
        except Exception as e:
            return [f"scan_error: {str(e)}"]
    

        
if __name__ == "__main__":
    si = PrivilegesInfo()
    print(si.get_privileges_info())  
                                    