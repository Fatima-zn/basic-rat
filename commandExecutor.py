import sys
import os
import platform
import threading
import time
from typing import List, Dict, Optional, Union, Callable
from datetime import datetime
import subprocess

class CommandExecutor:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.system = platform.system().lower()
        self._is_windows = (self.system == 'windows')
        
        self.execution_count = 0
        self.success_count = 0
        self.error_count = 0
        
        self._log("Command Executor Initialisation !")
        self._log(f"Detected system: {self.system}")
    
    def _log(self, message: str, level: str = "INFO"):
        if not self.verbose and level == "INFO":
            return
            
        colors = {
            "INFO": "\033[94m",
            "SUCCESS": "\033[92m", 
            "ERROR": "\033[91m",
            "WARNING": "\033[93m",
            "RESET": "\033[0m"
        }
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = colors.get(level, colors["INFO"])
        print(f"{color}[{timestamp}] {message}{colors['RESET']}")
    
    def get_cross_platform_command(self, command: str) -> str:
        #ndir le cross platform 
        if self._is_windows:
            # CONVERSIONS POUR WINDOWS
            command_map = {
                'pwd': 'echo %CD%',
                'ls -la': 'dir',
                'ls': 'dir',
                'cat': 'type',
                'grep': 'findstr',
                'cp': 'copy',
                'mv': 'move', 
                'rm': 'del',
                'mkdir -p': 'mkdir',
                'sleep': 'timeout'
            }
            
            for linux_cmd, windows_cmd in command_map.items():
                if command.strip().startswith(linux_cmd):
                    return command.replace(linux_cmd, windows_cmd, 1)
            
            # Adapte les var d'env Linux -> Windows
            if '$' in command:
                command = command.replace('$', '%')
        else:
            # CONVERSIONS POUR LINUX 
            command_map = {
                'dir': 'ls -la',
                'type': 'cat',
                'findstr': 'grep',
                'copy': 'cp',
                'del': 'rm',
                'timeout': 'sleep'
            }
            
            for windows_cmd, linux_cmd in command_map.items():
                if command.strip().startswith(windows_cmd):
                    return command.replace(windows_cmd, linux_cmd, 1)
        
        return command
    
    def prepare_cross_platform_test(self, test: Dict) -> Dict:
        command = test["command"]
        
        if self._is_windows:
            # ONLY WINDOWS
            if command == "pwd":
                test["command"] = "echo %CD%"
            elif command.startswith("for i in"):
                # Convertit boucle bash en boucle cmd
                test["command"] = "for /L %i in (1,1,3) do echo Ligne %i && timeout 1 >nul"
            elif "$" in command:
                # Var Linux -> Windows
                test["command"] = command.replace("$", "%")
        else:
            # COMMANDES LINUX
            if command == "echo %CD%":
                test["command"] = "pwd"
            elif command.startswith("for /L"):
                test["command"] = "for i in 1 2 3; do echo \"Ligne $i\"; sleep 0.5; done"
            elif "%" in command and "CD" in command:
                test["command"] = "pwd"
        
        return test
    
    def prepare_command(self, command: Union[str, List[str]], args: Optional[List[str]] = None) -> Union[str, List[str]]:
        
        if isinstance(command, str):
            command = self.get_cross_platform_command(command)
        
        if isinstance(command, list):
            cmd_list = command.copy()
            if args:
                cmd_list.extend(args)
            return cmd_list
        
        if args:
            if isinstance(args, list):
                full_command = f"{command} {' '.join(args)}"
            else:
                full_command = f"{command} {args}"
        else:
            full_command = command
            
        return full_command
    
    def stream_reader(self, stream, stream_type: str):
        try:
            while True:
                line = stream.readline()
                if not line:
                    break
                try:
                    # Gestion d'encodage cross-platform
                    if isinstance(line, bytes):
                        decoded_line = line.decode('utf-8', errors='replace').rstrip('\n\r')
                    else:
                        decoded_line = line.rstrip('\n\r')
                    
                    if decoded_line:
                        color = "\033[37m" if stream_type == "stdout" else "\033[31m"
                        prefix = "📤" if stream_type == "stdout" else "❌"
                        print(f"{color}{prefix} {decoded_line}\033[0m")
                except Exception as e:
                    self._log(f"Erreur décodage: {e}", "ERROR")
        except Exception as e:
            self._log(f"Erreur lecture flux: {e}", "ERROR")
    
    def execute(
        self,
        command: Union[str, List[str]],
        args: Optional[List[str]] = None,
        working_dir: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        shell: Optional[bool] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, any]:
        
        start_time = time.time()
        self.execution_count += 1
        
        # Prep de la cmd
        final_command = self.prepare_command(command, args)
        
        if shell is None:
            shell = isinstance(final_command, str)
        
        
        # Env
        environment = os.environ.copy()
        if env_vars:
            environment.update(env_vars)
            self._log(f"{len(env_vars)} environment variables defined")
            if self.verbose and env_vars:
                self._log(f"env variables: {list(env_vars.keys())}")
        
        # verif dir
        if working_dir and not os.path.exists(working_dir):
            error_msg = f"Directory not found: {working_dir}"
            self._log(error_msg, "ERROR")
            return {
                'success': False, 'return_code': -1, 'command': str(final_command),
                'working_dir': working_dir, 'timeout': False, 'error': error_msg,
                'duration': 0.0, 'output_lines': []
            }
        
        # Log exe
        self._log(f"Execution : {final_command}")
        if working_dir:
            self._log(f"Directory: {working_dir}")
        if timeout:
            self._log(f"Timeout: {timeout}s")
        
        # Config process - CROSS-PLATFORM
        process_options = {
            'env': environment,
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,


        }
        
        if working_dir:
            process_options['cwd'] = working_dir
        
        try:
            # Creation proces
            process = subprocess.Popen(
                final_command,
                shell=shell,
                **process_options
            )
            
            # Threads pour streaming
            stdout_thread = threading.Thread(
                target=self.stream_reader,
                args=(process.stdout, "stdout")
            )
            stderr_thread = threading.Thread(
                target=self.stream_reader, 
                args=(process.stderr, "stderr")
            )
            
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Attente
            return_code = process.wait(timeout=timeout)
            
            stdout_thread.join(timeout=2)
            stderr_thread.join(timeout=2)
            
            duration = time.time() - start_time
            
            # Rsult 
            success = (return_code == 0)
            
            if success:
                self.success_count += 1
                self._log(f"Success in {duration:.2f}s (code: {return_code})", "SUCCESS")
            else:
                self.error_count += 1
                self._log(f"Failure in {duration:.2f}s (code: {return_code})", "ERROR")
            
            return {
                'success': success,
                'return_code': return_code,
                'command': str(final_command),
                'working_dir': working_dir or os.getcwd(),
                'timeout': False,
                'error': None,
                'duration': duration,
                'system': self.system
            }
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self._log(f"Timeout after {duration:.2f}s", "ERROR")
            process.terminate()
            return {
                'success': False, 'return_code': -1, 'timeout': True,
                'error': f"Timeout after {timeout}s", 'duration': duration
            }
            
        except Exception as e:
            duration = time.time() - start_time
            self._log(f"Execution error: {e}", "ERROR")
            return {
                'success': False, 'return_code': -1, 'error': str(e),
                'duration': duration
            }
    
    def execute_simple(self, command: str, **kwargs) -> Dict[str, any]:
        return self.execute(command, shell=True, **kwargs)
    
    def get_stats(self) -> Dict[str, any]:
        success_rate = (self.success_count / self.execution_count * 100) if self.execution_count > 0 else 0
        return {
            'total_executions': self.execution_count,
            'successful': self.success_count,
            'failed': self.error_count,
            'success_rate': round(success_rate, 2)
        }

