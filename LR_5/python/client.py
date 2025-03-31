#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import logging
import sys
import os
import time
from datetime import datetime

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

# Создание логгера
logger = setup_logger('client')

def main():
    # Инициализация
    client_id = -1
    logger.info("Client started")

    try:
        # Создание сокета
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Подключение к серверу
        host = '127.0.0.1'
        port = 12345
        logger.info(f"Attempting to connect to server at {host}:{port}...")

        client_socket.connect((host, port))
        logger.info("Connection to server established")

        # Получение ID от сервера
        id_data = client_socket.recv(16).decode('utf-8')
        client_id = int(id_data)
        logger.info(f"[Client #{client_id}] Received ID from server: {client_id}")

        # Ввод массива чисел
        print("\nВведите элементы массива (числа, разделенные пробелами):")
        print("Для завершения ввода нажмите Enter > ", end="")
        user_input = input()

        logger.info(f"[Client #{client_id}] Array entered: {user_input}")

        # Проверка корректности ввода
        try:
            numbers = [float(num) for num in user_input.strip().split()]
            if not numbers:
                raise ValueError("Empty array")
        except ValueError as e:
            logger.error(f"[Client #{client_id}] Error: {str(e)}")
            print("Ошибка: введен пустой массив или некорректные данные")
            return 1

        # Отправка данных на сервер
        logger.info(f"[Client #{client_id}] Sending data to server")
        client_socket.send(user_input.encode('utf-8'))

        # Получение ответа от сервера
        response = client_socket.recv(4096).decode('utf-8')

        if response:
            logger.info(f"[Client #{client_id}] Response received from server")
            print("\nРезультат обработки на сервере:")
            print(response)
        else:
            logger.error(f"[Client #{client_id}] Error receiving response from server")

    except ConnectionRefusedError:
        logger.error("Error connecting to server: Connection refused")
        print("Ошибка подключения к серверу: соединение отклонено")
        return 1
    except socket.error as e:
        logger.error(f"Socket error: {e}")
        print(f"Ошибка сокета: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Непредвиденная ошибка: {e}")
        return 1
    finally:
        # Закрытие сокета
        if 'client_socket' in locals():
            client_socket.close()

        # Завершение
        if client_id != -1:
            logger.info(f"[Client #{client_id}] Client terminating")
        else:
            logger.info("Client terminating")

        print("\nНажмите Enter для выхода...")
        input()

    return 0

if __name__ == "__main__":
    sys.exit(main())