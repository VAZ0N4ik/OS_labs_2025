#!/usr/bin/env python3
import os
import sys
import numpy as np
import pickle

def help_message():
    """Выводит справку по использованию программы."""
    print("Программа для вычисления ранга матрицы.")
    print("Использование: запустите программу без параметров.")
    print("Для ввода матрицы следуйте инструкциям на экране.")
    print("Программа использует межпроцессное взаимодействие для вычисления ранга.")

def calculate_rank(matrix):
    """
    Вычисляет ранг матрицы с помощью NumPy.

    Args:
        matrix (numpy.ndarray): матрица для вычисления ранга

    Returns:
        int: ранг матрицы
    """
    return np.linalg.matrix_rank(matrix)

def server(pipe_in, pipe_out):
    """
    Серверная часть программы, вычисляющая ранг матрицы.

    Args:
        pipe_in (int): дескриптор канала для чтения
        pipe_out (int): дескриптор канала для записи
    """
    # Закрываем ненужные концы каналов
    os.close(pipe_out[0])  # Закрываем чтение из выходного канала
    os.close(pipe_in[1])   # Закрываем запись во входной канал

    # Создаем файловые объекты из дескрипторов
    read_pipe = os.fdopen(pipe_in[0], 'rb')
    write_pipe = os.fdopen(pipe_out[1], 'wb')

    try:
        # Читаем матрицу от клиента
        matrix = pickle.load(read_pipe)

        # Вычисляем ранг
        rank = calculate_rank(matrix)

        # Отправляем результат клиенту
        pickle.dump(rank, write_pipe)
        write_pipe.flush()
    finally:
        # Закрываем каналы
        read_pipe.close()
        write_pipe.close()

    # Завершаем серверный процесс
    sys.exit(0)

def client(pipe_in, pipe_out):
    """
    Клиентская часть программы, взаимодействующая с пользователем.

    Args:
        pipe_in (int): дескриптор канала для чтения
        pipe_out (int): дескриптор канала для записи
    """
    # Закрываем ненужные концы каналов
    os.close(pipe_in[0])   # Закрываем чтение из входного канала
    os.close(pipe_out[1])  # Закрываем запись в выходной канал

    # Создаем файловые объекты из дескрипторов
    write_pipe = os.fdopen(pipe_in[1], 'wb')
    read_pipe = os.fdopen(pipe_out[0], 'rb')

    try:
        print("Программа вычисления ранга матрицы")

        # Выбор способа ввода
        print("\nВыберите способ ввода матрицы:")
        print("1. Ввод с клавиатуры")
        print("2. Загрузка из файла")

        choice = 0
        while choice not in [1, 2]:
            try:
                choice = int(input("Ваш выбор: "))
                if choice not in [1, 2]:
                    print("Пожалуйста, введите 1 или 2.")
            except ValueError:
                print("Пожалуйста, введите число.")

        if choice == 1:
            # Ручной ввод матрицы
            rows = 0
            while rows <= 0:
                try:
                    rows = int(input("Введите количество строк матрицы: "))
                    if rows <= 0:
                        print("Количество строк должно быть положительным числом.")
                except ValueError:
                    print("Пожалуйста, введите целое число.")

            cols = 0
            while cols <= 0:
                try:
                    cols = int(input("Введите количество столбцов матрицы: "))
                    if cols <= 0:
                        print("Количество столбцов должно быть положительным числом.")
                except ValueError:
                    print("Пожалуйста, введите целое число.")

            # Создаем и заполняем матрицу
            matrix = np.zeros((rows, cols))
            print("Введите элементы матрицы:")

            for i in range(rows):
                for j in range(cols):
                    valid_input = False
                    while not valid_input:
                        try:
                            value = float(input(f"Матрица[{i}][{j}]: "))
                            matrix[i, j] = value
                            valid_input = True
                        except ValueError:
                            print("Пожалуйста, введите число.")
        else:
            # Загрузка из файла
            filename = input("Введите имя файла: ")
            try:
                matrix = np.loadtxt(filename)
                rows, cols = matrix.shape
            except Exception as e:
                print(f"Ошибка загрузки файла: {e}")
                print("Переключение на ручной ввод...")
                # Повторяем процесс ручного ввода
                rows = int(input("Введите количество строк матрицы: "))
                cols = int(input("Введите количество столбцов матрицы: "))
                matrix = np.zeros((rows, cols))
                print("Введите элементы матрицы:")
                for i in range(rows):
                    for j in range(cols):
                        matrix[i, j] = float(input(f"Матрица[{i}][{j}]: "))

        # Выводим введенную матрицу
        print("\nВведенная матрица:")
        print(matrix)

        # Отправляем матрицу серверу
        pickle.dump(matrix, write_pipe)
        write_pipe.flush()

        # Получаем результат от сервера
        rank = pickle.load(read_pipe)

        # Выводим результат
        print(f"\nРанг матрицы: {rank}")

        # Запрашиваем сохранение результата в файл
        save_choice = input("Хотите сохранить результат в файл? (да/нет): ").lower()
        if save_choice in ['да', 'y', 'yes']:
            out_filename = input("Введите имя файла для сохранения: ")
            with open(out_filename, 'w') as f:
                f.write(f"Исходная матрица ({rows}x{cols}):\n")
                f.write(str(matrix))
                f.write(f"\n\nРанг матрицы: {rank}\n")
            print(f"Результат успешно сохранен в файле {out_filename}")

    finally:
        # Закрываем каналы
        write_pipe.close()
        read_pipe.close()

    # Завершаем клиентский процесс
    sys.exit(0)

def main():
    # Проверяем параметры командной строки
    if len(sys.argv) == 2 and sys.argv[1] == '--help':
        help_message()
        sys.exit(0)
    elif len(sys.argv) > 1:
        print("Запустите программу с ключом --help для получения справки")
        sys.exit(1)

    # Создаем каналы
    pipe_in = os.pipe()   # Канал клиент -> сервер
    pipe_out = os.pipe()  # Канал сервер -> клиент

    # Разделяем процесс на клиент и сервер
    pid = os.fork()

    if pid < 0:
        print("Ошибка при вызове fork()")
        sys.exit(1)
    elif pid > 0:
        # Родительский процесс - клиент
        client(pipe_in, pipe_out)
    else:
        # Дочерний процесс - сервер
        server(pipe_in, pipe_out)

if __name__ == "__main__":
    main()