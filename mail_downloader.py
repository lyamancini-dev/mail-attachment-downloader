#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import imaplib
import email
import os
import sys
from datetime import datetime
from email import policy

try:
    import config
except ImportError:
    print("Ошибка: файл config.py не найден. Скопируйте config.example.py и заполните его.")
    sys.exit(1)

required_attrs = [
    'IMAP_SERVER', 'EMAIL_ADDRESS', 'PASSWORD', 'SENDER_FILTER',
    'SOURCE_FOLDER', 'SAVE_DIR'
]
for attr in required_attrs:
    if not hasattr(config, attr):
        print(f"Ошибка: в config.py отсутствует настройка {attr}")
        sys.exit(1)

IMAP_SERVER = config.IMAP_SERVER
EMAIL_ADDRESS = config.EMAIL_ADDRESS
PASSWORD = config.PASSWORD
SENDER_FILTER = config.SENDER_FILTER
SOURCE_FOLDER = config.SOURCE_FOLDER
SAVE_DIR = config.SAVE_DIR

def is_allowed_attachment(filename):
    if not filename:
        return False
    lower_filename = filename.lower()
    allowed_extensions = ('.pdf', '.xlsx', '.xls', '.docx', '.doc', '.rtf')
    return lower_filename.endswith(allowed_extensions)

def ensure_save_dir():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR, exist_ok=True)
        print(f"Создана папка {SAVE_DIR}")
    else:
        print(f"Папка {SAVE_DIR} уже существует")

def process_mailbox():
    mail = None
    try:
        print(f"Подключение к {IMAP_SERVER}...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        print("Подключено, вход...")
        mail.login(EMAIL_ADDRESS, PASSWORD)
        print("Вход выполнен успешно")
        mail.select(SOURCE_FOLDER)
        print(f"Папка '{SOURCE_FOLDER}' выбрана")

        search_query = f'UNSEEN TEXT "{SENDER_FILTER}"'
        print(f"Поиск: {search_query}")
        status, messages = mail.search(None, search_query)

        if not messages[0]:
            print("Нет новых писем от указанного отправителя.")
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

    except imaplib.IMAP4.error as e:
        print(f"Ошибка IMAP: {e}")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
    finally:
        if mail:
            mail.logout()
            print("Соединение закрыто")

if __name__ == "__main__":
    ensure_save_dir()
    process_mailbox()