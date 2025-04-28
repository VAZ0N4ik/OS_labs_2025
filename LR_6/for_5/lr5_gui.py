#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import socket
import threading
import time
import logging
from datetime import datetime
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QPushButton, QTextEdit,
                            QLineEdit, QSpinBox, QListWidget, QTabWidget,
                            QFileDialog, QMessageBox, QGroupBox, QFormLayout,
                            QSplitter, QDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QTextCursor, QFont, QIcon

# Настройка логирования
def setup_logger(name):
    # Создание директории для логов, если её нет
    if not os.path.exists('../for_4/logs'):
        os.makedirs('../for_4/logs')

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Обработчик для вывода в файл
    log_filename = f'logs/{name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.INFO)

    # Формат логов
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger, log_filename

# Глобальные переменные
server_logger, server_log_file = setup_logger('server')
client_counter = 0
active_clients = {}
client_data = {}  # Хранение данных от клиентов
client_results = {}  # Результаты обработки
statistics_file = "../for_4/server_stats.json"

# Класс для семафора с поддержкой событий
class EventSemaphore:
    def __init__(self, value=1):
        self.sem = threading.Semaphore(value)
        self.value = value
        self.lock = threading.Lock()
        self.waiting_clients = 0
        self.shutdown_event = threading.Event()

    def acquire(self, timeout=None):
        with self.lock:
            self.waiting_clients += 1

        try:
            # Ожидание получения семафора или события завершения
            acquired = False
            if timeout is not None:
                end_time = time.time() + timeout
                while time.time() < end_time and not self.shutdown_event.is_set():
                    if self.sem.acquire(blocking=False):
                        acquired = True
                        break
                    time.sleep(0.1)
            else:
                while not self.shutdown_event.is_set():
                    if self.sem.acquire(blocking=False):
                        acquired = True
                        break
                    time.sleep(0.1)

            return acquired and not self.shutdown_event.is_set()

        finally:
            with self.lock:
                self.waiting_clients -= 1

    def release(self):
        return self.sem.release()

    def get_waiting_count(self):
        with self.lock:
            return self.waiting_clients

    def shutdown(self):
        self.shutdown_event.set()

    def is_shutdown(self):
        return self.shutdown_event.is_set()

# Создаем семафор с максимальным значением 3
client_semaphore = EventSemaphore(3)

# Функция для удаления дубликатов из списка
def remove_duplicates(numbers):
    return list(dict.fromkeys(numbers))  # Сохраняет порядок, в отличие от set

# Сохранение статистики в файл
def save_statistics():
    stats = {
        "total_clients_served": client_counter,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "client_data": {str(cid): {"original": data, "processed": client_results.get(cid, [])}
                        for cid, data in client_data.items()}
    }

    with open(statistics_file, 'w') as f:
        json.dump(stats, f, indent=4)

    server_logger.info(f"Statistics saved to {statistics_file}")
    return stats

