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
                             QSplitter, QDialog, QDialogButtonBox, QComboBox,
                             QListWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QTextCursor, QFont, QIcon, QColor
import subprocess

# Создаем директорию для логов
if not os.path.exists('logs'):
    os.makedirs('logs')


# Настройка логирования
def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Создаем обработчик для записи в файл
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

# Цвета фона консоли для клиентов
CONSOLE_COLORS = {
    "black": "0",
    "blue": "1",
    "green": "2",
    "cyan": "3",
    "red": "4",
    "magenta": "5",
    "yellow": "6",
    "white": "7",
    "gray": "8",
    "bright_blue": "9",
    "bright_green": "A",
    "bright_cyan": "B",
    "bright_red": "C",
    "bright_magenta": "D",
    "bright_yellow": "E",
    "bright_white": "F"
}

# RGB значения для цветов (для отображения в GUI)
COLOR_RGB = {
    "black": "#000000",
    "blue": "#0000AA",
    "green": "#00AA00",
    "cyan": "#00AAAA",
    "red": "#AA0000",
    "magenta": "#AA00AA",
    "yellow": "#AAAA00",
    "white": "#AAAAAA",
    "gray": "#555555",
    "bright_blue": "#5555FF",
    "bright_green": "#55FF55",
    "bright_cyan": "#55FFFF",
    "bright_red": "#FF5555",
    "bright_magenta": "#FF55FF",
    "bright_yellow": "#FFFF55",
    "bright_white": "#FFFFFF",
    "reset": "#000000"  # Черный фон по умолчанию
}


# Служебная функция для изменения цвета консоли (только Windows)
def change_console_color(color_name):
    if sys.platform == 'win32':
        try:
            if color_name == "reset":
                os.system("color 07")  # Черный фон, белый текст (по умолчанию)
                return True

            if color_name in CONSOLE_COLORS:
                # Первая цифра - цвет фона, вторая - цвет текста
                color_code = CONSOLE_COLORS[color_name]
                os.system(f"color {color_code}7")  # Фон выбранного цвета, белый текст
                return True

        except Exception as e:
            print(f"Error changing console color: {str(e)}")

    return False


