import platform

class ProcessManager:
    def __init__(self):
        self.system = platform.system()
        self.monitoring = False
        self.process_history = []
        
        if self.system == "Linux":
            from linux_proc import LinuxProcManager
            self.manager = LinuxProcManager()
        elif self.system == "Windows":
            from windows_proc import WindowsProcManager
            self.manager = WindowsProcManager()
        else:
            raise NotImplementedError(f"Unsupported platform: {self.system}")
    
    
    def __getattr__(self, name):
        return getattr(self.manager, name)