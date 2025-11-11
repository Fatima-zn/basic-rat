import win32api
import win32con
import win32process
import win32security
import psutil
import datetime
import subprocess
import platform
from datetime import datetime


class WindowsProcManager():
    def __init__(self):
        self.system = "Windows"
        self.monitoring = False
        self.process_history = []
        self._wmi_available = self._check_wmi_availability()
   
   
    
    def _check_wmi_availability(self):
        try:
            import wmi
            wmi.WMI()
            return True
        
        except:
            return False
    
    
    def _get_windows_session_id(self, pid):
        try:
            process = win32api.OpenProcess(
                win32con.PROCESS_QUERY_INFORMATION,
                False,
                pid
            )
            
            session_id = win32process.GetProcessId(process)
            win32api.CloseHandle(process)
            return session_id

        except:
            return None
        
    
    def _get_process_services(self, pid):
        services = []
        if not self._wmi_available:
            return services
        
        try:
            import wmi
            c = wmi.WMI()
            
            for service in c.Win32_Service(ProcessId=pid):
                services.append({
                    "name": service.Name,
                    "display_name": service.DisplayName,
                    "state": service.State,
                    "start_mode": service.StartMode,
                    "path": service.PathName
                })
        except Exception as e:
            pass
        
        
        return services
    
    
    def _get_process_privileges(self, pid):
        try:
            process = win32api.OpenProcess(
                win32con.PROCESS_QUERY_INFORMATION,
                False,
                pid
            )
            
            token = win32security.OpenProcessToken(
                process,
                win32con.TOKEN_QUERY
            )
            
            privileges = win32security.GetTokenInformation(
                token,
                win32security.TokenPrivileges
            )
            
            win32api.CloseHandle(process)
            
            privilege_names = []
            for priv in privileges:
                name = win32security.LookupPrivilegeName(None, priv[0])
                privilege_names.append({
                    "name": name,
                    "enabled": bool(priv[1] & (win32con.SE_PRIVILEGE_ENABLED))
                })
                
                
            return privilege_names
        
        
        except:
            return []
    
    
    
    def get_all_processes(self, detailed=True):
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time', "status"]):
                try:
                    process_info = proc.info
                    
                    if len(processes) >= 30:  #TEST
                        break
                    
                    if detailed:
                        with proc.oneshot():
                            process_info.update({
                                "exe": proc.exe(),
                                "cmdline": proc.cmdline(),
                                "cpu_times": proc.cpu_times(),
                                "memory_info": proc.memory_info(),
                                "ppid": proc.ppid(),
                                "priority": proc.nice(),
                                "num_handles": proc.num_handles(),
                                "is_system_process": proc.username() == "SYSTEM",
                                "cwd": proc.cwd(),
                                "num_threads": proc.num_threads(),
                                "open_files": proc.open_files(),
                                "connections": proc.net_connections(),
                                "session_id": self._get_windows_session_id(proc.pid),
                                "services": self._get_process_services(proc.pid),
                                "privileges": self._get_process_privileges(proc.pid)
                            })
                            
                    processes.append(process_info)
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return processes
        
        except Exception as e:
            return {'error': f'Windows process enumeration failed; {e}'}
    
    
    
    
    """ def get_process_tree(self):
        def build_tree(pid, depth=0, max_depth=5):
            if depth > max_depth:
                return None
            
            try:
                proc = psutil.Process(pid)
                children = proc.children(recursive=False)
                
                
                tree_node = {
                    "pid": proc.pid,
                    "name": proc.name(),
                    "username": proc.username(),
                    "session_id": self._get_windows_session_id(proc.pid),
                    "is_service": len(self._get_process_services(proc.pid)) > 0,
                    "children": []
                }
                
                
                for child in children:
                    child_tree = build_tree(child.pid, depth+1, max_depth)
                    if child_tree:
                        tree_node["children"].append(child_tree)
                
                return tree_node
            
            except psutil.NoSuchProcess:
                return {"pid": pid, "name": "TERMINATED", "children": []}
        
        
        session_processes = {}
        for proc in psutil.process_iter(['pid', 'ppid']):
            try:
                if proc.info["ppid"] == 0:
                    session_id = self._get_windows_session_id(proc.info["pid"])
                    if session_id not in session_processes:
                        session_processes[session_id] = []
                    
                    process_tree = build_tree(proc.info["pid"])
                    if process_tree:
                        session_processes[session_id].append(process_tree)
            
            
            except:
                continue
        
        return session_processes """
  
  
  
  
    def get_process_tree(self):
        try:
            tree = []
            
            all_processes = []
            for proc in psutil.process_iter(['pid', 'ppid', 'name', 'username']):
                try:
                    all_processes.append({
                        'pid': proc.info['pid'],
                        'ppid': proc.info['ppid'], 
                        'name': proc.info['name'],
                        'username': proc.info['username'],
                        'children': []
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            processes_by_pid = {proc['pid']: proc for proc in all_processes}
            



            root_processes = []
            for proc in all_processes:
                ppid = proc['ppid']
                if ppid == 0 or ppid not in processes_by_pid:
                    root_processes.append(proc)
            


            def build_tree(process, visited=None, depth=0):
                if visited is None:
                    visited = set()
                
                if depth > 20 or process['pid'] in visited:
                    return process
                
                visited.add(process['pid'])
                

                children = [p for p in all_processes if p['ppid'] == process['pid']]
                for child in children:
                    if child['pid'] not in visited:
                        process['children'].append(build_tree(child, visited, depth + 1))
                
                return process
            
            for root in root_processes:
                tree.append(build_tree(root))
            
            return tree
            
        except Exception as e:
            return {"error": f"Failed to get process tree: {e}"}
        
        
        
    
    def get_process_details(self, pid):
        try:
            proc = psutil.Process(pid)
            
            details = {
                "pid": pid,
                "name": proc.name(),
                "status": proc.status(),
                "username": proc.username(),
                "create_time": datetime.fromtimestamp(proc.create_time()).isoformat(),
                "executable": proc.exe(),
                "command_line": proc.cmdline(),
                'working_directory': proc.cwd(),
                "cpu_percent": proc.cpu_percent(),
                "memory_percent": proc.memory_percent(),
                "session_id": self._get_windows_session_id(pid),
                "cpu_times": proc.cpu_times(),
                "io_counters": proc.io_counters()._asdict() if proc.io_counters() else None,
                "ppid": proc.ppid(),
                "priority": proc.nice(),
                
                "session_id": self._get_windows_session_id(pid),
                "num_handles": proc.num_handles(),
                "windows_services": self._get_process_services(pid),
                "privileges": self._get_process_privileges(pid),
                "is_system_process": proc.username() == "SYSTEM"
            }
            
            return details
        
        except psutil.NoSuchProcess:
            return {"error" : f"Windows process {pid} not found"}
        except Exception as e:
            return {"error" : f"Failed to get Windows process {pid} details; {e}"}
    
    
    def kill_process(self, pid):
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            try:
                proc.wait(timeout=3)
                return {
                    "success": True,
                    "message": f"Windows process {pid} terminated successfully.",
                    "method" : "terminate"
                }
                
            except psutil.TimeoutExpired:
                proc.kill()
                return {
                    "success" : True,
                    "message" : f'Windows process {pid} force killed',
                    "method" : "kill"
                }
        
        
        except psutil.NoSuchProcess:
            return {"success": False, "error": f'Windows process {pid} not found'}
        except psutil.AccessDenied:
            return {"success": False, "error": f"Access denied to kill windows process {pid}"}
        except Exception as e:
            return {"success": False, "error": f"windows process kill failed: {e}"}
    
    
    
    def start_process(self, command, hidden=False):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            if hidden:
                startupinfo.wShowWindow = 0
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            else:
                startupinfo.wShowWindow = 1
                creation_flags = 0
            
            
            proc = subprocess.Popen(
                command, 
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=creation_flags
            )
            
            
            return {
                "success": True,
                "pid": proc.pid,
                "message": f'Windows process started with PID {proc.pid}',
                "hidden": hidden
            }
        
        except FileNotFoundError:
            return {"success": False, "error": f'Command not found; {command[0]}'}
        except Exception as e:
            return {"success": False, "error": f'Windows process start failed: {e}'}
        
    
    def execute_command(self, command, hidden=False, working_dir=None):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            if hidden:
                startupinfo.wShowWindow = 0
                creation_flags = subprocess.CREATE_NO_WINDOW
            else:
                startupinfo.wShowWindow = 1
                creation_flags = 0
            
            
            cwd = working_dir if working_dir else None
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=creation_flags,
                shell=True,
                text=True,
                cwd=cwd
            )
            


            stdout, stderr = proc.communicate(timeout=30)
            return {
                "success": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "working_dir": cwd or "current directory",
                "message": f'Command executed with exit code {proc.returncode}'
            }
        
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except FileNotFoundError:
            return {"success": False, "error": f"Working directory not found: {working_dir}"}
        except Exception as e:
            return {"success": False, "error": f'Command execution failed: {e}'}
    
    
    def get_system_info(self):
        try:
            system_info = {
                "platform": "Windows",
                "hostname": platform.node(),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                "windows_version": platform.version(),
                "architecture": platform.architecture()[0]
            }
            
            
            if self._wmi_available:
                import wmi
                c = wmi.WMI()
                
                for cpu in c.Win32_Processor():
                    system_info["cpu"] = {
                        "name": cpu.Name,
                        "cores": cpu.NumberOfCores,
                        "logical_processors": cpu.NumberOfLogicalProcessors,
                        "max_clock": f"{cpu.MaxClockSpeed} MHz",
                        "manufacturer": cpu.Manufacturer
                    }
                    break #first only
                
                
                total_memory = 0
                for mem in c.Win32_ComputerSystem():
                    total_memory = int(mem.TotalPhysicalMemory)
                    break
                 
                system_info['memory'] = {
                    "total": total_memory,
                    "available": psutil.virtual_memory().available,
                    "percent": psutil.virtual_memory().percent
                }
                
                
                disks = []
                for disk in c.Win32_LogicalDisk():
                    disks.append({
                        'device': disk.DeviceID,
                        'type': disk.DriveType,
                        'size': int(disk.Size) if disk.Size else 0,
                        "free": int(disk.FreeSpace) if disk.FreeSpace else 0,
                        "filesystem": disk.FileSystem
                    })
                system_info['disks'] = disks
                
                for os_info in c.Win32_OperatingSystem():
                    system_info['os_details'] = {
                        "caption": os_info.Caption,
                        "version": os_info.Version,
                        "build_number": os_info.BuildNumber,
                        "install_date": os_info.InstallDate
                    }
                    break
            
            
            return system_info

        except Exception as e:
            return {"error": f'windows system info failed: {e}'}