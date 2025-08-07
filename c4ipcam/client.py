import socket
import pickle
import struct
import threading
import queue
import time
import cv2
import numpy as np
import hashlib

class CameraClient:
    def __init__(self, server_host, server_port, password="", compression_quality=85):
        self.server_host = server_host
        self.server_port = server_port
        self.password = password
        self.compression_quality = compression_quality
        self.client_socket = None
        self.running = False
        self.connected = False
        self.authenticated = False
        self.frame_queue = queue.Queue(maxsize=5) 
        self.latest_frame = None
        self.receive_thread = None
        self.connection_error = None
        
    def _send_auth(self):
        """Отправка данных аутентификации серверу"""
        try:
            password_hash = hashlib.sha256(self.password.encode()).hexdigest()
            auth_data = pickle.dumps({"password_hash": password_hash})
            
            auth_size = struct.pack("!I", len(auth_data))
            self.client_socket.sendall(auth_size + auth_data)
            
            response_size_data = b""
            while len(response_size_data) < 4:
                packet = self.client_socket.recv(4 - len(response_size_data))
                if not packet:
                    return False
                response_size_data += packet
            
            response_size = struct.unpack("!I", response_size_data)[0]
            response_data = b""
            while len(response_data) < response_size:
                packet = self.client_socket.recv(response_size - len(response_data))
                if not packet:
                    return False
                response_data += packet
            
            response = pickle.loads(response_data)
            return response.get("authenticated", False)
            
        except Exception as e:
            self.connection_error = f"Ошибка аутентификации: {str(e)}"
            return False
        
    def connect(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_host, self.server_port))
            self.connected = True
            self.connection_error = None
            
            if not self._send_auth():
                self.connection_error = "Неверный пароль или ошибка аутентификации"
                self.disconnect()
                return False
            
            self.authenticated = True
            self.running = True
            
            self.receive_thread = threading.Thread(target=self._receive_frames)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            return True
            
        except socket.error as e:
            self.connection_error = str(e)
            self.connected = False
            self.authenticated = False
            return False
    
    def _decompress_frame(self, compressed_data):
        """Распаковка сжатого кадра"""
        try:
            nparr = np.frombuffer(compressed_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return frame
        except Exception:
            return None
    
    def _receive_frames(self):
        try:
            data = b""
            payload_size = struct.calcsize("!I")
            
            while self.running and self.connected and self.authenticated:
                while len(data) < payload_size:
                    packet = self.client_socket.recv(4096)
                    if not packet:
                        self.connected = False
                        return
                    data += packet
                
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("!I", packed_msg_size)[0]
                
                while len(data) < msg_size:
                    packet = self.client_socket.recv(4096)
                    if not packet:
                        self.connected = False
                        return
                    data += packet
                
                frame_data = data[:msg_size]
                data = data[msg_size:]
                
                try:
                    frame = self._decompress_frame(frame_data)
                    if frame is None:
                        frame = pickle.loads(frame_data)
                    
                    self.latest_frame = frame
                    
                    try:
                        self.frame_queue.put_nowait(frame)
                    except queue.Full:
                        try:
                            self.frame_queue.get_nowait()
                            self.frame_queue.put_nowait(frame)
                        except queue.Empty:
                            pass
                            
                except (pickle.UnpicklingError, Exception):
                    continue
                    
        except socket.error:
            self.connected = False
            self.authenticated = False
        except Exception:
            self.connected = False
            self.authenticated = False
    
    def read(self, timeout=None):
        if not self.connected or not self.authenticated:
            return [False, None]
            
        try:
            return [True, self.frame_queue.get(timeout=timeout)]
        except queue.Empty:
            return [False, None]
    
    def get_latest_frame(self):
        return self.latest_frame
    
    def is_connected(self):
        return self.connected and self.authenticated
    
    def get_connection_error(self):
        return self.connection_error
    
    def disconnect(self):
        self.running = False
        self.connected = False
        self.authenticated = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=1)
    
    def cleanup(self):
        self.disconnect()