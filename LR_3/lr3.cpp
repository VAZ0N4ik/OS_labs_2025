#include <iostream>
#include <sys/types.h>
#include <unistd.h>
#include <cstring>
#include <cmath>
#include <vector>
#include <fstream>

using namespace std;

// Структура для передачи данных о матрице
struct MatrixData {
    int rows;
    int cols;
};

int pipe_in[2];   // клиент -> сервер
int pipe_out[2];  // сервер -> клиент
pid_t pid;

void help() {
    cout << "Программа для вычисления ранга матрицы.\n"
         << "Использование: запустите программу без параметров.\n"
         << "Для ввода матрицы следуйте инструкциям на экране.\n"
         << "Программа использует метод Гаусса для вычисления ранга матрицы.\n";
}

// Функция обработки некорректного ввода
void uncorrect() {
    cin.clear();
    cin.ignore(numeric_limits<streamsize>::max(), '\n');
    cout << "Incorrect input. Please, try again.\n";
}

// Шаблонная функция для считывания значений различных типов
template<typename T>
T read_value(const string& message, bool positive_only = false) {
    T value;
    bool flag = true;
    while (flag) {
        cout << message << ": ";
        cin >> value;

        if (cin.fail() || cin.peek() != '\n' || (positive_only && value <= 0)) {
            uncorrect();
        }
        else {
            flag = false;
        }
    }
    return value;
}

// Функция для вычисления ранга матрицы методом Гаусса
int calculate_rank(vector<vector<double>>& matrix, int rows, int cols) {
    int rank = 0;

    vector<vector<double>> temp_matrix = matrix;
    
    // Приводим к ступенчатому виду
    const double EPS = 1e-10;
    int row = 0;
    
    for (int col = 0; col < cols; ++col) {
        // Ищем строку с ненулевым элементом в текущем столбце
        int pivot_row = -1;
        for (int i = row; i < rows; ++i) {
            if (fabs(temp_matrix[i][col]) > EPS) {
                pivot_row = i;
                break;
            }
        }
        
        if (pivot_row != -1) {
            // Обмен строк, если текущая строка не является опорной
            if (pivot_row != row) {
                swap(temp_matrix[pivot_row], temp_matrix[row]);
            }
            
            // Нормализация опорной строки
            double pivot = temp_matrix[row][col];
            for (int j = col; j < cols; ++j) {
                temp_matrix[row][j] /= pivot;
            }
            
            // Вычитаем опорную строку из всех остальных строк
            for (int i = 0; i < rows; ++i) {
                if (i != row) {
                    double factor = temp_matrix[i][col];
                    for (int j = col; j < cols; ++j) {
                        temp_matrix[i][j] -= factor * temp_matrix[row][j];
                    }
                }
            }
            
            ++rank;
            ++row;

            if (row == rows) {
                break;
            }
        }
    }
    
    return rank;
}

// Клиентская часть программы
void client() {
    // Запрашиваем размерность матрицы
    int rows = read_value<int>("Введите количество строк матрицы: ", true);
    int cols = read_value<int>("Введите количество столбцов матрицы: ", true);
    
    // Создаем и заполняем матрицу
    vector<vector<double>> matrix(rows, vector<double>(cols));
    cout << "Введите элементы матрицы:\n";
    for (int i = 0; i < rows; ++i) {
        for (int j = 0; j < cols; ++j) {
            matrix[i][j] = read_value<double>("Матрица[" + to_string(i) + "][" + to_string(j) + "]: ");
        }
    }
    
    // Отображаем введенную матрицу
    cout << "\nВведенная матрица:\n";
    for (int i = 0; i < rows; ++i) {
        for (int j = 0; j < cols; ++j) {
            cout << matrix[i][j] << "\t";
        }
        cout << endl;
    }
    
    // Передаем данные серверу
    MatrixData data = {rows, cols};
    write(pipe_in[1], &data, sizeof(MatrixData));
    
    // Передаем элементы матрицы
    for (int i = 0; i < rows; ++i) {
        for (int j = 0; j < cols; ++j) {
            write(pipe_in[1], &matrix[i][j], sizeof(double));
        }
    }
    
    // Получаем результат от сервера
    int rank;
    read(pipe_out[0], &rank, sizeof(int));
    
    // Выводим результат
    cout << "\nРанг матрицы: " << rank << endl;
    
    // Закрываем неиспользуемые концы каналов
    close(pipe_in[1]);
    close(pipe_out[0]);
    
    exit(0);
}

// Серверная часть программы
void server() {
    // Читаем данные от клиента
    MatrixData data;
    read(pipe_in[0], &data, sizeof(MatrixData));
    
    // Создаем матрицу и заполняем ее
    vector<vector<double>> matrix(data.rows, vector<double>(data.cols));
    for (int i = 0; i < data.rows; ++i) {
        for (int j = 0; j < data.cols; ++j) {
            read(pipe_in[0], &matrix[i][j], sizeof(double));
        }
    }
    
    // Вычисляем ранг
    int rank = calculate_rank(matrix, data.rows, data.cols);
    
    // Отправляем результат клиенту
    write(pipe_out[1], &rank, sizeof(int));
    
    // Закрываем неиспользуемые концы каналов
    close(pipe_in[0]);
    close(pipe_out[1]);
    
    exit(0);
}