def run_command(command: Union[str, List[str]], **kwargs) -> Dict[str, any]:
    return CommandExecutor().execute(command, **kwargs)



if __name__ == "__main__":
    print("🧪 TEST COMMAND EXECUTOR - CROSS-PLATFORM")
    print("=" * 50)
    
    executor = CommandExecutor(verbose=True)
    
    common_tests = [
        {
            "name": "Commande echo basique",
            "command": "echo Hello Cross-Platform!",
        },
        {
            "name": "Avec variables d'environnement", 
            "command": "echo Test variable",
            "env_vars": {"MY_VAR": "valeur_test_123"}
        },
        {
            "name": "Avec répertoire de travail",
            "command": "echo Current directory test",
            "working_dir": os.path.dirname(__file__) or os.getcwd()
        }
    ]
    
    # TESTS SPÉCIFIQUES PAR SYSTÈME
    system_specific_tests = []
    
    if executor._is_windows:
        system_specific_tests = [
            {
                "name": "Liste fichiers (Windows)",
                "command": "dir",
            },
            {
                "name": "Boucle (Windows)", 
                "command": "for /L %i in (1,1,2) do echo Windows ligne %i",
                "timeout": 5
            }
        ]
    else:
        system_specific_tests = [
            {
                "name": "Liste fichiers (Linux/macOS)",
                "command": "ls -la",
            },
            {
                "name": "Boucle (Linux/macOS)",
                "command": "for i in 1 2; do echo \"Linux ligne $i\"; sleep 0.5; done",
                "timeout": 5
            }
        ]
    
    # EXÉCUTION DES TESTS
    all_tests = common_tests + system_specific_tests
    
    for i, test in enumerate(all_tests, 1):
        print(f"\n{i}. 🧪 {test['name']}")
        print("-" * 40)
        
        result = executor.execute_simple(
            command=test["command"],
            working_dir=test.get("working_dir"),
            env_vars=test.get("env_vars"),
            timeout=test.get("timeout")
        )
        
        print(f"📊 Résultat: {'✅ SUCCÈS' if result['success'] else '❌ ÉCHEC'}")
        print(f"🔢 Code: {result['return_code']} | ⏱️  {result['duration']:.2f}s")
        
        if result['error']:
            print(f"💥 Erreur: {result['error']}")
    
    # Résumé final
    print("\n" + "=" * 50)
    stats = executor.get_stats()
    print("📈 RÉSUMUM FINAL:")
    print(f"   Système: {executor.system}")
    print(f"   Tests exécutés: {stats['total_executions']}")
    print(f"   ✅ Succès: {stats['successful']}") 
    print(f"   ❌ Échecs: {stats['failed']}")
    print(f"   📊 Taux de succès: {stats['success_rate']}%")
    print("=" * 50)

    