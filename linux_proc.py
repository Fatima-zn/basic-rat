
import os
import pwd
import grp
import psutil
from datetime import datetime
import signal
import subprocess
import platform
import re




class LinuxProcManager():
    def __init__(self):        
        self.system = "Linux"
        self.monitoring = False
        self.process_history = []
        self._proc_path = "/proc"
        self._check_proc_access()
        
    
    def _check_proc_access(self):
        if not os.path.exists(self._proc_path):
            raise RuntimeError("/proc filesystem not available")
        if not os.access(self._proc_path, os.R_OK):
            raise RuntimeError("No read access to /proc filesystem")
        
        
        
    
    def _read_proc_file(self, pid, filename):
        try:
            filepath = os.path.join(self._proc_path, str(pid), filename)
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    return f.read().strip()
            
            return None
        
        except :
            return None
    
    
    
    def _get_username_from_uid(self, uid):
        try:
            return pwd.getpwuid(uid).pw_name
        except:
            return str(uid)
        
        
        
        
    def _get_groupname_from_gif(self, gid):
        try:
            return grp.getgrgid(gid).gr_name
        except:
            return str(gid)
      
      
      
        
    def _get_process_capabilities(self, pid):
        try:
            status_content = self._read_proc_file(pid, "status")
            if not status_content:
                return []
            
            capabilities = []
            for line in status_content.split("\n"):
                if line.startwith("Cap"):
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        cap_name = parts[0].replace("Cap", '').replace(":", '').lower()
                        cap_value = parts[1].strip()
                        
                        capabilities.append({
                            "name": cap_name,
                            "value": cap_value
                        })
            
            return capabilities
        
        except:
            return []
        
        
    def _get_process_limits(self, pid):
        try:
            limits_content = self._read_proc_file(pid, "limits")
            if not limits_content:
                return {}
            
            limits = {}
            for line in limits_content.split("\n")[1:]:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 4:
                        limit_name = parts[0]
                        soft_limit = parts[1]
                        hard_limit = parts[2]
                        units = parts[3] if len(parts) > 3 else ''
                        
                        
                        limits[limit_name] = {
                            "soft_limit" : soft_limit,
                            "hard_limit" : hard_limit,
                            "units" : units
                        } 
            
            return limits
        except: 
            return {}
        
        
    
    
    def get_all_processes(self, detailed=True):
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time', 'status']):
                try:
                    process_info = proc.info
                    
                    if detailed:
                        with proc.oneshot():
                            process_info.update({
                                "exe": ' '.join(proc.cmdline()) or proc.name(),
                                'cmdline': proc.cmdline(),
                                "cpu_times": proc.cpu_times()._asdict(),
                                "memory_info": proc.memory_info()._asdict(),
                                "ppid": proc.ppid(),
                                "nice": proc.nice(),
                                "num_threads": proc.num_threads(),
                                "open_files": len(proc.open_files()),
                                "connections": len(proc.connections()),
                                "uid": proc.uids().real,
                                "gid": proc.gids().real,
                                "num_context_switches": proc.num_ctx_switches().voluntary + proc.num_ctx_switches().involuntary
                            })
                            
                            proc_status = self._read_proc_file(proc.pid, "status")
                            if proc_status:
                                for line in proc_status.split("\n"):
                                    if line.startswith('State:'):
                                        process_info["state"] = line.split(":")[1].strip()
                                    elif line.startswith("VmSize:"):
                                        process_info["vm_size"] = line.split(":")[1].strip()
                    
                    
                    processes.append(process_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return processes
        except Exception as e:
            return {"error": f'Linux process enumeration failed: {e}'}
    
    
    
    def get_process_tree(self):
        def build_tree(pid, depth=0, max_depth=6):
            if depth > max_depth:
                return None
            
            try:
                proc = psutil.Process(pid)
                children = proc.children(recursive=False)
                
                tree_node = {
                    "pid": pid,
                    "name": proc.name(),
                    "username": proc.username(),
                    "uid": proc.uids().real,
                    "children": []
                }
                
                
                for child in children:
                    child_tree = build_tree(child.pid, depth + 1, max_depth)
                    if child_tree:
                        tree_node["children"].append(child_tree)
                        
                return tree_node
            
            except psutil.NoSuchProcess:
                return {"pid": pid, "name": "DEFUNCT", "children": []}
        
        try:
            return [build_tree(1)]
        except:
            return {"error": 'Could not build process tree from PID 1'}
        
    
    
    
    def get_process_details(self, pid):
        try:
            proc = psutil.Process(pid)
            
            details = {
                'pid': pid,
                'name': proc.name(),
                'status': proc.status(),
                'username': proc.username(),
                'create_time': datetime.fromtimestamp(proc.create_time()).isoformat(),
                "executable": ' '.join(proc.cmdline()) or proc.name(),
                "command_line": proc.cmdline(),
                "working_directory": proc.cwd(),
                "environment": dict(proc.environ()),
                "cpu_percent": proc.cpu_percent(),
                "memory_percent": proc.memory_percent(),
                "cpu_times": proc.cpu_times()._asdict(),
                "io_counters": proc.io_counters()._asdict() if proc.io_counters() else None,
                "ppid": proc.ppid(),
                "nice": proc.nice(),
                "num_threads": proc.nun_threads(),
                "uids": {
                    'real': proc.uids().real,
                    "effective": proc.uids().effective,
                    "saved": proc.uids().saved
                },
                "gids": {
                    "real": proc.gids().real,
                    "effective": proc.gids().effective,
                    "saved": proc.gids().saved
                },
                "open_files": [f.path for f in proc.open_files()],
                "connections": [
                    {
                        'fd': conn.fd,
                        "family": conn.family,
                        "type": conn.type,
                        "laddr": conn.laddr,
                        "raddr": conn.raddr,
                    "status": conn.status
                    } for conn in proc.net_connections()
                ],
                "num_ctx_switches": {
                    "voluntary": proc.num_ctx_switches().voluntary,
                    "involuntary": proc.num_ctx_switches().involuntary
                },
                'capabilities': self._get_process_capabilities(pid),
                "resource_limits": self._get_process_limits(pid)
            }
            
            proc_stat = self._read_proc_file(pid, "stat")
            if proc_stat:
                stat_parts = proc_stat.split()
                if len(stat_parts) > 22:
                    details["proc_stat"] = {
                        'state': stat_parts[2],
                        "ppid": int(stat_parts[3]),
                        "priority": int(stat_parts[17]),
                        'nice': int(stat_parts[18]),
                        "threads": int(stat_parts[19])
                    }
            
            return details
        except psutil.NoSuchProcess:
            return {"error": f'Linux process {pid} not found'}
        except Exception as e:
            return {"error": f'Linux process details failed: {e}'}
    
    
    def kill_process(self, pid):
        try:
            proc = psutil.Process(pid)
            
            os.kill(pid, signal.SIGTERM)
            
            try:
                proc.wait(timeout=3)
                return {
                    "success": True,
                    "message": f'Linux process {pid} terminated (SIGTERM)',
                    "method": "SIGTERM"
                }
            
            except psutil.TimeoutExpired:
                os.kill(pid, signal.SIGKILL)
                return {
                    "success": True,
                    "message": f'Linux process {pid} force killed (SIGKILL)',
                    'method': "SIGKILL"
                }
        
        
        except ProcessLookupError:
            return {"success": False, 'error': f'Linux process {pid} not found'}
        except PermissionError:
            return {"success": False, "error": f'Permission denied to kill linux process {pid}'}
        except Exception as e:
            return {'success': False, "error": f'linux process kill failed: {e}'}
        
    
    
    def start_process(self, command, hidden=False):
        try:
            if hidden:
                proc = subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    preexec_fn=os.setsid
                )
            
            else:
                proc = subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            return {
                "success": True,
                "pid": proc.pid,
                "message": f'linux process started with PID {proc.pid}',
                "hidden": hidden
            }
        
        
        except FileNotFoundError:
            return {"success": False, "error": f"Command not found: {command[0]}"}
        except PermissionError:
            return {"success": False, "error": f'Permission denied to execute: {command[0]}'}
        except Exception as e:
            return {"success": False, "error": f'linux process start failed: {e}'}
        
    
    def execute_command(self, command, hidden=False, working_dir=None):
        try:
            cwd = working_dir if working_dir else None
            
            
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                shell=True,
                text=True,
                cwd=cwd,
                preexec_fn=os.setpgrp if hidden else None
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
                'platform': 'Linux',
                'hostname': platform.node(),
                'kernel': platform.release(),
                'architecture': platform.architecture()[0],
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
            
            
            

            distro_info = {}
            try:
                if os.path.exists('/etc/os-release'):
                    with open('/etc/os-release', 'r') as f:
                        for line in f:
                            if '=' in line:
                                key, value = line.strip().split('=', 1)
                                distro_info[key.lower()] = value.strip('"')
            except:
                pass
            
            system_info['distribution'] = distro_info
            



            try:
                if os.path.exists('/proc/cpuinfo'):
                    with open('/proc/cpuinfo', 'r') as f:
                        cpuinfo = f.read()
                    
                    physical_cores = len(set(
                        re.findall(r'physical id\s*:\s*(\d+)', cpuinfo)
                    ))
                    logical_cores = len(re.findall(r'processor\s*:\s*\d+', cpuinfo))
                    
                    model_names = re.findall(r'model name\s*:\s*(.+)', cpuinfo)
                    cpu_model = model_names[0] if model_names else 'Unknown'
                    
                    system_info['cpu'] = {
                        'model': cpu_model,
                        'physical_cores': physical_cores or logical_cores,
                        'logical_cores': logical_cores,
                        'cpu_usage': psutil.cpu_percent(percpu=True)
                    }
            except:
                pass
            




            try:
                if os.path.exists('/proc/meminfo'):
                    with open('/proc/meminfo', 'r') as f:
                        meminfo = f.read()
                    
                    mem_total = re.search(r'MemTotal:\s*(\d+) kB', meminfo)
                    mem_available = re.search(r'MemAvailable:\s*(\d+) kB', meminfo)
                    swap_total = re.search(r'SwapTotal:\s*(\d+) kB', meminfo)
                    swap_free = re.search(r'SwapFree:\s*(\d+) kB', meminfo)
                    
                    system_info['memory'] = {
                        'total': int(mem_total.group(1)) * 1024 if mem_total else 0,
                        'available': int(mem_available.group(1)) * 1024 if mem_available else 0,
                        'percent': psutil.virtual_memory().percent,
                        'swap_total': int(swap_total.group(1)) * 1024 if swap_total else 0,
                        'swap_used': (int(swap_total.group(1)) - int(swap_free.group(1))) * 1024 
                                    if swap_total and swap_free else 0
                    }
            except:
                pass
            



            try:
                with open('/proc/loadavg', 'r') as f:
                    load_avg = f.read().strip().split()
                system_info['load_average'] = {
                    '1min': load_avg[0],
                    '5min': load_avg[1],
                    '15min': load_avg[2]
                }
            except:
                pass
            




            try:
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.readline().split()[0])
                system_info['uptime_seconds'] = uptime_seconds
            except:
                pass
            
            return system_info
            
            
            
            
        except Exception as e:
            return {'error': f'Linux system info failed: {e}'}
        
        