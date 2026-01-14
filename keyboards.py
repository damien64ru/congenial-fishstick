from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu():
    """Главное меню в лс бота"""
    keyboard = [
        [InlineKeyboardButton("⚙️ Настройки модерации", callback_data="settings")],
        [InlineKeyboardButton("🚫 Стоп-слова", callback_data="stop_words")],
        [InlineKeyboardButton("🔍 Проверка профилей", callback_data="profile_check")],
        [InlineKeyboardButton("💬 Мои чаты", callback_data="my_chats")],
        [InlineKeyboardButton("📊 Статистика", callback_data="logs")],
        [InlineKeyboardButton("👥 Забаненные", callback_data="banned_users")],
        [InlineKeyboardButton("👤 Исключения", callback_data="exceptions")],
        [InlineKeyboardButton("🔔 Уведомления", callback_data="notifications")],
        [InlineKeyboardButton("🔐 Капча", callback_data="captcha_settings")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_menu(settings):
    """Меню настроек"""
    automod_status = "✅ ВКЛ" if settings['automod_enabled'] else "❌ ВЫКЛ"
    profile_status = "✅ ВКЛ" if settings['check_profiles'] else "❌ ВЫКЛ"
    media_status = "✅ ВКЛ" if settings['check_media'] else "❌ ВЫКЛ"
    notify_status = "✅ ВКЛ" if settings['notify_admin'] else "❌ ВЫКЛ"
    captcha_status = "✅ ВКЛ" if settings.get('captcha_enabled', True) else "❌ ВЫКЛ"
    
    action_text = {
        'ban': 'БАН', 
        'delete': 'УДАЛЕНИЕ', 
        'warn': 'ПРЕДУПРЕЖДЕНИЕ'
    }[settings['action_type']]
    
    keyboard = [
        [InlineKeyboardButton(f"Автомодерация: {automod_status}", callback_data="toggle_automod")],
        [InlineKeyboardButton(f"Действие: {action_text}", callback_data="change_action")],
        [InlineKeyboardButton(f"Проверка профилей: {profile_status}", callback_data="toggle_profile_check")],
        [InlineKeyboardButton(f"Проверка медиа: {media_status}", callback_data="toggle_media_check")],
        [InlineKeyboardButton(f"Уведомления: {notify_status}", callback_data="toggle_notifications")],
        [InlineKeyboardButton(f"Капча: {captcha_status}", callback_data="toggle_captcha")],
        [InlineKeyboardButton("← Назад", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_action_menu():
    """Меню выбора действия"""
    keyboard = [
        [InlineKeyboardButton("✅ БАН", callback_data="ban")],
        [InlineKeyboardButton("🗑️ УДАЛЕНИЕ", callback_data="delete")],
        [InlineKeyboardButton("⚠️ ПРЕДУПРЕЖДЕНИЕ", callback_data="warn")],
        [InlineKeyboardButton("← Назад", callback_data="settings")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_stop_words_menu(word_count):
    """Меню стоп-слов"""
    keyboard = [
        [InlineKeyboardButton(f"📋 Список слов ({word_count})", callback_data="show_words")],
        [InlineKeyboardButton("➕ Добавить слово", callback_data="add_word")],
        [InlineKeyboardButton("📊 Популярные слова", callback_data="popular_words")],
        [InlineKeyboardButton("🗑️ Удалить слово", callback_data="show_words")],
        [InlineKeyboardButton("🧹 Очистить все", callback_data="clear_words")],
        [InlineKeyboardButton("← Назад", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_words_list_keyboard(words):
    """Клавиатура для списка слов с удалением"""
    keyboard = []
    
    # Добавляем кнопки для каждого слова
    for word in words:
        keyboard.append([InlineKeyboardButton(f"🗑️ {word}", callback_data=f"remove_{word}")])
    
    # Кнопка назад
    keyboard.append([InlineKeyboardButton("← Назад", callback_data="stop_words")])
    
    return InlineKeyboardMarkup(keyboard)

def get_popular_words_keyboard(popular_words):
    """Клавиатура для популярных слов"""
    keyboard = []
    
    # Добавляем кнопки для каждого популярного слова
    for word, count in popular_words[:10]:  # Первые 10 слов
        keyboard.append([InlineKeyboardButton(f"➕ {word} ({count} users)", callback_data=f"add_popular_{word}")])
    
    # Кнопка добавить несколько
    keyboard.append([InlineKeyboardButton("✅ Добавить топ-5 слов", callback_data="add_multiple_popular")])
    
    # Кнопка назад
    keyboard.append([InlineKeyboardButton("← Назад", callback_data="stop_words")])
    
    return InlineKeyboardMarkup(keyboard)

def get_profile_check_menu(settings, profile_count):
    """Меню проверки профилей"""
    status = "✅ ВКЛ" if settings['check_profiles'] else "❌ ВЫКЛ"
    
    keyboard = [
        [InlineKeyboardButton(f"Статус: {status}", callback_data="toggle_profile_check")],
        [InlineKeyboardButton("← Назад", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_logs_menu(stats):
    """Меню логов"""
    keyboard = [
        [InlineKeyboardButton("📈 Последние действия", callback_data="recent_logs")],
        [InlineKeyboardButton("📅 Общая статистика", callback_data="month_stats")],
        [InlineKeyboardButton("📊 Статистика капчи", callback_data="captcha_stats")],
        [InlineKeyboardButton("← Назад", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_banned_users_menu(banned_count):
    """Меню забаненных пользователей"""
    keyboard = [
        [InlineKeyboardButton(f"📋 Список забаненных ({banned_count})", callback_data="show_banned")],
        [InlineKeyboardButton("🔄 Обновить список", callback_data="banned_users")],
        [InlineKeyboardButton("← Назад", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_banned_list_keyboard(banned_users):
    """Клавиатура для списка забаненных с разбаном"""
    keyboard = []
    
    # Добавляем кнопки для каждого забаненного пользователя
    for user_id, username, chat_id, chat_title, reason, banned_at in banned_users:
        display_name = username if username else f"ID: {user_id}"
        keyboard.append([
            InlineKeyboardButton(f"🔓 {display_name}", callback_data=f"unban_{user_id}_{chat_id}")
        ])
    
    # Кнопки управления
    keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data="show_banned")])
    keyboard.append([InlineKeyboardButton("← Назад", callback_data="banned_users")])
    
    return InlineKeyboardMarkup(keyboard)

def get_exceptions_menu(exceptions_count):
    """Меню исключений"""
    keyboard = [
        [InlineKeyboardButton(f"📋 Список исключений ({exceptions_count})", callback_data="show_exceptions")],
        [InlineKeyboardButton("➕ Добавить исключение", callback_data="add_exception")],
        [InlineKeyboardButton("← Назад", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_exceptions_list_keyboard(exceptions):
    """Клавиатура для списка исключений с удалением"""
    keyboard = []
    
    # Добавляем кнопки для каждого исключения
    for user_id, username, chat_id, chat_title, reason in exceptions:
        display_name = username if username else f"ID: {user_id}"
        keyboard.append([
            InlineKeyboardButton(f"🗑️ {display_name}", callback_data=f"remove_exception_{user_id}_{chat_id}")
        ])
    
    # Кнопка назад
    keyboard.append([InlineKeyboardButton("← Назад", callback_data="exceptions")])
    
    return InlineKeyboardMarkup(keyboard)

def get_notifications_menu(notifications_count):
    """Меню уведомлений"""
    keyboard = [
        [InlineKeyboardButton(f"📋 Активные уведомления ({notifications_count})", callback_data="show_notifications")],
        [InlineKeyboardButton("🔄 Обновить", callback_data="notifications")],
        [InlineKeyboardButton("← Назад", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_notifications_list_keyboard(notifications):
    """Клавиатура для списка уведомлений"""
    keyboard = []
    
    # Добавляем кнопки для каждого уведомления
    for notif_id, chat_id, chat_title, user_id, username, reason, created_at in notifications:
        display_name = username if username else f"ID: {user_id}"
        time_str = created_at.split(' ')[1][:5]
        keyboard.append([
            InlineKeyboardButton(f"⏰ {time_str} - {display_name}", callback_data=f"resolve_{user_id}_{chat_id}")
        ])
    
    # Кнопка назад
    keyboard.append([InlineKeyboardButton("← Назад", callback_data="notifications")])
    
    return InlineKeyboardMarkup(keyboard)

def get_my_chats_menu(chats_count):
    """Меню моих чатов"""
    keyboard = [
        [InlineKeyboardButton(f"📋 Список чатов ({chats_count})", callback_data="show_chats")],
        [InlineKeyboardButton("➕ Добавить чат", callback_data="add_chat")],
        [InlineKeyboardButton("🔄 Проверить чаты", callback_data="refresh_chats")],
        [InlineKeyboardButton("← Назад", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_chats_list_keyboard(chats):
    """Клавиатура для списка чатов"""
    keyboard = []
    
    # Добавляем кнопки для каждого чат
    for chat_id, chat_title, status, automod_enabled in chats:
        status_icon = "✅" if status == "active" else "⚠️" if status == "no_bot_rights" else "❌"
        mod_icon = "🔒" if automod_enabled else "🔓"
        keyboard.append([
            InlineKeyboardButton(f"{status_icon}{mod_icon} {chat_title[:20]}", callback_data=f"chat_{chat_id}")
        ])
    
    # Кнопки управления
    keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data="show_chats")])
    keyboard.append([InlineKeyboardButton("➕ Добавить чат", callback_data="add_chat")])
    keyboard.append([InlineKeyboardButton("← Назад", callback_data="my_chats")])
    
    return InlineKeyboardMarkup(keyboard)

def get_chat_management_keyboard(chat_id, chat_title, status, automod_enabled):
    """Клавиатура управления конкретным чатом - УПРОЩЕННАЯ ВЕРСИЯ"""
    automod_text = "❌ Выключить модерацию" if automod_enabled else "✅ Включить модерацию"
    
    keyboard = [
        [InlineKeyboardButton(automod_text, callback_data=f"toggle_chat_{chat_id}")],
        [InlineKeyboardButton("🗑️ Удалить из списка", callback_data=f"remove_chat_{chat_id}")],
        [InlineKeyboardButton("← Назад к чатам", callback_data="show_chats")],
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_add_chat_keyboard():
    """Клавиатура для добавления чата"""
    keyboard = [
        [InlineKeyboardButton("🔄 Проверить чаты", callback_data="refresh_chats")],
        [InlineKeyboardButton("💬 Мои чаты", callback_data="my_chats")],
        [InlineKeyboardButton("← Назад", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_captcha_menu():
    """Меню капчи"""
    from config import CAPTCHA_ENABLED
    captcha_status = "✅ ВКЛ" if CAPTCHA_ENABLED else "❌ ВЫКЛ"
    
    keyboard = [
        [InlineKeyboardButton(f"Капча: {captcha_status}", callback_data="toggle_captcha_global")],
        [InlineKeyboardButton("📊 Статистика капчи", callback_data="captcha_stats")],
        [InlineKeyboardButton("← Назад", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_captcha_stats_keyboard():
    """Клавиатура для статистики капчи"""
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="captcha_stats")],
        [InlineKeyboardButton("← Назад", callback_data="logs")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_button():
    """Кнопка назад"""
    keyboard = [[InlineKeyboardButton("← Назад", callback_data="back")]]
    return InlineKeyboardMarkup(keyboard)

def get_help_menu():
    """Меню помощи"""
    keyboard = [
        [InlineKeyboardButton("← Назад", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)