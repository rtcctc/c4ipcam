# c4ipcam

Простая Python библиотека для передачи видео потока с камеры по сети. Позволяет легко создать сервер для трансляции видео с камеры и клиент для получения видео потока.

[![PyPI version](https://badge.fury.io/py/c4ipcam.svg)](https://badge.fury.io/py/c4ipcam)
[![Python versions](https://img.shields.io/pypi/pyversions/c4ipcam.svg)](https://pypi.org/project/c4ipcam/)
[![License](https://img.shields.io/pypi/l/c4ipcam.svg)](https://github.com/rtcctc/c4ipcam/blob/main/LICENSE)

## Особенности

- Простая клиент-серверная архитектура
- Поддержка нескольких клиентов одновременно
- Буферизация кадров для плавного воспроизведения
- Автоматическое переподключение и обработка ошибок
- Поддержка различных источников видео (веб-камера, IP-камера, видеофайлы)
- Многопоточная архитектура для оптимальной производительности

## Установка

```bash
pip install c4ipcam
```

Библиотека автоматически установит все необходимые зависимости, включая OpenCV.

## Быстрый старт

### Запуск сервера

```bash
# Запуск с параметрами по умолчанию (localhost:8000, камера 0)
c4ipcam

# Запуск с пользовательскими параметрами
c4ipcam --host 0.0.0.0 --port 9999 --camera 0
```

### Подключение клиента

```python
from c4ipcam import CameraClient
import cv2

# Создание клиента
cap = CameraClient("localhost", 9999)

# Подключение к серверу
if not cap.connect():
    print("Ошибка подключения к серверу")
    exit()

# Получение и отображение кадров
while cap.is_connected():
    ret, frame = cap.read()
    
    if not ret:
        print("Ошибка получения кадра")
        break
    
    cv2.imshow('Camera Feed', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Освобождение ресурсов
cap.disconnect()
cv2.destroyAllWindows()
```

## API Documentation

### CameraServer

Класс для создания сервера, который транслирует видео поток с камеры.

#### Конструктор

```python
CameraServer(host='0.0.0.0', port=9999, camera_id=0)
```

**Параметры:**
- `host` (str): IP-адрес для привязки сервера (по умолчанию '0.0.0.0')
- `port` (int): Порт для прослушивания (по умолчанию 9999)
- `camera_id` (int): ID камеры или путь к видеофайлу (по умолчанию 0)

#### Методы

##### `start_server()`
Запускает сервер и начинает трансляцию видео потока.

```python
server = CameraServer()
server.start_server()  # Блокирующий вызов
```

##### `cleanup()`
Освобождает ресурсы и останавливает сервер.

```python
server.cleanup()
```

### CameraClient

Класс для подключения к серверу и получения видео потока.

#### Конструктор

```python
CameraClient(server_host, server_port)
```

**Параметры:**
- `server_host` (str): IP-адрес сервера
- `server_port` (int): Порт сервера

#### Методы

##### `connect()`
Устанавливает соединение с сервером.

**Возвращает:** `bool` - True при успешном подключении, False при ошибке

```python
client = CameraClient("192.168.1.100", 9999)
if client.connect():
    print("Успешно подключен!")
else:
    print("Ошибка подключения:", client.get_connection_error())
```

##### `read(timeout=None)`
Получает следующий кадр из очереди.

**Параметры:**
- `timeout` (float, optional): Максимальное время ожидания кадра в секундах

**Возвращает:** `[bool, numpy.ndarray]` - статус и кадр

```python
ret, frame = client.read(timeout=1.0)
if ret:
    cv2.imshow('Frame', frame)
```

##### `get_latest_frame()`
Возвращает последний полученный кадр без удаления из очереди.

**Возвращает:** `numpy.ndarray` или `None`

```python
frame = client.get_latest_frame()
if frame is not None:
    cv2.imshow('Latest Frame', frame)
```

##### `is_connected()`
Проверяет статус соединения.

**Возвращает:** `bool`

```python
if client.is_connected():
    print("Соединение активно")
```

##### `get_connection_error()`
Возвращает последнюю ошибку соединения.

**Возвращает:** `str` или `None`

```python
error = client.get_connection_error()
if error:
    print(f"Ошибка: {error}")
```

##### `disconnect()`
Закрывает соединение и освобождает ресурсы.

```python
client.disconnect()
```

##### `cleanup()`
Альтернативный метод для освобождения ресурсов.

```python
client.cleanup()
```

## Примеры использования

### Запуск сервера

Основной способ запуска сервера - через консольную команду:

```bash
# Базовый запуск с веб-камерой
c4ipcam

# Настройка хоста и порта
c4ipcam --host 0.0.0.0 --port 9999

# Использование конкретной камеры
c4ipcam --camera 1

# IP-камера (RTSP URL)
c4ipcam --camera "rtsp://username:password@192.168.1.100:554/stream"
```

### Клиент с обработкой ошибок

```python
from c4ipcam import CameraClient
import cv2
import time

def main():
    client = CameraClient("localhost", 9999)
    
    # Попытка подключения с повторами
    max_retries = 5
    for attempt in range(max_retries):
        if client.connect():
            print("Успешно подключен к серверу")
            break
        else:
            print(f"Попытка {attempt + 1}/{max_retries} не удалась: {client.get_connection_error()}")
            if attempt < max_retries - 1:
                time.sleep(2)
    else:
        print("Не удалось подключиться к серверу")
        return
    
    try:
        while client.is_connected():
            ret, frame = client.read(timeout=1.0)
            
            if not ret:
                print("Таймаут или ошибка получения кадра")
                continue
            
            # Обработка кадра
            cv2.imshow('Camera Feed', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Сохранение кадра
                cv2.imwrite(f'frame_{int(time.time())}.jpg', frame)
                print("Кадр сохранен")
                
    except KeyboardInterrupt:
        print("Прерывание пользователем")
    finally:
        client.disconnect()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
```

### Программное использование сервера (опционально)

Если нужно интегрировать сервер в другое приложение:

```python
from c4ipcam import CameraServer

server = CameraServer(host='0.0.0.0', port=9999, camera_id=0)
try:
    server.start_server()
except KeyboardInterrupt:
    server.cleanup()
```

## Конфигурация

### Настройки сервера

Сервер автоматически устанавливает разрешение камеры 640x480 для оптимальной производительности. Вы можете изменить это в коде сервера:

```python
self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
```

### Настройки клиента

Клиент использует очередь кадров с максимальным размером 5 для буферизации. Это можно изменить в конструкторе:

```python
self.frame_queue = queue.Queue(maxsize=10)  # Увеличить буфер
```

## Устранение неполадок

### Сервер не запускается

1. Проверьте, что порт не занят другим приложением
2. Убедитесь, что камера доступна и не используется другим приложением
3. Проверьте права доступа к камере

### Клиент не может подключиться

1. Убедитесь, что сервер запущен и прослушивает правильный порт
2. Проверьте сетевое соединение между клиентом и сервером
3. Убедитесь, что брандмауэр не блокирует соединение

### Низкое качество или задержка видео

1. Уменьшите разрешение камеры на сервере
2. Увеличьте размер буфера на клиенте
3. Используйте более быстрое сетевое соединение

### Ошибки при получении кадров

1. Проверьте стабильность сетевого соединения
2. Увеличьте таймаут при чтении кадров
3. Добавьте логику переподключения в клиенте

## Зависимости

- Python 3.6+
- opencv-python>=4.11.0.86 (автоматически устанавливается)

Все зависимости устанавливаются автоматически при установке библиотеки через pip.

## Лицензия

Этот проект распространяется под лицензией MIT.

## Поддержка

- **GitHub**: [https://github.com/rtcctc/c4ipcam](https://github.com/rtcctc/c4ipcam)
- **PyPI**: [https://pypi.org/project/c4ipcam/](https://pypi.org/project/c4ipcam/)
- **Автор**: 4edbark (vangogprogprog@gmail.com)

При возникновении вопросов или проблем создайте issue в репозитории проекта на GitHub.