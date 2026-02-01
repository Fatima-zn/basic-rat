import platform
import psutil

class ArchitectureInfo():
    def __init__(self):
        self.get_architecture = self.get_architecture_info()
        
    #avoir les info sur l'architecture 
    def get_architecture_info(self):
        architecture_info = {
            "CPU": self.get_cpu_info(),
            "Memory": self.get_memory_info(),
            "Storage": self.get_storage_info()
        }
        return architecture_info
    
    def get_cpu_info(self): 
        system = platform.system().lower()
        if system == 'windows':
            return self.get_windows_cpu_info()
        elif system == 'linux':
            return self.get_linux_cpu_info()
        else:
            return self.get_generic_cpu_info()
        
    
    def get_windows_cpu_info(self):
        try:
            import psutil
            cpu_freq = psutil.cpu_freq()
            return {
                "Model": platform.processor(),
                "Architecture": platform.machine(),
                "Physical Cores": psutil.cpu_count(logical=False),
                "Logical Cores": psutil.cpu_count(logical=True),
                "Frequency": round(cpu_freq.current)if cpu_freq else "Unknown"
            }
        except Exception as e:
            return self.get_generic_cpu_info()
        
    def get_linux_cpu_info(self):
        try:
            import psutil
            cpu_freq = psutil.cpu_freq()
            
            model = platform.processor()
            physical_cores = psutil.cpu_count(logical=False)
            
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'model name' in line:
                        model = line.split(':')[1].strip()
                        break
                    
            return {
                "Model": model,
                "Architecture": platform.machine(),
                "Physical Cores": physical_cores,
                "Logical Cores": psutil.cpu_count(logical=True),
                "Frequency (MHz)": round(cpu_freq.current) if cpu_freq else "Unknown"
            }
        except Exception as e :
            return self.get_generic_cpu_info()
        
    def get_generic_cpu_info(self):
        return{
            "Model": platform.processor(),
            "Architecture": platform.machine(),
            "Physical Cores": psutil.cpu_count(logical=False),
            "Logical Cores": psutil.cpu_count(logical=True),
            "Frequency (MHz)": "Unknown"
        }
        
    def get_memory_info(self):
        try:
            import psutil
            memory = psutil.virtual_memory()
            return{
                "Total GB": round(memory.total / (1024**3), 2),
                "Available GB": round(memory.available / (1024**3), 2),
                "Used GB": round(memory.used / (1024**3), 2),
                "Usage Percent": round(memory.percent, 1)
            }
        except Exception as e:
            return self.get_memory_info()
        
    def get_storage_info(self):
        try:
            import psutil 
            storage_info = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    storage_info.append({
                        "Device": partition.device,
                        "Mountpoint": partition.mountpoint,
                        "Type": partition.fstype,
                        "Total_GB": round(usage.total / (1024**3), 2),
                        "Free_GB": round(usage.free / (1024**3), 2),
                        "Used_GB": round(usage.used / (1024**3), 2),
                        "Usage_Percent": round(usage.percent, 1)
                    })
                except : 
                    continue
            return storage_info
        except Exception as e:
            return []
        
    
if __name__ == "__main__":
    archi = ArchitectureInfo()
    print(archi.get_architecture_info())