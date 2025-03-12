#include <iostream>
#include <winsock2.h>  // Этот заголовок должен идти перед windows.h
#include <windows.h>
#include <string>
#include <map>
#include <ws2tcpip.h> // Для совместимости с TCP/IP функциями
using namespace std;

// Доступные цвета консоли
map<string, int> colorCodes = {
    {"black", 0},
    {"blue", 1},
    {"green", 2},
    {"cyan", 3},
    {"red", 4},
    {"magenta", 5},
    {"yellow", 6},
    {"white", 7},
    {"gray", 8},
    {"brightblue", 9},
    {"brightgreen", 10},
    {"brightcyan", 11},
    {"brightred", 12},
    {"brightmagenta", 13},
    {"brightyellow", 14},
    {"brightwhite", 15}
};

// Функция для изменения цвета фона консоли
bool changeConsoleColor(const string& colorName) {
    HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);
    if (hConsole == INVALID_HANDLE_VALUE) {
        return false;
    }

    // Получение текущих атрибутов консоли
    CONSOLE_SCREEN_BUFFER_INFO csbi;
    if (!GetConsoleScreenBufferInfo(hConsole, &csbi)) {
        return false;
    }

    // Текущий цвет текста (сохраняем)
    int textColor = csbi.wAttributes & 0x0F;

    // Новый цвет фона
    int bgColor = colorCodes[colorName] << 4;

    // Установка нового цвета (сохраняем цвет текста, меняем только фон)
    WORD newAttributes = bgColor | textColor;
    if (!SetConsoleTextAttribute(hConsole, newAttributes)) {
        return false;
    }

    // Очистка консоли для применения нового цвета ко всему экрану
    DWORD length = csbi.dwSize.X * csbi.dwSize.Y;
    COORD coordScreen = { 0, 0 };
    DWORD charsWritten;

    // Убедимся, что весь буфер заполнен пробелами
    FillConsoleOutputCharacter(hConsole, ' ', length, coordScreen, &charsWritten);

    // Заполним весь буфер новыми атрибутами цвета
    FillConsoleOutputAttribute(hConsole, newAttributes, length, coordScreen, &charsWritten);

    // Перемещаем курсор в начало
    SetConsoleCursorPosition(hConsole, coordScreen);

    // Сбрасываем буфер вывода, чтобы изменения стали видны немедленно
    FlushConsoleInputBuffer(GetStdHandle(STD_INPUT_HANDLE));

    // Выводим текст, чтобы обновить экран
    system("cls");
    cout << "Console color changed to " << colorName << endl;
    cout << "Waiting for commands from server..." << endl;

    return true;
}

// Хранение изначального цвета консоли
WORD originalAttributes = 0;

// Функция для сохранения изначального цвета консоли
void saveOriginalConsoleColor() {
    HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);
    CONSOLE_SCREEN_BUFFER_INFO csbi;

    if (GetConsoleScreenBufferInfo(hConsole, &csbi)) {
        originalAttributes = csbi.wAttributes;
    }
}

// Функция для восстановления изначального цвета консоли
bool resetConsoleColor() {
    if (originalAttributes == 0) {
        return false;
    }

    HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);
    if (hConsole == INVALID_HANDLE_VALUE) {
        return false;
    }

    // Получение текущих атрибутов консоли
    CONSOLE_SCREEN_BUFFER_INFO csbi;
    if (!GetConsoleScreenBufferInfo(hConsole, &csbi)) {
        return false;
    }

    // Установка изначального цвета
    if (!SetConsoleTextAttribute(hConsole, originalAttributes)) {
        return false;
    }

    // Очистка консоли для применения нового цвета ко всему экрану
    DWORD length = csbi.dwSize.X * csbi.dwSize.Y;
    COORD coordScreen = { 0, 0 };
    DWORD charsWritten;

    // Заполним весь буфер пробелами
    FillConsoleOutputCharacter(hConsole, ' ', length, coordScreen, &charsWritten);

    // Заполним весь буфер оригинальными атрибутами цвета
    FillConsoleOutputAttribute(hConsole, originalAttributes, length, coordScreen, &charsWritten);

    // Перемещаем курсор в начало
    SetConsoleCursorPosition(hConsole, coordScreen);

    // Сбрасываем буфер ввода
    FlushConsoleInputBuffer(GetStdHandle(STD_INPUT_HANDLE));

    // Очищаем экран и выводим сообщение
    system("cls");
    cout << "Console color reset to original" << endl;
    cout << "Waiting for commands from server..." << endl;

    return true;
}