# Класс для серверного потока
class ServerThread(QThread):
    # Сигналы для обновления GUI
    update_log = pyqtSignal(str)
    update_clients = pyqtSignal(dict)
    server_started = pyqtSignal(bool)
    client_color_changed = pyqtSignal(int, str)

    def __init__(self, host='127.0.0.1', port=8888):
        super().__init__()
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        self.client_sockets = {}
        self.client_threads = {}
        self.client_colors = {}  # Для отслеживания текущего цвета каждого клиента

    def log(self, message):
        server_logger.info(message)
        self.update_log.emit(message)

    def run(self):
        global client_counter, active_clients

        try:
            # Создание сокета
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Установка таймаута для socket.accept()
            self.server_socket.settimeout(0.5)

            # Привязка сокета к адресу
            self.server_socket.bind((self.host, self.port))

            # Начало прослушивания
            self.server_socket.listen(5)
            self.log(f"Server started on {self.host}:{self.port}")

            self.running = True
            self.server_started.emit(True)

            # Цикл обработки подключений
            while self.running:
                try:
                    # Принятие подключения
                    client_socket, addr = self.server_socket.accept()

                    client_counter += 1
                    client_id = client_counter
                    active_clients[client_id] = addr
                    self.client_sockets[client_id] = client_socket
                    self.client_colors[client_id] = "default"  # Изначальный цвет клиента

                    self.log(f"New client connected: #{client_id} from {addr[0]}:{addr[1]}")
                    self.update_clients.emit(active_clients.copy())

                    # Отправка ID клиенту
                    client_socket.send(str(client_id).encode('utf-8'))

                    # Создание потока для обработки клиента
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_id, addr)
                    )
                    client_thread.daemon = True
                    self.client_threads[client_id] = client_thread
                    client_thread.start()

                except socket.timeout:
                    # Тайм-аут нужен для регулярной проверки self.running
                    continue
                except Exception as e:
                    if self.running:
                        self.log(f"Error accepting connection: {str(e)}")

        except Exception as e:
            self.log(f"Server error: {str(e)}")
        finally:
            # Закрытие сокетов
            for client_id, client_socket in self.client_sockets.items():
                try:
                    client_socket.close()
                except:
                    pass

            if self.server_socket:
                self.server_socket.close()

            self.running = False
            self.server_started.emit(False)
            self.log("Server stopped")

    def handle_client(self, client_socket, client_id, addr):
        try:
            while self.running:
                try:
                    # Получение команды от клиента
                    data = client_socket.recv(1024).decode('utf-8')

                    if not data:
                        break

                    self.log(f"Received from client #{client_id}: {data}")

                    # Обработка подтверждений от клиента
                    if data.startswith("color_changed "):
                        color_name = data.split(" ", 1)[1].strip()
                        self.client_colors[client_id] = color_name
                        self.log(f"Client #{client_id} confirmed color change to {color_name}")
                        self.client_color_changed.emit(client_id, color_name)

                    elif data == "color_reset":
                        self.client_colors[client_id] = "default"
                        self.log(f"Client #{client_id} confirmed color reset")
                        self.client_color_changed.emit(client_id, "reset")

                    elif data == "exit" or data == "exit_acknowledged":
                        self.log(f"Client #{client_id} requested to exit")
                        break

                    # Если клиент отправляет подтверждения об ошибках
                    elif data.startswith("color_change_failed") or data == "color_reset_failed":
                        self.log(f"Client #{client_id} reported failure: {data}")

                except ConnectionResetError:
                    self.log(f"Connection reset by client #{client_id}")
                    break
                except Exception as e:
                    self.log(f"Error handling client #{client_id}: {str(e)}")
                    break

        finally:
            # Очистка после отключения клиента
            client_socket.close()
            if client_id in active_clients:
                del active_clients[client_id]
            if client_id in self.client_sockets:
                del self.client_sockets[client_id]
            if client_id in self.client_threads:
                del self.client_threads[client_id]
            if client_id in self.client_colors:
                del self.client_colors[client_id]

            self.log(f"Client #{client_id} disconnected")
            self.update_clients.emit(active_clients.copy())

    def send_to_client(self, client_id, message):
        if client_id not in self.client_sockets:
            self.log(f"Error: Client #{client_id} not found")
            return False

        try:
            self.client_sockets[client_id].send(message.encode('utf-8'))
            self.log(f"Sent to client #{client_id}: {message}")
            return True
        except Exception as e:
            self.log(f"Error sending to client #{client_id}: {str(e)}")
            return False

    def stop(self):
        self.running = False

        # Отправляем команду выхода всем клиентам
        for client_id, client_socket in list(self.client_sockets.items()):
            try:
                client_socket.send("exit".encode('utf-8'))
            except:
                pass

        # Ждем немного, чтобы клиенты успели обработать команду
        time.sleep(0.5)

        # Закрываем все клиентские сокеты
        for client_id, client_socket in list(self.client_sockets.items()):
            try:
                client_socket.close()
            except:
                pass

        # Закрываем серверный сокет
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass


# Диалог для создания нескольких клиентов
class CreateClientsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Create Multiple Clients")
        self.setGeometry(300, 300, 300, 150)

        layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.num_clients_label = QLabel("Number of Clients:")
        self.num_clients_input = QSpinBox()
        self.num_clients_input.setRange(1, 10)
        self.num_clients_input.setValue(1)
        form_layout.addRow(self.num_clients_label, self.num_clients_input)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        self.setLayout(layout)

    def get_num_clients(self):
        return self.num_clients_input.value()


