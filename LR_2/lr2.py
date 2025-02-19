#!/usr/bin/env python3
import os
import sys
import stat
from datetime import datetime
import argparse

# Размер буфера для копирования файлов (4 KB)
BUFFER_SIZE = 4096

def copy_file(source: str, dest: str) -> bool:
    # Копирование файла с использованием блочного чтения/записи.
    try:
        with open(source, 'rb') as src, open(dest, 'wb') as dst:
            while True:
                # Читаем блок данных
                buffer = src.read(BUFFER_SIZE)
                if not buffer:
                    break
                # Записываем блок в целевой файл
                dst.write(buffer)
        return True
    except IOError as e:
        print(f"Error copying file: {e}")
        return False

def move_file(source: str, dest: str) -> bool:
    # Перемещение файла.
    try:
        # Сначала пробуем просто переименовать
        os.rename(source, dest)
        return True
    except OSError:
        # Если не удалось, копируем и удаляем оригинал
        if copy_file(source, dest):
            try:
                os.remove(source)
                return True
            except OSError as e:
                print(f"Error removing source file: {e}")
                return False
        return False

def get_file_info(filename: str) -> None:
    #Получение и вывод информации о файле.
    try:
        file_stat = os.stat(filename)

        # Получаем права доступа в восьмеричном формате
        mode = stat.S_IMODE(file_stat.st_mode)

        # Форматируем время последней модификации
        mtime = datetime.fromtimestamp(file_stat.st_mtime)

        print(f"File: {filename}")
        print(f"Size: {file_stat.st_size} bytes")
        print(f"Permissions: {oct(mode)[2:]} ({stat.filemode(file_stat.st_mode)})")
        print(f"Last modified: {mtime}")

    except OSError as e:
        print(f"Error getting file information: {e}")

def change_permissions(filename: str, mode: str) -> bool:
    # Изменение прав доступа к файлу.
    try:
        # Преобразуем строку с восьмеричным числом в int
        mode_int = int(mode, 8)
        os.chmod(filename, mode_int)
        return True
    except (OSError, ValueError) as e:
        print(f"Error changing file permissions: {e}")
        return False

def console_interface():
    # Интерактивный консольный интерфейс программы.
    while True:
        print("\nFile Operations:")
        print("1. Copy file")
        print("2. Move file")
        print("3. Get file information")
        print("4. Change file permissions")
        print("5. Exit")

        try:
            choice = int(input("Choose operation (1-5): "))
        except ValueError:
            print("Please enter a number between 1 and 5")
            continue

        if choice == 5:
            break

        if choice == 1:
            source = input("Enter source file: ")
            dest = input("Enter destination file: ")
            if copy_file(source, dest):
                print("File copied successfully")

        elif choice == 2:
            source = input("Enter source file: ")
            dest = input("Enter destination file: ")
            if move_file(source, dest):
                print("File moved successfully")

        elif choice == 3:
            filename = input("Enter filename: ")
            get_file_info(filename)

        elif choice == 4:
            filename = input("Enter filename: ")
            mode = input("Enter new permissions (octal, e.g. 644): ")
            if change_permissions(filename, mode):
                print("Permissions changed successfully")

        else:
            print("Invalid choice")

def main():
    # Создаём парсер аргументов командной строки
    parser = argparse.ArgumentParser(description='File operations program')

    # Добавляем аргументы
    parser.add_argument('--copy', nargs=2, metavar=('SOURCE', 'DEST'),
                        help='Copy source file to destination')
    parser.add_argument('--move', nargs=2, metavar=('SOURCE', 'DEST'),
                        help='Move source file to destination')
    parser.add_argument('--info', metavar='FILE',
                        help='Display file information')
    parser.add_argument('--chmod', nargs=2, metavar=('FILE', 'MODE'),
                        help='Change file permissions (octal mode)')

    args = parser.parse_args()

    # Если нет аргументов, запускаем интерактивный режим
    if len(sys.argv) == 1:
        console_interface()
        return

    # Обработка аргументов командной строки
    if args.copy:
        if copy_file(args.copy[0], args.copy[1]):
            print("File copied successfully")

    elif args.move:
        if move_file(args.move[0], args.move[1]):
            print("File moved successfully")

    elif args.info:
        get_file_info(args.info)

    elif args.chmod:
        if change_permissions(args.chmod[0], args.chmod[1]):
            print("Permissions changed successfully")

if __name__ == "__main__":
    main()