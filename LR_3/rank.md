# Метод вычисления ранга матрицы

## Определение ранга матрицы

Рангом матрицы называется наибольшее число линейно независимых строк или столбцов матрицы. Ранг матрицы является важной характеристикой, которая используется в различных областях линейной алгебры, например, при решении систем линейных уравнений, определении базиса линейного пространства, и т.д.

## Метод Гаусса для вычисления ранга

Для вычисления ранга матрицы в программе используется метод Гаусса (также известный как метод последовательного исключения или метод элементарных преобразований).

Основные шаги метода Гаусса для вычисления ранга матрицы:

1. **Приведение матрицы к ступенчатому виду**:
    - Находим первый ненулевой элемент в первом столбце (опорный элемент).
    - Делим всю строку на этот элемент, чтобы получить 1 на месте опорного элемента.
    - Вычитаем из всех остальных строк эту строку, умноженную на соответствующий элемент в том же столбце, чтобы получить нули под опорным элементом.
    - Повторяем процесс для следующих столбцов и строк.

2. **Подсчет ненулевых строк** в полученной ступенчатой матрице. Это количество и будет равно рангу матрицы.

## Псевдокод алгоритма

```
function calculate_rank(matrix, rows, cols):
    rank = 0
    row = 0
    
    for col = 0 to cols-1:
        // Ищем строку с ненулевым элементом в текущем столбце
        pivot_row = -1
        for i = row to rows-1:
            if matrix[i][col] != 0:
                pivot_row = i
                break
        
        if pivot_row != -1:
            // Меняем местами строки, если нужно
            if pivot_row != row:
                swap(matrix[pivot_row], matrix[row])
            
            // Нормируем опорную строку
            pivot = matrix[row][col]
            for j = col to cols-1:
                matrix[row][j] /= pivot
            
            // Обнуляем элементы ниже опорного
            for i = 0 to rows-1:
                if i != row:
                    factor = matrix[i][col]
                    for j = col to cols-1:
                        matrix[i][j] -= factor * matrix[row][j]
            
            rank += 1
            row += 1
            
            // Если обработали все строки, выходим
            if row == rows:
                break
    
    return rank
```

## Пример вычисления ранга матрицы

Рассмотрим пример вычисления ранга для матрицы:
```
1  2  3
4  5  6
7  8  9
```

1. **Первый шаг**: выбираем опорный элемент (1) в позиции (0,0).
    - Нормализуем первую строку: `(1, 2, 3)`
    - Вычитаем из второй строки: `(4, 5, 6) - 4*(1, 2, 3) = (0, -3, -6)`
    - Вычитаем из третьей строки: `(7, 8, 9) - 7*(1, 2, 3) = (0, -6, -12)`
    - Получаем матрицу:
      ```
      1  2   3
      0 -3  -6
      0 -6 -12
      ```

2. **Второй шаг**: выбираем опорный элемент (-3) в позиции (1,1).
    - Нормализуем вторую строку: `(0, -3, -6) / (-3) = (0, 1, 2)`
    - Вычитаем из третьей строки: `(0, -6, -12) - (-6)*(0, 1, 2) = (0, 0, 0)`
    - Получаем матрицу:
      ```
      1  2  3
      0  1  2
      0  0  0
      ```

3. В результате у нас получилась ступенчатая форма с двумя ненулевыми строками, следовательно, ранг матрицы равен 2.

## Особенности реализации

В реализации алгоритма в коде есть несколько важных моментов:

1. **Обработка погрешностей вычислений** - при работе с числами с плавающей точкой могут возникать небольшие погрешности. Поэтому для сравнения с нулем используется небольшая константа `EPS`.

2. **Выбор опорного элемента** - в каждом столбце ищется первый ненулевой элемент, начиная с текущей строки.

3. **Нормализация строк** - опорный элемент приводится к единице, а затем все элементы в этой строке делятся на него.

4. **Вычитание строк** - для каждой строки, кроме опорной, вычитается опорная строка, умноженная на элемент в столбце опорного элемента.

5. **Подсчет ранга** - ранг увеличивается на 1 каждый раз, когда находится новый опорный элемент.

## Применение

Вычисление ранга матрицы находит применение во многих областях:

- Решение систем линейных уравнений
- Определение количества линейно независимых векторов в наборе
- Анализ линейной зависимости в наборе данных
- Определение размерности подпространства
- Анализ матриц в приложениях машинного обучения и компьютерного зрения

В данной программе реализована возможность вычисления ранга матрицы, заданной пользователем, с использованием межпроцессного взаимодействия через неименованные каналы в операционной системе Linux.