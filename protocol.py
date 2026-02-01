import time

class Protocol:
    #Types
    MSG_REGISTER = "register"
    MSG_HEARTBEAT = "heartbeat" 
    MSG_COMMAND = "command"
    MSG_RESULT = "result"
    MSG_ERROR = "error"
    MSG_GET_COMMANDS = "get_commands"
    MSG_COMMAND_RESULT = "command_result"
    

    @staticmethod
    def create_register_message(client_id, system_info):
        return {
            "type": Protocol.MSG_REGISTER,
            "client_id": client_id,
            "system_info": system_info,
            "timestamp": time.time()
        }
    

    @staticmethod
    def create_heartbeat_message(client_id, extra_data):
        return {
            "type": Protocol.MSG_HEARTBEAT,
            "client_id": client_id,
            "additional_data": extra_data,
            "timestamp": time.time()
        }
    

    @staticmethod
    def create_command_message(client_id, command, command_id):
        return {
            "type": Protocol.MSG_COMMAND,
            "client_id": client_id,
            "command": command,
            "command_id": command_id,
            "timestamp": time.time()
        }
    

    @staticmethod
    def create_result_message(client_id, command_id, output):
        return {
            "type": Protocol.MSG_RESULT,
            "client_id": client_id,
            "command_id": command_id,
            "output": output,
            "timestamp": time.time()
        }

    
    @staticmethod
    def create_error_message(message, details=None):
        return {
            "type": Protocol.MSG_ERROR,
            "message": message,
            "details": details,
            "timestamp": time.time()
        }
    
    
    @staticmethod
    def create_success_message(message=None):
        return {
            "type": "success",
            "message": message or "Operation completed successfully",
            "timestamp": time.time()
        }
    
    
    
    @staticmethod
    def create_process_message(client_id, action, data=None):
        return {
            "type": "process_command",
            "client_id": client_id,
            "action": action,
            "data": data or {},
            "timestamp": time.time()
        }
    
    
    @staticmethod
    def create_get_commands_message(client_id):
        return {
            "type": Protocol.MSG_GET_COMMANDS,
            "client_id": client_id,
            "timestamp": time.time()
        }
        
    @staticmethod
    def create_command_result_message(client_id, command_id, result):
        return {
            "type": Protocol.MSG_COMMAND_RESULT,
            "client_id": client_id,
            "command_id": command_id,
            "result": result,
            "timestamp": time.time()
        }
