#include <iostream>
#include <limits>
#include <cmath>
#include <string>
using namespace std;

// Функция обработки некорректного ввода
void uncorrect() {
    // сброс флага ошибки потока ввода
    cin.clear();
    // очищаем весь буфер до символа новой строки
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

/*  Функция вычисления суммы геометрической прогрессии
    Для r = 1: используется формула S = a₁n
    Для r ≠ 1: используется формула S = a₁(1-r^n)/(1-r) */
double calculate_sum(double first, double ratio, int count) {
    if (ratio == 1) {
        return first * count;
    }
    return first * (1 - pow(ratio, count)) / (1 - ratio);
}

// Точка входа
int main() {
    cout << "Program for calculating sum of geometrical progression\n\n";

    char restart = 'y';

    do {
        // Считываем первый элемент и знаменатель прогрессии
        double first = read_value<double>("Input first element");
        double ratio = read_value<double>("Input ratio");

        // Считываем количество элементов
        int count = read_value<int>("Input count of progression elements", true);

        // Вычисляем сумму
        double sum = calculate_sum(first, ratio, count);

        // Выводим результат
        cout << "\nSum of " << count << " elements of geometrical progression with "
             << first << " as the first element and " << ratio << " as the ratio equals: " << sum << endl;

        cout << "Do you want to continue? (y/n): ";
        cin >> restart;

    } while (restart == 'y' || restart == 'Y');

    cout << "Program terminated.\n";

    return 0;
}