# config.example.py
# Скопируйте этот файл как config.py и заполните своими данными.

# --- Почтовые настройки (Яндекс) ---
IMAP_SERVER = "imap.yandex.ru"
EMAIL_ADDRESS = "your_email@sochi.com"
# Используйте пароль приложения Яндекса!
PASSWORD = "your_app_password"

SENDER_FILTER = "result@arhimed.clinic"
SOURCE_FOLDER = "inbox"

# --- Путь для сохранения вложений (внутри контейнера, где смонтирована сетевая папка) ---
SAVE_DIR = "/mnt/share/Cytology"