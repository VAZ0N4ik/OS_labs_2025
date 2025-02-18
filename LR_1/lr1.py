def read_value(message: str, value_type: type, positive_only: bool = False):
    # Универсальная функция для считывания значений с проверкой корректности ввода
    while True:
        try:
            value = value_type(input(f"{message}: "))
            if positive_only and value <= 0:
                print("Value must be positive. Please try again.")
                continue
            return value
        except ValueError:
            print("Incorrect input. Please try again.")

def calculate_sum(first: float, ratio: float, count: int) -> float:
    # Вычисляет сумму геометрической прогрессии
    if ratio == 1:
        return first * count
    return first * (1 - ratio ** count) / (1 - ratio)

def main():
    print("Program for calculating sum of geometrical progression\n")
    flag = 'y'
    while flag == 'y' or flag == 'Y':
        # Считываем первый элемент и знаменатель прогрессии
        first = read_value("Input first element", float)
        ratio = read_value("Input ratio", float)

        # Считываем количество элементов (только положительные числа)
        count = read_value("Input count of progression elements", int, positive_only=True)

        # Вычисляем сумму
        sum_result = calculate_sum(first, ratio, count)

        # Выводим результат
        print(f"\nSum of {count} elements of geometrical progression with {first} as the first element and {ratio} as the ratio equals: {sum_result}")

        print("Do you want to continue? (y/n): ")
        flag = input()

    print("Program terminated.\n")

if __name__ == "__main__":
    main()