# Класс для серверного потока
class ServerThread(QThread):
    # Сигналы для обновления GUI
    update_log = pyqtSignal(str)
    update_clients = pyqtSignal(dict)
    update_stats = pyqtSignal(dict)
    server_started = pyqtSignal(bool)

    def __init__(self, host='127.0.0.1', port=12345, max_clients=3):
        super().__init__()
        self.host = host
        self.port = port
        self.max_clients = max_clients
        self.running = False
        self.server_socket = None

    def log(self, message):
        server_logger.info(message)
        self.update_log.emit(message)

    def run(self):
        global client_counter, client_semaphore

        # Пересоздаем семафор с нужным значением
        client_semaphore = EventSemaphore(self.max_clients)

        try:
            # Создание сокета
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Установка таймаута
            self.server_socket.settimeout(1.0)

            # Привязка сокета к адресу
            self.server_socket.bind((self.host, self.port))

            # Начало прослушивания
            self.server_socket.listen(5)
            self.log(f"Server started on {self.host}:{self.port}")
            self.log("Server waiting for connections...")

            self.running = True
            self.server_started.emit(True)

            # Цикл обработки подключений
            while self.running:
                try:
                    # Принятие подключения с таймаутом
                    client_socket, addr = self.server_socket.accept()
                    self.log(f"New connection from {addr[0]}:{addr[1]}")

                    # Создание потока для обработки клиента
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                except socket.timeout:
                    # Таймаут нужен для регулярной проверки running
                    continue
                except Exception as e:
                    if self.running:  # Выводим ошибку только если сервер должен работать
                        self.log(f"Error accepting connection: {e}")

                # Обновление статистики и списка клиентов
                if self.running:
                    stats = {"active_clients": len(active_clients),
                             "total_clients": client_counter,
                             "waiting_clients": client_semaphore.get_waiting_count()}
                    self.update_stats.emit(stats)
                    self.update_clients.emit(active_clients.copy())

        except Exception as e:
            self.log(f"Server error: {e}")
        finally:
            # Завершение работы сервера
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None

            self.log("Server stopped")
            self.server_started.emit(False)
            self.running = False

    def handle_client(self, client_socket, addr):
        global client_counter

        # Ожидание доступа к семафору
        self.log(f"Client {addr} waiting for server access")

        if not client_semaphore.acquire():
            self.log(f"Client {addr} connection rejected due to server shutdown")
            client_socket.close()
            return

        # Получили доступ
        client_counter += 1
        client_id = client_counter
        active_clients[client_id] = addr

        self.update_clients.emit(active_clients.copy())
        self.log(f"Client #{client_id} from {addr} gained access to the server")

        try:
            # Отправка ID клиенту
            client_socket.send(str(client_id).encode('utf-8'))

            # Получение данных от клиента
            data = client_socket.recv(4096).decode('utf-8')

            if data:
                self.log(f"Received data from client #{client_id}: {data}")

                # Парсинг данных
                try:
                    numbers = [float(num) for num in data.strip().split()]

                    # Сохранение исходных данных
                    client_data[client_id] = numbers

                    # Обработка данных - удаление дубликатов
                    unique_numbers = remove_duplicates(numbers)
                    client_results[client_id] = unique_numbers

                    # Формирование результата
                    result = f"Original array ({len(numbers)} elements): {' '.join(map(str, numbers))}\n"
                    result += f"Array without duplicates ({len(unique_numbers)} elements): {' '.join(map(str, unique_numbers))}"

                    self.log(f"Sending result to client #{client_id}")

                    # Отправка результата клиенту
                    client_socket.send(result.encode('utf-8'))
                except ValueError:
                    error_msg = "Error: Invalid data format. Expected space-separated numbers."
                    client_socket.send(error_msg.encode('utf-8'))
                    self.log(f"Client #{client_id} sent invalid data format")
        except Exception as e:
            self.log(f"Error handling client #{client_id}: {e}")
        finally:
            # Закрытие соединения
            client_socket.close()
            self.log(f"Connection with client #{client_id} closed")

            # Освобождение семафора
            client_semaphore.release()
            if client_id in active_clients:
                del active_clients[client_id]
                self.update_clients.emit(active_clients.copy())

    def stop(self):
        self.log("Shutting down server...")
        self.running = False
        client_semaphore.shutdown()

        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        self.wait(2000)  # Ждем до 2 секунд

