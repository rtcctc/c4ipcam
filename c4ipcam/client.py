import socket
import pickle
import struct
import threading
import queue
import time

class CameraClient:
    def __init__(self, server_host, server_port):
        self.server_host = server_host
        self.server_port = server_port
        self.client_socket = None
        self.running = False
        self.connected = False
        self.frame_queue = queue.Queue(maxsize=5) 
        self.latest_frame = None
        self.receive_thread = None
        self.connection_error = None
        
    def connect(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_host, self.server_port))
            self.connected = True
            self.running = True
            self.connection_error = None
            
            self.receive_thread = threading.Thread(target=self._receive_frames)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            return True
            
        except socket.error as e:
            self.connection_error = str(e)
            self.connected = False
            return False
    
    def _receive_frames(self):
        try:
            data = b""
            payload_size = struct.calcsize("L")
            
            while self.running and self.connected:
                while len(data) < payload_size:
                    packet = self.client_socket.recv(4096)
                    if not packet:
                        self.connected = False
                        return
                    data += packet
                
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("L", packed_msg_size)[0]
                
                while len(data) < msg_size:
                    packet = self.client_socket.recv(4096)
                    if not packet:
                        self.connected = False
                        return
                    data += packet
                
                frame_data = data[:msg_size]
                data = data[msg_size:]
                
                try:
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
                            
                except pickle.UnpicklingError:
                    continue
                    
        except socket.error:
            self.connected = False
        except Exception:
            self.connected = False
    
    def read(self, timeout=None):
        if not self.connected:
            return [False, None]
            
        try:
            return [True, self.frame_queue.get(timeout=timeout)]
        except queue.Empty:
            return [False, None]
    
    def get_latest_frame(self):
        return self.latest_frame
    
    def is_connected(self):
        return self.connected
    
    def get_connection_error(self):
        return self.connection_error
    
    def disconnect(self):
        self.running = False
        self.connected = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=1)
    
    def cleanup(self):
        self.disconnect()