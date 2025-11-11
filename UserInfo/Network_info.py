import socket
import subprocess
import os
import platform
import json

class NetworkInfo:
    def __init__(self):
        self.network_info = self.get_network_info()  
        
    def get_network_info(self):
        system = platform.system().lower()
        
        if system == 'windows':
            return self.get_windows_network_info()
        elif system == 'linux':
            return self.get_linux_network_info()
        else:
            return {"error": f"Unsupported platform: {system}"}
        
    def get_linux_network_info(self):
        try:
            return {
                "network_config": self.get_linux_network_config(),
                "active_connections": self.get_linux_active_connections(),
                "listening_ports": self.get_linux_listening_ports(),
                "sensitive_data": self.get_linux_sensitive_data(),
                "network_status": self.get_linux_network_status(),
                "mac_address": self.get_mac_addresses()
            }
        except Exception as e:
            return {"error": f"Linux network info error: {str(e)}"}
    
    def get_linux_network_config(self):
        try:
            config = {}
            config["hostname"] = socket.gethostname()
            
            ip_addresses = []
            
            
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                if ip not in ip_addresses:
                    ip_addresses.append(ip)
                s.close()
            except Exception as e:
                print(f"IP method 1 failed: {e}")
            
            
            try:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                if local_ip not in ip_addresses and not local_ip.startswith("127."):
                    ip_addresses.append(local_ip)
            except Exception as e:
                print(f"IP method 2 failed: {e}")
            
           
            try:
                result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    ips = result.stdout.strip().split()
                    for ip in ips:
                        if ip not in ip_addresses and not ip.startswith("127."):
                            ip_addresses.append(ip)
            except Exception as e:
                print(f"IP method 3 failed: {e}")
            
            config["ip_addresses"] = ip_addresses if ip_addresses else ["unknown"]
            
            
            try:
                result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=5)
                for line in result.stdout.split('\n'):
                    if 'default via' in line:
                        gateway = line.split()[2]
                        config["gateway"] = gateway
                        break
                else:
                    config["gateway"] = "unknown"
            except Exception as e:
                print(f"Gateway failed: {e}")
                config["gateway"] = "unknown"
            
            
            try:
                dns_servers = []
                if os.path.exists('/etc/resolv.conf'):
                    with open('/etc/resolv.conf', 'r') as f:
                        for line in f:
                            if line.startswith('nameserver'):
                                dns_ip = line.split()[1]
                                if dns_ip not in dns_servers:
                                    dns_servers.append(dns_ip)
                config["dns_servers"] = dns_servers if dns_servers else ["unknown"]
            except Exception as e:
                print(f"DNS failed: {e}")
                config["dns_servers"] = ["unknown"]
            
            return config
            
        except Exception as e:
            print(f"Network config error: {e}")
            return {
                "hostname": "unknown",
                "ip_addresses": ["unknown"],
                "gateway": "unknown",
                "dns_servers": ["unknown"]
            }
    
    def get_linux_active_connections(self):
        connections = []
        try:
            
            result = subprocess.run(['netstat', '-tun'], capture_output=True, text=True, timeout=10)
            for line in result.stdout.split('\n'):
                if 'ESTABLISHED' in line and ('tcp' in line or 'udp' in line):
                    parts = line.split()
                    if len(parts) >= 5:
                        connections.append({
                            "protocol": "tcp" if 'tcp' in line else "udp",
                            "local": parts[3],
                            "remote": parts[4],
                            "state": "ESTABLISHED"
                        })
        except Exception as e:
            print(f"Active connections method 1 failed: {e}")
        
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            if sock.connect_ex(("8.8.8.8", 443)) == 0:
                local_ip = socket.gethostbyname(socket.gethostname())
                connections.append({
                    "protocol": "tcp", 
                    "local": f"{local_ip}:random",
                    "remote": "8.8.8.8:443",
                    "state": "ESTABLISHED"
                })
            sock.close()
        except Exception as e:
            print(f"Active connections method 2 failed: {e}")
        
        return connections if connections else [{"info": "No active connections found"}]
    
    def get_linux_listening_ports(self):
        ports = []
        try:
            
            result = subprocess.run(['netstat', '-tunl'], capture_output=True, text=True, timeout=10)
            for line in result.stdout.split('\n'):
                if 'LISTEN' in line and ('tcp' in line or 'udp' in line):
                    parts = line.split()
                    if len(parts) >= 4:
                        local_addr = parts[3]
                        if ':' in local_addr:
                            port = int(local_addr.split(':')[-1])
                            if port not in ports:
                                ports.append(port)
        except Exception as e:
            print(f"Listening ports method 1 failed: {e}")
    
        
        try:
            common_ports = [22, 80, 443, 3000, 5000, 8000, 8080, 9000]
            for port in common_ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.3)
                    result = sock.connect_ex(("127.0.0.1", port))
                    if result == 0 and port not in ports:
                        ports.append(port)
                    sock.close()
                except:
                    continue
        except Exception as e:
            print(f"Listening ports method 2 failed: {e}")
        
        return ports if ports else [{"info": "No listening ports found"}]
    
    def get_linux_sensitive_data(self):
        sensitive = {}
        try:
            user_home = os.path.expanduser("~")
            
            
            config_files = []
            ssh_files = [
                f"{user_home}/.ssh/config",
                f"{user_home}/.ssh/known_hosts", 
                f"{user_home}/.ssh/authorized_keys"
            ]
            
            for ssh_file in ssh_files:
                if os.path.exists(ssh_file):
                    config_files.append(os.path.basename(ssh_file))
            
            sensitive["network_config_files"] = config_files
            
            proxy_settings = {}
            proxy_vars = ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]
            for var in proxy_vars:
                if var in os.environ:
                    proxy_settings[var] = os.environ[var]
            
            sensitive["proxy_settings"] = proxy_settings
            
            
            wifi_info = []
            wifi_paths = [
                f"{user_home}/.local/share/NetworkManager",
                "/etc/NetworkManager/system-connections",
                f"{user_home}/.config/wifi"
            ]
            
            for path in wifi_paths:
                if os.path.exists(path):
                    wifi_info.append(os.path.basename(path))
            
            sensitive["wifi_info"] = wifi_info
           
           
            vpn_configs = []
            vpn_paths = [
                f"{user_home}/.vpn",
                f"{user_home}/.openvpn",
                f"{user_home}/.wireguard",
                f"{user_home}/.config/vpn"
            ]
            
            for path in vpn_paths:
                if os.path.exists(path):
                    vpn_configs.append(os.path.basename(path))
            
            sensitive["vpn_configs"] = vpn_configs
            
        except Exception as e:
            print(f"Sensitive data error: {e}")
            sensitive["error"] = str(e)
        
        return sensitive
    
    def get_linux_network_status(self):
        status = {}
        try:
            
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=5)
                status["internet_connectivity"] = "connected"
            except:
                status["internet_connectivity"] = "disconnected"
            
            status["platform"] = "Linux"
            
            
            interfaces = []
            try:
                result = subprocess.run(['ip', 'addr'], capture_output=True, text=True, timeout=5)
                for line in result.stdout.split('\n'):
                    if 'mtu' in line and 'state' in line:
                        parts = line.split()
                        if len(parts) > 1 and ':' in parts[1]:
                            interface = parts[1].replace(':', '')
                            if interface != 'lo' and interface not in interfaces:
                                interfaces.append(interface)
            except:
                try:
                    with open('/proc/net/dev', 'r') as f:
                        for line in f.readlines()[2:]:
                            if ':' in line:
                                interface = line.split(':')[0].strip()
                                if interface and interface != 'lo' and interface not in interfaces:
                                    interfaces.append(interface)
                except:
                    interfaces = ["unknown"]
            
            status["interfaces"] = interfaces
            
        except Exception as e:
            print(f"Network status error: {e}")
            status["error"] = str(e)
        
        return status
    
    def get_windows_network_info(self):
        try:
            return {
                "network_config": self.get_windows_network_config(),
                "active_connections": self.get_windows_active_connections(),
                "listening_ports": self.get_windows_listening_ports(),
                "sensitive_data": self.get_windows_sensitive_data(),
                "network_status": self.get_windows_network_status(),
                "mac_address": self.get_mac_addresses()
            }
        except Exception as e:
            return {"error": f"Windows network info error: {str(e)}"}
    
    def get_windows_network_config(self):
        config = {}
        try:
            config["hostname"] = socket.gethostname()
            
            
            ip_addresses = []
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                ip_addresses.append(ip)
                s.close()
            except Exception as e:
                print(f"Windows IP method failed: {e}")
            
           
            try:
                result = subprocess.run(
                    ['ipconfig'], 
                    capture_output=True, text=True, shell=True, timeout=10
                )
                for line in result.stdout.split('\n'):
                    if 'IPv4 Address' in line:
                        ip = line.split(':')[-1].strip()
                        if ip and ip not in ip_addresses and not ip.startswith('169.254'):
                            ip_addresses.append(ip)
            except Exception as e:
                print(f"Windows ipconfig failed: {e}")
            
            config["ip_addresses"] = ip_addresses if ip_addresses else ["unknown"]
            
            
            try:
                result = subprocess.run(
                    ['ipconfig'], 
                    capture_output=True, text=True, shell=True, timeout=10
                )
                for line in result.stdout.split('\n'):
                    if 'Default Gateway' in line and ':' in line:
                        gateway = line.split(':')[-1].strip()
                        if gateway and gateway.lower() != "":
                            config["gateway"] = gateway
                            break
                else:
                    config["gateway"] = "unknown"
            except Exception as e:
                print(f"Windows gateway failed: {e}")
                config["gateway"] = "unknown"
            
            
            try:
                result = subprocess.run(
                    ['ipconfig', '/all'], 
                    capture_output=True, text=True, shell=True, timeout=10
                )
                dns_servers = []
                for line in result.stdout.split('\n'):
                    if 'DNS Servers' in line and ':' in line:
                        dns_ip = line.split(':')[-1].strip()
                        if dns_ip and dns_ip not in dns_servers:
                            dns_servers.append(dns_ip)
                config["dns_servers"] = dns_servers if dns_servers else ["unknown"]
            except Exception as e:
                print(f"Windows DNS failed: {e}")
                config["dns_servers"] = ["unknown"]
                
        except Exception as e:
            config["error"] = str(e)
        
        return config
    
    def get_windows_active_connections(self):
        connections = []
        try:
            result = subprocess.run(
                ['netstat', '-n'], 
                capture_output=True, text=True, shell=True, timeout=10
            )
            for line in result.stdout.split('\n'):
                if "ESTABLISHED" in line and ("TCP" in line or "UDP" in line):
                    parts = line.split()
                    if len(parts) >= 4:
                        connections.append({
                            "protocol": "tcp" if "TCP" in line else "udp",
                            "local": parts[1],
                            "remote": parts[2],
                            "state": "ESTABLISHED"
                        })
        except Exception as e:
            print(f"Windows active connections failed: {e}")
        
        
        if not connections:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                if sock.connect_ex(("8.8.8.8", 443)) == 0:
                    connections.append({
                        "protocol": "tcp",
                        "local": f"{socket.gethostbyname(socket.gethostname())}:random",
                        "remote": "8.8.8.8:443",
                        "state": "ESTABLISHED"
                    })
                sock.close()
            except Exception as e:
                print(f"Windows connection fallback failed: {e}")
        
        return connections if connections else [{"info": "No active connections found"}]
    
    def get_windows_listening_ports(self):
        ports = []
        try:
            
            common_ports = [80, 443, 135, 139, 445, 3389, 5985, 5986, 21, 22, 23, 53, 110, 143, 993, 995]
            for port in common_ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.5)
                    if sock.connect_ex(("127.0.0.1", port)) == 0 and port not in ports:
                        ports.append(port)
                    sock.close()
                except: 
                    continue
        except Exception as e:
            print(f"Windows listening ports failed: {e}")
        
        return ports if ports else [{"info": "No listening ports found"}]
    
    def get_windows_sensitive_data(self):
        sensitive = {}
        try:
            user_home = os.path.expanduser("~")
            
            
            config_files = []
            ssh_path = f"{user_home}\\.ssh"
            if os.path.exists(ssh_path):
                for file in ["config", "known_hosts", "authorized_keys"]:
                    if os.path.exists(f"{ssh_path}\\{file}"):
                        config_files.append(file)
            sensitive["network_config_files"] = config_files
            
            
            proxy_settings = {}
            for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
                if var in os.environ:
                    proxy_settings[var] = os.environ[var]
            
           
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                  r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
                    try:
                        proxy_enable = winreg.QueryValueEx(key, "ProxyEnable")[0]
                        if proxy_enable == 1:
                            proxy_server = winreg.QueryValueEx(key, "ProxyServer")[0]
                            proxy_settings["Windows_Proxy"] = proxy_server
                    except: 
                        pass
            except: 
                pass
            
            sensitive["proxy_settings"] = proxy_settings
            
            
            wifi_info = []
            try:
                result = subprocess.run(
                    ['netsh', 'wlan', 'show', 'profiles'], 
                    capture_output=True, text=True, shell=True, timeout=10
                )
                if "All User Profile" in result.stdout:
                    wifi_info.append("wifi_profiles_available")
            except: 
                pass
            sensitive["wifi_info"] = wifi_info
            
            
            vpn_configs = []
            vpn_paths = [
                f"{user_home}\\VPN", 
                f"{user_home}\\.vpn",
                f"{user_home}\\OpenVPN",
                f"{user_home}\\WireGuard"
            ]
            for path in vpn_paths:
                if os.path.exists(path):
                    vpn_configs.append(os.path.basename(path))
            sensitive["vpn_configs"] = vpn_configs
            
        except Exception as e:
            sensitive["error"] = str(e)
        
        return sensitive
    
    def get_windows_network_status(self):
        status = {}
        try:
            
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                status["internet_connectivity"] = "connected"
            except:
                status["internet_connectivity"] = "disconnected"
            
            status["platform"] = "Windows"
            
            
            interfaces = []
            try:
                result = subprocess.run(
                    ['netsh', 'interface', 'show', 'interface'], 
                    capture_output=True, text=True, shell=True, timeout=10
                )
                for line in result.stdout.split('\n'):
                    if "Connected" in line and "Enabled" in line:
                        parts = line.split('  ')
                        for part in parts:
                            if part.strip() and part.strip() not in ['', 'Connected', 'Enabled']:
                                if part.strip() not in interfaces:
                                    interfaces.append(part.strip())
            except Exception as e:
                print(f"Windows interfaces failed: {e}")
            
            status["interfaces"] = interfaces if interfaces else ["unknown"]
            
        except Exception as e:
            status["error"] = str(e)
        
        return status
    
    def get_mac_addresses(self):
    
        mac_addresses = {}
        system = platform.system().lower()
        
        try:
            if system == 'windows':
                result = subprocess.run(
                    ['ipconfig', '/all'], 
                    capture_output=True, text=True, shell=True, timeout=10
                )
                current_interface = None
                for line in result.stdout.split('\n'):
                    if 'adapter' in line.lower() and ':' in line:
                        current_interface = line.split(':')[0].strip()
                    elif 'physical address' in line.lower() and current_interface:
                        mac = line.split(':')[-1].strip()
                        mac_addresses[current_interface] = mac
                        
            elif system == 'linux':
                
                result = subprocess.run(['ip', 'link'], capture_output=True, text=True, timeout=5)
                current_interface = None
                for line in result.stdout.split('\n'):
                    if line.strip().startswith('2:') or line.strip().startswith('3:'):
                        parts = line.split()
                        if len(parts) > 1 and ':' in parts[1]:
                            current_interface = parts[1].replace(':', '')
                    elif 'link/ether' in line and current_interface:
                        mac = line.split()[1]
                        mac_addresses[current_interface] = mac
        except Exception as e:
            print(f"MAC address collection failed: {e}")
        
        return mac_addresses

if __name__ == "__main__":
    si = NetworkInfo()
    print(json.dumps(si.network_info, indent=2))  