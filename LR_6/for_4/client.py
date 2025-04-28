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
                             QLineEdit, QComboBox, QMessageBox, QGroupBox, QFormLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QTextCursor, QFont, QIcon, QIntValidator

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


# Цвета фона консоли
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


# Класс для клиентского потока
class ClientThread(QThread):
    # Сигналы для обновления GUI
    update_log = pyqtSignal(str)
    update_status = pyqtSignal(str)
    connection_status = pyqtSignal(bool)
    client_id_received = pyqtSignal(int)
    color_changed = pyqtSignal(str)

    def __init__(self, host='127.0.0.1', port=8888, client_logger=None):
        super().__init__()
        self.host = host
        self.port = port
        self.client_socket = None
        self.client_id = -1
        self.connected = False
        self.running = True
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
            self.log(f"Connecting to server at {self.host}:{self.port}...")
            self.update_status.emit("Connecting...")

            self.client_socket.connect((self.host, self.port))
            self.log("Connected to server")
            self.update_status.emit("Connected")

            # Получаем ID клиента от сервера
            client_id_str = self.client_socket.recv(1024).decode('utf-8')
            self.client_id = int(client_id_str)
            self.log(f"Received client ID: {self.client_id}")

            self.client_id_received.emit(self.client_id)
            self.connected = True
            self.connection_status.emit(True)

            return True

        except ConnectionRefusedError:
            self.log("Connection refused. Server not available.")
            self.update_status.emit("Connection refused")
            self.connection_status.emit(False)
            return False

        except Exception as e:
            self.log(f"Connection error: {str(e)}")
            self.update_status.emit(f"Error: {str(e)}")
            self.connection_status.emit(False)
            return False

    def run(self):
        if not self.connect_to_server():
            return

        # Основной цикл получения сообщений от сервера
        try:
            while self.running and self.connected:
                # Получаем данные от сервера
                try:
                    data = self.client_socket.recv(1024).decode('utf-8')

                    if not data:
                        self.log("Disconnected from server (empty response)")
                        self.disconnect_from_server()
                        break

                    self.log(f"Received from server: {data}")

                    # Обработка команд
                    if data.startswith("color "):
                        color_name = data.split(" ", 1)[1].strip()
                        if color_name in CONSOLE_COLORS:
                            self.log(f"Changing console color to: {color_name}")
                            if change_console_color(color_name):
                                self.log(f"Console color changed to: {color_name}")
                                self.color_changed.emit(color_name)

                                # Подтверждаем серверу, что цвет изменен
                                self.send_message(f"color_changed {color_name}")
                            else:
                                self.log(f"Failed to change console color to: {color_name}")
                                self.send_message(f"color_change_failed {color_name}")
                        else:
                            self.log(f"Unknown color: {color_name}")
                            self.send_message(f"unknown_color {color_name}")

                    elif data == "reset":
                        self.log("Resetting console color")
                        if change_console_color("reset"):
                            self.log("Console color reset to default")
                            self.color_changed.emit("reset")

                            # Подтверждаем серверу, что цвет сброшен
                            self.send_message("color_reset")
                        else:
                            self.log("Failed to reset console color")
                            self.send_message("color_reset_failed")

                    elif data == "exit":
                        self.log("Server requested to close the connection")
                        # Подтверждаем серверу, что получили команду выхода
                        self.send_message("exit_acknowledged")
                        self.disconnect_from_server()
                        break

                except socket.timeout:
                    continue
                except ConnectionResetError:
                    self.log("Connection reset by server")
                    self.disconnect_from_server()
                    break
                except Exception as e:
                    self.log(f"Error receiving data: {str(e)}")
                    self.disconnect_from_server()
                    break

        except Exception as e:
            self.log(f"Error in client thread: {str(e)}")
        finally:
            self.connection_status.emit(False)
            self.update_status.emit("Disconnected")

    def send_message(self, message):
        if not self.connected or not self.client_socket:
            self.log("Cannot send message: Not connected to server")
            return False

        try:
            self.client_socket.send(message.encode('utf-8'))
            self.log(f"Sent to server: {message}")
            return True
        except Exception as e:
            self.log(f"Error sending message: {str(e)}")
            return False

    def disconnect_from_server(self):
        self.connected = False

        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass

            self.client_socket = None

        self.log("Disconnected from server")
        self.update_status.emit("Disconnected")
        self.connection_status.emit(False)

    def stop(self):
        self.running = False
        self.disconnect_from_server()


