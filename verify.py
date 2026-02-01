"""
Script de vérification pour le projet Basic RAT Merged
Vérifie que tous les modules et dépendances sont présents
"""

import sys
import os
from pathlib import Path

# Couleurs pour l'affichage
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✓{RESET} {msg}")

def print_error(msg):
    print(f"{RED}✗{RESET} {msg}")

def print_warning(msg):
    print(f"{YELLOW}!{RESET} {msg}")

def print_info(msg):
    print(f"{BLUE}ℹ{RESET} {msg}")

def check_python_version():
    """Vérifie la version de Python"""
    print("\n" + "="*50)
    print("Vérification de la version Python")
    print("="*50)
    
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor}.{version.micro} (3.8+ requis)")
        return False

def check_required_files():
    """Vérifie que tous les fichiers requis sont présents"""
    print("\n" + "="*50)
    print("Vérification des fichiers requis")
    print("="*50)
    
    required_files = [
        "client.py", "server.py", "controller.py",
        "config.py", "protocol.py", "encryptor.py",
        "client_identity_manager.py", "persistence.py",
        "process_manager.py", "file_manager.py",
        "keylogger.py", "screenshotManager.py",
        "System_info.py", "Architecture_info.py",
        "Network_info.py", "Os_info.py",
        "Privileges_info.py", "User_info.py",
        "windows_pers.py", "windows_proc.py",
        "linux_pers.py", "linux_proc.py",
        "requirements.txt", "README.md"
    ]
    
    all_present = True
    for file in required_files:
        if Path(file).exists():
            print_success(f"{file}")
        else:
            print_error(f"{file} - MANQUANT")
            all_present = False
    
    return all_present

def check_dependencies():
    """Vérifie que toutes les dépendances Python sont installées"""
    print("\n" + "="*50)
    print("Vérification des dépendances")
    print("="*50)
    
    dependencies = {
        "Flask": "flask",
        "Requests": "requests",
        "Psutil": "psutil",
        "Pynput": "pynput",
        "Pillow": "PIL"
    }
    
    if sys.platform == "win32":
        dependencies["PyWin32"] = "win32api"
    
    all_installed = True
    for name, module in dependencies.items():
        try:
            __import__(module)
            print_success(f"{name}")
        except ImportError:
            print_error(f"{name} - NON INSTALLÉ")
            all_installed = False
    
    # MSS est optionnel mais recommandé
    try:
        __import__("mss")
        print_success("MSS (optionnel)")
    except ImportError:
        print_warning("MSS - non installé (optionnel, pour screenshots)")
    
    return all_installed

def check_imports():
    """Vérifie que les imports principaux fonctionnent"""
    print("\n" + "="*50)
    print("Vérification des imports")
    print("="*50)
    
    imports_to_test = [
        ("config", "Configuration"),
        ("protocol", "Protocole"),
        ("encryptor", "Chiffrement"),
        ("client_identity_manager", "Gestion ID Client"),
        ("persistence", "Persistence Manager"),
        ("process_manager", "Process Manager"),
        ("file_manager", "File Manager"),
        ("keylogger", "Keylogger"),
        ("screenshotManager", "Screenshot Manager"),
        ("System_info", "System Info")
    ]
    
    all_ok = True
    for module, name in imports_to_test:
        try:
            __import__(module)
            print_success(f"{name} ({module})")
        except Exception as e:
            print_error(f"{name} ({module}) - ERREUR: {str(e)[:50]}")
            all_ok = False
    
    return all_ok

def main():
    print("\n" + "="*60)
    print(" "*15 + "BASIC RAT - VERIFICATION")
    print(" "*10 + "Complete Merged Edition - Check")
    print("="*60)
    
    results = []
    
    # Vérifications
    results.append(("Python Version", check_python_version()))
    results.append(("Fichiers Requis", check_required_files()))
    results.append(("Dépendances", check_dependencies()))
    results.append(("Imports Modules", check_imports()))
    
    # Résumé
    print("\n" + "="*60)
    print("RÉSUMÉ DE LA VÉRIFICATION")
    print("="*60)
    
    all_passed = True
    for check_name, result in results:
        if result:
            print_success(f"{check_name:<20} - OK")
        else:
            print_error(f"{check_name:<20} - ÉCHEC")
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print_success("TOUTES LES VÉRIFICATIONS SONT RÉUSSIES ! ✓")
        print_info("Le projet est prêt à être utilisé.")
        print_info("Utilisez launcher.bat (Windows) ou launcher.sh (Linux)")
    else:
        print_error("CERTAINES VÉRIFICATIONS ONT ÉCHOUÉ ! ✗")
        print_warning("Installez les dépendances manquantes avec:")
        print("  pip install -r requirements.txt")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
