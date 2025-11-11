import platform
import uuid
import os


class ClientIdentityManager:
    def __init__(self):
        self.platform = platform.system()
    

    def _get_hardware_based_client_id(self):
        try:
            import subprocess

            result = subprocess.check_output('wmic csproduct get uuid', shell=True)
            lines = result.decode().split('\n')
            if len(lines) >= 2:
                hardware_id = lines[1].strip()

                if hardware_id and hardware_id != "":
                    return str(uuid.uuid5(uuid.NAMESPACE_DNS, hardware_id))
        except:
            pass
            
        return None


    def _get_linux_persistent_id(self):
        client_id_file = os.path.expanduser("~/.config/system-update-id")

        try:
            os.makedirs(os.path.dirname(client_id_file), exist_ok=True)
            
            if os.path.exists(client_id_file):
                with open(client_id_file, "r") as f:
                    client_id  = f.read().strip()
                    uuid.UUID(client_id) #validation
                    return client_id
        
        except:
            pass
        
        
        new_client_id = str(uuid.uuid4())
        try:
            with open(client_id_file, 'w') as f:
                f.write(new_client_id)
            
            os.chmod(client_id_file, 0o600)
        
        except:
            pass
        
        return new_client_id


    def _get_persistent_client_id(self):
        if self.platform == "Windows":
            return self._get_hardware_based_client_id()
        elif self.platform == "Linux":
            return self._get_linux_persistent_id()
        else:
            return str(uuid.uuid4()) #not persistent