import datetime
from Os_info import OsInfo
from Architecture_info import ArchitectureInfo
from User_info import UserInfo
from Privileges_info import PrivilegesInfo
from Network_info import NetworkInfo
import json

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
        return {
            "operating_system": self.os_info, 
            "architecture": self.get_architecture, 
            "user": self.detailed_user_data,  
            "privileges": self.get_privileges, 
            "network": self.network_info,  
            "timestamp": datetime.datetime.now().isoformat()
        }
        
    def get_Os_informations(self):
        return {
            "operating_system": self.os_info
        }


if __name__ == "__main__":
    si = SystemInfo()
    
    print(json.dumps(si.all_system_info, indent=2))