# Главное окно клиента
class ClientMainWindow(QMainWindow):
    def __init__(self, host='127.0.0.1', port=8888):
        super().__init__()

        # Инициализация логирования
        self.client_logger, self.client_log_file = setup_logger('client')

        self.setWindowTitle("Client - Color Control")
        self.setGeometry(100, 100, 600, 500)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Главный layout
        main_layout = QVBoxLayout(central_widget)

        # Настройки соединения
        connection_group = QGroupBox("Connection Settings")
        connection_layout = QFormLayout()

        self.host_label = QLabel("Host:")
        self.host_input = QLineEdit(host)
        connection_layout.addRow(self.host_label, self.host_input)

        self.port_label = QLabel("Port:")
        self.port_input = QLineEdit(str(port))
        self.port_input.setValidator(QIntValidator(1024, 65535))
        connection_layout.addRow(self.port_label, self.port_input)

        connection_group.setLayout(connection_layout)
        main_layout.addWidget(connection_group)

        # Кнопки управления соединением
        control_layout = QHBoxLayout()

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_server)
        control_layout.addWidget(self.connect_button)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_from_server)
        self.disconnect_button.setEnabled(False)
        control_layout.addWidget(self.disconnect_button)

        main_layout.addLayout(control_layout)

        # Статус соединения
        status_layout = QHBoxLayout()

        self.status_label = QLabel("Status:")
        status_layout.addWidget(self.status_label)

        self.status_value = QLabel("Disconnected")
        self.status_value.setStyleSheet("color: red")
        status_layout.addWidget(self.status_value)

        self.client_id_label = QLabel("Client ID:")
        status_layout.addWidget(self.client_id_label)

        self.client_id_value = QLabel("-")
        status_layout.addWidget(self.client_id_value)

        status_layout.addStretch()

        main_layout.addLayout(status_layout)

        # Индикатор текущего цвета
        color_indicator_layout = QHBoxLayout()

        self.color_indicator_label = QLabel("Current Color:")
        color_indicator_layout.addWidget(self.color_indicator_label)

        self.color_indicator = QLabel()
        self.color_indicator.setFixedSize(30, 20)
        self.color_indicator.setStyleSheet("background-color: #000000; border: 1px solid black;")
        color_indicator_layout.addWidget(self.color_indicator)

        self.color_name_label = QLabel("default")
        color_indicator_layout.addWidget(self.color_name_label)

        color_indicator_layout.addStretch()

        main_layout.addLayout(color_indicator_layout)

        # Ручное управление цветом
        color_group = QGroupBox("Manual Color Control")
        color_layout = QVBoxLayout()

        color_buttons_layout = QHBoxLayout()

        self.color_combo = QComboBox()
        self.color_combo.addItems(list(CONSOLE_COLORS.keys()))
        color_buttons_layout.addWidget(self.color_combo)

        self.change_color_button = QPushButton("Change Color")
        self.change_color_button.clicked.connect(self.change_color)
        self.change_color_button.setEnabled(False)
        color_buttons_layout.addWidget(self.change_color_button)

        self.reset_color_button = QPushButton("Reset Color")
        self.reset_color_button.clicked.connect(self.reset_color)
        self.reset_color_button.setEnabled(False)
        color_buttons_layout.addWidget(self.reset_color_button)

        color_layout.addLayout(color_buttons_layout)

        #color_group.setLayout(color_layout)
        #main_layout.addWidget(color_group)

        # Лог клиента
        log_group = QGroupBox("Client Log")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        # Кнопки для работы с логом
        log_buttons_layout = QHBoxLayout()

        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.clear_log)
        log_buttons_layout.addWidget(self.clear_log_button)

        self.view_previous_log_button = QPushButton("View Previous Logs")
        self.view_previous_log_button.clicked.connect(self.show_previous_logs)
        log_buttons_layout.addWidget(self.view_previous_log_button)

        log_layout.addLayout(log_buttons_layout)

        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        # Инициализация клиентского потока
        self.client_thread = None
        self.current_color = "default"

        # Обновление лога с текущей информацией
        self.update_log("Client application started")
        self.update_log(f"Log file: {self.client_log_file}")

        # Проверка аргументов командной строки
        if len(sys.argv) >= 3:
            self.host_input.setText(sys.argv[1])
            self.port_input.setText(sys.argv[2])
            # Если присутствуют аргументы командной строки, сразу подключаемся
            QTimer.singleShot(500, self.connect_to_server)

    def update_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.moveCursor(QTextCursor.End)

        if self.client_logger:
            self.client_logger.info(message)

    def connect_to_server(self):
        if self.client_thread and self.client_thread.isRunning():
            return

        host = self.host_input.text()
        port = int(self.port_input.text())

        self.client_thread = ClientThread(host, port, self.client_logger)
        self.client_thread.update_log.connect(self.update_log)
        self.client_thread.update_status.connect(self.update_status)
        self.client_thread.connection_status.connect(self.connection_status_changed)
        self.client_thread.client_id_received.connect(self.update_client_id)
        self.client_thread.color_changed.connect(self.update_color_display)

        self.client_thread.start()

    def disconnect_from_server(self):
        if self.client_thread and self.client_thread.isRunning():
            self.client_thread.send_message("exit")
            self.client_thread.stop()

    def update_status(self, status):
        self.status_value.setText(status)

        if status == "Connected":
            self.status_value.setStyleSheet("color: green")
        else:
            self.status_value.setStyleSheet("color: red")

    def connection_status_changed(self, connected):
        if connected:
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.change_color_button.setEnabled(True)
            self.reset_color_button.setEnabled(True)
            self.host_input.setEnabled(False)
            self.port_input.setEnabled(False)
        else:
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            self.change_color_button.setEnabled(False)
            self.reset_color_button.setEnabled(False)
            self.host_input.setEnabled(True)
            self.port_input.setEnabled(True)

    def update_client_id(self, client_id):
        self.client_id_value.setText(str(client_id))

    def change_color(self):
        if not self.client_thread or not self.client_thread.connected:
            return

        color = self.color_combo.currentText()
        self.client_thread.send_message(f"color {color}")

    def reset_color(self):
        if not self.client_thread or not self.client_thread.connected:
            return

        self.client_thread.send_message("reset")

    def update_color_display(self, color):
        if color == "reset":
            self.current_color = "default"
            self.color_indicator.setStyleSheet("background-color: #000000; border: 1px solid black;")
        else:
            self.current_color = color
            if color in COLOR_RGB:
                self.color_indicator.setStyleSheet(f"background-color: {COLOR_RGB[color]}; border: 1px solid black;")
                self.log_text.setStyleSheet(f"background-color: {COLOR_RGB[color]}")

        self.color_name_label.setText(self.current_color)

    def clear_log(self):
        self.log_text.clear()

    def show_previous_logs(self):
        from PyQt5.QtWidgets import QFileDialog, QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox

        log_dir = os.path.join(os.getcwd(), 'logs')
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Log File", log_dir, "Log Files (client_*.log);;All Files (*)"
        )

        if file_name:
            # Создаем диалог для просмотра лога
            log_dialog = QDialog(self)
            log_dialog.setWindowTitle(f"Log File: {os.path.basename(file_name)}")
            log_dialog.setGeometry(200, 200, 700, 500)

            layout = QVBoxLayout()

            log_viewer = QTextEdit()
            log_viewer.setReadOnly(True)
            layout.addWidget(log_viewer)

            # Добавляем кнопки OK
            button_box = QDialogButtonBox(QDialogButtonBox.Ok)
            button_box.accepted.connect(log_dialog.accept)
            layout.addWidget(button_box)

            log_dialog.setLayout(layout)

            try:
                with open(file_name, 'r') as f:
                    log_content = f.read()

                log_viewer.setPlainText(log_content)

                # Показываем диалог
                log_dialog.exec_()

            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to open log file: {str(e)}"
                )

    def closeEvent(self, event):
        if self.client_thread and self.client_thread.isRunning():
            reply = QMessageBox.question(
                self, 'Close Confirmation',
                "You are still connected to the server. Disconnect and exit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.disconnect_from_server()
                # Даем время на корректное отключение
                time.sleep(0.5)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Определение хоста и порта из аргументов командной строки
    host = '127.0.0.1'
    port = 8888

    if len(sys.argv) >= 2:
        host = sys.argv[1]
    if len(sys.argv) >= 3:
        try:
            port = int(sys.argv[2])
        except:
            pass

    window = ClientMainWindow(host, port)
    window.show()

    sys.exit(app.exec_())