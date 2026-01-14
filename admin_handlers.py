from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
import os
from config import ADMIN_IDS
from handlers.message_handler import message_handler

def is_admin(user_id):
    """Проверить является ли пользователь администратором"""
    return user_id in ADMIN_IDS

class AdminHandlers:
    async def handle_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /admin"""
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_text("❌ Доступ запрещен")
            return
        
        stats = db.get_admin_stats()
        monitor_stats = message_handler.monitor.get_stats()
        
        text = (
            "👑 Админ-панель\n\n"
            "📊 Общая статистика:\n"
            f"• Пользователей: {stats['total_users']}\n"
            f"• Активных чатов: {stats['total_chats']}\n"
            f"• Забаненных: {stats['total_banned']}\n"
            f"• Стоп-слов: {stats['total_stop_words']}\n\n"
            
            "🔍 Мониторинг сообщений:\n"
            f"• Отслеживается: {monitor_stats['active_tracking']} сообщений\n"
            f"• Всего отслежено: {monitor_stats['total_tracked']}\n"
            f"• Нарушений найдено: {monitor_stats['violations_found']}\n\n"
            
            "⚙️ Доступные действия:"
        )
        
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton("💬 Чаты", callback_data="admin_chats")],
            [InlineKeyboardButton("🚫 Нарушители", callback_data="admin_violators")],
            [InlineKeyboardButton("🔍 Мониторинг", callback_data="admin_monitoring")],
            [InlineKeyboardButton("⚙️ Система", callback_data="admin_system")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика админ-панели"""
        query = update.callback_query
        await query.answer()
        
        if not is_admin(query.from_user.id):
            await query.edit_message_text("❌ Доступ запрещен")
            return
        
        stats = db.get_admin_stats()
        
        # Форматируем активность за неделю
        activity_text = ""
        for date, count in stats['weekly_activity']:
            activity_text += f"• {date}: {count} нарушений\n"
        
        if not activity_text:
            activity_text = "• Нет данных за последние 7 дней\n"
        
        text = (
            "📊 Детальная статистика\n\n"
            "📈 Основные метрики:\n"
            f"• Пользователей: {stats['total_users']}\n"
            f"• Активных чатов: {stats['total_chats']}\n"
            f"• Забаненных: {stats['total_banned']}\n"
            f"• Стоп-слов: {stats['total_stop_words']}\n\n"
            
            "📅 Активность за 7 дней:\n"
            f"{activity_text}"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
            [InlineKeyboardButton("← Назад", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_admin_monitoring(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика мониторинга сообщений"""
        query = update.callback_query
        await query.answer()
        
        if not is_admin(query.from_user.id):
            await query.edit_message_text("❌ Доступ запрещен")
            return
        
        monitor_stats = message_handler.monitor.get_stats()
        
        # Рассчитываем эффективность
        efficiency = 0
        if monitor_stats['total_checked'] > 0:
            efficiency = (monitor_stats['violations_found'] / monitor_stats['total_checked']) * 100
        
        # Время самого старого сообщения
        from datetime import datetime
        oldest_time = datetime.fromtimestamp(monitor_stats['oldest_message'])
        time_diff = datetime.now().timestamp() - monitor_stats['oldest_message']
        
        text = (
            "🔍 Мониторинг сообщений\n\n"
            "📈 Активная статистика:\n"
            f"• Сейчас отслеживается: {monitor_stats['active_tracking']} сообщений\n"
            f"• Размер кэша: {monitor_stats['cache_size']}\n"
            f"• Самое старое сообщение: {int(time_diff // 60)} минут назад\n\n"
            
            "📊 Общая статистика:\n"
            f"• Всего отслежено: {monitor_stats['total_tracked']}\n"
            f"• Проверок выполнено: {monitor_stats['total_checked']}\n"
            f"• Нарушений найдено: {monitor_stats['violations_found']}\n"
            f"• Редакций обнаружено: {monitor_stats['edits_detected']}\n"
            f"• Эффективность: {efficiency:.1f}%\n\n"
            
            "📝 Метрики кэша:\n"
            f"• Попадания в кэш: {monitor_stats['cache_hits']}\n"
            f"• Промахи кэша: {monitor_stats['cache_misses']}"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_monitoring")],
            [InlineKeyboardButton("🧹 Очистить кэш", callback_data="admin_clear_monitoring")],
            [InlineKeyboardButton("← Назад", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_admin_clear_monitoring(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка кэша мониторинга"""
        query = update.callback_query
        await query.answer()
        
        if not is_admin(query.from_user.id):
            await query.edit_message_text("❌ Доступ запрещен")
            return
        
        # Очищаем кэш мониторинга
        message_handler.monitor.cache.clear()
        message_handler.monitor.cache_keys_by_time.clear()
        
        text = "✅ Кэш мониторинга очищен"
        
        keyboard = [
            [InlineKeyboardButton("← Назад в мониторинг", callback_data="admin_monitoring")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_admin_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список пользователей"""
        query = update.callback_query
        await query.answer()
        
        if not is_admin(query.from_user.id):
            await query.edit_message_text("❌ Доступ запрещен")
            return
        
        users = db.get_all_users()
        
        text = "👥 Все пользователи\n\n"
        
        if not users:
            text += "Пользователей не найдено"
        else:
            for i, (user_id, created_at, chat_count, violation_count) in enumerate(users[:20], 1):
                text += f"{i}. ID: {user_id}\n"
                text += f"   📅 Регистрация: {created_at.split()[0]}\n"
                text += f"   💬 Чатов: {chat_count} | 🚫 Нарушений: {violation_count}\n\n"
            
            if len(users) > 20:
                text += f"\n... и еще {len(users) - 20} пользователей"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_users")],
            [InlineKeyboardButton("← Назад", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_admin_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список чатов"""
        query = update.callback_query
        await query.answer()
        
        if not is_admin(query.from_user.id):
            await query.edit_message_text("❌ Доступ запрещен")
            return
        
        chats = db.get_all_chats()
        
        text = "💬 Все чаты\n\n"
        
        if not chats:
            text += "Чатов не найдено"
        else:
            for i, (chat_id, chat_title, admin_id, added_at, violation_count, admin_created) in enumerate(chats[:15], 1):
                text += f"{i}. {chat_title}\n"
                text += f"   🆔 ID: {chat_id}\n"
                text += f"   👤 Админ: {admin_id}\n"
                text += f"   📅 Добавлен: {added_at.split()[0]}\n"
                text += f"   🚫 Нарушений: {violation_count}\n\n"
            
            if len(chats) > 15:
                text += f"\n... и еще {len(chats) - 15} чатов"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_chats")],
            [InlineKeyboardButton("← Назад", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_admin_violators(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Топ нарушителей"""
        query = update.callback_query
        await query.answer()
        
        if not is_admin(query.from_user.id):
            await query.edit_message_text("❌ Доступ запрещен")
            return
        
        violators = db.get_top_violators(10)
        
        text = "🚫 Топ нарушителей\n\n"
        
        if not violators:
            text += "Нарушителей не найдено"
        else:
            for i, (user_id, username, violation_count, reasons) in enumerate(violators, 1):
                display_name = username if username else f"ID: {user_id}"
                text += f"{i}. {display_name}\n"
                text += f"   🚫 Нарушений: {violation_count}\n"
                
                # Показываем основные причины
                reason_list = reasons.split(',')[:3]
                text += f"   📝 Причины: {', '.join(reason_list)}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_violators")],
            [InlineKeyboardButton("← Назад", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_admin_system(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о системе"""
        query = update.callback_query
        await query.answer()
        
        if not is_admin(query.from_user.id):
            await query.edit_message_text("❌ Доступ запрещен")
            return
        
        system_info = db.get_system_info()
        
        # Форматируем размер базы данных
        db_size_mb = system_info['db_size'] / (1024 * 1024)
        
        text = (
            "⚙️ Информация о системе\n\n"
            "💾 База данных:\n"
            f"• Размер: {db_size_mb:.2f} MB\n\n"
            
            "📊 Статистика таблиц:\n"
        )
        
        for table, count in system_info['table_counts'].items():
            text += f"• {table}: {count} записей\n"
        
        text += "\n🛠 Действия:"
        
        keyboard = [
            [InlineKeyboardButton("🧹 Очистить логи (30+ дней)", callback_data="admin_cleanup_logs")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_system")],
            [InlineKeyboardButton("← Назад", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_admin_cleanup_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка старых логов"""
        query = update.callback_query
        await query.answer()
        
        if not is_admin(query.from_user.id):
            await query.edit_message_text("❌ Доступ запрещен")
            return
        
        deleted_count = db.cleanup_old_logs(30)
        
        text = f"✅ Очищено {deleted_count} старых логов (старше 30 дней)"
        
        keyboard = [
            [InlineKeyboardButton("← Назад в систему", callback_data="admin_system")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_admin_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поиск пользователей"""
        query = update.callback_query
        await query.answer()
        
        if not is_admin(query.from_user.id):
            await query.edit_message_text("❌ Доступ запрещен")
            return
        
        text = (
            "🔍 Поиск пользователей\n\n"
            "Введите ID пользователя или часть ID для поиска:\n\n"
            "Пример: 123456789 или 123"
        )
        
        keyboard = [
            [InlineKeyboardButton("← Назад", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_admin_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Назад в главное меню админ-панели"""
        query = update.callback_query
        await query.answer()
        
        await self.handle_admin(update, context)

# Создаем экземпляр обработчика
admin_handlers = AdminHandlers()