#include <iostream>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <string>
#include <cstring>
#include <time.h>

using namespace std;

// Размер буфера для копирования файлов
const int BUFFER_SIZE = 4096;

void printHelp() {
    cout << "File Operations Program\n\n"
         << "Usage from command line:\n"
         << "  --copy source_file dest_file   : Copy file\n"
         << "  --move source_file dest_file   : Move file\n"
         << "  --info file_name               : Get file information\n"
         << "  --chmod file_name mode         : Change file permissions\n"
         << "  --help                         : Show this help\n\n"
         << "Usage from console:\n"
         << "  Run program without arguments and follow prompts\n";
}

// Копирование файла с использованием блочного чтения/записи
bool copyFile(const char* source, const char* dest) {
    int fd_source = open(source, O_RDONLY);
    if (fd_source == -1) {
        cout << "Error opening source file\n";
        return false;
    }

    int fd_dest = open(dest, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd_dest == -1) {
        close(fd_source);
        cout << "Error creating destination file\n";
        return false;
    }

    char buffer[BUFFER_SIZE];
    ssize_t bytes_read;

    while ((bytes_read = read(fd_source, buffer, BUFFER_SIZE)) > 0) {
        if (write(fd_dest, buffer, bytes_read) != bytes_read) {
            close(fd_source);
            close(fd_dest);
            cout << "Error writing to destination file\n";
            return false;
        }
    }

    close(fd_source);
    close(fd_dest);
    return bytes_read != -1;
}

// Получение информации о файле
void getFileInfo(const char* filename) {
    struct stat file_stat;

    if (stat(filename, &file_stat) == -1) {
        cout << "Error getting file information\n";
        return;
    }

    cout << "File: " << filename << "\n"
         << "Size: " << file_stat.st_size << " bytes\n"
         << "Permissions: " << (file_stat.st_mode & 0777) << "\n"
         << "Last modified: " << ctime(&file_stat.st_mtime);
}

// Изменение прав доступа к файлу
bool changePermissions(const char* filename, mode_t mode) {
    return chmod(filename, mode) != -1;
}

// Перемещение файла
bool moveFile(const char* source, const char* dest) {
    if (rename(source, dest) == -1) {
        // Если перемещение не удалось, пробуем копировать и удалить
        if (copyFile(source, dest)) {
            return unlink(source) != -1;
        }
        return false;
    }
    return true;
}

// Консольный интерфейс
void consoleInterface() {
    while (true) {
        cout << "\nFile Operations:\n"
             << "1. Copy file\n"
             << "2. Move file\n"
             << "3. Get file information\n"
             << "4. Change file permissions\n"
             << "5. Exit\n"
             << "Choose operation (1-5): ";

        int choice;
        cin >> choice;

        if (choice == 5) break;

        string source, dest;
        mode_t mode;

        switch (choice) {
            case 1:
                cout << "Enter source file: ";
                cin >> source;
                cout << "Enter destination file: ";
                cin >> dest;
                if (copyFile(source.c_str(), dest.c_str())) {
                    cout << "File copied successfully\n";
                }
                break;

            case 2:
                cout << "Enter source file: ";
                cin >> source;
                cout << "Enter destination file: ";
                cin >> dest;
                if (moveFile(source.c_str(), dest.c_str())) {
                    cout << "File moved successfully\n";
                }
                break;

            case 3:
                cout << "Enter filename: ";
                cin >> source;
                getFileInfo(source.c_str());
                break;

            case 4:
                cout << "Enter filename: ";
                cin >> source;
                cout << "Enter new permissions (octal): ";
                cin >> oct >> mode;
                if (changePermissions(source.c_str(), mode)) {
                    cout << "Permissions changed successfully\n";
                }
                break;

            default:
                cout << "Invalid choice\n";
        }
    }
}

int main(int argc, char* argv[]) {
    if (argc == 1) {
        consoleInterface();
        return 0;
    }

    string command = argv[1];

    if (command == "--help") {
        printHelp();
    }
    else if (command == "--copy" && argc == 4) {
        if (copyFile(argv[2], argv[3])) {
            cout << "File copied successfully\n";
        }
    }
    else if (command == "--move" && argc == 4) {
        if (moveFile(argv[2], argv[3])) {
            cout << "File moved successfully\n";
        }
    }
    else if (command == "--info" && argc == 3) {
        getFileInfo(argv[2]);
    }
    else if (command == "--chmod" && argc == 4) {
        mode_t mode;
        sscanf(argv[3], "%o", &mode);
        if (changePermissions(argv[2], mode)) {
            cout << "Permissions changed successfully\n";
        }
    }
    else {
        cout << "Invalid arguments. Use --help for usage information.\n";
    }

    return 0;
}