# Класс для клиентского потока
class ClientThread(QThread):
    # Сигналы для обновления GUI
    update_log = pyqtSignal(str)
    update_status = pyqtSignal(str)
    update_result = pyqtSignal(str)
    connection_status = pyqtSignal(bool)
    client_id_received = pyqtSignal(int)

    def __init__(self, host='127.0.0.1', port=12345, client_logger=None):
        super().__init__()
        self.host = host
        self.port = port
        self.client_socket = None
        self.client_id = -1
        self.connected = False
        self.numbers = []
        self.logger = client_logger

    def log(self, message):
        if self.logger:
            self.logger.info(message)
        self.update_log.emit(message)

    def connect_to_server(self):
        try:
            # Создание сокета
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Подключение к серверу
            self.log(f"Attempting to connect to server at {self.host}:{self.port}...")
            self.update_status.emit("Connecting to server...")

            self.client_socket.connect((self.host, self.port))
            self.log("Connection to server established")
            self.update_status.emit("Connected to server")

            # Получение ID от сервера
            id_data = self.client_socket.recv(16).decode('utf-8')
            self.client_id = int(id_data)
            self.log(f"Received ID from server: {self.client_id}")
            self.client_id_received.emit(self.client_id)

            self.connected = True
            self.connection_status.emit(True)

            return True
        except ConnectionRefusedError:
            self.log("Error connecting to server: Connection refused")
            self.update_status.emit("Connection refused")
            self.connection_status.emit(False)
            return False
        except socket.error as e:
            self.log(f"Socket error: {e}")
            self.update_status.emit(f"Socket error: {e}")
            self.connection_status.emit(False)
            return False
        except Exception as e:
            self.log(f"Unexpected error: {e}")
            self.update_status.emit(f"Error: {e}")
            self.connection_status.emit(False)
            return False

    def disconnect_from_server(self):
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass

            self.client_socket = None
            self.connected = False
            self.connection_status.emit(False)
            self.log("Disconnected from server")
            self.update_status.emit("Disconnected")

    def send_data(self, data):
        if not self.connected or not self.client_socket:
            self.log("Cannot send data: Not connected to server")
            self.update_status.emit("Not connected to server")
            return False

        try:
            self.log(f"Sending data to server: {data}")
            self.update_status.emit("Sending data...")

            self.client_socket.send(data.encode('utf-8'))
            self.numbers = [float(num) for num in data.strip().split()]

            # Получение ответа от сервера
            response = self.client_socket.recv(4096).decode('utf-8')

            if response:
                self.log(f"Response received from server")
                self.update_status.emit("Response received")
                self.update_result.emit(response)
                return True
            else:
                self.log("Error receiving response from server")
                self.update_status.emit("Error receiving response")
                return False

        except socket.error as e:
            self.log(f"Socket error while sending data: {e}")
            self.update_status.emit(f"Socket error: {e}")
            self.connection_status.emit(False)
            self.connected = False
            return False
        except Exception as e:
            self.log(f"Error sending data: {e}")
            self.update_status.emit(f"Error: {e}")
            return False

    def run(self):
        self.connect_to_server()

