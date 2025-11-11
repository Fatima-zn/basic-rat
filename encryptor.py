import base64
import json


class Encryptor:
    def __init__(self, key):
        self.key = key
    

    def encrypt(self, data):
        try:
            json_string = self._xor_encrypt(json.dumps(data), self.key)
            encrypted = base64.b64encode(json_string.encode()).decode()

            return encrypted
        
        except Exception as e:
            print(f"[-] Encryptions error: {e}")
            return None
    

    def decrypt(self, encrypted_data):
        try:
            json_string = self._xor_decrypt(base64.b64decode(encrypted_data).decode(), self.key)
            data = json.loads(json_string)

            return data
        
        except Exception as e:
            print(f"[-] Decryption error: {e}")

            return None
    

    def _xor_encrypt(self, text, key):
        encrypted_chars = []

        for i, char in enumerate(text):
            key_char = key[i % len(key)]
            encrypted_char = chr(ord(char) ^ ord(key_char))
            encrypted_chars.append(encrypted_char)

        return ''.join(encrypted_chars)


    def _xor_decrypt(self, text, key):
        return self._xor_encrypt(text, key)