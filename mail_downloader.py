#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import imaplib
import email
import os
import subprocess
import sys
from datetime import datetime
from email import policy
import time

# Импорт настроек из отдельного файла
try:
    import config
except ImportError:
    print("Ошибка: файл config.py не найден. Скопируйте config.example.py и заполните его.")
    sys.exit(1)

# Проверка обязательных настроек
required_attrs = [
    'IMAP_SERVER', 'EMAIL_ADDRESS', 'PASSWORD', 'SENDER_FILTER',
    'SOURCE_FOLDER', 'NETWORK_PATH_TO_MOUNT', 'SAVE_DIR',
    'NETWORK_LOGIN', 'NETWORK_PASSWORD'
]
if sys.platform == 'win32':
    required_attrs.append('TEMP_DRIVE_LETTER')
else:
    required_attrs.append('MOUNT_POINT')

for attr in required_attrs:
    if not hasattr(config, attr):
        print(f"Ошибка: в config.py отсутствует настройка {attr}")
        sys.exit(1)

# Константы из config
IMAP_SERVER = config.IMAP_SERVER
EMAIL_ADDRESS = config.EMAIL_ADDRESS
PASSWORD = config.PASSWORD
SENDER_FILTER = config.SENDER_FILTER
SOURCE_FOLDER = config.SOURCE_FOLDER
NETWORK_PATH_TO_MOUNT = config.NETWORK_PATH_TO_MOUNT
SAVE_DIR = config.SAVE_DIR
NETWORK_LOGIN = config.NETWORK_LOGIN
NETWORK_PASSWORD = config.NETWORK_PASSWORD

# Платформозависимые параметры
if sys.platform == 'win32':
    TEMP_DRIVE_LETTER = config.TEMP_DRIVE_LETTER
    MOUNT_POINT = None
else:
    MOUNT_POINT = config.MOUNT_POINT
    TEMP_DRIVE_LETTER = None

# --------------------------------------------------

def is_allowed_attachment(filename):
    """Разрешённые форматы: PDF, Excel, Word"""
    if not filename:
        return False
    lower_filename = filename.lower()
    allowed_extensions = ('.pdf', '.xlsx', '.xls', '.docx', '.doc', '.rtf')
    return lower_filename.endswith(allowed_extensions)

def mount_network_share():
    """Подключает сетевую папку (Windows или Linux)"""
    if sys.platform == 'win32':
        # Отключаем ранее использованную букву
        subprocess.run(f'net use {TEMP_DRIVE_LETTER} /delete /y', shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Подключаем
        cmd = f'net use {TEMP_DRIVE_LETTER} "{NETWORK_PATH_TO_MOUNT}" /user:{NETWORK_LOGIN} {NETWORK_PASSWORD} /persistent:no'
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"Сетевой диск {TEMP_DRIVE_LETTER} подключен.")
    else:
        # Linux: mount -t cifs
        if not os.path.exists(MOUNT_POINT):
            os.makedirs(MOUNT_POINT, exist_ok=True)
        # Отмонтируем, если уже смонтировано
        subprocess.run(f'umount {MOUNT_POINT}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Монтируем
        cmd = f'mount -t cifs "{NETWORK_PATH_TO_MOUNT}" "{MOUNT_POINT}" -o username={NETWORK_LOGIN},password={NETWORK_PASSWORD},uid={os.getuid()},gid={os.getgid()},file_mode=0777,dir_mode=0777'
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"Сетевая папка {NETWORK_PATH_TO_MOUNT} смонтирована в {MOUNT_POINT}")

def unmount_network_share():
    """Отключает сетевую папку"""
    if sys.platform == 'win32':
        subprocess.run(f'net use {TEMP_DRIVE_LETTER} /delete /y', shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Диск {TEMP_DRIVE_LETTER} отключён.")
    else:
        subprocess.run(f'umount {MOUNT_POINT}', shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Точка монтирования {MOUNT_POINT} отключена.")

def ensure_network_path_is_ready():
    """Подключает ресурс и создаёт целевую папку, если нужно"""
    mount_network_share()
    # Пауза, чтобы файловая система стала доступна (для Linux)
    time.sleep(1)
    # Создаём SAVE_DIR, если не существует
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR, exist_ok=True)
        print(f"Создана папка {SAVE_DIR}")

def process_mailbox():
    """Основная логика: поиск писем, сохранение вложений, пометка прочитанными"""
    mail = None
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, PASSWORD)
        mail.select(SOURCE_FOLDER)

        search_query = f'UNSEEN TEXT "{SENDER_FILTER}"'
        print(f"Поиск: {search_query}")
        status, messages = mail.search(None, search_query)

        if not messages[0]:
            print("Нет новых писем.")
            mail.logout()
            return

        uids = messages[0].split()
        print(f"Найдено писем: {len(uids)}")

        for num in uids:
            status, data = mail.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1], policy=policy.default)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"{timestamp}_{SENDER_FILTER.split('@')[0]}"
            attachment_saved = False

            for part in msg.walk():
                if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is None:
                    continue
                filename_original = part.get_filename()
                if not filename_original:
                    continue
                if is_allowed_attachment(filename_original):
                    new_filename = f"{base_filename}_{filename_original}"
                    filepath = os.path.join(SAVE_DIR, new_filename)
                    with open(filepath, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                    print(f"Сохранён: {new_filename}")
                    attachment_saved = True

            if attachment_saved:
                mail.store(num, '+FLAGS', '\\Seen')
                print(f"Письмо {num} помечено прочитанным.")

        mail.logout()

    except imaplib.IMAP4.error as e:
        print(f"Ошибка IMAP: {e}")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
    finally:
        unmount_network_share()

if __name__ == "__main__":
    ensure_network_path_is_ready()
    process_mailbox()