// Дополнительная функция для загрузки матрицы из файла
bool load_matrix_from_file(const string& filename, vector<vector<double>>& matrix, int& rows, int& cols) {
    ifstream file(filename);
    if (!file.is_open()) {
        cout << "Ошибка: не удалось открыть файл " << filename << endl;
        return false;
    }

    file >> rows >> cols;
    if (cin.fail()) {
      return false;
    }
    if (rows <= 0 || cols <= 0) {
        cout << "Ошибка: некорректные размеры матрицы в файле" << endl;
        file.close();
        return false;
    }
    
    matrix.resize(rows, vector<double>(cols));
    for (int i = 0; i < rows; ++i) {
        for (int j = 0; j < cols; ++j) {
            if (!(file >> matrix[i][j])) {
                cout << "Ошибка: некорректные данные в файле" << endl;
                file.close();
                return false;
            }
        }
    }
    
    file.close();
    return true;
}

// Дополнительная функция для сохранения результата в файл
bool save_result_to_file(const string& filename, int rank, const vector<vector<double>>& matrix, int rows, int cols) {
    ofstream file(filename);
    if (!file.is_open()) {
        cout << "Ошибка: не удалось открыть файл " << filename << " для записи" << endl;
        return false;
    }
    
    file << "Исходная матрица (" << rows << "x" << cols << "):\n";
    for (int i = 0; i < rows; ++i) {
        for (int j = 0; j < cols; ++j) {
            file << matrix[i][j] << "\t";
        }
        file << "\n";
    }
    
    file << "\nРанг матрицы: " << rank << endl;
    
    file.close();
    return true;
}

// Клиентская часть программы с поддержкой файлового ввода-вывода
void client_with_file_io() {
    // Запрашиваем тип ввода
    cout << "Выберите способ ввода матрицы:\n";
    cout << "1. Ввод с клавиатуры\n";
    cout << "2. Загрузка из файла\n";
    int choice = read_value<int>("Ваш выбор: ");
    
    int rows, cols;
    vector<vector<double>> matrix;
    
    if (choice == 2) {
        // Загрузка из файла
        string filename;
        cout << "Введите имя файла: ";
        cin >> filename;
        
        if (!load_matrix_from_file(filename, matrix, rows, cols)) {
            cout << "Переключение на ручной ввод...\n";
            choice = 1;
        }
    }
    
    if (choice == 1) {
        // Ручной ввод
        rows = read_value<int>("Введите количество строк матрицы: ", true);
        cols = read_value<int>("Введите количество столбцов матрицы: ", true);
        
        matrix.resize(rows, vector<double>(cols));
        cout << "Введите элементы матрицы:\n";
        for (int i = 0; i < rows; ++i) {
            for (int j = 0; j < cols; ++j) {
                matrix[i][j] = read_value<double>("Матрица[" + to_string(i) + "][" + to_string(j) + "]: ");
            }
        }
    }
    
    // Отображаем введенную матрицу
    cout << "\nВведенная матрица:\n";
    for (int i = 0; i < rows; ++i) {
        for (int j = 0; j < cols; ++j) {
            cout << matrix[i][j] << "\t";
        }
        cout << endl;
    }
    
    // Передаем данные серверу
    MatrixData data = {rows, cols};
    write(pipe_in[1], &data, sizeof(MatrixData));
    
    // Передаем элементы матрицы
    for (int i = 0; i < rows; ++i) {
        for (int j = 0; j < cols; ++j) {
            write(pipe_in[1], &matrix[i][j], sizeof(double));
        }
    }
    
    // Получаем результат от сервера
    int rank;
    read(pipe_out[0], &rank, sizeof(int));
    
    // Выводим результат
    cout << "\nРанг матрицы: " << rank << endl;
    
    // Запрашиваем сохранение результата в файл
    cout << "Хотите сохранить результат в файл? (1 - да, 0 - нет): ";
    if (read_value<int>("") == 1) {
        string filename;
        cout << "Введите имя файла для сохранения: ";
        cin >> filename;
        if (save_result_to_file(filename, rank, matrix, rows, cols)) {
            cout << "Результат успешно сохранен в файле " << filename << endl;
        }
    }
    
    // Закрываем неиспользуемые концы каналов
    close(pipe_in[1]);
    close(pipe_out[0]);
    
    exit(0);
}

int main(int argc, char* argv[]) {
    // Устанавливаем локализацию для корректного отображения
    setlocale(LC_ALL, "");
    
    // Проверяем параметры командной строки
    if (argc == 2 && strcmp(argv[1], "--help") == 0) {
        help();
        return 0;
    } else if (argc != 1) {
        cout << "Запустите программу с ключом --help для получения справки" << endl;
        return 1;
    }
    
    // Создаем каналы
    if (pipe(pipe_in) < 0 || pipe(pipe_out) < 0) {
        perror("Ошибка при создании канала");
        return 1;
    }
    
    // Разделяем процесс на клиент и сервер
    pid = fork();
    
    if (pid < 0) {
        perror("Ошибка при вызове fork()");
        return 1;
    } else if (pid > 0) {
        // Родительский процесс - клиент
        cout << "Программа вычисления ранга матрицы\n";
        
        // Закрываем неиспользуемые концы каналов
        close(pipe_in[0]);  // Закрываем чтение из входного канала
        close(pipe_out[1]); // Закрываем запись в выходной канал
        
        // Запускаем клиентскую часть с поддержкой файлового ввода-вывода
        client_with_file_io();
    } else {
        // Дочерний процесс - сервер
        
        // Закрываем неиспользуемые концы каналов
        close(pipe_in[1]);  // Закрываем запись во входной канал
        close(pipe_out[0]); // Закрываем чтение из выходного канала
        
        // Запускаем серверную часть
        server();
    }
    
    // Закрываем все концы каналов (на случай, если не вышли из процессов)
    close(pipe_in[0]);
    close(pipe_in[1]);
    close(pipe_out[0]);
    close(pipe_out[1]);
    
    return 0;
}