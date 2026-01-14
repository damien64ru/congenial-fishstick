import os

# Токен бота
TOKEN = "8339588613:AAFwvFD9KT4H79UsD0DtW1OpnRNFJ3jEmd4"

# Настройки базы данных - сохраняем в /data для persistence
DB_PATH = "/data/bot_database.db"

# ID администраторов (твои user_id)
ADMIN_IDS = [499402258]  # ЗАМЕНИ НА СВОЙ USER_ID

# Паттерны для поиска каналов в профиле
CHANNEL_PATTERNS = [
    # Telegram ссылки (самые надежные)
    r't\.me/\+[a-zA-Z0-9_-]+',                  # t.me/+invitecode
    r't\.me/[a-zA-Z0-9_]{4,32}',                # t.me/username
    r'https://t\.me/\+[a-zA-Z0-9_-]+',          # https://t.me/+invitecode
    r'https://t\.me/[a-zA-Z0-9_]{4,32}',        # https://t.me/username
    r'http://t\.me/[a-zA-Z0-9_]{4,32}',         # http://t.me/username
    r'telegram\.me/[a-zA-Z0-9_]{4,32}',         # telegram.me/username
    r'https://telegram\.me/[a-zA-Z0-9_]{4,32}', # https://telegram.me/username
    
    # TG ссылки
    r'tg://resolve\?domain=[a-zA-Z0-9_]{4,32}', # tg://resolve?domain=username
    r'tg://join\?invite=[a-zA-Z0-9_]+',         # tg://join?invite=invitecode
    
    # Общие URL паттерны
    r'https?://[^\s]+',                         # любые http/https ссылки
    
    # Ключевые слова
    r'блог',                                    # блог
    r'канал',                                   # канал
    r'channel',                                 # channel
    r'подпис',                                  # подписка, подписывайся
    r'subscribe',                               # subscribe
    r'партнер',                                 # партнер
    r'реклама',                                 # реклама
    r'продвижение',                             # продвижение
    r'заработок',                               # заработок
]

# НАСТРОЙКИ КАПЧИ (НОВОЕ)
CAPTCHA_ENABLED = True  # Вкл/выкл капчу глобально
CAPTCHA_TIMEOUT = 15    # Секунд на ответ
CAPTCHA_SIMPLE_PROBLEMS = [  # Простые примеры
    ("2+3", "5"), ("5-2", "3"), ("4*2", "8"),
    ("6/3", "2"), ("1+4", "5"), ("7-3", "4"),
    ("3+2", "5"), ("8-4", "4"), ("2*3", "6"),
    ("9/3", "3"), ("5+1", "6"), ("6-1", "5")
]

# ВАЖНО: Порядок работы системы капчи:
# 1. Сообщение всегда удаляется сразу
# 2. Если CAPTCHA_ENABLED = True → отправляется капча
# 3. Если капча пройдена → пользователь в исключения
# 4. Если капча не пройдена/таймаут → бан/предупреждение

# Настройки OCR (для будущего использования)
OCR_ENABLED = False
TESSERACT_PATH = "/usr/bin/tesseract"

# Настройки проверки медиа
CHECK_MEDIA = False