# Загрузчик вложений из почты

Кроссплатформенный скрипт (Windows/Linux) для скачивания вложений (PDF, Excel, Word) из новых писем указанного отправителя, сохраняет их в сетевую папку SMB и помечает письма прочитанными.

## Установка на Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install -y python3 python3-pip cifs-utils