import platform
import getpass
import os

class UserInfo:
    def __init__(self):
        self.detailed_user_data = self.get_user_data()
    
    def get_user_data(self):
        system = platform.system().lower()
        
        base_info = {
            "Username": getpass.getuser(),
            "Privilege level": self.get_privilege_level(system),
            "Home directory": os.path.expanduser('~')
        }
        
        if system == 'windows':
            base_info.update(self.get_windows_specific_data())
        elif system == 'linux':
            base_info.update(self.get_linux_specific_data())
            
        return {"User": base_info}
    
    def get_privilege_level(self, system):
        if system == 'windows':
            
            try:
                
                system_paths = [
                    r'C:\Windows\System32\config\system',
                    r'C:\Windows\System32\drivers\etc\hosts'
                ]
                
                for path in system_paths:
                    try:
                        with open(path, 'r'):
                            return "Probable Admin"  # Accès réussi = probable admin
                    except:
                        continue
                return "User"
            except:
                return "Unknown"
        else:
            # Linux - vérification sans privilèges
            try:
                # Vérifier si on peut écrire dans des répertoires système
                system_dirs = ['/etc', '/usr/local/bin', '/var/log']
                
                for directory in system_dirs:
                    if os.path.exists(directory):
                        if os.access(directory, os.W_OK):
                            return "Probable root"
                
                # Vérifier les groupes avec une commande simple
                import subprocess
                result = subprocess.run(
                    ['id'],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if result.returncode == 0:
                    if "uid=0" in result.stdout:
                        return "root"
                    elif "sudo" in result.stdout or "wheel" in result.stdout:
                        return "Sudo User"
                
                return "User"
            except:
                return "User"
                
    def get_windows_specific_data(self):
        data = {}
        try:
           
            data["uac_level"] = self.get_uac_indirect()
            
           
            session_type = "local"
            if os.environ.get('SESSIONNAME', '').startswith('RDP'):
                session_type = "rdp"
            elif 'SSH_CONNECTION' in os.environ:
                session_type = "ssh"
            data["session_type"] = session_type
            
            
            data["domain"] = os.environ.get('USERDOMAIN', 'WORKGROUP')
            data["domain_joined"] = self.is_windows_domain_joined_indirect()
            
            
            data["integrity_level"] = self.get_windows_integrity_indirect()
        
            
            data["has_debug_privilege"] = self.has_debug_privilege_indirect()
            
        except Exception as e:
            data["error"] = str(e)
        return data
    
    def get_linux_specific_data(self):
        data = {}
        try:
            import pwd
            import grp
            
            # Informations utilisateur basiques - sans privilèges
            user_info = pwd.getpwnam(getpass.getuser())
            data["uid"] = user_info.pw_uid
            data["gid"] = user_info.pw_gid
            data["shell"] = user_info.pw_shell
            
           
            groups = []
            try:
                import subprocess
                result = subprocess.run(
                    ['groups'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    groups = result.stdout.strip().split()
            except:
                # Fallback basique
                try:
                    user_groups = grp.getgrgid(user_info.pw_gid)
                    groups = [user_groups.gr_name]
                except:
                    groups = ["groups_info_unavailable"]
            data["groups"] = groups
            
            # Capacités - détection indirecte
            data["capabilities"] = self.get_linux_capabilities_indirect()
            data["selinux_enabled"] = self.is_selinux_enabled_indirect()
            data["apparmor_enabled"] = self.is_apparmor_enabled_indirect()
            data["is_container"] = self.is_linux_container()
            
        except Exception as e:
            data["error"] = str(e)
        return data
    
    def get_uac_indirect(self):
        
        try:
        
            protected_paths = [
                r'C:\Windows\System32\drivers\etc\hosts',
                r'C:\Program Files',
                r'C:\Windows\System32\config'
            ]
            
            accessible_count = 0
            for path in protected_paths:
                try:
                    if os.path.exists(path):
                        
                        if os.path.isdir(path):
                            os.listdir(path)
                        else:
                            with open(path, 'r'):
                                pass
                        accessible_count += 1
                except (PermissionError, OSError):
                    continue
            
            if accessible_count >= 2:
                return "UAC likely disabled or admin"
            elif accessible_count == 1:
                return "UAC medium"
            else:
                return "UAC likely enabled"
        except:
            return "Unknown"
    
    def is_windows_domain_joined_indirect(self):
        """Détection de domaine sans systeminfo"""
        try:
            
            domain = os.environ.get('USERDOMAIN', '')
            logonserver = os.environ.get('LOGONSERVER', '')
            userdnsdomain = os.environ.get('USERDNSDOMAIN', '')
            
            
            domain_indicators = [
                domain and domain.upper() != "WORKGROUP",
                logonserver and logonserver.startswith('\\\\'),
                userdnsdomain and '.' in userdnsdomain
            ]
            
            return sum(domain_indicators) >= 2
        except:
            return False
        
    def get_windows_integrity_indirect(self):
        try:

            high_integrity_paths = [
                r'C:\Windows\System32\config\SAM',
                r'C:\Windows\System32\drivers\etc\hosts'
            ]
            
            medium_integrity_paths = [
                r'C:\Program Files',
                r'C:\Windows\System32'
            ]
            
            low_integrity_paths = [
                r'C:\Users\Public',
                os.path.expanduser('~\\AppData\\Local\\Temp')
            ]
            
        
            high_access = any(self.test_file_access(path) for path in high_integrity_paths)
            medium_access = any(self.test_file_access(path) for path in medium_integrity_paths)
            
            if high_access:
                return "High"
            elif medium_access:
                return "Medium"
            else:
                return "Low"
        except:
            return "Unknown"
    
    def test_file_access(self, path):
    
        try:
            if os.path.exists(path):
                if os.path.isdir(path):
                    os.listdir(path)
                    return True
                else:
                    with open(path, 'r'):
                        return True
        except:
            return False
        return False
    
    def has_debug_privilege_indirect(self):
        
        try:
            
            import subprocess
            result = subprocess.run(
                ['tasklist', '/fi', 'imagename eq csrss.exe'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            return "csrss.exe" in result.stdout
        except:
            return False
    
    def get_linux_capabilities_indirect(self):
        """Détection indirecte des capacités Linux"""
        try:
            capable_binaries = []
            
            common_bins = [
                '/bin/ping', '/usr/bin/passwd', '/usr/sbin/tcpdump',
                '/usr/bin/mtr', '/usr/bin/traceroute'
            ]
            
            for bin_path in common_bins:
                if os.path.exists(bin_path):
                    try:
                        stat_info = os.stat(bin_path)
                        if stat_info.st_mode & 0o4000:  # SUID bit
                            capable_binaries.append(f"{bin_path}: SUID")
                        elif stat_info.st_mode & 0o2000:  # SGID bit
                            capable_binaries.append(f"{bin_path}: SGID")
                    except:
                        pass
            
            return capable_binaries
        except:
            return []
    
    def is_selinux_enabled_indirect(self):
        
        try:
            
            selinux_paths = [
                '/sys/fs/selinux',
                '/etc/selinux/config',
                '/usr/sbin/sestatus'
            ]
            
            for path in selinux_paths:
                if os.path.exists(path):
                    return True
            
            
            import subprocess
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=3
            )
            if 'selinux' in result.stdout.lower():
                return True
                
            return False
        except:
            return False
        
    def is_apparmor_enabled_indirect(self):
        
        try:
    
            apparmor_paths = [
                '/sys/kernel/security/apparmor',
                '/etc/apparmor',
                '/etc/apparmor.d'
            ]
            
            for path in apparmor_paths:
                if os.path.exists(path):
                    return True
            
            import subprocess
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=3
            )
            if 'apparmor' in result.stdout.lower():
                return True
                
            return False
        except:
            return False
    
    def is_linux_container(self):
        
        checks = [
            '/.dockerenv',
            '/run/.containerenv',
            '/proc/1/cgroup',
            '/proc/1/environ'
        ]
        
        for check in checks:
            if os.path.exists(check):
                if check == '/proc/1/cgroup':
                    try:
                        with open('/proc/1/cgroup', 'r') as f:
                            content = f.read()
                            if 'docker' in content or 'kubepods' in content or 'container' in content:
                                return True
                    except:
                        pass
                elif check == '/proc/1/environ':
                    try:
                        with open('/proc/1/environ', 'r') as f:
                            content = f.read()
                            if 'container=' in content or 'DOCKER' in content:
                                return True
                    except:
                        pass
                else:
                    return True
        
        
        try:
            if os.path.exists('/proc/1/sched'):
                with open('/proc/1/sched', 'r') as f:
                    content = f.read()
                    if 'docker' in content.lower() or 'container' in content.lower():
                        return True
        except:
            pass
            
        return False
    
    
if __name__ == "__main__":
    si = UserInfo()
    print(si.detailed_user_data)