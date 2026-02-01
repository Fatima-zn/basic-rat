import datetime
from Os_info import OsInfo
from Architecture_info import ArchitectureInfo
from User_info import UserInfo
from Privileges_info import PrivilegesInfo
from Network_info import NetworkInfo
import json
import platform
import psutil
import socket

class SystemInfo(OsInfo, ArchitectureInfo, UserInfo, PrivilegesInfo, NetworkInfo):
    def __init__(self):
        # Initialiser les classes parentes
        OsInfo.__init__(self)
        ArchitectureInfo.__init__(self)
        UserInfo.__init__(self)
        PrivilegesInfo.__init__(self)
        NetworkInfo.__init__(self)
        
        # Rassembler toutes les infos
        self.all_system_info = self.get_all_system_info()
        
    def get_all_system_info(self):
        """Return system info in structured format for database"""
        cpu_info = self.get_architecture.get('CPU', {})
        memory_info = self.get_architecture.get('Memory', {})
        
        return {
            # Platform information (for database columns)
            "platform": {
                "system": platform.system(),
                "version": platform.version(),
                "release": platform.release(),
                "machine": platform.machine(),
                "hostname": socket.gethostname()
            },
            # Hardware information (for database columns)
            "hardware": {
                "cpu_count": psutil.cpu_count(logical=False) or 0,
                "cpu_model": cpu_info.get('Model', 'Unknown'),
                "total_ram": psutil.virtual_memory().total if hasattr(psutil, 'virtual_memory') else 0
            },
            # User information (for database columns)
            "user": {
                "username": self.detailed_user_data.get('username', 'Unknown'),
                "computer_name": self.detailed_user_data.get('computer_name', 'Unknown')
            },
            # Privileges information (for database columns)
            "privileges": {
                "is_admin": self.get_privileges.get('is_admin', False)
            },
            # Additional detailed info (stored as JSONB)
            "details": {
                "operating_system": self.os_info, 
                "architecture": self.get_architecture, 
                "user_details": self.detailed_user_data,  
                "privileges_details": self.get_privileges, 
                "network": self.network_info,  
                "timestamp": datetime.datetime.now().isoformat()
            }
        }
        
    def get_Os_informations(self):
        return {
            "operating_system": self.os_info
        }


if __name__ == "__main__":
    si = SystemInfo()
    
    print(json.dumps(si.all_system_info, indent=2))