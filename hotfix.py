import sqlite3
import os

def fix_tables():
    """Создать недостающие таблицы"""
    db_path = "/data/bot_database.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🛠️ Создаем недостающие таблицы...")
    
    # Таблица detailed_logs
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detailed_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                chat_id INTEGER,
                user_id INTEGER,
                username TEXT,
                message_id INTEGER,
                message_text TEXT,
                profile_info TEXT,
                violation_type TEXT,
                violation_details TEXT,
                action_taken TEXT,
                captcha_used BOOLEAN DEFAULT 0,
                captcha_result TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ Таблица detailed_logs создана")
    except Exception as e:
        print(f"❌ Ошибка создания detailed_logs: {e}")
    
    # Таблица captcha_stats
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS captcha_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                username TEXT,
                captcha_type TEXT,
                passed BOOLEAN,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ Таблица captcha_stats создана")
    except Exception as e:
        print(f"❌ Ошибка создания captcha_stats: {e}")
    
    conn.commit()
    conn.close()
    print("✅ Таблицы созданы успешно!")

if __name__ == "__main__":
    fix_tables()
    print("\n🔧 Запустите этот скрипт и перезапустите бота:")
    print("python hotfix.py")
    print("python bot.py")