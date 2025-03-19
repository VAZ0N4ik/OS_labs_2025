#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <set>
#include <map>
#include <ctime>
#include <fstream>

using namespace std;

// Глобальные переменные
HANDLE hSemaphore; // Семафор для ограничения числа обрабатываемых клиентов
map<int, vector<double>> clientData; // Хранение данных от клиентов
map<int, vector<double>> clientResults; // Результаты обработки
int clientCounter = 0; // Счетчик клиентов
SOCKET serverSocket; // Сокет сервера
ofstream logFile; // Файл для логирования

// Функция для логирования событий
void logEvent(const string& event) {
    time_t now = time(0);
    char timeStr[26];
    ctime_s(timeStr, sizeof timeStr, &now);
    string timestamp(timeStr);
    timestamp = timestamp.substr(0, timestamp.length() - 1); // Удаление символа новой строки
    
    cout << "[" << timestamp << "] " << event << endl;
    logFile << "[" << timestamp << "] " << event << endl;
    logFile.flush();
}

// Функция для удаления дубликатов из вектора
vector<double> removeDuplicates(const vector<double>& numbers) {
    set<double> uniqueNumbers(numbers.begin(), numbers.end());
    return vector<double>(uniqueNumbers.begin(), uniqueNumbers.end());
}

// Функция для обработки соединения с клиентом
DWORD WINAPI ClientHandler(LPVOID lpParam) {
    SOCKET clientSocket = (SOCKET)lpParam;
    
    // Ожидание доступа к семафору (ограничение на 3 одновременных клиента)
    logEvent("Client waiting for server access");
    WaitForSingleObject(hSemaphore, INFINITE);

    // Получили доступ
    int clientId = ++clientCounter;
    logEvent("Client #" + to_string(clientId) + " gained access to the server");

    // Отправка ID клиенту
    send(clientSocket, to_string(clientId).c_str(), to_string(clientId).length(), 0);

    // Получение данных от клиента
    char buffer[4096];
    int bytesReceived = recv(clientSocket, buffer, sizeof(buffer), 0);

    if (bytesReceived > 0) {
        buffer[bytesReceived] = '\0';
        string data(buffer);
        logEvent("Received data from client #" + to_string(clientId) + ": " + data);

        // Парсинг данных
        vector<double> numbers;
        stringstream ss(data);
        double number;
        while (ss >> number) {
            numbers.push_back(number);
        }

        // Сохранение исходных данных
        clientData[clientId] = numbers;

        // Обработка данных - удаление дубликатов
        vector<double> uniqueNumbers = removeDuplicates(numbers);
        clientResults[clientId] = uniqueNumbers;

        // Формирование результата для отправки клиенту
        stringstream resultSS;
        resultSS << "Original array (" << numbers.size() << " elements): ";
        for (double num : numbers) {
            resultSS << num << " ";
        }
        resultSS << "\nArray without duplicates (" << uniqueNumbers.size() << " elements): ";
        for (double num : uniqueNumbers) {
            resultSS << num << " ";
        }

        string resultStr = resultSS.str();
        logEvent("Sending result to client #" + to_string(clientId));

        // Отправка результата клиенту
        send(clientSocket, resultStr.c_str(), resultStr.length(), 0);
    }

    // Закрытие соединения
    closesocket(clientSocket);
    logEvent("Connection with client #" + to_string(clientId) + " closed");

    // Освобождение семафора
    ReleaseSemaphore(hSemaphore, 1, NULL);
    return 0;
}

int main() {
    // Открываем лог-файл
    logFile.open("server_log.txt", ios::app);
    logEvent("Server started");

    // Создание семафора для ограничения числа обрабатываемых клиентов (максимум 3)
    hSemaphore = CreateSemaphore(NULL, 3, 3, TEXT("ClientLimitSemaphore"));
    if (hSemaphore == NULL) {
        logEvent("Error creating semaphore: " + to_string(GetLastError()));
        return 1;
    }

    // Инициализация Winsock
    WSADATA wsaData;
    int result = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (result != 0) {
        logEvent("WSAStartup failed: " + to_string(result));
        CloseHandle(hSemaphore);
        return 1;
    }

    // Создание сокета
    serverSocket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (serverSocket == INVALID_SOCKET) {
        logEvent("Error creating socket: " + to_string(WSAGetLastError()));
        WSACleanup();
        CloseHandle(hSemaphore);
        return 1;
    }

    // Настройка адреса сервера
    sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_addr.s_addr = INADDR_ANY;
    serverAddr.sin_port = htons(12345); // Порт для прослушивания

    // Привязка сокета к адресу
    if (bind(serverSocket, (SOCKADDR*)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR) {
        logEvent("Binding error: " + to_string(WSAGetLastError()));
        closesocket(serverSocket);
        WSACleanup();
        CloseHandle(hSemaphore);
        return 1;
    }

    // Начало прослушивания
    if (listen(serverSocket, SOMAXCONN) == SOCKET_ERROR) {
        logEvent("Listening error: " + to_string(WSAGetLastError()));
        closesocket(serverSocket);
        WSACleanup();
        CloseHandle(hSemaphore);
        return 1;
    }

    logEvent("Server waiting for connections...");

    // Бесконечный цикл обработки подключений
    while (true) {
        // Принятие подключения
        sockaddr_in clientAddr;
        int clientAddrSize = sizeof(clientAddr);
        SOCKET clientSocket = accept(serverSocket, (SOCKADDR*)&clientAddr, &clientAddrSize);

        if (clientSocket == INVALID_SOCKET) {
            logEvent("Error accepting connection: " + to_string(WSAGetLastError()));
            continue;
        }

        // Вывод информации о подключении
        char clientIP[16];
        strcpy(clientIP, inet_ntoa(clientAddr.sin_addr));
        logEvent("New connection from " + string(clientIP) + ":" + to_string(ntohs(clientAddr.sin_port)));

        // Создание потока для обработки клиента
        HANDLE hThread = CreateThread(NULL, 0, ClientHandler, (LPVOID)clientSocket, 0, NULL);
        if (hThread == NULL) {
            logEvent("Error creating thread: " + to_string(GetLastError()));
            closesocket(clientSocket);
        } else {
            CloseHandle(hThread); // Закрываем дескриптор потока, т.к. нам не нужно на него ждать
        }
    }

    // Закрытие сокета и очистка
    closesocket(serverSocket);
    WSACleanup();
    CloseHandle(hSemaphore);
    logEvent("Server stopped");
    logFile.close();
    
    return 0;
}