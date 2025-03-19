import socket
import subprocess
import os
import sys

# Доступные цвета консоли (Windows)
COLOR_CODES = {
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

def display_help():
    """Отображает справку по командам"""
    print("Available commands:")
    print("  color <colorname> - Change client console background color")
    print("  reset - Reset client console to original color")
    print("  help - Display this help message")
    print("  exit - Close the connection and exit")
    print("\nAvailable colors:")

    # Вывод доступных цветов в столбцах
    col_count = 0
    for color in COLOR_CODES:
        print(f"{color}", end="\t")
        col_count += 1
        if col_count % 4 == 0:
            print()
    print()
def change_console_color(color_name):
    """Изменяет цвет фона консоли"""
    if sys.platform == 'win32':
        # Для Windows используем системный вызов 'color'
        # Первая цифра - цвет фона, вторая - цвет текста
        color_code = COLOR_CODES.get(color_name)
        # Получаем текущий цвет текста (символы)
        # По умолчанию используем белый текст (7)
        text_color = "7"

        if color_code:
            # Комбинируем: фон + текст
            os.system(f"color {color_code}{text_color}")
            os.system("cls")  # Очистка экрана для применения цвета
            print(f"Console color changed to {color_name}")
            print("Waiting for commands from server...")
            return True
    return False
def main():
    # Настройка сервера
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_address = ('127.0.0.1', 8888)
    print(f"Starting server on {server_address[0]}:{server_address[1]}")

    try:
        server_socket.bind(server_address)
        server_socket.listen(1)

        # Запуск клиентского процесса
        print("Creating client process...")

        # Определяем текущий путь для запуска клиента из той же директории
        current_dir = os.path.dirname(os.path.abspath(__file__))
        client_path = os.path.join(current_dir, "client.py")

        # Запуск клиентского процесса в новом окне
        if sys.platform == 'win32':
            client_process = subprocess.Popen(
                ["start", "python", client_path],
                shell=True
            )
        else:
            # Для Linux/macOS (может потребоваться настройка)
            client_process = subprocess.Popen(
                ["python3", client_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

        print("Waiting for client connection...")
        client_socket, client_address = server_socket.accept()
        print(f"Client connected: {client_address[0]}:{client_address[1]}")

        print("Type 'help' for available commands.")

        # Основной цикл
        while True:
            command = input("\nEnter command: ")

            if command == "exit":
                print("Closing connection and exiting...")
                client_socket.send(command.encode('utf-8'))
                break
            elif command == "help":
                display_help()
                continue  # Не отправляем эту команду клиенту
            elif command.startswith("color "):
                color_name = command.split(maxsplit=1)[1] if len(command.split()) > 1 else ""
                if color_name not in COLOR_CODES:
                    print(f"Unknown color: {color_name}")
                    print("Type 'help' to see available colors.")
                    continue
                change_console_color(color_name)

            elif command == "reset":
                change_console_color("black")

            elif command != "reset" and command != "":
                print("Unknown command. Type 'help' for available commands.")
                continue

            # Отправка команды клиенту
            client_socket.send(command.encode('utf-8'))

            # Получение ответа от клиента
            response = client_socket.recv(1024).decode('utf-8')
            print(f"Client response: {response}")

    except ConnectionRefusedError:
        print("Connection to client failed. Make sure client is running.")
    except KeyboardInterrupt:
        print("\nServer interrupted by user.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            client_socket.close()
        except:
            pass
        server_socket.close()
        print("Server shutdown completed.")

if __name__ == "__main__":
    main()