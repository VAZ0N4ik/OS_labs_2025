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

void displayHelp() {
    cout << "Available commands:" << endl;
    cout << "  color <colorname> - Change client console background color" << endl;
    cout << "  reset - Reset client console to original color" << endl;
    cout << "  help - Display this help message" << endl;
    cout << "  exit - Close the connection and exit" << endl;
    cout << "\nAvailable colors: " << endl;

    int count = 0;
    for (auto const& color : colorCodes) {
        cout << color.first;
        count++;
        if (count % 4 == 0) {
            cout << endl;
        } else {
            cout << "\t";
        }
    }
    cout << endl;
}

// Проверка результата операций с сокетами
bool checkSocketOperation(int result, const char* operationName) {
    if (result == SOCKET_ERROR) {
        cerr << operationName << " failed with error: " << WSAGetLastError() << endl;
        return false;
    }
    return true;
}

int main() {
    // Инициализация библиотеки Winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        cerr << "WSAStartup failed with error: " << WSAGetLastError() << endl;
        return 1;
    }

    // Создание сокета
    SOCKET serverSocket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (serverSocket == INVALID_SOCKET) {
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

    // Привязка сокета к адресу
    if (bind(serverSocket, (SOCKADDR*)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR) {
        cerr << "Bind failed with error: " << WSAGetLastError() << endl;
        closesocket(serverSocket);
        WSACleanup();
        return 1;
    }

    // Ожидание соединений
    if (listen(serverSocket, 1) == SOCKET_ERROR) {
        cerr << "Listen failed with error: " << WSAGetLastError() << endl;
        closesocket(serverSocket);
        WSACleanup();
        return 1;
    }

    cout << "Server started. Creating client process..." << endl;

    // Запуск клиентского процесса
    STARTUPINFO si;
    PROCESS_INFORMATION pi;

    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    // Путь к клиентскому приложению
    const char* clientPath = "Client.exe";

    // Создаем копию пути, т.к. CreateProcess может модифицировать параметр
    char cmdLine[256];
    strncpy(cmdLine, clientPath, sizeof(cmdLine) - 1);
    cmdLine[sizeof(cmdLine) - 1] = '\0';

    // Запуск процесса с помощью ASCII-версии функции
    if (!CreateProcessA(
        NULL,           // Имя приложения
        cmdLine,        // Командная строка
        NULL,           // Атрибуты безопасности процесса
        NULL,           // Атрибуты безопасности потока
        FALSE,          // Наследование дескрипторов
        CREATE_NEW_CONSOLE,  // Флаги создания (новая консоль)
        NULL,           // Среда процесса
        NULL,           // Текущая директория
        &si,            // Информация о запуске
        &pi)            // Информация о процессе
    ) {
        cerr << "CreateProcess failed with error: " << GetLastError() << endl;
        closesocket(serverSocket);
        WSACleanup();
        return 1;
    }

    cout << "Client process created. Waiting for connection..." << endl;

    // Ожидание подключения клиента
    sockaddr_in clientAddr;
    int clientAddrSize = sizeof(clientAddr);
    SOCKET clientSocket = accept(serverSocket, (SOCKADDR*)&clientAddr, &clientAddrSize);

    if (clientSocket == INVALID_SOCKET) {
        cerr << "Accept failed with error: " << WSAGetLastError() << endl;
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        closesocket(serverSocket);
        WSACleanup();
        return 1;
    }

    cout << "Client connected. Type 'help' for available commands." << endl;

    // Основной цикл обработки команд
    string command;
    bool connected = true;

    while (connected) {
        cout << "\nEnter command: ";
        getline(cin, command);

        if (command == "exit") {
            cout << "Closing connection and exiting..." << endl;
            connected = false;
        }
        else if (command == "help") {
            displayHelp();
            continue;  // Не отправляем команду 'help' клиенту
        }
        else if (command.substr(0, 5) == "color") {
            string colorName;
            if (command.length() > 6) {
                colorName = command.substr(6);
                if (colorCodes.find(colorName) == colorCodes.end()) {
                    cout << "Unknown color: " << colorName << endl;
                    cout << "Type 'help' to see available colors." << endl;
                    continue;
                }
            }
            else {
                cout << "Please specify a color. Type 'help' to see available colors." << endl;
                continue;
            }
        }
        else if (command != "reset") {
            cout << "Unknown command. Type 'help' for available commands." << endl;
            continue;
        }

        // Отправка команды клиенту
        if (send(clientSocket, command.c_str(), command.length(), 0) == SOCKET_ERROR) {
            cerr << "Send failed with error: " << WSAGetLastError() << endl;
            connected = false;
        }
        else {
            // Если команда не exit, ожидаем ответ от клиента
            if (command != "exit") {
                char buffer[512] = {0};
                int bytesReceived = recv(clientSocket, buffer, sizeof(buffer), 0);

                if (bytesReceived > 0) {
                    cout << "Client response: " << buffer << endl;
                }
                else if (bytesReceived == 0) {
                    cout << "Connection closed by client." << endl;
                    connected = false;
                }
                else {
                    cerr << "Recv failed with error: " << WSAGetLastError() << endl;
                    connected = false;
                }
            }
        }
    }

    // Закрытие сокетов и очистка ресурсов
    closesocket(clientSocket);
    closesocket(serverSocket);
    WSACleanup();

    // Ожидание завершения клиентского процесса
    WaitForSingleObject(pi.hProcess, 1000);  // Ждем до 1 секунды

    // Завершаем процесс клиента, если он еще работает
    TerminateProcess(pi.hProcess, 0);

    // Освобождаем дескрипторы
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    return 0;
}