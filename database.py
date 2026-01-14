import sqlite3
import json
import os
from datetime import datetime, timedelta
from config import DB_PATH

class Database:
    def __init__(self):
        # Создаем папку /data если её нет
        os.makedirs('/data', exist_ok=True)
        self.init_db()
    
    def init_db(self):
        """Инициализация базы данных"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Таблица настроек пользователей (для лс бота)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    automod_enabled BOOLEAN DEFAULT 1,
                    action_type TEXT DEFAULT 'ban',
                    check_profiles BOOLEAN DEFAULT 1,
                    check_media BOOLEAN DEFAULT 0,
                    notify_admin BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица стоп-слов пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stop_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    word TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_settings (user_id)
                )
            ''')
            
            # Таблица логов по группам
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    chat_id INTEGER,
                    banned_user_id INTEGER,
                    banned_username TEXT,
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица чатов где работает бот
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_chats (
                    chat_id INTEGER PRIMARY KEY,
                    chat_title TEXT,
                    admin_id INTEGER,
                    automod_enabled BOOLEAN DEFAULT 1,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица забаненных пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS banned_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    chat_id INTEGER,
                    chat_title TEXT,
                    banned_by INTEGER,
                    reason TEXT,
                    banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица исключений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_exceptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    chat_id INTEGER,
                    admin_id INTEGER,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица уведомлений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    chat_id INTEGER,
                    chat_title TEXT,
                    user_id INTEGER,
                    username TEXT,
                    reason TEXT,
                    message_id INTEGER,
                    resolved BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def get_user_settings(self, user_id):
        """Получить настройки пользователя"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM user_settings WHERE user_id = ?', 
                (user_id,)
            )
            result = cursor.fetchone()
            
            if result:
                return {
                    'user_id': result[0],
                    'automod_enabled': bool(result[1]),
                    'action_type': result[2],
                    'check_profiles': bool(result[3]),
                    'check_media': bool(result[4]),
                    'notify_admin': bool(result[5]),
                    'created_at': result[6]
                }
            
            # Создаем настройки по умолчанию
            self.create_user_settings(user_id)
            return self.get_user_settings(user_id)
    
    def get_chat_settings(self, chat_id):
        """Получить настройки конкретного чата"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT chat_id, chat_title, automod_enabled FROM bot_chats WHERE chat_id = ?',
                (chat_id,)
            )
            result = cursor.fetchone()
            
            if result:
                return {
                    'chat_id': result[0],
                    'chat_title': result[1],
                    'automod_enabled': bool(result[2])
                }
            return None
    
    def create_user_settings(self, user_id):
        """Создать настройки для пользователя"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_settings (user_id, automod_enabled, action_type, check_profiles, check_media, notify_admin)
                VALUES (?, 1, 'ban', 1, 0, 1)
            ''', (user_id,))
            conn.commit()
    
    def update_user_setting(self, user_id, setting, value):
        """Обновить настройку пользователя"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'UPDATE user_settings SET {setting} = ? WHERE user_id = ?',
                (value, user_id)
            )
            conn.commit()
    
    def get_stop_words(self, user_id):
        """Получить стоп-слова пользователя"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT word FROM stop_words WHERE user_id = ? ORDER BY created_at',
                (user_id,)
            )
            return [row[0] for row in cursor.fetchall()]
    
    def add_stop_word(self, user_id, word):
        """Добавить стоп-слово"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Проверяем нет ли уже такого слова
            cursor.execute(
                'SELECT id FROM stop_words WHERE user_id = ? AND word = ?',
                (user_id, word.lower())
            )
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO stop_words (user_id, word) VALUES (?, ?)',
                    (user_id, word.lower())
                )
                conn.commit()
                return True
            return False
    
    def remove_stop_word(self, user_id, word):
        """Удалить конкретное стоп-слово"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM stop_words WHERE user_id = ? AND word = ?',
                (user_id, word.lower())
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def clear_stop_words(self, user_id):
        """Очистить все стоп-слова"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM stop_words WHERE user_id = ?',
                (user_id,)
            )
            conn.commit()
    
    def get_popular_stop_words(self, limit=20):
        """Получить популярные стоп-слова всех пользователей"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT word, COUNT(DISTINCT user_id) as user_count
                FROM stop_words 
                GROUP BY word 
                ORDER BY user_count DESC, word ASC
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()
    
    def add_log(self, user_id, chat_id, banned_user_id, banned_username, reason):
        """Добавить запись в логи"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO logs (user_id, chat_id, banned_user_id, banned_username, reason)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, chat_id, banned_user_id, banned_username, reason))
            conn.commit()
    
    def get_user_logs(self, user_id, limit=10):
        """Получить логи пользователя"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT chat_id, banned_username, reason, timestamp 
                FROM logs 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (user_id, limit))
            return cursor.fetchall()
    
    def get_user_stats(self, user_id):
        """Получить статистику пользователя"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Общее количество
            cursor.execute(
                'SELECT COUNT(*) FROM logs WHERE user_id = ?',
                (user_id,)
            )
            total = cursor.fetchone()[0]
            
            # По стоп-словам
            cursor.execute(
                'SELECT COUNT(*) FROM logs WHERE user_id = ? AND reason LIKE "%стоп-слово%"',
                (user_id,)
            )
            stop_words_count = cursor.fetchone()[0]
            
            # По профилям
            cursor.execute(
                'SELECT COUNT(*) FROM logs WHERE user_id = ? AND reason LIKE "%профиль%"',
                (user_id,)
            )
            profile_count = cursor.fetchone()[0]
            
            return {
                'total': total,
                'stop_words': stop_words_count,
                'profiles': profile_count
            }
    
    def add_bot_chat(self, chat_id, chat_title, admin_id):
        """Добавить чат где работает бот"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO bot_chats (chat_id, chat_title, admin_id, automod_enabled)
                VALUES (?, ?, ?, 1)
            ''', (chat_id, chat_title, admin_id))
            conn.commit()
    
    def get_user_chats(self, user_id):
        """Получить чаты пользователя где работает бот"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT chat_id, chat_title, automod_enabled FROM bot_chats WHERE admin_id = ?',
                (user_id,)
            )
            return cursor.fetchall()
    
    def get_chat_admin(self, chat_id):
        """Получить администратора чата"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT admin_id FROM bot_chats WHERE chat_id = ?',
                (chat_id,)
            )
            result = cursor.fetchone()
            return result[0] if result else None

    def remove_bot_chat(self, chat_id, admin_id):
        """Удалить чат из списка"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM bot_chats WHERE chat_id = ? AND admin_id = ?',
                (chat_id, admin_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def chat_exists(self, chat_id, admin_id):
        """Проверить существует ли чат в базе"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT chat_id FROM bot_chats WHERE chat_id = ? AND admin_id = ?',
                (chat_id, admin_id)
            )
            return cursor.fetchone() is not None

    def update_chat_setting(self, chat_id, setting, value):
        """Обновить настройку чата"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'UPDATE bot_chats SET {setting} = ? WHERE chat_id = ?',
                (value, chat_id)
            )
            conn.commit()

    # Новые функции для управления банами
    
    def add_banned_user(self, user_id, username, chat_id, chat_title, banned_by, reason):
        """Добавить забаненного пользователя"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO banned_users 
                (user_id, username, chat_id, chat_title, banned_by, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, username, chat_id, chat_title, banned_by, reason))
            conn.commit()
    
    def remove_banned_user(self, user_id, chat_id):
        """Удалить пользователя из списка забаненных (разбан)"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM banned_users WHERE user_id = ? AND chat_id = ?',
                (user_id, chat_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def get_banned_users(self, admin_id):
        """Получить список забаненных пользователей для администратора"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, chat_id, chat_title, reason, banned_at
                FROM banned_users 
                WHERE banned_by = ?
                ORDER BY banned_at DESC
            ''', (admin_id,))
            return cursor.fetchall()
    
    def get_banned_users_count(self, admin_id):
        """Получить количество забаненных пользователей"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM banned_users WHERE banned_by = ?',
                (admin_id,)
            )
            return cursor.fetchone()[0]

    # Функции для системы исключений
    
    def add_user_exception(self, user_id, username, chat_id, admin_id, reason=""):
        """Добавить пользователя в исключения"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Проверяем нет ли уже такого исключения
            cursor.execute(
                'SELECT id FROM user_exceptions WHERE user_id = ? AND chat_id = ? AND admin_id = ?',
                (user_id, chat_id, admin_id)
            )
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO user_exceptions (user_id, username, chat_id, admin_id, reason)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, username, chat_id, admin_id, reason))
                conn.commit()
                return True
            return False
    
    def remove_user_exception(self, user_id, chat_id, admin_id):
        """Удалить пользователя из исключений"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM user_exceptions WHERE user_id = ? AND chat_id = ? AND admin_id = ?',
                (user_id, chat_id, admin_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def is_user_exception(self, user_id, chat_id):
        """Проверить является ли пользователь исключением"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id FROM user_exceptions WHERE user_id = ? AND chat_id = ?',
                (user_id, chat_id)
            )
            return cursor.fetchone() is not None
    
    def get_chat_exceptions(self, chat_id, admin_id):
        """Получить исключения для чата"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT user_id, username, reason FROM user_exceptions WHERE chat_id = ? AND admin_id = ?',
                (chat_id, admin_id)
            )
            return cursor.fetchall()

    # Функции для системы уведомлений
    
    def add_notification(self, admin_id, chat_id, chat_title, user_id, username, reason, message_id):
        """Добавить уведомление"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notifications (admin_id, chat_id, chat_title, user_id, username, reason, message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (admin_id, chat_id, chat_title, user_id, username, reason, message_id))
            conn.commit()
            return cursor.lastrowid
    
    def resolve_notification(self, notification_id):
        """Пометить уведомление как решенное"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE notifications SET resolved = 1 WHERE id = ?',
                (notification_id,)
            )
            conn.commit()
    
    def get_pending_notifications(self, admin_id):
        """Получить нерешенные уведомления"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, chat_id, chat_title, user_id, username, reason, created_at
                FROM notifications 
                WHERE admin_id = ? AND resolved = 0
                ORDER BY created_at DESC
                LIMIT 10
            ''', (admin_id,))
            return cursor.fetchall()

    # НОВЫЕ ФУНКЦИИ ДЛЯ АДМИН-ПАНЕЛИ
    
    def get_admin_stats(self):
        """Получить общую статистику для админ-панели"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Общее количество пользователей
            cursor.execute('SELECT COUNT(*) FROM user_settings')
            total_users = cursor.fetchone()[0]
            
            # Общее количество чатов
            cursor.execute('SELECT COUNT(*) FROM bot_chats')
            total_chats = cursor.fetchone()[0]
            
            # Общее количество забаненных
            cursor.execute('SELECT COUNT(*) FROM banned_users')
            total_banned = cursor.fetchone()[0]
            
            # Общее количество стоп-слов
            cursor.execute('SELECT COUNT(*) FROM stop_words')
            total_stop_words = cursor.fetchone()[0]
            
            # Активность за последние 7 дней
            cursor.execute('''
                SELECT DATE(timestamp), COUNT(*) 
                FROM logs 
                WHERE timestamp >= date('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY DATE(timestamp)
            ''')
            weekly_activity = cursor.fetchall()
            
            return {
                'total_users': total_users,
                'total_chats': total_chats,
                'total_banned': total_banned,
                'total_stop_words': total_stop_words,
                'weekly_activity': weekly_activity
            }
    
    def get_all_users(self):
        """Получить список всех пользователей"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT us.user_id, us.created_at, 
                       (SELECT COUNT(*) FROM bot_chats WHERE admin_id = us.user_id) as chat_count,
                       (SELECT COUNT(*) FROM logs WHERE user_id = us.user_id) as violation_count
                FROM user_settings us
                ORDER BY us.created_at DESC
            ''')
            return cursor.fetchall()
    
    def get_user_detailed_info(self, user_id):
        """Получить детальную информацию о пользователе"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Основная информация
            cursor.execute('SELECT * FROM user_settings WHERE user_id = ?', (user_id,))
            user_info = cursor.fetchone()
            
            if not user_info:
                return None
            
            # Чаты пользователя
            cursor.execute('SELECT chat_id, chat_title FROM bot_chats WHERE admin_id = ?', (user_id,))
            user_chats = cursor.fetchall()
            
            # Статистика
            cursor.execute('SELECT COUNT(*) FROM logs WHERE user_id = ?', (user_id,))
            total_violations = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM stop_words WHERE user_id = ?', (user_id,))
            stop_words_count = cursor.fetchone()[0]
            
            return {
                'user_info': user_info,
                'chats': user_chats,
                'total_violations': total_violations,
                'stop_words_count': stop_words_count
            }
    
    def get_all_chats(self):
        """Получить список всех чатов"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT bc.chat_id, bc.chat_title, bc.admin_id, bc.added_at,
                       (SELECT COUNT(*) FROM logs WHERE chat_id = bc.chat_id) as violation_count,
                       us.created_at as admin_created
                FROM bot_chats bc
                LEFT JOIN user_settings us ON bc.admin_id = us.user_id
                ORDER BY bc.added_at DESC
            ''')
            return cursor.fetchall()
    
    def get_top_violators(self, limit=10):
        """Получить топ нарушителей"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT banned_user_id, banned_username, COUNT(*) as violation_count,
                       GROUP_CONCAT(DISTINCT reason) as reasons
                FROM logs 
                GROUP BY banned_user_id, banned_username
                ORDER BY violation_count DESC
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()
    
    def search_users(self, query):
        """Поиск пользователей"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, created_at 
                FROM user_settings 
                WHERE user_id LIKE ? OR user_id = ?
                ORDER BY created_at DESC
                LIMIT 50
            ''', (f'%{query}%', query))
            return cursor.fetchall()
    
    def get_system_info(self):
        """Получить информацию о системе"""
        import os
        db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Количество записей в таблицах
            tables = ['user_settings', 'bot_chats', 'logs', 'banned_users', 'stop_words']
            table_counts = {}
            
            for table in tables:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                table_counts[table] = cursor.fetchone()[0]
            
            return {
                'db_size': db_size,
                'table_counts': table_counts
            }
    
    def cleanup_old_logs(self, days=30):
        """Очистить старые логи"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM logs 
                WHERE timestamp < date('now', ?)
            ''', (f'-{days} days',))
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count

# Глобальный экземпляр базы данных
db = Database()