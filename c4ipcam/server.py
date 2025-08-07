import cv2
import socket
import pickle
import struct
import threading
import select
import signal
import sys
import time
import hashlib
import numpy as np

class CameraServer:
    def __init__(self, host='0.0.0.0', port=9999, camera_id=0, password="", 
                 width=640, height=480, compression_quality=85, fps=30):
        self.host = host
        self.port = port
        self.server_socket = None
        self.camera_ip = camera_id
        self.camera = None
        self.password = password
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()
        self.width = width
        self.height = height
        self.compression_quality = compression_quality
        self.fps = fps
        self.frame_delay = 1.0 / fps if fps > 0 else 0.033
        self.clients = []
        self.running = False
        self.client_threads = []
        self.shutdown_event = threading.Event()
        
    def signal_handler(self, signum, frame):
        """Обработчик сигнала для корректного завершения"""
        print("\nПолучен сигнал завершения. Останавливаем сервер...")
        self.stop_server()
    
    def _authenticate_client(self, client_socket):
        """Аутентификация клиента"""
        try:
            auth_size_data = b""
            while len(auth_size_data) < 4:
                packet = client_socket.recv(4 - len(auth_size_data))
                if not packet:
                    return False
                auth_size_data += packet
            
            auth_size = struct.unpack("L", auth_size_data)[0]
            auth_data = b""
            while len(auth_data) < auth_size:
                packet = client_socket.recv(auth_size - len(auth_data))
                if not packet:
                    return False
                auth_data += packet
            
            auth_info = pickle.loads(auth_data)
            client_password_hash = auth_info.get("password_hash", "")
            
            authenticated = (client_password_hash == self.password_hash)
            
            response = {"authenticated": authenticated}
            response_data = pickle.dumps(response)
            response_size = struct.pack("L", len(response_data))
            client_socket.sendall(response_size + response_data)
            
            return authenticated
            
        except Exception as e:
            print(f"Ошибка аутентификации: {e}")
            return False
    
    def _compress_frame(self, frame):
        """Сжатие кадра для передачи"""
        try:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.compression_quality]
            result, compressed_data = cv2.imencode('.jpg', frame, encode_param)
            if result:
                return compressed_data.tobytes()
            return None
        except Exception:
            return None
        
    def start_server(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        
        self.camera = cv2.VideoCapture(self.camera_ip)
        if not self.camera.isOpened():
            print("Ошибка: Не удалось открыть камеру")
            return
        
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        self.camera.set(cv2.CAP_PROP_FPS, self.fps)
        
        actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.camera.get(cv2.CAP_PROP_FPS)
        
        print(f"Настройки камеры:")
        print(f"  Разрешение: {actual_width}x{actual_height} (запрошено: {self.width}x{self.height})")
        print(f"  FPS: {actual_fps:.1f} (запрошено: {self.fps})")
        print(f"  Качество сжатия: {self.compression_quality}%")
        print(f"  Аутентификация: {'Включена' if self.password else 'Отключена'}")
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.settimeout(1.0)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            print(f"Сервер запущен на {self.host}:{self.port}")
            print("Ожидание подключений... (Нажмите Ctrl+C для остановки)")
            
            while self.running and not self.shutdown_event.is_set():
                try:
                    client_socket, address = self.server_socket.accept()
                    if not self.running or self.shutdown_event.is_set():
                        client_socket.close()
                        break
                        
                    print(f"Попытка подключения от: {address}")
                    
                    if not self._authenticate_client(client_socket):
                        print(f"Аутентификация не пройдена для {address}")
                        client_socket.close()
                        continue
                    
                    print(f"Клиент аутентифицирован: {address}")
                    
                    client_socket.settimeout(None)
                    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
                    
                    client_thread = threading.Thread(
                        target=self.handle_client, 
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    self.client_threads.append(client_thread)
                    
                except socket.timeout:
                    continue
                except socket.error as e:
                    if self.running and not self.shutdown_event.is_set():
                        print(f"Ошибка при принятии подключения: {e}")
                    break
                    
        except Exception as e:
            print(f"Ошибка запуска сервера: {e}")
        finally:
            self.cleanup()
    
    def stop_server(self):
        """Корректная остановка сервера"""
        self.running = False
        self.shutdown_event.set()
        
    def handle_client(self, client_socket, address):
        try:            
            while self.running and not self.shutdown_event.is_set():
                ret, frame = self.camera.read()
                if not ret:
                    print("Ошибка захвата кадра")
                    break
                
                if not self.running or self.shutdown_event.is_set():
                    break
                
                try:
                    compressed_frame = self._compress_frame(frame)
                    if compressed_frame is None:
                        data = pickle.dumps(frame)
                    else:
                        data = compressed_frame
                    
                    message_size = struct.pack("L", len(data))
                    client_socket.sendall(message_size + data)
                    
                except socket.error as e:
                    print(f"Клиент {address} отключился: {e}")
                    break
                except BrokenPipeError:
                    print(f"Клиент {address} разорвал соединение")
                    break
                
                time.sleep(self.frame_delay)
                    
        except Exception as e:
            print(f"Ошибка при обработке клиента {address}: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            print(f"Соединение с {address} закрыто")
    
    def cleanup(self):
        print("Очистка ресурсов...")
        self.running = False
        
        for thread in self.client_threads:
            if thread.is_alive():
                thread.join(timeout=2)
        
        if self.camera:
            self.camera.release()
            
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
                
        print("Сервер остановлен")

def run_server(address, port, camera_id=0, password="", width=640, height=480, 
               compression_quality=85, fps=30):
    server = CameraServer(
        host=address, 
        port=port, 
        camera_id=camera_id,
        password=password,
        width=width,
        height=height,
        compression_quality=compression_quality,
        fps=fps
    )
    
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\nПолучен KeyboardInterrupt...")
        server.stop_server()
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        server.stop_server()

import argparse

def run_server_cli():
    parser = argparse.ArgumentParser(description='Camera streaming server')
    parser.add_argument("--port", type=int, default=9999, help="Server port")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--camera", type=int, default=0, help="Camera ID")
    parser.add_argument("--password", default="", help="Authentication password")
    parser.add_argument("--width", type=int, default=640, help="Frame width")
    parser.add_argument("--height", type=int, default=480, help="Frame height")
    parser.add_argument("--quality", type=int, default=85, 
                       help="JPEG compression quality (1-100)")
    parser.add_argument("--fps", type=int, default=30, help="Target FPS")
    
    args = parser.parse_args()
    
    print(f"Запуск сервера {args.host}:{args.port}")
    if args.password:
        print(f"Authentication enabled")
    print(f"Разрешение: {args.width}x{args.height}")
    print(f"Качество: {args.quality}%, FPS: {args.fps}")
    
    run_server(
        args.host, 
        args.port, 
        args.camera, 
        args.password,
        args.width,
        args.height,
        args.quality,
        args.fps
    )