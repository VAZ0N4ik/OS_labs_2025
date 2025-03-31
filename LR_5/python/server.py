#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import threading
import time
import logging
from datetime import datetime
import sys
import os

# Настройка логирования
def setup_logger(name):
    # Создание директории для логов, если её нет
    if not os.path.exists('logs'):
        os.makedirs('logs')

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Обработчик для вывода в файл
    file_handler = logging.FileHandler(f'logs/{name}.log')
    file_handler.setLevel(logging.INFO)

    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Формат логов
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Глобальные переменные
logger = setup_logger('server')
client_counter = 0
active_clients = {}

# Класс для семафора (в Python нет прямого аналога Win32 API семафора)
class Semaphore:
    def __init__(self, value=1):
        self.sem = threading.Semaphore(value)
        self.value = value

    def acquire(self):
        return self.sem.acquire()

    def release(self):
        return self.sem.release()

    def get_value(self):
        # Приблизительное значение, так как Python не предоставляет метода для получения текущего значения
        return self.value

# Создаем семафор с максимальным значением 3
client_semaphore = Semaphore(1)

# Функция для удаления дубликатов из списка
def remove_duplicates(numbers):
    return list(dict.fromkeys(numbers))  # Сохраняет порядок, в отличие от set

# Обработчик подключения клиента
def handle_client(client_socket, addr):
    global client_counter

    # Ожидание доступа к семафору
    logger.info(f"Client {addr} waiting for server access")
    client_semaphore.acquire()

    # Получили доступ
    client_counter += 1
    client_id = client_counter
    active_clients[client_id] = addr

    logger.info(f"Client #{client_id} from {addr} gained access to the server")

    try:
        # Отправка ID клиенту
        client_socket.send(str(client_id).encode('utf-8'))

        # Получение данных от клиента
        data = client_socket.recv(4096).decode('utf-8')

        if data:
            logger.info(f"Received data from client #{client_id}: {data}")

            # Парсинг данных
            try:
                numbers = [float(num) for num in data.strip().split()]

                # Обработка данных - удаление дубликатов
                unique_numbers = remove_duplicates(numbers)

                # Формирование результата
                result = f"Original array ({len(numbers)} elements): {' '.join(map(str, numbers))}\n"
                result += f"Array without duplicates ({len(unique_numbers)} elements): {' '.join(map(str, unique_numbers))}"

                logger.info(f"Sending result to client #{client_id}")

                # Отправка результата клиенту
                client_socket.send(result.encode('utf-8'))
            except ValueError:
                error_msg = "Error: Invalid data format. Expected space-separated numbers."
                client_socket.send(error_msg.encode('utf-8'))
                logger.error(f"Client #{client_id} sent invalid data format")
    except Exception as e:
        logger.error(f"Error handling client #{client_id}: {e}")
    finally:
        # Закрытие соединения
        client_socket.close()
        logger.info(f"Connection with client #{client_id} closed")

        # Освобождение семафора
        client_semaphore.release()
        del active_clients[client_id]

def main():
    try:
        # Создание сокета
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Привязка сокета к адресу
        host = '127.0.0.1'
        port = 12345
        server_socket.bind((host, port))

        # Начало прослушивания
        server_socket.listen(5)
        logger.info(f"Server started on {host}:{port}")
        logger.info("Server waiting for connections...")

        # Обработка статистики в отдельном потоке
        def print_stats():
            while True:
                time.sleep(10)  # Обновление каждые 10 секунд
                logger.info(f"Active clients: {len(active_clients)}, Total clients served: {client_counter}")

        stats_thread = threading.Thread(target=print_stats)
        stats_thread.daemon = True
        stats_thread.start()

        # Бесконечный цикл обработки подключений
        while True:
            # Принятие подключения
            client_socket, addr = server_socket.accept()
            logger.info(f"New connection from {addr[0]}:{addr[1]}")

            # Создание потока для обработки клиента
            client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            client_thread.daemon = True
            client_thread.start()

    except KeyboardInterrupt:
        logger.info("Server is shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        # Закрытие сервера
        if 'server_socket' in locals():
            server_socket.close()
        logger.info("Server stopped")

if __name__ == "__main__":
    main()