# Диалоговое окно клиента
class ClientDialog(QDialog):
    def __init__(self, parent=None, host='127.0.0.1', port=12345, client_number=0):
        super().__init__(parent)

        # Настройка логирования для клиента
        self.client_logger, self.log_filename = setup_logger(f'client_{client_number}')

        self.setWindowTitle(f"Client #{client_number}")
        self.setGeometry(100, 100, 600, 500)
        self.setModal(False)  # Не блокирует основное окно

        # Главный layout
        main_layout = QVBoxLayout(self)

        # Настройки подключения
        connection_group = QGroupBox("Connection Settings")
        connection_layout = QFormLayout()

        self.host_label = QLabel("Host:")
        self.host_input = QLineEdit(host)
        connection_layout.addRow(self.host_label, self.host_input)

        self.port_label = QLabel("Port:")
        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(port)
        connection_layout.addRow(self.port_label, self.port_input)

        connection_group.setLayout(connection_layout)
        main_layout.addWidget(connection_group)

        # Кнопки управления подключением
        connection_buttons = QHBoxLayout()

        self.connect_button = QPushButton("Connect to Server")
        self.connect_button.clicked.connect(self.connect_to_server)
        connection_buttons.addWidget(self.connect_button)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_from_server)
        self.disconnect_button.setEnabled(False)
        connection_buttons.addWidget(self.disconnect_button)

        main_layout.addLayout(connection_buttons)

        # Статус подключения
        status_group = QGroupBox("Connection Status")
        status_layout = QFormLayout()

        self.status_label = QLabel("Status:")
        self.status_value = QLabel("Disconnected")
        status_layout.addRow(self.status_label, self.status_value)

        self.client_id_label = QLabel("Client ID:")
        self.client_id_value = QLabel("Not assigned")
        status_layout.addRow(self.client_id_label, self.client_id_value)

        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        # Ввод данных
        input_group = QGroupBox("Input Data")
        input_layout = QVBoxLayout()

        self.data_input_label = QLabel("Enter array elements (space-separated numbers):")
        input_layout.addWidget(self.data_input_label)

        self.data_input = QLineEdit()
        input_layout.addWidget(self.data_input)

        self.send_button = QPushButton("Send Data")
        self.send_button.clicked.connect(self.send_data)
        self.send_button.setEnabled(False)
        input_layout.addWidget(self.send_button)

        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        # Результаты
        results_group = QGroupBox("Processing Results")
        results_layout = QVBoxLayout()

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)

        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)

        # Лог клиента
        log_group = QGroupBox("Client Log")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        # Кнопки лога
        log_buttons = QHBoxLayout()

        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.clear_log)
        log_buttons.addWidget(self.clear_log_button)

        self.save_log_button = QPushButton("Save Log")
        self.save_log_button.clicked.connect(self.save_log)
        log_buttons.addWidget(self.save_log_button)

        log_layout.addLayout(log_buttons)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        # Клиентский поток
        self.client_thread = None

        # Автоматическое подключение, если передан порт и хост
        if host and port > 0:
            self.connect_to_server()

    def connect_to_server(self):
        host = self.host_input.text()
        port = self.port_input.value()

        self.client_thread = ClientThread(host, port, self.client_logger)

        # Подключение сигналов
        self.client_thread.update_log.connect(self.update_log)
        self.client_thread.update_status.connect(self.update_status)
        self.client_thread.update_result.connect(self.update_results)
        self.client_thread.connection_status.connect(self.update_connection_status)
        self.client_thread.client_id_received.connect(self.update_client_id)

        # Запуск клиента
        self.client_thread.start()

    def disconnect_from_server(self):
        if self.client_thread:
            self.client_thread.disconnect_from_server()

    def send_data(self):
        if not self.client_thread or not self.client_thread.connected:
            QMessageBox.warning(self, "Not Connected", "Please connect to the server first")
            return

        data = self.data_input.text().strip()

        if not data:
            QMessageBox.warning(self, "Empty Input", "Please enter numbers separated by spaces")
            return

        # Проверка формата данных
        try:
            numbers = [float(num) for num in data.split()]
            if not numbers:
                raise ValueError("No numbers entered")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers separated by spaces")
            return

        # Отправка данных
        self.client_thread.send_data(data)

    def update_log(self, message):
        self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        # Прокрутка к концу
        self.log_text.moveCursor(QTextCursor.End)

    def update_status(self, status):
        self.status_value.setText(status)

    def update_connection_status(self, connected):
        if connected:
            self.status_value.setText("Connected")
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.send_button.setEnabled(True)
            self.host_input.setEnabled(False)
            self.port_input.setEnabled(False)
        else:
            self.status_value.setText("Disconnected")
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            self.send_button.setEnabled(False)
            self.host_input.setEnabled(True)
            self.port_input.setEnabled(True)
            self.client_id_value.setText("Not assigned")

    def update_client_id(self, client_id):
        self.client_id_value.setText(str(client_id))

    def update_results(self, results):
        self.results_text.clear()
        self.results_text.setText(results)

    def clear_log(self):
        self.log_text.clear()

    def save_log(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Log File", "", "Log Files (*.log);;All Files (*)"
        )

        if file_path:
            with open(file_path, 'w') as f:
                f.write(self.log_text.toPlainText())

            QMessageBox.information(self, "Log Saved", f"Log saved to {file_path}")

    def closeEvent(self, event):
        if self.client_thread and self.client_thread.connected:
            reply = QMessageBox.question(
                self, 'Exit Confirmation',
                "You are still connected to the server. Disconnect and exit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.client_thread.disconnect_from_server()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

# Главное окно сервера
class ServerMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Server and Clients Application")
        self.setGeometry(100, 100, 1000, 700)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Главный layout
        main_layout = QVBoxLayout(central_widget)

        # Создание вкладок
        tabs = QTabWidget()

        # Вкладка сервера
        server_tab = QWidget()
        server_layout = QVBoxLayout(server_tab)

        # Разделим вкладку на серверную часть и область управления клиентами
        server_splitter = QSplitter(Qt.Vertical)

        # Верхняя часть - сервер
        server_widget = QWidget()
        server_widget_layout = QVBoxLayout(server_widget)

        # Настройки сервера
        settings_group = QGroupBox("Server Settings")
        settings_layout = QFormLayout()

        self.host_label = QLabel("Host:")
        self.host_value = QLabel("127.0.0.1")
        settings_layout.addRow(self.host_label, self.host_value)

        self.port_label = QLabel("Port:")
        self.port_value = QSpinBox()
        self.port_value.setRange(1024, 65535)
        self.port_value.setValue(12345)
        settings_layout.addRow(self.port_label, self.port_value)

        self.max_clients_label = QLabel("Max Clients:")
        self.max_clients_value = QSpinBox()
        self.max_clients_value.setRange(1, 10)
        self.max_clients_value.setValue(3)
        settings_layout.addRow(self.max_clients_label, self.max_clients_value)

        settings_group.setLayout(settings_layout)
        server_widget_layout.addWidget(settings_group)

        # Кнопки управления сервером
        server_control_layout = QHBoxLayout()

        self.start_button = QPushButton("Start Server")
        self.start_button.clicked.connect(self.start_server)
        server_control_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Server")
        self.stop_button.clicked.connect(self.stop_server)
        self.stop_button.setEnabled(False)
        server_control_layout.addWidget(self.stop_button)

        self.save_stats_button = QPushButton("Save Statistics")
        self.save_stats_button.clicked.connect(self.save_server_stats)
        server_control_layout.addWidget(self.save_stats_button)

        server_widget_layout.addLayout(server_control_layout)

        # Статистика сервера
        stats_group = QGroupBox("Server Statistics")
        stats_layout = QFormLayout()

        self.status_label = QLabel("Status:")
        self.status_value = QLabel("Stopped")
        stats_layout.addRow(self.status_label, self.status_value)

        self.clients_label = QLabel("Active Clients:")
        self.clients_value = QLabel("0")
        stats_layout.addRow(self.clients_label, self.clients_value)

        self.total_label = QLabel("Total Clients Served:")
        self.total_value = QLabel("0")
        stats_layout.addRow(self.total_label, self.total_value)

        self.waiting_label = QLabel("Waiting Clients:")
        self.waiting_value = QLabel("0")
        stats_layout.addRow(self.waiting_label, self.waiting_value)

        stats_group.setLayout(stats_layout)
        server_widget_layout.addWidget(stats_group)

        # Активные клиенты
        clients_group = QGroupBox("Active Clients")
        clients_layout = QVBoxLayout()

        self.clients_list = QListWidget()
        clients_layout.addWidget(self.clients_list)

        clients_group.setLayout(clients_layout)
        server_widget_layout.addWidget(clients_group)

        # Лог сервера
        log_group = QGroupBox("Server Log")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        log_buttons_layout = QHBoxLayout()

        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.clear_log)
        log_buttons_layout.addWidget(self.clear_log_button)

        self.save_log_button = QPushButton("Save Log")
        self.save_log_button.clicked.connect(self.save_log)
        log_buttons_layout.addWidget(self.save_log_button)

        log_layout.addLayout(log_buttons_layout)

        log_group.setLayout(log_layout)
        server_widget_layout.addWidget(log_group)

        # Добавление серверного виджета в сплиттер
        server_splitter.addWidget(server_widget)

        # Нижняя часть - управление клиентами
        clients_control_widget = QWidget()
        clients_control_layout = QVBoxLayout(clients_control_widget)

        clients_control_group = QGroupBox("Client Control")
        clients_control_inner_layout = QVBoxLayout()

        # Кнопки для управления клиентами
        client_buttons_layout = QHBoxLayout()

        self.launch_client_button = QPushButton("Launch New Client")
        self.launch_client_button.clicked.connect(self.launch_client)
        self.launch_client_button.setEnabled(False)
        client_buttons_layout.addWidget(self.launch_client_button)

        self.launch_multiple_button = QPushButton("Launch Multiple Clients")
        self.launch_multiple_button.clicked.connect(self.launch_multiple_clients)
        self.launch_multiple_button.setEnabled(False)
        client_buttons_layout.addWidget(self.launch_multiple_button)

        clients_control_inner_layout.addLayout(client_buttons_layout)

        # Количество клиентов для запуска
        client_count_layout = QHBoxLayout()

        self.client_count_label = QLabel("Number of clients to launch:")
        client_count_layout.addWidget(self.client_count_label)

        self.client_count_spin = QSpinBox()
        self.client_count_spin.setRange(1, 10)
        self.client_count_spin.setValue(3)
        client_count_layout.addWidget(self.client_count_spin)

        clients_control_inner_layout.addLayout(client_count_layout)

        # Список текущих клиентов
        self.client_windows_list = QListWidget()
        clients_control_inner_layout.addWidget(self.client_windows_list)

        clients_control_group.setLayout(clients_control_inner_layout)
        clients_control_layout.addWidget(clients_control_group)

        # Добавление виджета управления клиентами в сплиттер
        server_splitter.addWidget(clients_control_widget)

        # Добавление сплиттера в layout вкладки
        server_layout.addWidget(server_splitter)

        # Добавление вкладки сервера
        tabs.addTab(server_tab, "Server and Clients")

        # Вкладка для просмотра предыдущих логов
        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)

        # Выбор и загрузка логов
        log_selection_layout = QHBoxLayout()

        self.load_log_button = QPushButton("Load Log File")
        self.load_log_button.clicked.connect(self.load_log_file)
        log_selection_layout.addWidget(self.load_log_button)

        logs_layout.addLayout(log_selection_layout)

        # Просмотр выбранного лога
        self.loaded_log_text = QTextEdit()
        self.loaded_log_text.setReadOnly(True)
        logs_layout.addWidget(self.loaded_log_text)

        # Добавление вкладки логов
        tabs.addTab(logs_tab, "Previous Logs")

        # Вкладка для просмотра статистики
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)

        # Выбор файла статистики
        stats_selection_layout = QHBoxLayout()

        self.load_stats_button = QPushButton("Load Statistics File")
        self.load_stats_button.clicked.connect(self.load_stats_file)
        stats_selection_layout.addWidget(self.load_stats_button)

        stats_layout.addLayout(stats_selection_layout)

        # Просмотр статистики
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)

        # Добавление вкладки статистики
        tabs.addTab(stats_tab, "Statistics")

        # Добавление вкладок в главный layout
        main_layout.addWidget(tabs)

        # Серверный поток
        self.server_thread = None

        # Список открытых клиентских окон
        self.client_windows = []

        # Счетчик клиентов
        self.client_window_counter = 0

        # Таймер для обновления статистики
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats_display)
        self.stats_timer.start(1000)  # Обновление каждую секунду

    def start_server(self):
        if self.server_thread and self.server_thread.isRunning():
            return

        port = self.port_value.value()
        max_clients = self.max_clients_value.value()

        self.server_thread = ServerThread(
            host='127.0.0.1',
            port=port,
            max_clients=max_clients
        )

        # Подключение сигналов
        self.server_thread.update_log.connect(self.update_log)
        self.server_thread.update_clients.connect(self.update_clients_list)
        self.server_thread.update_stats.connect(self.update_stats)
        self.server_thread.server_started.connect(self.update_server_status)

        # Запуск сервера
        self.server_thread.start()

        # Обновление UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.port_value.setEnabled(False)
        self.max_clients_value.setEnabled(False)
        self.launch_client_button.setEnabled(True)
        self.launch_multiple_button.setEnabled(True)

    def stop_server(self):
        if self.server_thread and self.server_thread.isRunning():
            # Сначала закрываем все клиентские окна
            for window in self.client_windows:
                if window:
                    window.disconnect_from_server()
                    window.close()

            self.client_windows = []
            self.client_windows_list.clear()

            # Затем останавливаем сервер
            self.server_thread.stop()
            self.update_server_status(False)

    def update_server_status(self, running):
        if running:
            self.status_value.setText("Running")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.port_value.setEnabled(False)
            self.max_clients_value.setEnabled(False)
            self.launch_client_button.setEnabled(True)
            self.launch_multiple_button.setEnabled(True)
        else:
            self.status_value.setText("Stopped")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.port_value.setEnabled(True)
            self.max_clients_value.setEnabled(True)
            self.launch_client_button.setEnabled(False)
            self.launch_multiple_button.setEnabled(False)

    def update_log(self, message):
        self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        # Прокрутка к концу
        self.log_text.moveCursor(QTextCursor.End)

    def update_clients_list(self, clients):
        self.clients_list.clear()
        for client_id, addr in clients.items():
            self.clients_list.addItem(f"Client #{client_id} from {addr[0]}:{addr[1]}")

    def update_stats(self, stats):
        if 'active_clients' in stats:
            self.clients_value.setText(str(stats['active_clients']))
        if 'total_clients' in stats:
            self.total_value.setText(str(stats['total_clients']))
        if 'waiting_clients' in stats:
            self.waiting_value.setText(str(stats['waiting_clients']))

    def update_stats_display(self):
        if self.server_thread and self.server_thread.isRunning():
            stats = {
                "active_clients": len(active_clients),
                "total_clients": client_counter,
                "waiting_clients": client_semaphore.get_waiting_count() if client_semaphore else 0
            }
            self.update_stats(stats)

    def clear_log(self):
        self.log_text.clear()

    def save_log(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Log File", "", "Log Files (*.log);;All Files (*)"
        )

        if file_path:
            with open(file_path, 'w') as f:
                f.write(self.log_text.toPlainText())

            QMessageBox.information(self, "Log Saved", f"Log saved to {file_path}")

    def load_log_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Log File", "logs", "Log Files (*.log);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    log_content = f.read()

                self.loaded_log_text.clear()
                self.loaded_log_text.setText(log_content)
            except Exception as e:
                QMessageBox.warning(self, "Error Loading Log", f"Failed to load log: {e}")

    def save_server_stats(self):
        stats = save_statistics()

        formatted_stats = json.dumps(stats, indent=4)
        QMessageBox.information(
            self, "Statistics Saved",
            f"Statistics saved to {statistics_file}\n\nSummary:\n"
            f"Total clients served: {stats['total_clients_served']}\n"
            f"Client records: {len(stats['client_data'])}"
        )

    def load_stats_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Statistics File", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    stats = json.load(f)

                formatted_stats = json.dumps(stats, indent=4)
                self.stats_text.clear()
                self.stats_text.setText(formatted_stats)
            except Exception as e:
                QMessageBox.warning(self, "Error Loading Statistics", f"Failed to load statistics: {e}")

    def launch_client(self):
        if not self.server_thread or not self.server_thread.isRunning():
            QMessageBox.warning(self, "Server Not Running", "Please start the server first")
            return

        # Увеличиваем счетчик клиентов
        self.client_window_counter += 1

        # Создаем новое окно клиента
        client_dialog = ClientDialog(
            self,
            host='127.0.0.1',
            port=self.port_value.value(),
            client_number=self.client_window_counter
        )

        # Сохраняем ссылку на окно
        self.client_windows.append(client_dialog)

        # Добавляем в список окон
        self.client_windows_list.addItem(f"Client Dialog #{self.client_window_counter}")

        # Показываем окно
        client_dialog.show()

    def launch_multiple_clients(self):
        count = self.client_count_spin.value()

        for _ in range(count):
            self.launch_client()

    def closeEvent(self, event):
        if self.server_thread and self.server_thread.isRunning():
            reply = QMessageBox.question(
                self, 'Exit Confirmation',
                "Server is still running. Stop server and exit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Закрыть все клиентские окна
                for window in self.client_windows:
                    if window:
                        window.disconnect_from_server()
                        window.close()

                # Остановить сервер
                self.server_thread.stop()
                self.server_thread.wait(2000)  # Ждем до 2 секунд
                event.accept()
            else:
                event.ignore()
        else:
            # Закрыть все клиентские окна, если они есть
            for window in self.client_windows:
                if window:
                    window.close()

            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Установка стиля приложения
    app.setStyle("Fusion")

    window = ServerMainWindow()
    window.show()

    sys.exit(app.exec_())