int main() {
    // Сохраняем изначальный цвет консоли
    saveOriginalConsoleColor();

    // Инициализация библиотеки Winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        cerr << "WSAStartup failed with error: " << WSAGetLastError() << endl;
        return 1;
    }

    // Создание сокета
    SOCKET clientSocket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (clientSocket == INVALID_SOCKET) {
        cerr << "Socket creation failed with error: " << WSAGetLastError() << endl;
        WSACleanup();
        return 1;
    }

    // Настройка адреса сервера
    sockaddr_in serverAddr;
    memset(&serverAddr, 0, sizeof(serverAddr));
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_addr.s_addr = inet_addr("127.0.0.1");
    serverAddr.sin_port = htons(8888);

    cout << "Client started. Connecting to server..." << endl;

    // Подключение к серверу
    if (connect(clientSocket, (SOCKADDR*)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR) {
        cerr << "Connection failed with error: " << WSAGetLastError() << endl;
        closesocket(clientSocket);
        WSACleanup();
        return 1;
    }

    // Сохраняем информацию о начальном состоянии консоли
    HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);
    CONSOLE_SCREEN_BUFFER_INFO csbi;
    if (GetConsoleScreenBufferInfo(hConsole, &csbi)) {
        originalAttributes = csbi.wAttributes;
    }

    system("cls"); // Очищаем экран
    cout << "Connected to server. Waiting for commands..." << endl;
    cout << "This client can change its console background color based on server commands." << endl;

    // Основной цикл получения команд от сервера
    char buffer[512];
    bool connected = true;

    while (connected) {
        // Очистка буфера
        memset(buffer, 0, sizeof(buffer));

        // Получение команды от сервера
        int bytesReceived = recv(clientSocket, buffer, sizeof(buffer) - 1, 0);

        if (bytesReceived > 0) {
            string command(buffer);
            string response;

            cout << "Received command: " << command << endl;

            // Обработка команды
            if (command == "exit") {
                cout << "Server requested to close the connection. Exiting..." << endl;
                connected = false;
                response = "Client is shutting down";
            }
            else if (command.substr(0, 5) == "color") {
                string colorName = command.substr(6);
                if (colorCodes.find(colorName) != colorCodes.end()) {
                    // Немедленно меняем цвет до отправки ответа серверу
                    if (changeConsoleColor(colorName)) {
                        response = "Color changed to " + colorName;
                        // Не выводим сообщение здесь, т.к. оно уже выведено в функции changeConsoleColor
                    }
                    else {
                        response = "Failed to change color";
                        cerr << response << endl;
                    }
                }
                else {
                    response = "Unknown color: " + colorName;
                    cerr << response << endl;
                }
            }
            else if (command == "reset") {
                if (resetConsoleColor()) {
                    response = "Console color reset to original";
                    // Не выводим сообщение здесь, т.к. оно уже выведено в функции resetConsoleColor
                }
                else {
                    response = "Failed to reset console color";
                    cerr << response << endl;
                }
            }
            else {
                response = "Unknown command: " + command;
                cerr << response << endl;
            }
            
            // Отправка ответа серверу
            if (connected) {
                if (send(clientSocket, response.c_str(), response.length(), 0) == SOCKET_ERROR) {
                    cerr << "Send failed with error: " << WSAGetLastError() << endl;
                    connected = false;
                }
            }
        }
        else if (bytesReceived == 0) {
            cout << "Connection closed by server." << endl;
            connected = false;
        }
        else {
            cerr << "Recv failed with error: " << WSAGetLastError() << endl;
            connected = false;
        }
    }

    // Восстанавливаем изначальный цвет консоли перед выходом
    resetConsoleColor();

    // Закрытие сокета и очистка ресурсов
    closesocket(clientSocket);
    WSACleanup();

    cout << "Press any key to exit..." << endl;
    cin.get();

    return 0;
}