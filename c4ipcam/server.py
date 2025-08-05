import cv2
import socket
import pickle
import struct
import threading
import select
import signal
import sys

class CameraServer:
    def __init__(self, host='0.0.0.0', port=9999, camera_id=0):
        self.host = host
        self.port = port
        self.server_socket = None
        self.camera_ip = camera_id
        self.camera = None
        self.clients = []
        self.running = False
        self.client_threads = []
        
    def signal_handler(self, signum, frame):
        """Обработчик сигнала для корректного завершения"""
        print("\nПолучен сигнал завершения. Останавливаем сервер...")
        self.stop_server()
        
    def start_server(self):
        # Устанавливаем обработчик сигнала
        signal.signal(signal.SIGINT, self.signal_handler)
        
        self.camera = cv2.VideoCapture(self.camera_ip)
        if not self.camera.isOpened():
            print("Ошибка: Не удалось открыть камеру")
            return
        
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Устанавливаем таймаут для accept()
        self.server_socket.settimeout(1.0)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            print(f"Сервер запущен на {self.host}:{self.port}")
            print("Ожидание подключений... (Нажмите Ctrl+C для остановки)")
            
            while self.running:
                try:
                    # Используем select для неблокирующего ожидания
                    ready, _, _ = select.select([self.server_socket], [], [], 1.0)
                    
                    if ready:
                        client_socket, address = self.server_socket.accept()
                        if not self.running:  # Проверяем состояние после accept
                            client_socket.close()
                            break
                            
                        print(f"Подключен клиент: {address}")
                        
                        client_thread = threading.Thread(
                            target=self.handle_client, 
                            args=(client_socket, address)
                        )
                        client_thread.daemon = True
                        client_thread.start()
                        self.client_threads.append(client_thread)
                        
                except socket.error as e:
                    if self.running:
                        print(f"Ошибка при принятии подключения: {e}")
                    break
                    
        except Exception as e:
            print(f"Ошибка запуска сервера: {e}")
        finally:
            self.cleanup()
    
    def stop_server(self):
        """Корректная остановка сервера"""
        self.running = False
        
    def handle_client(self, client_socket, address):
        try:
            # Устанавливаем таймаут для клиентского сокета
            client_socket.settimeout(0.5)
            
            while self.running:
                ret, frame = self.camera.read()
                if not ret:
                    print("Ошибка захвата кадра")
                    break
                
                data = pickle.dumps(frame)
                message_size = struct.pack("L", len(data))
                
                try:
                    client_socket.sendall(message_size + data)
                except socket.timeout:
                    # Проверяем состояние и продолжаем
                    continue
                except socket.error:
                    print(f"Клиент {address} отключился")
                    break
                    
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
        
        # Ждем завершения потоков клиентов
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

def run_server(address, port):
    server = CameraServer(host=address, port=port)
    
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()
    
    print(f"Запуск сервера на {args.host}:{args.port}")
    run_server(args.host, args.port)