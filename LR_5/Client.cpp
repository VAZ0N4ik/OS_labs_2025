#include <iostream>
#include <string>
#include <sstream>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <vector>
#include <ctime>
#include <fstream>

using namespace std;

// Глобальные переменные
ofstream logFile; // Файл для логирования

// Функция для логирования событий
void logEvent(const string& event, int clientId = -1) {
    time_t now = time(0);
    char timeStr[26];
    ctime_s(timeStr, sizeof timeStr, &now);
    string timestamp(timeStr);
    timestamp = timestamp.substr(0, timestamp.length() - 1); // Удаление символа новой строки
    
    string prefix = (clientId != -1) ? "[Client #" + to_string(clientId) + "] " : "";

    cout << "[" << timestamp << "] " << prefix << event << endl;
    logFile << "[" << timestamp << "] " << prefix << event << endl;
    logFile.flush();
}

int main() {
    // Открываем лог-файл
    logFile.open("client_log.txt", ios::app);
    logEvent("Client started");

    // Инициализация Winsock
    WSADATA wsaData;
    int result = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (result != 0) {
        logEvent("WSAStartup failed: " + to_string(result));
        return 1;
    }

    // Создание сокета
    SOCKET clientSocket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (clientSocket == INVALID_SOCKET) {
        logEvent("Error creating socket: " + to_string(WSAGetLastError()));
        WSACleanup();
        return 1;
    }

    // Настройка адреса сервера
    sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_addr.s_addr = inet_addr("127.0.0.1"); // IP-адрес сервера (localhost)
    serverAddr.sin_port = htons(12345); // Порт сервера

    // Подключение к серверу
    logEvent("Attempting to connect to server...");
    if (connect(clientSocket, (SOCKADDR*)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR) {
        logEvent("Error connecting to server: " + to_string(WSAGetLastError()));
        closesocket(clientSocket);
        WSACleanup();
        return 1;
    }

    logEvent("Connection to server established");

    // Получение ID от сервера
    char idBuffer[16];
    int bytesReceived = recv(clientSocket, idBuffer, sizeof(idBuffer), 0);
    idBuffer[bytesReceived] = '\0';
    int clientId = atoi(idBuffer);

    logEvent("Received ID from server: " + to_string(clientId), clientId);

    // Ввод массива чисел
    cout << "\nInsert array elements (numbers separated with spaces):" << endl;
    cout << "To finish input, press Enter > ";

    string input;
    getline(cin, input);

    logEvent("Array entered: " + input, clientId);

    // Проверка корректности ввода
    stringstream ss(input);
    vector<double> numbers;
    double num;
    while (ss >> num) {
        numbers.push_back(num);
    }

    if (numbers.empty()) {
        logEvent("Error: empty array entered", clientId);
        cout << "Error: empty array entered" << endl;
        closesocket(clientSocket);
        WSACleanup();
        logFile.close();
        return 1;
    }

    // Отправка данных на сервер
    logEvent("Sending data to server", clientId);
    if (send(clientSocket, input.c_str(), input.length(), 0) == SOCKET_ERROR) {
        logEvent("Error sending data: " + to_string(WSAGetLastError()), clientId);
        closesocket(clientSocket);
        WSACleanup();
        return 1;
    }

    // Получение ответа от сервера
    char buffer[4096];
    bytesReceived = recv(clientSocket, buffer, sizeof(buffer), 0);

    if (bytesReceived > 0) {
        buffer[bytesReceived] = '\0';
        string response(buffer);

        logEvent("Response received from server", clientId);
        cout << "\nResult received from server:\n" << response << endl;
    } else {
        logEvent("Error receiving response from server", clientId);
    }

    // Закрытие сокета и очистка
    closesocket(clientSocket);
    WSACleanup();

    logEvent("Client terminating", clientId);
    logFile.close();
    
    cout << "\nPress Enter to exit..." << endl;
    cin.get();

    return 0;
}