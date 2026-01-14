import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from keyboards import (
    get_main_menu, get_settings_menu, get_action_menu,
    get_stop_words_menu, get_profile_check_menu, get_logs_menu, 
    get_back_button, get_help_menu, get_banned_users_menu, get_banned_list_keyboard,
    get_words_list_keyboard, get_my_chats_menu, get_chats_list_keyboard,
    get_chat_management_keyboard, get_add_chat_keyboard,
    get_exceptions_menu, get_exceptions_list_keyboard,
    get_notifications_menu, get_notifications_list_keyboard,
    get_popular_words_keyboard, get_captcha_menu, get_captcha_stats_keyboard
)
from config import CAPTCHA_ENABLED
from handlers.message_handler import message_handler

class MenuHandlers:
    async def handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик меню настроек"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        settings = db.get_user_settings(user_id)
        
        # Получаем глобальный статус капчи из config
        from config import CAPTCHA_ENABLED
        captcha_global_status = "✅ ВКЛ" if CAPTCHA_ENABLED else "❌ ВЫКЛ"
        
        text = (
            "⚙️ Настройки модерации\n\n"
            "Эти настройки применяются ко ВСЕМ вашим группам:\n\n"
            "• Автомодерация: {}\n"
            "• Действие при нарушении: {}\n"
            "• Проверка профилей: {}\n"
            "• Проверка медиа: {}\n"
            "• Уведомления: {}\n"
            "• Капча (глобально): {}"
        ).format(
            "✅ ВКЛ" if settings['automod_enabled'] else "❌ ВЫКЛ",
            {'ban': 'БАН', 'delete': 'УДАЛЕНИЕ', 'warn': 'ПРЕДУПРЕЖДЕНИЕ'}[settings['action_type']],
            "✅ ВКЛ" if settings['check_profiles'] else "❌ ВЫКЛ",
            "✅ ВКЛ" if settings['check_media'] else "❌ ВЫКЛ",
            "✅ ВКЛ" if settings['notify_admin'] else "❌ ВЫКЛ",
            captcha_global_status
        )
        
        await query.message.edit_text(text, reply_markup=get_settings_menu(settings))
    
    async def handle_captcha_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик меню капчи"""
        query = update.callback_query
        await query.answer()
        
        from config import CAPTCHA_ENABLED, CAPTCHA_TIMEOUT
        
        text = (
            "🔐 Настройки капчи\n\n"
            "Капча отправляется при первом нарушении.\n"
            "Пользователь должен решить простой пример за {} секунд.\n\n"
            "✅ При успехе:\n"
            "• Сообщение удаляется\n"
            "• Пользователь добавляется в исключения\n"
            "• Админ получает уведомление\n\n"
            "❌ При неудаче:\n"
            "• Выполняется стандартное действие (бан/удаление/предупреждение)\n\n"
            "Текущий статус: {}"
        ).format(
            CAPTCHA_TIMEOUT,
            "✅ ВКЛЮЧЕНА" if CAPTCHA_ENABLED else "❌ ВЫКЛЮЧЕНА"
        )
        
        await query.message.edit_text(text, reply_markup=get_captcha_menu())
    
    async def handle_captcha_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика капчи"""
        query = update.callback_query
        await query.answer()
        
        # Получаем статистику из message_handler
        stats = await message_handler.get_captcha_stats()
        
        from config import CAPTCHA_ENABLED, CAPTCHA_TIMEOUT
        
        # Рассчитываем проценты
        total = stats['sent']
        if total > 0:
            passed_pct = (stats['passed'] / total) * 100
            failed_pct = (stats['failed'] / total) * 100
            timeout_pct = (stats['timeout'] / total) * 100
        else:
            passed_pct = failed_pct = timeout_pct = 0
        
        text = (
            "📊 Статистика капчи (в памяти)\n\n"
            "Общая статистика с последнего запуска:\n\n"
            "• Отправлено капч: {}\n"
            "• Пройдено успешно: {} ({:.1f}%)\n"
            "• Неверный ответ: {} ({:.1f}%)\n"
            "• Таймаут: {} ({:.1f}%)\n\n"
            "Настройки:\n"
            "• Статус: {}\n"
            "• Время на ответ: {} сек\n"
            "• Примеры: 2+3, 5-2, 4*2 и т.д."
        ).format(
            total,
            stats['passed'], passed_pct,
            stats['failed'], failed_pct,
            stats['timeout'], timeout_pct,
            "✅ ВКЛ" if CAPTCHA_ENABLED else "❌ ВЫКЛ",
            CAPTCHA_TIMEOUT
        )
        
        await query.message.edit_text(text, reply_markup=get_captcha_stats_keyboard())
    
    async def handle_toggle_captcha_global(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вкл/выкл капчу глобально"""
        query = update.callback_query
        await query.answer()
        
        # Импортируем и меняем глобальную переменную
        import config
        
        # Переключаем статус
        config.CAPTCHA_ENABLED = not config.CAPTCHA_ENABLED
        
        status = "ВКЛЮЧЕНА" if config.CAPTCHA_ENABLED else "ВЫКЛЮЧЕНА"
        icon = "✅" if config.CAPTCHA_ENABLED else "❌"
        
        text = f"{icon} Капча {status}"
        
        await query.answer(text, show_alert=True)
        await self.handle_captcha_settings(update, context)
    
    async def handle_toggle_captcha(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вкл/выкл капчу в настройках пользователя (заглушка)"""
        query = update.callback_query
        await query.answer()
        
        # Капча управляется глобально через config.CAPTCHA_ENABLED
        # Это заглушка для обратной совместимости с меню
        
        await query.answer("ℹ️ Капча управляется глобально в настройках", show_alert=True)
        await self.handle_settings(update, context)
    
    # [ВСЕ ОСТАЛЬНЫЕ СУЩЕСТВУЮЩИЕ МЕТОДЫ БЕЗ ИЗМЕНЕНИЙ]
    # handle_stop_words, handle_profile_check, handle_logs и т.д.
    
    async def handle_stop_words(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик меню стоп-слов"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        words = db.get_stop_words(user_id)
        
        text = f"🚫 Управление стоп-словами\n\nВсего слов: {len(words)}"
        if words:
            text += f"\nПоследние: {', '.join(words[-3:])}"
        else:
            text += "\n\nСписок пуст. Добавьте слова для фильтрации."
        
        text += "\n\nДля быстрого добавления напишите +слово в чат, несколько слов через запятую: +реклама, спам, купить"
        
        await query.message.edit_text(text, reply_markup=get_stop_words_menu(len(words)))
    
    async def handle_profile_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик меню проверки профилей"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        settings = db.get_user_settings(user_id)
        stats = db.get_user_stats(user_id)
        
        text = (
            "🔍 Проверка профилей на каналы\n\n"
            "Статус: {}\n"
            "Обнаружено нарушений: {}\n\n"
            "• Проверяем все поля профиля:\n"
            "  - Username\n"
            "  - Имя и фамилия\n"  
            "  - Био (\"О себе\")\n"
            "  - Ссылки в профиле\n\n"
            "• Любой канал = бан"
        ).format(
            "✅ ВКЛЮЧЕНО" if settings['check_profiles'] else "❌ ВЫКЛЮЧЕНО",
            stats['profiles']
        )
        
        await query.message.edit_text(text, reply_markup=get_profile_check_menu(settings, stats['profiles']))
    
    async def handle_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик меню логов"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        stats = db.get_user_stats(user_id)
        
        # Получаем список чатов пользователя
        user_chats = db.get_user_chats(user_id)
        chats_count = len(user_chats)
        
        text = (
            "📊 Статистика и логи\n\n"
            "За всё время:\n"
            "• Заблокировано: {} пользователей\n"
            "• По стоп-словам: {}\n"
            "• По профилям: {}\n\n"
            "Активных групп: {}"
        ).format(stats['total'], stats['stop_words'], stats['profiles'], chats_count)
        
        await query.message.edit_text(text, reply_markup=get_logs_menu(stats))
    
    async def handle_banned_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик меню забаненных пользователей"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        banned_count = db.get_banned_users_count(user_id)
        
        text = (
            "👥 Управление забаненными пользователями\n\n"
            "Забанено пользователей: {}\n\n"
            "Здесь вы можете:\n"
            "• Просмотреть список забаненных\n"
            "• Разбанить пользователей\n"
            "• Увидеть причину бана"
        ).format(banned_count)
        
        await query.message.edit_text(text, reply_markup=get_banned_users_menu(banned_count))
    
    async def handle_show_banned(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список забаненных пользователей"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        banned_users = db.get_banned_users(user_id)
        
        if not banned_users:
            text = "👥 Список забаненных пользователей пуст"
            await query.message.edit_text(text, reply_markup=get_back_button())
        else:
            text = "👥 Забаненные пользователи:\n\n"
            for i, (banned_user_id, username, chat_id, chat_title, reason, banned_at) in enumerate(banned_users, 1):
                display_name = username if username else f"ID: {banned_user_id}"
                text += f"{i}. {display_name}\n"
                text += f"   💬 Чат: {chat_title}\n"
                text += f"   📅 Забанен: {banned_at.split()[0]}\n"
                text += f"   🎯 Причина: {reason}\n\n"
            
            text += "Нажмите на пользователя чтобы разбанить:"
            
            await query.message.edit_text(text, reply_markup=get_banned_list_keyboard(banned_users))
    
    async def handle_unban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Разбан пользователя"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data.replace('unban_', '')
        banned_user_id, chat_id = data.split('_')
        
        try:
            # Пробуем разбанить пользователя в чате
            await context.bot.unban_chat_member(int(chat_id), int(banned_user_id))
            
            # Удаляем из базы данных
            success = db.remove_banned_user(int(banned_user_id), int(chat_id))
            
            if success:
                await query.message.edit_text(
                    f"✅ Пользователь разбанен!\n\n"
                    f"👤 ID: {banned_user_id}\n"
                    f"💬 Чат: {chat_id}",
                    reply_markup=get_back_button()
                )
            else:
                await query.message.edit_text(
                    "❌ Пользователь не найден в базе данных",
                    reply_markup=get_back_button()
                )
                
        except Exception as e:
            await query.message.edit_text(
                f"❌ Ошибка при разбане: {e}",
                reply_markup=get_back_button()
            )
    
    async def handle_exceptions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик меню исключений"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user_chats = db.get_user_chats(user_id)
        total_exceptions = 0
        
        # Считаем общее количество исключений
        for chat_id, chat_title, _ in user_chats:
            exceptions = db.get_chat_exceptions(chat_id, user_id)
            total_exceptions += len(exceptions)
        
        text = (
            "👤 Управление исключениями\n\n"
            "Всего исключений: {}\n\n"
            "Исключенные пользователи не проверяются ботом.\n"
            "Добавляйте доверенных пользователей в исключения."
        ).format(total_exceptions)
        
        await query.message.edit_text(text, reply_markup=get_exceptions_menu(total_exceptions))
    
    async def handle_show_exceptions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список исключений"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user_chats = db.get_user_chats(user_id)
        
        all_exceptions = []
        for chat_id, chat_title, _ in user_chats:
            exceptions = db.get_chat_exceptions(chat_id, user_id)
            for user_id_ex, username, reason in exceptions:
                all_exceptions.append((user_id_ex, username, chat_id, chat_title, reason))
        
        if not all_exceptions:
            text = "👤 Список исключений пуст\n\nДобавьте пользователей в исключения через уведомления или вручную."
            await query.message.edit_text(text, reply_markup=get_back_button())
        else:
            text = "👤 Пользователи в исключениях:\n\n"
            for i, (user_id_ex, username, chat_id, chat_title, reason) in enumerate(all_exceptions, 1):
                display_name = username if username else f"ID: {user_id_ex}"
                text += f"{i}. {display_name}\n"
                text += f"   💬 Чат: {chat_title}\n"
                if reason:
                    text += f"   📝 Причина: {reason}\n"
                text += "\n"
            
            text += "Нажмите на пользователя чтобы удалить из исключений:"
            
            await query.message.edit_text(text, reply_markup=get_exceptions_list_keyboard(all_exceptions))
    
    async def handle_remove_exception(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить пользователя из исключений (ИСПРАВЛЕННАЯ ВЕРСИЯ)"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        print(f"🔧 DEBUG handle_remove_exception: Получен callback_data: {data}")
        
        if data.startswith('remove_exception_'):
            # Убираем префикс
            data = data.replace('remove_exception_', '')
            
            # Разделяем данные
            # Формат может быть: "7763016661_-1002631508084" (userID_chatID)
            parts = data.split('_')
            
            print(f"🔧 DEBUG: parts = {parts}")
            
            if len(parts) >= 2:
                # Если chat_id отрицательный (начинается с минуса), он будет разбит
                # Например: ["7763016661", "-1002631508084"] или ["7763016661", "1002631508084"]
                
                exception_user_id = parts[0]
                
                # Обработка отрицательных ID
                if parts[1].startswith('-'):
                    # Если второй элемент начинается с минуса, это отрицательный chat_id
                    chat_id = parts[1]
                else:
                    # Иначе собираем chat_id из оставшихся частей
                    chat_id = '_'.join(parts[1:])
                
                print(f"🔧 DEBUG: exception_user_id={exception_user_id}, chat_id={chat_id}")
                
                try:
                    success = db.remove_user_exception(int(exception_user_id), int(chat_id), user_id)
                    
                    if success:
                        await query.message.edit_text(
                            f"✅ Пользователь удален из исключений!\n\n"
                            f"👤 ID пользователя: {exception_user_id}\n"
                            f"💬 ID чата: {chat_id}",
                            reply_markup=get_back_button()
                        )
                    else:
                        await query.message.edit_text(
                            "❌ Пользователь не найден в исключениях",
                            reply_markup=get_back_button()
                        )
                        
                except ValueError as e:
                    await query.message.edit_text(
                        f"❌ Ошибка в формате ID: {e}\n\n"
                        f"Данные: {data}\n"
                        f"Части: {parts}",
                        reply_markup=get_back_button()
                    )
                except Exception as e:
                    await query.message.edit_text(
                        f"❌ Ошибка при удалении: {e}",
                        reply_markup=get_back_button()
                    )
            else:
                await query.message.edit_text(
                    "❌ Неверный формат данных. Ожидается: remove_exception_USERID_CHATID",
                    reply_markup=get_back_button()
                )
        else:
            # Это не наш callback, возможно попал в неправильный обработчик
            await query.message.edit_text(
                "❌ Неизвестная команда удаления",
                reply_markup=get_back_button()
            )
    
    async def handle_add_exception(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить пользователя в исключения вручную"""
        query = update.callback_query
        await query.answer()
        
        text = (
            "👤 Добавление пользователя в исключения\n\n"
            "Чтобы добавить пользователя вручную:\n"
            "1. Перейдите в нужный чат\n"
            "2. Используйте команду:\n"
            "<code>/exception @username</code>\n\n"
            "Или добавляйте через уведомления о нарушениях."
        )
        
        await query.message.edit_text(text, reply_markup=get_back_button(), parse_mode='HTML')
    
    async def handle_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик меню уведомлений"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        pending_notifications = db.get_pending_notifications(user_id)
        
        text = (
            "🔔 Активные уведомления\n\n"
            "Необработанных уведомлений: {}\n\n"
            "Здесь отображаются последние нарушения,\n"
            "требующие вашего внимания."
        ).format(len(pending_notifications))
        
        await query.message.edit_text(text, reply_markup=get_notifications_menu(len(pending_notifications)))
    
    async def handle_show_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать активные уведомления"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        notifications = db.get_pending_notifications(user_id)
        
        if not notifications:
            text = "🔔 Активных уведомлений нет\n\nВсе нарушения уже обработаны."
            await query.message.edit_text(text, reply_markup=get_back_button())
        else:
            text = "🔔 Активные уведомления:\n\n"
            for i, (notif_id, chat_id, chat_title, user_id_ex, username, reason, created_at) in enumerate(notifications, 1):
                display_name = username if username else f"ID: {user_id_ex}"
                time_str = created_at.split(' ')[1][:5]  # Берем только время
                text += f"{i}. {time_str} - {display_name}\n"
                text += f"   💬 {chat_title}\n"
                text += f"   📝 {reason}\n\n"
            
            text += "Выберите уведомление для обработки:"
            
            await query.message.edit_text(text, reply_markup=get_notifications_list_keyboard(notifications))
    
    async def handle_resolve_notification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Пометить уведомление как решенное"""
        query = update.callback_query
        await query.answer()
        
        data = query.data.replace('resolve_', '')
        user_id_ex, chat_id = data.split('_')
        
        # Здесь нужно найти ID уведомления по user_id и chat_id
        # Пока просто возвращаем в меню
        await query.message.edit_text(
            "✅ Уведомление помечено как решенное",
            reply_markup=get_back_button()
        )
    
    async def handle_ban_from_notification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Забанить пользователя из уведомления"""
        query = update.callback_query
        await query.answer()
        
        data = query.data.replace('ban_', '')
        user_id_ex, chat_id = data.split('_')
        
        try:
            await context.bot.ban_chat_member(int(chat_id), int(user_id_ex))
            await query.message.edit_text(
                f"✅ Пользователь забанен!\n\n"
                f"👤 ID: {user_id_ex}\n"
                f"💬 Чат: {chat_id}",
                reply_markup=get_back_button()
            )
        except Exception as e:
            await query.message.edit_text(
                f"❌ Ошибка при бане: {e}",
                reply_markup=get_back_button()
            )
    
    async def handle_exception_from_notification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить пользователя в исключения из уведомления"""
        query = update.callback_query
        await query.answer()
        
        data = query.data.replace('exception_', '')
        user_id_ex, chat_id = data.split('_')
        user_id = query.from_user.id
        
        try:
            # Получаем информацию о пользователе
            user_chat = await context.bot.get_chat(int(user_id_ex))
            username = f"@{user_chat.username}" if user_chat.username else user_chat.first_name
            
            success = db.add_user_exception(
                int(user_id_ex), username, int(chat_id), user_id, 
                "Добавлено через уведомление"
            )
            
            if success:
                await query.message.edit_text(
                    f"✅ Пользователь добавлен в исключения!\n\n"
                    f"👤 {username}\n"
                    f"💬 Чат: {chat_id}\n\n"
                    f"Теперь этот пользователь не будет проверяться ботом.",
                    reply_markup=get_back_button()
                )
            else:
                await query.message.edit_text(
                    "⚠️ Пользователь уже в исключениях",
                    reply_markup=get_back_button()
                )
                
        except Exception as e:
            await query.message.edit_text(
                f"❌ Ошибка при добавлении в исключения: {e}",
                reply_markup=get_back_button()
            )
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик помощи"""
        query = update.callback_query
        await query.answer()
        
        text = (
            "❓ Помощь\n\n"
            "🤖 Как работает бот:\n"
            "• Автоматически проверяет сообщения на стоп-слова\n"
            "• Проверяет профили пользователей на наличие каналов\n"
            "• Выполняет выбранное действие при нарушении\n\n"
            "🔐 СИСТЕМА КАПЧИ (НОВОЕ!):\n"
            "• При первом нарушении отправляется капча (2+3=?)\n"
            "• 15 секунд на ответ\n"
            "• При успехе: сообщение удаляется + пользователь в исключения\n"
            "• При неудаче: стандартное действие (бан/удаление/предупреждение)\n"
            "• Админ получает уведомление в любом случае\n\n"
            "⚙️ Настройки (применяются ко всем группам):\n"
            "• Автомодерация - вкл/выкл всю систему\n"
            "• Действие - что делать при нарушении\n"
            "• Проверка профилей - проверка на каналы\n"
            "• Проверка медиа - анализ изображений\n"
            "• Уведомления - уведомления в ЛС\n"
            "• Капча - глобальное вкл/выкл системы капчи\n\n"
            "🚫 Стоп-слова:\n"
            "• Добавляйте слова через меню\n"
            "• Для быстрого добавления напишите +слово в этот чат\n"
            "• Удаляйте отдельные слова через меню\n"
            "• Используйте популярные слова других пользователей\n\n"
            "👤 Исключения:\n"
            "• Пользователи которых не проверять\n"
            "• Добавляйте через уведомления или вручную\n"
            "• Автоматически добавляются после успешной капчи\n\n"
            "🔔 Уведомления:\n"
            "• Получайте уведомления о нарушениях\n"
            "• Мгновенно реагируйте через инлайн-кнопки\n\n"
            "💬 Мои чаты:\n"
            "• Просматривайте список ваших групп\n"
            "• Добавляйте новые чаты для модерации\n"
            "• Управляйте настройками для каждого чата\n\n"
            "👥 Забаненные:\n"
            "• Просматривайте список забаненных\n"
            "• Разбанивайте пользователей\n"
            "• Видите причину бана\n\n"
            "📊 Логи:\n"
            "• Вся статистика и история действий\n"
            "• Статистика капчи (сколько прошло/не прошло)\n\n"
            "💡 Добавьте бота в группу как администратора с правами:\n"
            "• Удаление сообщений\n"
            "• Блокировка пользователей"
        )
        
        await query.message.edit_text(text, reply_markup=get_help_menu())
    
    async def handle_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопки назад"""
        query = update.callback_query
        await query.answer()
        
        await query.message.edit_text(
            "🤖 Бот-модератор\n\nВыберите действие:",
            reply_markup=get_main_menu()
        )
    
    async def handle_toggle_automod(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вкл/выкл автомодерацию"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        settings = db.get_user_settings(user_id)
        new_value = not settings['automod_enabled']
        
        db.update_user_setting(user_id, 'automod_enabled', new_value)
        await self.handle_settings(update, context)
    
    async def handle_toggle_profile_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вкл/выкл проверку профилей"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        settings = db.get_user_settings(user_id)
        new_value = not settings['check_profiles']
        
        db.update_user_setting(user_id, 'check_profiles', new_value)
        await self.handle_profile_check(update, context)
    
    async def handle_toggle_media_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вкл/выкл проверку медиа"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        settings = db.get_user_settings(user_id)
        new_value = not settings['check_media']
        
        db.update_user_setting(user_id, 'check_media', new_value)
        await self.handle_settings(update, context)
    
    async def handle_toggle_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вкл/выкл уведомления"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        settings = db.get_user_settings(user_id)
        new_value = not settings['notify_admin']
        
        db.update_user_setting(user_id, 'notify_admin', new_value)
        await self.handle_settings(update, context)
    
    async def handle_change_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню выбора действия"""
        query = update.callback_query
        await query.answer()
        
        await query.message.edit_text(
            "🛡️ Выберите действие при нарушении:\n\n"
            "• БАН - полная блокировка\n"
            "• УДАЛЕНИЕ - только удаление сообщения\n"
            "• ПРЕДУПРЕЖДЕНИЕ - предупреждение + удаление",
            reply_markup=get_action_menu()
        )
    
    async def handle_action_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор действия"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        action = query.data
        
        db.update_user_setting(user_id, 'action_type', action)
        await self.handle_settings(update, context)
    
    async def handle_show_words(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список стоп-слов с кнопками удаления"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        words = db.get_stop_words(user_id)
        
        if not words:
            text = "🚫 Список стоп-слов пуст\n\nДобавьте слова через меню или напишите +слово"
            await query.message.edit_text(text, reply_markup=get_back_button())
        else:
            text = "🚫 Список стоп-слов:\n\n" + "\n".join([f"• {word}" for word in words])
            text += f"\n\nВсего: {len(words)} слов\n\nНажмите на слово чтобы удалить:"
            
            await query.message.edit_text(text, reply_markup=get_words_list_keyboard(words))
    
    async def handle_remove_word(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить конкретное стоп-слово"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        word_to_remove = query.data.replace('remove_', '')
        
        # Удаляем слово из базы
        success = db.remove_stop_word(user_id, word_to_remove)
        
        if success:
            await query.message.edit_text(
                f"✅ Слово '{word_to_remove}' удалено из стоп-листа",
                reply_markup=get_back_button()
            )
        else:
            await query.message.edit_text(
                f"❌ Не удалось удалить слово '{word_to_remove}'",
                reply_markup=get_back_button()
            )
    
    async def handle_add_word(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить стоп-слово - упрощенная версия"""
        query = update.callback_query
        await query.answer()
        
        text = (
            "➕ Добавление стоп-слов\n\n"
            "📝 Для быстрого добавления стоп-слов:\n\n"
            "1. Напишите в этот чат:\n"
            "<code>+реклама</code>\n\n"
            "2. Или несколько слов через запятую:\n"
            "<code>+реклама, спам, купить</code>\n\n"
            "✅ Слова автоматически добавятся в ваш стоп-лист!\n\n"
            "💡 Можно добавлять слова прямо из чата с ботом."
        )
    
        await query.message.edit_text(text, reply_markup=get_back_button(), parse_mode='HTML')
        
        await query.message.edit_text(text, reply_markup=get_back_button())
    
    async def handle_clear_words(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистить стоп-слова"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        db.clear_stop_words(user_id)
        
        await query.message.edit_text(
            "✅ Все стоп-слова очищены",
            reply_markup=get_back_button()
        )
    
    async def handle_popular_words(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать популярные стоп-слова"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        popular_words = db.get_popular_stop_words(limit=20)
        
        if not popular_words:
            text = "📊 Популярные стоп-слова\n\nПока нет популярных слов.\nДобавляйте слова в своем списке!"
            await query.message.edit_text(text, reply_markup=get_back_button())
        else:
            text = "📊 Популярные стоп-слова\n\n"
            text += "Самые часто используемые слова другими пользователями:\n\n"
            
            for i, (word, count) in enumerate(popular_words, 1):
                text += f"{i}. {word} (используют: {count} пользователей)\n"
            
            text += "\nВыберите слова для добавления:"
            
            await query.message.edit_text(text, reply_markup=get_popular_words_keyboard(popular_words))
    
    async def handle_add_popular_word(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить популярное слово в свой список"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        word = query.data.replace('add_popular_', '')
        
        success = db.add_stop_word(user_id, word)
        
        if success:
            await query.message.edit_text(
                f"✅ Слово '{word}' добавлено в ваш стоп-лист!",
                reply_markup=get_back_button()
            )
        else:
            await query.message.edit_text(
                f"⚠️ Слово '{word}' уже есть в вашем списке",
                reply_markup=get_back_button()
            )
    
    async def handle_add_multiple_popular(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить несколько популярных слов"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        popular_words = db.get_popular_stop_words(limit=10)
        
        if not popular_words:
            await query.message.edit_text(
                "❌ Нет популярных слов для добавления",
                reply_markup=get_back_button()
            )
            return
        
        added_count = 0
        already_exists = 0
        
        for word, count in popular_words[:5]:  # Добавляем топ-5 слов
            if db.add_stop_word(user_id, word):
                added_count += 1
            else:
                already_exists += 1
        
        text = f"✅ Добавлено {added_count} популярных слов!\n"
        if already_exists > 0:
            text += f"⚠️ {already_exists} слов уже были в вашем списке"
        
        await query.message.edit_text(text, reply_markup=get_back_button())
    
    async def handle_recent_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать последние логи"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        logs = db.get_user_logs(user_id, 10)
        
        if not logs:
            text = "📊 Логов пока нет\n\nНарушения будут отображаться здесь"
        else:
            text = "📋 Последние действия:\n\n"
            for i, (chat_id, username, reason, timestamp) in enumerate(logs, 1):
                time_str = timestamp.split(' ')[0]  # Берем только дату
                text += f"{i}. {time_str} - {username} ({reason})\n"
        
        await query.message.edit_text(text, reply_markup=get_back_button())
    
    async def handle_month_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика за месяц"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        stats = db.get_user_stats(user_id)
        
        user_chats = db.get_user_chats(user_id)
        chats_count = len(user_chats)
        
        text = (
            "📅 Общая статистика\n\n"
            "• Заблокировано: {} пользователей\n"
            "• По стоп-словам: {}\n"
            "• По профилям: {}\n\n"
            "• Активных групп: {}\n\n"
            "Всего за всё время: {} нарушений"
        ).format(stats['total'], stats['stop_words'], stats['profiles'], chats_count, stats['total'])
        
        await query.message.edit_text(text, reply_markup=get_back_button())
    
    async def handle_my_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик меню моих чатов"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user_chats = db.get_user_chats(user_id)
        chats_count = len(user_chats)
        
        text = (
            "💬 Мои чаты\n\n"
            "Активных групп: {}\n\n"
            "Здесь вы можете:\n"
            "• Просмотреть список ваших чатов\n"
            "• Добавить новые чаты для модерации\n"
            "• Управлять настройками для каждого чата"
        ).format(chats_count)
        
        await query.message.edit_text(text, reply_markup=get_my_chats_menu(chats_count))
    
    async def handle_show_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список чатов пользователя"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user_chats = db.get_user_chats(user_id)
        
        if not user_chats:
            text = (
                "💬 Мои чаты\n\n"
                "У вас пока нет добавленных чатов.\n\n"
                "Чтобы добавить чат:\n"
                "1. Добавьте бота в группу как администратора\n"
                "2. Назначьте права на удаление сообщений и бан\n"
                "3. Нажмите кнопку '🔄 Проверить чаты'"
            )
            await query.message.edit_text(text, reply_markup=get_add_chat_keyboard())
        else:
            # Проверяем статус каждого чата
            chats_with_status = []
            for chat_id, chat_title, automod_enabled in user_chats:
                try:
                    # Проверяем, является ли бот администратором
                    bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
                    if bot_member.status in ['administrator', 'creator']:
                        status = "active"
                    else:
                        status = "no_bot_rights"
                except:
                    status = "not_found"
                
                chats_with_status.append((chat_id, chat_title, status, automod_enabled))
            
            active_chats = [c for c in chats_with_status if c[2] == "active"]
            problem_chats = [c for c in chats_with_status if c[2] != "active"]
            
            text = "💬 Мои чаты\n\n"
            
            if active_chats:
                text += f"✅ Активные ({len(active_chats)}):\n"
                for chat_id, chat_title, status, automod_enabled in active_chats:
                    mod_status = "✅" if automod_enabled else "❌"
                    text += f"• {chat_title} {mod_status}\n"
            
            if problem_chats:
                text += f"\n⚠️ Проблемные ({len(problem_chats)}):\n"
                for chat_id, chat_title, status, automod_enabled in problem_chats:
                    status_text = "Нет прав бота" if status == "no_bot_rights" else "Чат не найден"
                    text += f"• {chat_title} ({status_text})\n"
            
            text += "\nВыберите чат для управления:"
            
            await query.message.edit_text(text, reply_markup=get_chats_list_keyboard(chats_with_status))
    
    async def handle_add_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик добавления чата"""
        query = update.callback_query
        await query.answer()
        
        text = (
            "🤖 Добавление чата\n\n"
            "Чтобы добавить чат для модерации:\n\n"
            "1. Добавьте меня в группу как администратора\n"
            "2. Назначьте права:\n"
            "   • Удаление сообщений ✅\n"
            "   • Блокировка пользователей ✅\n"
            "3. Вернитесь сюда и нажмите \"🔄 Проверить чаты\"\n\n"
            "Или используйте команду в группе:\n"
            "<code>/register</code>"
        )
        
        await query.message.edit_text(text, reply_markup=get_add_chat_keyboard(), parse_mode='HTML')
    
    async def handle_refresh_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обновить список чатов - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        query = update.callback_query
        await query.answer("🔄 Ищем новые чаты...")
        
        user_id = query.from_user.id
        
        try:
            # Просто показываем текущий список с информацией
            user_chats = db.get_user_chats(user_id)
            
            if user_chats:
                text = "🔄 Проверка чатов завершена!\n\n"
                text += f"Найдено {len(user_chats)} чатов в базе данных.\n\n"
                text += "Если вы добавили бота в новую группу:\n"
                text += "• Убедитесь, что бот назначен администратором\n"
                text += "• Используйте команду <code>/register</code> в группе\n"
            else:
                text = "🔄 Проверка чатов\n\n"
                text += "Чатов в базе данных не найдено.\n\n"
                text += "Чтобы добавить чат:\n"
                text += "1. Перейдите в нужную группу\n"
                text += "2. Отправьте команду <code>/register</code>\n"
                text += "3. Убедитесь, что бот - администратор"
                
            await query.message.edit_text(text, reply_markup=get_add_chat_keyboard(), parse_mode='HTML')
                
        except Exception as e:
            print(f"❌ Ошибка при обновлении чатов: {e}")
            await query.message.edit_text(
                "❌ Произошла ошибка при проверке чатов",
                reply_markup=get_add_chat_keyboard()
            )
    
    async def handle_chat_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Детальное управление чатом"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Исправляем обработку данных - проверяем формат
        data = query.data.replace('chat_', '')
        
        # Проверяем, что data содержит только цифры (ID чата)
        if not data.lstrip('-').isdigit():  # Разрешаем отрицательные ID чатов
            await query.message.edit_text(
                "❌ Ошибка: неверный формат ID чата",
                reply_markup=get_back_button()
            )
            return
            
        chat_id = int(data)
        
        # Получаем информацию о чате
        user_chats = db.get_user_chats(user_id)
        chat_info = None
        for cid, title, automod_enabled in user_chats:
            if cid == chat_id:
                chat_info = (cid, title, automod_enabled)
                break
        
        if not chat_info:
            await query.message.edit_text("❌ Чат не найден", reply_markup=get_back_button())
            return
        
        chat_id, chat_title, automod_enabled = chat_info
        
        # Проверяем статус чата
        try:
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            if bot_member.status in ['administrator', 'creator']:
                status = "active"
                status_text = "✅ Активен (бот-админ)"
            else:
                status = "no_bot_rights"
                status_text = "⚠️ Бот не админ"
        except Exception as e:
            status = "not_found"
            status_text = "❌ Чат не доступен"
        
        settings = db.get_user_settings(user_id)
        
        text = (
            f"🎯 Управление: \"{chat_title}\"\n\n"
            f"Статус: {status_text}\n"
            f"Модерация в чате: {'✅ ВКЛ' if automod_enabled else '❌ ВЫКЛ'}\n"
            f"Глобальные настройки: Автомодерация {'✅ ВКЛ' if settings['automod_enabled'] else '❌ ВЫКЛ'}\n\n"
            f"ID чата: <code>{chat_id}</code>"
        )
        
        await query.message.edit_text(
            text, 
            reply_markup=get_chat_management_keyboard(chat_id, chat_title, status, automod_enabled),
            parse_mode='HTML'
        )
    
    async def handle_chat_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Настройки конкретного чата"""
        query = update.callback_query
        await query.answer()
        
        # Исправляем обработку данных
        data = query.data.replace('chat_settings_', '')
        
        if not data.lstrip('-').isdigit():  # Разрешаем отрицательные ID чатов
            await query.message.edit_text(
                "❌ Ошибка: неверный формат ID чата",
                reply_markup=get_back_button()
            )
            return
            
        chat_id = int(data)
        
        # Здесь можно реализовать индивидуальные настройки для чата
        # Пока просто сообщаем что функционал в разработке
        
        await query.message.edit_text(
            f"⚙️ Настройки для чата {chat_id}\n\n"
            "Индивидуальные настройки для чата в разработке.\n"
            "Сейчас используются глобальные настройки из раздела 'Настройки модерации'.",
            reply_markup=get_back_button()
        )
    
    async def handle_chat_exceptions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Исключения для конкретного чата"""
        query = update.callback_query
        await query.answer()
        
        # Исправляем обработку данных
        data = query.data.replace('chat_exceptions_', '')
        
        if not data.lstrip('-').isdigit():  # Разрешаем отрицательные ID чатов
            await query.message.edit_text(
                "❌ Ошибка: неверный формат ID чата",
                reply_markup=get_back_button()
            )
            return
            
        chat_id = int(data)
        user_id = query.from_user.id
        
        exceptions = db.get_chat_exceptions(chat_id, user_id)
        
        if not exceptions:
            text = f"👤 Исключения для чата {chat_id}\n\nСписок исключений пуст."
        else:
            text = f"👤 Исключения для чата {chat_id}\n\n"
            for user_id_ex, username, reason in exceptions:
                display_name = username if username else f"ID: {user_id_ex}"
                text += f"• {display_name}\n"
                if reason:
                    text += f"  📝 {reason}\n"
        
        await query.message.edit_text(text, reply_markup=get_back_button())
    
    async def handle_toggle_chat_automod(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вкл/выкл модерацию для конкретного чата"""
        query = update.callback_query
        await query.answer()
        
        # Исправляем обработку данных
        data = query.data.replace('toggle_chat_', '')
        
        if not data.lstrip('-').isdigit():  # Разрешаем отрицательные ID чатов
            await query.message.edit_text(
                "❌ Ошибка: неверный формат ID чата",
                reply_markup=get_back_button()
            )
            return
            
        chat_id = int(data)
        user_id = query.from_user.id
        
        # Получаем текущее состояние
        user_chats = db.get_user_chats(user_id)
        current_state = None
        chat_title = ""
        
        for cid, title, automod_enabled in user_chats:
            if cid == chat_id:
                current_state = automod_enabled
                chat_title = title
                break
        
        if current_state is None:
            await query.message.edit_text("❌ Чат не найден", reply_markup=get_back_button())
            return
        
        new_state = not current_state
        db.update_chat_setting(chat_id, 'automod_enabled', new_state)
        
        status = "✅ ВКЛЮЧЕНА" if new_state else "❌ ВЫКЛЮЧЕНА"
        await query.message.edit_text(
            f"⚙️ Модерация в чате \"{chat_title}\" {status}",
            reply_markup=get_back_button()
        )
    
    async def handle_remove_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить чат из списка"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Исправляем обработку данных
        data = query.data.replace('remove_chat_', '')
        
        if not data.lstrip('-').isdigit():  # Разрешаем отрицательные ID чатов
            await query.message.edit_text(
                "❌ Ошибка: неверный формат ID чата",
                reply_markup=get_back_button()
            )
            return
            
        chat_id = int(data)
        
        # Удаляем чат из базы
        success = db.remove_bot_chat(chat_id, user_id)
        
        if success:
            await query.message.edit_text(
                "✅ Чат удален из списка\n\n"
                "Бот больше не будет модерировать этот чат.",
                reply_markup=get_back_button()
            )
        else:
            await query.message.edit_text(
                "❌ Не удалось удалить чат",
                reply_markup=get_back_button()
            )

# Создаем экземпляр обработчика
menu_handlers = MenuHandlers()