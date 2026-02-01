import hashlib
import zipfile
import tempfile
from datetime import datetime
import platform
import os
import stat
from config import CHUNK_SIZE


class FileManager:
    def __init__(self):
        self.system = platform.system()
        self.chunk_size = CHUNK_SIZE
    
    
    
    def list_directory(self, path="."):
        try:
            if not os.path.exists(path):
                return {"error": f"Path doesn't exist: {path}"}
            
            if not os.path.isdir(path):
                return {"error": f"Not a directory: {path}"}
            
            abs_path = os.path.abspath(path)
            items = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                
                try:
                    stat_info = os.stat(item_path)
                    
                    item_data = {
                        "name": item,
                        "path": item_path,
                        "is_directory": os.path.isdir(item_path),
                        "is_file": os.path.isfile(item_path),
                        "size": stat_info.st_size if os.path.isfile(item_path) else 0,
                        "permissions": self._get_permissions(item_path, stat_info),
                        "modified_time": stat_info.st_mtime,
                        "created_time": stat_info.st_ctime
                    }
                    
                    
                    
                    
                    try:
                        item_data["owner"] = self._get_owner(stat_info)
                    except: 
                        item_data['owner'] = "Unknown"
                    
                    items.append(item_data)
                
                except (PermissionError, OSError) as e:
                    items.append({
                        "name": item,
                        "path": item_path,
                        "error": str(e),
                        "is_directory": False,
                        "is_file": False
                    })
            
            
            
            return {
                "success": True,
                "current_path": abs_path,
                "parent_path": os.path.dirname(abs_path) if abs_path != os.path.dirname(abs_path) else None,
                "items": items,
                "total_items": len(items),
                "total_size": sum(item.get("size", 0) for item in items if item.get("is_file"))
                
            }
        
        except Exception as e:
            return {"error": f"failed to list directory: {e}"}
        
        
        
    def _get_permissions(self, path, stat_info):
        if self.system == "Windows":
            return self._get_windows_permissions(path)
        else:
            return self._get_linux_permissions(stat_info)
        
    
    
    def _get_linux_permissions(self, stat_info):
        permissions = []
        mode = stat_info.st_mode
        
        if stat.S_ISDIR(mode):
            permissions.append("d")
        elif stat.S_ISLNK(mode):
            permissions.append("l")
        else:
            permissions.append("-")
            
        
        #Owner
        permissions.append("r" if mode & stat.S_IRUSR else "-")
        permissions.append("w" if mode & stat.S_IWUSR else "-")
        permissions.append("x" if mode & stat.S_IXUSR else "-")
        
        #Group
        permissions.append("r" if mode & stat.S_IRGRP else "-")
        permissions.append("w" if mode & stat.S_IWGRP else "-")
        permissions.append("x" if mode & stat.S_IXGRP else "-")
        
        #Other
        permissions.append("r" if mode & stat.S_IROTH else "-")
        permissions.append("w" if mode & stat.S_IWOTH else "-")
        permissions.append("x" if mode & stat.S_IXOTH else "-")
        
        return "".join(permissions)
    
    
    
    def _get_windows_permissions(self, path):
        try:
            permissions = []
            
            if os.access(path, os.R_OK):
                permissions.append("r")
            if os.access(path, os.W_OK):
                permissions.append('W')
            if os.access(path, os.X_OK):
                permissions.append("x")
            return "-" + "".join(permissions).ljust(9, '-')
        
        
        except:
            return "----------------"
        
    
    
    def _get_owner(self, stat_info):
        try:
            if self.system == "Windows":
                import win32security
                
                sd = win32security.GetFileSecurity(stat_info, win32security.OWNER_SECURITY_INFORMATION)
                owner_sid = sd.GetSecurityDescriptorOwner()
                name, domain, _ = win32security.LookupAccountSid(None, owner_sid)
                return f"{domain}\\{name}"
            
            else:
                import pwd
                
                return pwd.getpwuid(stat_info.st_uid).pw_name
        
        
        except:
            return "Unknown"
        

    
    def download_file_chunk(self, file_path, chunk_index=0):
        try:
            if not os.path.exists(file_path):
                return {"error": f'File does not exist: {file_path}'}
            
            
            if not os.path.isfile(file_path):
                return {"error": f"Not a file: {file_path}"}
            
            
            file_size = os.path.getsize(file_path)
            total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
            
            
            with open(file_path, "rb") as f:
                f.seek(chunk_index * self.chunk_size)
                chunk_data = f.read(self.chunk_size)
                
            
            
            is_last = (chunk_index >= total_chunks - 1)
            
            
            return {
                "success": True,
                "file_path": file_path,
                "file_size": file_size,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "chunk_size": len(chunk_data),
                "data": chunk_data.hex() if chunk_data else "",
                "is_last": is_last,
                "progress": f"{(chunk_index + 1) / total_chunks * 100:.1f}%" if total_chunks > 0 else "100%"
            }
        
        
        except Exception as e:
            return {"error": f"failed to download file chunk: {e}"}
        
    
    
    
    def upload_file_chunk(self, file_path, chunk_data_hex, chunk_index=0, is_last=False):
        try:
            chunk_data = bytes.fromhex(chunk_data_hex) if chunk_data_hex else b""
            
            mode = "ab" if chunk_index > 0 else "wb"
            with open(file_path, mode) as f:
                f.write(chunk_data)
                
            
            if is_last:
                file_size = os.path.getsize(file_path)
                return {
                    "success": True,
                    "file_path": file_path,
                    "file_size": file_size,
                    "message": f"File upload completed: {file_path} ({file_size} bytes)"
                }
            
            
            else:
                return {
                    "success": True,
                    "chunk_index": chunk_index,
                    "message": f"Chunk {chunk_index} received"
                }
        
        except Exception as e:
            return {"error": f"failed to upload file chunk: {e}"}
        
        
        
    
    
    
    def search_files(self, root_path, pattern, max_results=50):
        try:
            import fnmatch
            
            
            results = []
            for root, dirs, files in os.walk(root_path):
                for file in files:
                    if fnmatch.fnmatch(file, pattern):
                        file_path = os.path.join(root, file)
                        
                        try:
                            stat_info = os.stat(file_path)
                            results.append({
                                "path": file_path,
                                "name": file,
                                "size": stat_info.st_size,
                                "modified_time": stat_info.st_mtime,
                                "directory": root
                            })
                            
                            if len(results) >= max_results:
                                return {
                                    "success": True,
                                    "results": results,
                                    "total_found": len(results),
                                    "search_complete": False
                                }
                        
                        except (PermissionError, OSError):
                            continue #Skip those which can be accessed
            
            return {
                "success": True,
                "results": results,
                "total_found": len(results),
                "search_complete": True
            }
        
        except Exception as e:
            return {"error": f"file search failed: {e}"}
    
    
    def compress_files(self, files, output_path):
        try:
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files:
                    if os.path.isdir(file_path):
                        for root, dirs, files_in_dir in os.walk(file_path):
                            for file in files_in_dir:
                                full_path = os.path.join(root, file)
                                arcname = os.path.relpath(full_path, os.path.dirname(file_path))
                                zipf.write(full_path, arcname)
                    
                    else:
                        zipf.write(file_path, os.path.basename(file_path))
            
            
            output_size = os.path.getsize(output_path)
            return {
                "success": True,
                "output_path": output_path,
                "output_size": output_size,
                "compressed_files": len(files),
                "message": f"Compressed {len(files)} items to {output_path} ({output_size} bytes)"
            }
        
        except Exception as e:
            return {"error": f"Compression failed: {e}"}

  
    
    def delete_file(self, file_path):
        try:
            if not os.path.exists(file_path):
                return {"error": f"path doesn't exist: {file_path}"}
            
            if os.path.isdir(file_path):
                import shutil
                
                shutil.rmtree(file_path)
                message = f"directory deleted! {file_path}"
                
            else:
                os.remove(file_path)
                message = f"file deleted: {file_path}"
                

            return {"success": True, "message": message}
        
        
        except Exception as e:
            return {"error": f"Delete failed: {e}"}
        
        

    def create_directory(self, dir_path):
        try:
            print(f"[DEBUG CLIENT] Received dir_path: '{dir_path}'")
            print(f"[DEBUG CLIENT] Path length: {len(dir_path)}")
            print(f"[DEBUG CLIENT] Path as list: {list(dir_path)}")
            
            
            
            #cleaning
            if ':/' in dir_path or ':\\' in dir_path:
                parts = dir_path.replace('/', '\\').split('\\')
                clean_parts = []
                found_drive = False
                
                for part in parts:
                    if ':' in part:
                        if found_drive:


                            clean_parts = []
                        found_drive = True
                        clean_parts.append(part)
                    elif part:
                        clean_parts.append(part)
                
                dir_path = '\\'.join(clean_parts)
        
            print(f"[DEBUG CLIENT] After cleaning: '{dir_path}'")
            
            
            
            
            
            #normalize the path
            dir_path = os.path.normpath(dir_path)
            print(f"[DEBUG CLIENT] After normalization: '{dir_path}'")
            



            os.makedirs(dir_path, exist_ok=True)
            return {"success": True, "message": f"Directory created: {dir_path}"}
        
        
        except Exception as e:
            print(f"[DEBUG CLIENT] Create directory error: {e}")
            print(f"[DEBUG CLIENT] Error type: {type(e)}")
            return {"error": f"Create directory failed: {e}"}
        
        
        
        
    
