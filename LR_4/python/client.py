import socket
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

# Исходный цвет консоли
original_color = None

def get_original_console_color():
    """Получает и сохраняет оригинальный цвет консоли"""
    if sys.platform == 'win32':
        # Для Windows используем API из kernel32.dll
        try:
            import ctypes
            STD_OUTPUT_HANDLE = -11
            handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

            class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
                _fields_ = [
                    ("dwSize", ctypes.wintypes._COORD),
                    ("dwCursorPosition", ctypes.wintypes._COORD),
                    ("wAttributes", ctypes.c_ushort),
                    ("srWindow", ctypes.wintypes._SMALL_RECT),
                    ("dwMaximumWindowSize", ctypes.wintypes._COORD)
                ]

            csbi = CONSOLE_SCREEN_BUFFER_INFO()
            if ctypes.windll.kernel32.GetConsoleScreenBufferInfo(handle, ctypes.byref(csbi)):
                return csbi.wAttributes
        except:
            pass
    return None

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

def reset_console_color():
    """Восстанавливает оригинальный цвет консоли"""
    if sys.platform == 'win32':
        # Сброс к стандартным настройкам (черный фон, белый текст)
        os.system("color 07")
        os.system("cls")  # Очистка экрана
        print("Console color reset to original")
        print("Waiting for commands from server...")
        return True
    return False

def main():
    # Подключение к серверу
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('127.0.0.1', 8888)

    try:
        # Получение и сохранение оригинального цвета консоли
        global original_color
        original_color = get_original_console_color()

        print(f"Client started. Connecting to server at {server_address[0]}:{server_address[1]}...")
        client_socket.connect(server_address)

        # Очистка экрана и приветственное сообщение
        os.system("cls" if sys.platform == 'win32' else "clear")
        print("Connected to server. Waiting for commands...")
        print("This client can change its console background color based on server commands.")

        # Основной цикл
        while True:
            # Получение команды от сервера
            command = client_socket.recv(1024).decode('utf-8')

            if not command:
                print("Connection closed by server.")
                break

            print(f"Received command: {command}")

            # Обработка команды
            if command == "exit":
                print("Server requested to close the connection. Exiting...")
                response = "Client is shutting down"
                client_socket.send(response.encode('utf-8'))
                break
            elif command.startswith("color "):
                color_name = command.split(maxsplit=1)[1]
                if color_name in COLOR_CODES:
                    if change_console_color(color_name):
                        response = f"Color changed to {color_name}"
                    else:
                        response = "Failed to change color"
                        print(response)
                else:
                    response = f"Unknown color: {color_name}"
                    print(response)
            elif command == "reset":
                if reset_console_color():
                    response = "Console color reset to original"
                else:
                    response = "Failed to reset console color"
                    print(response)
            else:
                response = f"Unknown command: {command}"
                print(response)

            # Отправка ответа серверу
            client_socket.send(response.encode('utf-8'))

    except ConnectionRefusedError:
        print("Failed to connect to server. Make sure server is running.")
    except KeyboardInterrupt:
        print("\nClient interrupted by user.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Восстановление оригинального цвета консоли
        reset_console_color()
        client_socket.close()
        print("Press Enter to exit...")
        input()

if __name__ == "__main__":
    main()