# Главное окно сервера
class ServerMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Server - Color Control")
        self.setGeometry(100, 100, 800, 600)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Главный layout
        main_layout = QVBoxLayout(central_widget)

        # Создание вкладок
        tabs = QTabWidget()

        # Вкладка управления сервером
        server_tab = QWidget()
        server_layout = QVBoxLayout(server_tab)

        # Настройки сервера
        settings_group = QGroupBox("Server Settings")
        settings_layout = QFormLayout()

        self.host_label = QLabel("Host:")
        self.host_input = QLineEdit("127.0.0.1")
        settings_layout.addRow(self.host_label, self.host_input)

        self.port_label = QLabel("Port:")
        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(8888)
        settings_layout.addRow(self.port_label, self.port_input)

        settings_group.setLayout(settings_layout)
        server_layout.addWidget(settings_group)

        # Кнопки управления сервером
        control_layout = QHBoxLayout()

        self.start_button = QPushButton("Start Server")
        self.start_button.clicked.connect(self.start_server)
        control_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Server")
        self.stop_button.clicked.connect(self.stop_server)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)

        self.create_client_button = QPushButton("Create Client")
        self.create_client_button.clicked.connect(self.create_client)
        self.create_client_button.setEnabled(False)
        control_layout.addWidget(self.create_client_button)

        self.create_multi_clients_button = QPushButton("Create Multiple Clients")
        self.create_multi_clients_button.clicked.connect(self.create_multiple_clients)
        self.create_multi_clients_button.setEnabled(False)
        control_layout.addWidget(self.create_multi_clients_button)

        server_layout.addLayout(control_layout)

        # Список подключенных клиентов
        clients_group = QGroupBox("Connected Clients")
        clients_layout = QVBoxLayout()

        self.clients_list = QListWidget()
        self.clients_list.setSelectionMode(QListWidget.ExtendedSelection)
        clients_layout.addWidget(self.clients_list)

        # Отправка команд клиентам
        command_layout = QHBoxLayout()

        self.cmd_label = QLabel("Color:")
        command_layout.addWidget(self.cmd_label)

        self.color_combo = QComboBox()
        self.color_combo.addItems(list(CONSOLE_COLORS.keys()))
        command_layout.addWidget(self.color_combo)

        self.send_color_button = QPushButton("Change Color")
        self.send_color_button.clicked.connect(self.send_color_command)
        self.send_color_button.setEnabled(False)
        command_layout.addWidget(self.send_color_button)

        self.reset_color_button = QPushButton("Reset Color")
        self.reset_color_button.clicked.connect(self.send_reset_command)
        self.reset_color_button.setEnabled(False)
        command_layout.addWidget(self.reset_color_button)

        clients_layout.addLayout(command_layout)
        clients_group.setLayout(clients_layout)
        server_layout.addWidget(clients_group)

        # Лог сервера
        log_group = QGroupBox("Server Log")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        # Кнопки для работы с логом
        log_buttons = QHBoxLayout()

        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.clear_log)
        log_buttons.addWidget(self.clear_log_button)

        self.save_log_button = QPushButton("Save Log")
        self.save_log_button.clicked.connect(self.save_log)
        log_buttons.addWidget(self.save_log_button)

        log_layout.addLayout(log_buttons)
        log_group.setLayout(log_layout)
        server_layout.addWidget(log_group)

        # Добавление вкладки сервера
        tabs.addTab(server_tab, "Server")

        # Вкладка просмотра логов
        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)

        # Выбор файла лога
        log_file_layout = QHBoxLayout()

        self.select_log_button = QPushButton("Select Log File")
        self.select_log_button.clicked.connect(self.select_log_file)
        log_file_layout.addWidget(self.select_log_button)

        self.log_file_path = QLineEdit()
        self.log_file_path.setReadOnly(True)
        log_file_layout.addWidget(self.log_file_path)

        logs_layout.addLayout(log_file_layout)

        # Просмотр содержимого лога
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        logs_layout.addWidget(self.log_viewer)

        # Добавление вкладки логов
        tabs.addTab(logs_tab, "View Logs")

        # Добавление вкладок в главный layout
        main_layout.addWidget(tabs)

        # Инициализация серверного потока
        self.server_thread = None

        # Словарь для хранения цветов клиентов для визуального отображения
        self.client_colors = {}

        # Список запущенных процессов клиентов
        self.client_processes = {}

        # Обновление лога с текущей информацией
        self.update_log("Server application started")
        self.update_log(f"Log file: {server_log_file}")

        # Изменить цвет консоли сервера (только на Windows)
        change_console_color("green")

    def update_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.moveCursor(QTextCursor.End)

    def start_server(self):
        if self.server_thread and self.server_thread.isRunning():
            return

        host = self.host_input.text()
        port = self.port_input.value()

        self.server_thread = ServerThread(host, port)
        self.server_thread.update_log.connect(self.update_log)
        self.server_thread.update_clients.connect(self.update_clients_list)
        self.server_thread.server_started.connect(self.server_status_changed)
        self.server_thread.client_color_changed.connect(self.handle_client_color_changed)

        self.server_thread.start()

    def stop_server(self):
        if self.server_thread and self.server_thread.isRunning():
            self.server_thread.stop()

            # Завершение клиентских процессов
            for client_id, process in list(self.client_processes.items()):
                try:
                    process.terminate()
                    self.update_log(f"Terminated client process #{client_id}")
                except:
                    pass

            self.client_processes.clear()

            # Восстанавливаем цвет консоли сервера (только на Windows)
            change_console_color("reset")

    def server_status_changed(self, running):
        if running:
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.create_client_button.setEnabled(True)
            self.create_multi_clients_button.setEnabled(True)
            self.host_input.setEnabled(False)
            self.port_input.setEnabled(False)
        else:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.create_client_button.setEnabled(False)
            self.create_multi_clients_button.setEnabled(False)
            self.send_color_button.setEnabled(False)
            self.reset_color_button.setEnabled(False)
            self.host_input.setEnabled(True)
            self.port_input.setEnabled(True)

            # Очистка списка клиентов
            self.clients_list.clear()
            self.client_colors.clear()

    def update_clients_list(self, clients):
        self.clients_list.clear()

        for client_id, addr in clients.items():
            item_text = f"Client #{client_id} - {addr[0]}:{addr[1]}"

            item = QListWidgetItem(item_text)

            # Если у клиента задан цвет, отображаем его в списке
            if client_id in self.client_colors:
                color_name = self.client_colors[client_id]
                if color_name != "default" and color_name in COLOR_RGB:
                    item.setBackground(QColor(COLOR_RGB[color_name]))
                    # Для темных цветов используем светлый текст
                    if color_name in ["black", "blue", "red", "magenta", "bright_blue", "bright_red", "bright_magenta"]:
                        item.setForeground(QColor(255, 255, 255))

            self.clients_list.addItem(item)

        # Включаем кнопки управления, если есть клиенты
        has_clients = len(clients) > 0
        self.send_color_button.setEnabled(has_clients)
        self.reset_color_button.setEnabled(has_clients)

    def create_client(self):
        if not self.server_thread or not self.server_thread.isRunning():
            QMessageBox.warning(self, "Server Not Running", "Please start the server first")
            return

        host = self.host_input.text()
        port = self.port_input.value()

        try:
            # Запустить клиентский процесс
            client_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "client.py")

            # Создаем команду для запуска клиента
            cmd = [sys.executable, client_script, host, str(port)]

            # Запускаем клиентский процесс
            process = subprocess.Popen(cmd)

            # Сохраняем процесс для отслеживания
            client_id = len(self.client_processes) + 1
            self.client_processes[client_id] = process

            self.update_log(f"Client process #{client_id} started")

        except Exception as e:
            self.update_log(f"Error creating client: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to create client: {str(e)}")

    def create_multiple_clients(self):
        if not self.server_thread or not self.server_thread.isRunning():
            QMessageBox.warning(self, "Server Not Running", "Please start the server first")
            return

        dialog = CreateClientsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            num_clients = dialog.get_num_clients()

            host = self.host_input.text()
            port = self.port_input.value()

            client_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "client.py")

            for i in range(num_clients):
                try:
                    # Создаем команду для запуска клиента
                    cmd = [sys.executable, client_script, host, str(port)]

                    # Запускаем клиентский процесс
                    process = subprocess.Popen(cmd)

                    # Сохраняем процесс для отслеживания
                    client_id = len(self.client_processes) + 1
                    self.client_processes[client_id] = process

                    self.update_log(f"Client process #{client_id} started")

                    # Небольшая задержка между запусками клиентов
                    time.sleep(0.2)

                except Exception as e:
                    self.update_log(f"Error creating client: {str(e)}")

    def send_color_command(self):
        selected_items = self.clients_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Client Selected", "Please select a client from the list")
            return

        color = self.color_combo.currentText()

        for item in selected_items:
            # Парсим ID клиента из текста элемента списка
            text = item.text()
            try:
                client_id = int(text.split("#")[1].split(" ")[0])

                if self.server_thread:
                    command = f"color {color}"
                    self.server_thread.send_to_client(client_id, command)

                    # Обновляем цвет в нашем локальном словаре
                    self.client_colors[client_id] = color

                    # Также изменяем цвет фона элемента в списке
                    if color in COLOR_RGB:
                        item.setBackground(QColor(COLOR_RGB[color]))
                        # Для темных цветов используем светлый текст
                        if color in ["black", "blue", "red", "magenta", "bright_blue", "bright_red", "bright_magenta"]:
                            item.setForeground(QColor(255, 255, 255))
                        else:
                            item.setForeground(QColor(0, 0, 0))
            except:
                self.update_log(f"Failed to parse client ID from: {text}")

    def send_reset_command(self):
        selected_items = self.clients_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Client Selected", "Please select a client from the list")
            return

        for item in selected_items:
            # Парсим ID клиента из текста элемента списка
            text = item.text()
            try:
                client_id = int(text.split("#")[1].split(" ")[0])

                if self.server_thread:
                    self.server_thread.send_to_client(client_id, "reset")

                    # Сбрасываем цвет в нашем локальном словаре
                    if client_id in self.client_colors:
                        self.client_colors[client_id] = "default"

                    # Сбрасываем цвет фона элемента в списке
                    item.setBackground(QColor(255, 255, 255))
                    item.setForeground(QColor(0, 0, 0))
            except:
                self.update_log(f"Failed to parse client ID from: {text}")

    def handle_client_color_changed(self, client_id, color):
        # Этот метод вызывается, когда клиент меняет свой цвет
        self.client_colors[client_id] = color if color != "reset" else "default"

        # Обновляем отображение клиентов
        for i in range(self.clients_list.count()):
            item = self.clients_list.item(i)
            if item and f"Client #{client_id} " in item.text():
                if color == "reset":
                    # Сбрасываем цвет
                    item.setBackground(QColor(255, 255, 255))
                    item.setForeground(QColor(0, 0, 0))
                elif color in COLOR_RGB:
                    # Устанавливаем новый цвет
                    item.setBackground(QColor(COLOR_RGB[color]))
                    # Для темных цветов используем светлый текст
                    if color in ["black", "blue", "red", "magenta", "bright_blue", "bright_red", "bright_magenta"]:
                        item.setForeground(QColor(255, 255, 255))
                    else:
                        item.setForeground(QColor(0, 0, 0))
                break

    def clear_log(self):
        self.log_text.clear()

    def save_log(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Log File", "", "Log Files (*.log);;All Files (*)")

        if file_name:
            try:
                with open(file_name, 'w') as f:
                    f.write(self.log_text.toPlainText())

                self.update_log(f"Log saved to: {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save log: {str(e)}")

    def select_log_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Log File", "logs", "Log Files (*.log);;All Files (*)")

        if file_name:
            self.log_file_path.setText(file_name)

            try:
                with open(file_name, 'r') as f:
                    content = f.read()

                self.log_viewer.clear()
                self.log_viewer.setText(content)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read log file: {str(e)}")

    def closeEvent(self, event):
        # Проверка, запущен ли сервер
        if self.server_thread and self.server_thread.isRunning():
            reply = QMessageBox.question(
                self, 'Close Confirmation',
                "Server is still running. Stop server and exit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.stop_server()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = ServerMainWindow()
    window.show()

    sys.exit(app.exec_())