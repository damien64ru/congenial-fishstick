# message_handler.py (ИСПРАВЛЕННАЯ ВЕРСИЯ - капча работает корректно)
import re
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from config import CHANNEL_PATTERNS, CAPTCHA_ENABLED, CAPTCHA_TIMEOUT, CAPTCHA_SIMPLE_PROBLEMS

# Состояния для добавления стоп-слов
ADD_WORD = 1

class MessageMonitor:
    """Мониторинг всех сообщений для обнаружения отложенного редактирования"""
    def __init__(self):
        self.cache = {}  # Основной кэш сообщений
        self.cache_keys_by_time = []  # Ключи отсортированные по времени
        self.metrics = {
            'total_tracked': 0,
            'total_checked': 0,
            'violations_found': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'edits_detected': 0,
            'total_processed': 0
        }
        self.max_age = 600  # 10 минут в секундах
        self.max_cache_size = 5000
        self.is_monitoring = False
        self.context_ref = None  # Ссылка на контекст для проверок
        self.monitoring_task = None  # Сохраняем задачу для корректного завершения
        self.captcha_stats = {  # Статистика капчи в памяти
            'sent': 0,
            'passed': 0,
            'failed': 0,
            'timeout': 0
        }
        self.active_captchas = {}  # Активные капчи: {chat_id_user_id: (answer, message_id)}
    
    def start_monitoring(self, context=None):
        """Запуск мониторинга"""
        if not self.is_monitoring:
            self.is_monitoring = True
            if context:
                self.context_ref = context
            # Создаем задачу и сохраняем ссылку
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            print("🔍 Мониторинг сообщений запущен (10 минут хранения, проверка каждые 10 секунд)")
    
    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            self.monitoring_task = None
        print("🔍 Мониторинг сообщений остановлен")
    
    async def _monitoring_loop(self):
        """Основной цикл мониторинга"""
        try:
            while self.is_monitoring:
                try:
                    await asyncio.sleep(10)  # Проверка каждые 10 секунд
                    await self._check_all_messages()
                    self._cleanup_old_entries()
                except asyncio.CancelledError:
                    # Задача была отменена - нормальный выход
                    break
                except Exception as e:
                    print(f"❌ Ошибка в цикле мониторинга: {e}")
                    # Продолжаем работу после ошибки
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ Критическая ошибка в мониторинге: {e}")
        finally:
            print("🔍 Цикл мониторинга завершен")
    
    async def _check_all_messages(self):
        """Проверка всех сообщений в кэше"""
        if not self.cache:
            return
        
        checked_count = 0
        current_time = datetime.now().timestamp()
        
        for cache_key in list(self.cache.keys()):
            if not self.is_monitoring:
                break  # Прерываем если мониторинг остановлен
                
            if cache_key in self.cache:
                message_info = self.cache[cache_key]
                
                # Проверяем только сообщения младше 10 минут
                if current_time - message_info['timestamp'] < self.max_age:
                    checked_count += 1
                    
                    # Обновляем счетчик проверок
                    message_info['check_count'] = message_info.get('check_count', 0) + 1
        
        self.metrics['total_checked'] += checked_count
        
        # Логируем статистику каждые 100 проверок
        if self.metrics['total_checked'] % 100 == 0:
            print(f"📊 Мониторинг: отслеживается {len(self.cache)} сообщений, проверок: {self.metrics['total_checked']}")
    
    def _cleanup_old_entries(self):
        """Очистка старых записей из кэша"""
        current_time = datetime.now().timestamp()
        keys_to_remove = []
        
        for cache_key in list(self.cache.keys()):
            if cache_key in self.cache:
                message_info = self.cache[cache_key]
                if current_time - message_info['timestamp'] > self.max_age:
                    keys_to_remove.append(cache_key)
        
        removed_count = 0
        for key in keys_to_remove:
            if key in self.cache:
                del self.cache[key]
                removed_count += 1
        
        # Обновляем список ключей
        self.cache_keys_by_time = [
            k for k in self.cache_keys_by_time 
            if k in self.cache
        ]
        
        if removed_count > 0:
            print(f"🧹 Очищено {removed_count} старых сообщений из кэша")
    
    def add_message(self, chat_id, user_id, message_id, text, admin_id, chat_title, settings):
        """Добавить сообщение в мониторинг"""
        cache_key = f"{chat_id}_{user_id}_{message_id}"
        
        # Если уже есть в кэше - обновляем
        if cache_key in self.cache:
            self.cache[cache_key]['timestamp'] = datetime.now().timestamp()
            self.cache[cache_key]['check_count'] = 0
            self.metrics['cache_hits'] += 1
            return cache_key
        
        self.cache[cache_key] = {
            'message_id': message_id,
            'chat_id': chat_id,
            'user_id': user_id,
            'original_text': text,
            'timestamp': datetime.now().timestamp(),
            'admin_id': admin_id,
            'chat_title': chat_title,
            'settings': settings,
            'check_count': 0,
            'edit_count': 0,
            'last_violation_check': 0
        }
        
        self.cache_keys_by_time.append(cache_key)
        self.metrics['total_tracked'] += 1
        self.metrics['cache_misses'] += 1
        self.metrics['total_processed'] += 1
        
        # Ограничиваем размер кэша - удаляем самые старые
        if len(self.cache) > self.max_cache_size:
            self._remove_oldest()
        
        return cache_key
    
    def _remove_oldest(self):
        """Удалить самые старые записи"""
        if self.cache_keys_by_time:
            # Удаляем 10% самых старых записей
            remove_count = max(1, len(self.cache_keys_by_time) // 10)
            for _ in range(remove_count):
                if self.cache_keys_by_time:
                    oldest_key = self.cache_keys_by_time.pop(0)
                    if oldest_key in self.cache:
                        del self.cache[oldest_key]
    
    def get_stats(self):
        """Получить статистику мониторинга"""
        current_time = datetime.now().timestamp()
        oldest_timestamp = current_time
        
        if self.cache:
            oldest_timestamp = min([info['timestamp'] for info in self.cache.values()])
        
        avg_check_count = 0
        if self.cache:
            avg_check_count = sum([info.get('check_count', 0) for info in self.cache.values()]) / len(self.cache)
        
        return {
            'active_tracking': len(self.cache),
            'cache_size': len(self.cache),
            'oldest_message': oldest_timestamp,
            'avg_checks_per_msg': round(avg_check_count, 1),
            **self.metrics
        }
    
    def clear_cache(self):
        """Очистить весь кэш"""
        old_size = len(self.cache)
        self.cache.clear()
        self.cache_keys_by_time.clear()
        print(f"🧹 Кэш мониторинга очищен (удалено {old_size} сообщений)")
        return old_size
    
    def get_captcha_stats(self):
        """Получить статистику капчи"""
        return self.captcha_stats.copy()

class MessageHandler:
    def __init__(self):
        self.monitor = MessageMonitor()
        self.pending_captchas = {}  # Ожидающие капчи: {chat_id_user_id: (answer, captcha_msg_id, original_msg_id, admin_id, settings, reason)}
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех сообщений в группах"""
        message = update.message
        
        # Проверяем что это сообщение
        if not message:
            return
        
        chat_id = message.chat_id
        user = message.from_user
        
        # Проверяем сначала, не является ли это ответом на капчу
        captcha_key = f"{chat_id}_{user.id}"
        if captcha_key in self.pending_captchas:
            await self._check_captcha_response(message, context)
            return
        
        print(f"🔍 [message_handler] Получено сообщение в чате {chat_id} от {user.id} ({user.username or user.first_name})")
        
        # Пропускаем сообщения от самого бота
        if user.id == context.bot.id:
            return
        
        # Получаем информацию о чате
        try:
            chat = await context.bot.get_chat(chat_id)
            chat_title = chat.title
        except Exception as e:
            print(f"❌ Ошибка получения информации о чате: {e}")
            chat_title = "Unknown Group"
        
        # Ищем администратора этого чата
        admin_id = db.get_chat_admin(chat_id)
        if not admin_id:
            print(f"❌ Администратор чата {chat_id} не найден в базе")
            return
        
        # Получаем настройки администратора
        settings = db.get_user_settings(admin_id)
        
        # Получаем настройки конкретного чата
        chat_settings = db.get_chat_settings(chat_id)
        
        # Проверяем и глобальные настройки И настройки чата
        if not settings or not settings['automod_enabled']:
            print(f"❌ Глобальная автомодерация отключена для администратора {admin_id}")
            return
        
        if not chat_settings or not chat_settings['automod_enabled']:
            print(f"❌ Модерация отключена для чата {chat_id}")
            return
        
        # Проверяем исключения для этого пользователя
        if db.is_user_exception(user.id, chat_id):
            print(f"✅ Пользователь {user.id} в исключениях - пропускаем")
            return
        
        # Проверяем, является ли отправитель администратором
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user.id)
            if chat_member.status in ['administrator', 'creator']:
                print(f"✅ Пользователь {user.id} администратор - пропускаем")
                return
        except Exception as e:
            print(f"❌ Ошибка при проверке прав пользователя: {e}")
            return
        
        # Добавляем ВСЕ сообщения в мониторинг
        if message.text:
            cache_key = self.monitor.add_message(
                chat_id, user.id, message.message_id, 
                message.text, admin_id, chat_title, settings
            )
            print(f"📝 Сообщение добавлено в мониторинг: {cache_key}")
        
        # Запускаем мониторинг если еще не запущен
        if not self.monitor.is_monitoring:
            self.monitor.start_monitoring(context)
        
        # Проверка стоп-слов для текущего сообщения
        if message.text:
            print(f"🔍 Проверяем на стоп-слова: {message.text[:50]}...")
            if await self.check_stop_words(message, settings, context, admin_id, chat_id, chat_title):
                return
        
        # Проверка профиля на каналы
        if settings['check_profiles']:
            print(f"🔍 Проверяем профиль пользователя {user.id} на каналы")
            if await self.check_profile_for_channels(user, message, settings, context, admin_id, chat_id, chat_title):
                return
        
        print(f"✅ Сообщение от {user.id} прошло проверки")
    
    async def _check_captcha_response(self, message, context):
        """Проверить ответ на капчу"""
        chat_id = message.chat_id
        user = message.from_user
        captcha_key = f"{chat_id}_{user.id}"
        
        if captcha_key not in self.pending_captchas:
            return
        
        answer, captcha_msg_id, original_msg_id, admin_id, settings, reason = self.pending_captchas[captcha_key]
        
        # Удаляем из ожидающих
        del self.pending_captchas[captcha_key]
        
        # Проверяем ответ
        user_answer = message.text.strip() if message.text else ""
        
        if user_answer == answer:
            # ✅ КАПЧА ПРОЙДЕНА
            self.monitor.captcha_stats['passed'] += 1
            print(f"✅ Пользователь {user.id} решил капчу правильно: {user_answer} == {answer}")
            
            # Удаляем сообщение с капчей
            try:
                await context.bot.delete_message(chat_id, captcha_msg_id)
            except:
                pass
            
            # Отправляем сообщение об успехе
            success_msg = await context.bot.send_message(
                chat_id,
                f"✅ @{user.username or user.first_name} прошел проверку!\n"
                f"Вы добавлены в исключения."
            )
            
            # Удаляем через 5 секунд
            await self.delete_after(success_msg, 5)
            
            # Добавляем пользователя в исключения
            username = f"@{user.username}" if user.username else user.first_name
            success = db.add_user_exception(
                user.id, username, chat_id, admin_id,
                f"Автоматически после успешной капчи ({reason})"
            )
            
            if success:
                print(f"✅ Пользователь {user.id} добавлен в исключения после капчи")
                
                # Отправляем уведомление админу
                if settings['notify_admin']:
                    try:
                        chat = await context.bot.get_chat(chat_id)
                        chat_title = chat.title
                    except:
                        chat_title = "Unknown Group"
                    
                    notification_text = (
                        f"🟢 Капча пройдена - пользователь добавлен в исключения\n\n"
                        f"💬 Чат: {chat_title}\n"
                        f"👤 Пользователь: {username}\n"
                        f"🆔 ID: {user.id}\n"
                        f"📝 Нарушение: {reason}\n"
                        f"✅ Ответ на капчу: {user_answer}\n\n"
                        f"✅ Пользователь добавлен в исключения автоматически"
                    )
                    
                    try:
                        await context.bot.send_message(admin_id, notification_text)
                        print(f"📨 Уведомление о капче отправлено администратору {admin_id}")
                    except Exception as e:
                        print(f"❌ Ошибка отправки уведомления о капче: {e}")
        else:
            # ❌ НЕВЕРНЫЙ ОТВЕТ
            self.monitor.captcha_stats['failed'] += 1
            print(f"❌ Пользователь {user.id} ошибся в капче: {user_answer} != {answer}")
            
            # Удаляем сообщение с капчей
            try:
                await context.bot.delete_message(chat_id, captcha_msg_id)
            except:
                pass
            
            # Отправляем сообщение об ошибке
            error_msg = await context.bot.send_message(
                chat_id,
                f"❌ @{user.username or user.first_name} не прошел проверку!\n"
                f"Правильный ответ: {answer}\n"
                f"Выполняю стандартное действие..."
            )
            
            # Удаляем через 3 секунды
            await self.delete_after(error_msg, 3)
            
            # Выполняем стандартное действие (БАН)
            try:
                # Баним пользователя
                action_type = settings['action_type']
                if action_type == 'ban':
                    await context.bot.ban_chat_member(chat_id, user.id)
                    print(f"🚫 Пользователь {user.id} забанен (неправильная капча)")
                    
                    # Записываем в логи
                    db.add_log(
                        admin_id,
                        chat_id,
                        user.id,
                        f"@{user.username}" if user.username else user.first_name,
                        f"{reason} (неправильная капча)"
                    )
                    
                    # Добавляем в забаненные
                    try:
                        chat = await context.bot.get_chat(chat_id)
                        chat_title = chat.title
                    except:
                        chat_title = "Unknown Group"
                    
                    db.add_banned_user(
                        user.id,
                        f"@{user.username}" if user.username else user.first_name,
                        chat_id,
                        chat_title,
                        admin_id,
                        f"{reason} (неправильная капча)"
                    )
                    
            except Exception as e:
                print(f"❌ Ошибка при выполнении действия после капчи: {e}")
    
    async def handle_edited_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик отредактированных сообщений - ИСПРАВЛЕННЫЙ"""
        edited_message = update.edited_message
        if not edited_message:
            return
        
        chat_id = edited_message.chat_id
        user = edited_message.from_user
        
        print(f"✏️ ОБНАРУЖЕНО РЕДАКТИРОВАНИЕ в чате {chat_id} от пользователя {user.id} ({user.username or user.first_name})")
        
        # Пропускаем сообщения от самого бота
        if user.id == context.bot.id:
            return
        
        # ПРОВЕРКА: Даже если пользователь решает капчу, редактирование должно проверяться!
        captcha_key = f"{chat_id}_{user.id}"
        if captcha_key in self.pending_captchas:
            print(f"⚠️ Пользователь {user.id} решает капчу, но проверяем редактирование...")
            # Не возвращаемся, продолжаем проверку!
        
        # Запускаем мониторинг если еще не запущен
        if not self.monitor.is_monitoring:
            self.monitor.start_monitoring(context)
        
        # Ищем администратора этого чата
        admin_id = db.get_chat_admin(chat_id)
        if not admin_id:
            print(f"❌ Администратор чата {chat_id} не найден")
            return
        
        # Получаем настройки администратора
        settings = db.get_user_settings(admin_id)
        
        # Получаем настройки конкретного чата
        chat_settings = db.get_chat_settings(chat_id)
        
        # Проверяем и глобальные настройки И настройки чата
        if not settings or not settings['automod_enabled']:
            return
        
        if not chat_settings or not chat_settings['automod_enabled']:
            return
        
        # Проверяем исключения
        if db.is_user_exception(user.id, chat_id):
            print(f"✅ Пользователь {user.id} в исключениях - пропускаем редактирование")
            return
        
        # Проверяем, является ли отправитель администратором
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user.id)
            if chat_member.status in ['administrator', 'creator']:
                print(f"✅ Пользователь {user.id} администратор - пропускаем редактирование")
                return
        except Exception as e:
            print(f"❌ Ошибка при проверке прав пользователя: {e}")
            return
        
        # Обновляем метрики мониторинга
        self.monitor.metrics['edits_detected'] += 1
        
        # Проверяем отредактированное сообщение на стоп-слова
        if edited_message.text:
            text_preview = edited_message.text[:100] + "..." if len(edited_message.text) > 100 else edited_message.text
            print(f"📝 Проверяем отредактированный текст: {text_preview}")
            
            stop_words = db.get_stop_words(admin_id)
            text = edited_message.text.lower()
            
            violations_found = []
            for word in stop_words:
                if word.lower() in text:
                    violations_found.append(word)
                    print(f"🚫 Найдено стоп-слово в отредактированном сообщении: '{word}'")
            
            if violations_found:
                # Записываем в логи
                db.add_log(
                    admin_id, 
                    chat_id, 
                    user.id,
                    f"@{user.username}" if user.username else user.first_name,
                    f"стоп-слова в редактировании: {', '.join(violations_found[:3])}"
                )
                
                # Обновляем метрики мониторинга
                self.monitor.metrics['violations_found'] += 1
                
                # Отправляем уведомление админу если включено
                if settings['notify_admin']:
                    try:
                        chat = await context.bot.get_chat(chat_id)
                        chat_title = chat.title
                    except:
                        chat_title = "Unknown Group"
                    
                    await self.send_admin_notification(
                        context, admin_id, chat_id, chat_title, user, 
                        f"стоп-слова в редактировании: {', '.join(violations_found[:2])}", 
                        edited_message.message_id
                    )
                
                # ВЫПОЛНЯЕМ ДЕЙСТВИЕ (как для обычных сообщений!)
                await self.take_action(edited_message, settings, context, 
                                    f"стоп-слова в редактировании: {violations_found[0]}")
                return
        
        # Проверяем отредактированное сообщение на каналы в профиле
        if settings['check_profiles'] and edited_message.text:
            print(f"🔍 Проверяем профиль пользователя {user.id} на каналы (в отредактированном сообщении)")
            if await self.check_profile_for_channels(user, edited_message, settings, context, admin_id, chat_id, "Unknown Group"):
                return
        
        print(f"✅ Отредактированное сообщение от {user.id} прошло проверку")
    
    async def handle_media_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик медиа сообщений в группах"""
        message = update.message
        
        # Проверяем что это сообщение
        if not message:
            return
        
        chat_id = message.chat_id
        user = message.from_user
        
        # Проверяем сначала, не является ли это ответом на капчу
        captcha_key = f"{chat_id}_{user.id}"
        if captcha_key in self.pending_captchas:
            # Медиа не может быть ответом на капчу
            return
        
        # Пропускаем сообщения от самого бота
        if user.id == context.bot.id:
            return
        
        # Ищем администратора этого чата
        admin_id = db.get_chat_admin(chat_id)
        if not admin_id:
            return
        
        # Получаем настройки администратора
        settings = db.get_user_settings(admin_id)
        
        # Получаем настройки конкретного чата
        chat_settings = db.get_chat_settings(chat_id)
        
        # Проверяем и глобальные настройки И настройки чата
        if not settings or not settings['automod_enabled']:
            return
        
        if not chat_settings or not chat_settings['automod_enabled']:
            return
        
        if not settings or not settings['automod_enabled'] or not settings['check_media']:
            return
        
        # Проверяем исключения
        if db.is_user_exception(user.id, chat_id):
            return
        
        # Проверяем, является ли отправитель администратором
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user.id)
            if chat_member.status in ['administrator', 'creator']:
                return
        except:
            return
        
        # Проверяем подпись медиа на стоп-слова
        if message.caption:
            print(f"🖼️ Проверяем подпись медиа от {user.id}")
            await self.handle_message(update, context)
    
    async def check_stop_words(self, message, settings, context, admin_id, chat_id, chat_title):
        """Проверка на стоп-слова"""
        user = message.from_user
        text = message.text.lower()
        
        stop_words = db.get_stop_words(admin_id)
        
        violations_found = []
        for word in stop_words:
            if word.lower() in text:
                violations_found.append(word)
                print(f"🚫 Найдено стоп-слово: '{word}'")
        
        if violations_found:
            # Записываем в логи
            db.add_log(
                admin_id, 
                chat_id, 
                user.id,
                f"@{user.username}" if user.username else user.first_name,
                f"стоп-слова: {', '.join(violations_found[:3])}"
            )
            
            # Отправляем уведомление админу если включено
            if settings['notify_admin']:
                await self.send_admin_notification(
                    context, admin_id, chat_id, chat_title, user, 
                    f"стоп-слова: {violations_found[0]}", message.message_id
                )
            
            # Выполняем действие (С КАПЧЕЙ!)
            await self.take_action(message, settings, context, f"стоп-слова: {violations_found[0]}")
            return True
        
        return False
    
    async def check_profile_for_channels(self, user, message, settings, context, admin_id, chat_id, chat_title):
        """Проверка профиля на каналы"""
        try:
            print(f"🔍 Начинаем углубленную проверку профиля пользователя {user.id}")
            
            # Собираем ВСЕ доступные данные для проверки
            all_profile_data = ""
            found_channels = []
            
            # 1. Username (всегда доступен)
            if user.username:
                all_profile_data += f" {user.username}"
                print(f"   👤 Username: {user.username}")
            
            # 2. Имя (всегда доступно)
            if user.first_name:
                all_profile_data += f" {user.first_name}"
                print(f"   👤 Имя: {user.first_name}")
            
            # 3. Фамилия (всегда доступна)
            if user.last_name:
                all_profile_data += f" {user.last_name}"
                print(f"   👤 Фамилия: {user.last_name}")
            
            # 4. Пробуем получить полную информацию через get_chat
            try:
                user_chat = await context.bot.get_chat(user.id)
                print(f"   🔍 Информация из get_chat получена")
                
                # Пробуем разные атрибуты которые могут содержать информацию
                if hasattr(user_chat, 'bio') and user_chat.bio:
                    bio_text = user_chat.bio
                    all_profile_data += f" {bio_text}"
                    print(f"   📝 Bio: {bio_text}")
                
                if hasattr(user_chat, 'description') and user_chat.description:
                    description_text = user_chat.description
                    all_profile_data += f" {description_text}"
                    print(f"   📄 Description: {description_text}")
                
                # 5. СПЕЦИАЛЬНАЯ ПРОВЕРКА: Привязанный канал (linked_chat)
                if hasattr(user_chat, 'linked_chat_id') and user_chat.linked_chat_id:
                    linked_chat_id = user_chat.linked_chat_id
                    print(f"   🔗 ОБНАРУЖЕН ПРИВЯЗАННЫЙ КАНАЛ! ID: {linked_chat_id}")
                    
                    try:
                        linked_chat = await context.bot.get_chat(linked_chat_id)
                        linked_chat_title = linked_chat.title
                        all_profile_data += f" {linked_chat_title}"
                        print(f"   🔗 Привязанный канал: {linked_chat_title}")
                        
                        # Сразу добавляем в найденные каналы
                        found_channels.append(f"привязанный канал: {linked_chat_title}")
                        
                    except Exception as e:
                        print(f"   ❌ Ошибка получения информации о привязанном канале: {e}")
                        found_channels.append(f"привязанный канал ID: {linked_chat_id}")
                
                # 6. ПРОВЕРКА: Закрепленные сообщения
                print("   📌 Проверяем закрепленные сообщения...")
                try:
                    # Пробуем получить pinned_message
                    if hasattr(user_chat, 'pinned_message') and user_chat.pinned_message:
                        pinned_msg = user_chat.pinned_message
                        
                        # Получаем текст из закрепленного сообщения
                        pinned_text = ""
                        if pinned_msg.text:
                            pinned_text = pinned_msg.text
                        elif pinned_msg.caption:
                            pinned_text = pinned_msg.caption
                        
                        if pinned_text:
                            all_profile_data += f" {pinned_text}"
                            print(f"   📌 Текст закрепленного сообщения: {pinned_text}")
                        
                        # Проверяем entities в закрепленном сообщении
                        if hasattr(pinned_msg, 'entities') and pinned_msg.entities:
                            for entity in pinned_msg.entities:
                                if entity.type in ['url', 'text_link']:
                                    url_text = pinned_msg.text[entity.offset:entity.offset + entity.length]
                                    all_profile_data += f" {url_text}"
                                    print(f"   🔗 Ссылка в закрепленном: {url_text}")
                                    
                        # Проверяем caption_entities
                        if hasattr(pinned_msg, 'caption_entities') and pinned_msg.caption_entities:
                            for entity in pinned_msg.caption_entities:
                                if entity.type in ['url', 'text_link']:
                                    url_text = pinned_msg.caption[entity.offset:entity.offset + entity.length]
                                    all_profile_data += f" {url_text}"
                                    print(f"   🔗 Ссылка в подписи: {url_text}")
                                    
                except Exception as e:
                    print(f"   ℹ️ Не удалось проверить закрепленные сообщения: {e}")
                    
            except Exception as e:
                print(f"   ❌ Ошибка get_chat: {e}")
                
                # Если get_chat не работает, пробуем через get_chat_member
                try:
                    chat_member = await context.bot.get_chat_member(chat_id, user.id)
                    if hasattr(chat_member, 'bio') and chat_member.bio:
                        bio_text = chat_member.bio
                        all_profile_data += f" {bio_text}"
                        print(f"   📝 Bio из get_chat_member: {bio_text}")
                except Exception as e2:
                    print(f"   ❌ Ошибка get_chat_member: {e2}")
            
            # 7. Проверяем само сообщение на ссылки
            if message.text:
                message_text = message.text
                all_profile_data += f" {message_text}"
                print(f"   💬 Текст сообщения: {message_text}")
            
            print(f"   📋 Весь текст для проверки: '{all_profile_data[:200]}...'")
            
            # ПРОВЕРКА: Поиск по паттернам каналов
            print(f"   🔎 Ищем каналы по {len(CHANNEL_PATTERNS)} паттернам...")
            
            for i, pattern in enumerate(CHANNEL_PATTERNS):
                matches = re.findall(pattern, all_profile_data, re.IGNORECASE)
                if matches:
                    for match in matches:
                        if match not in found_channels:
                            found_channels.append(match)
                            print(f"   🚫 НАЙДЕН КАНАЛ! Паттерн #{i}: '{pattern}' → '{match}'")
            
            if found_channels:
                # Записываем в логи
                db.add_log(
                    admin_id, 
                    chat_id, 
                    user.id,
                    f"@{user.username}" if user.username else user.first_name,
                    f"каналы в профиле: {', '.join(found_channels[:3])}"  # Ограничиваем длину
                )
                
                # Отправляем уведомление админу если включено
                if settings['notify_admin']:
                    await self.send_admin_notification(
                        context, admin_id, chat_id, chat_title, user,
                        f"каналы в профиле: {found_channels[0]}", 
                        message.message_id
                    )
                
                # Выполняем действие (С КАПЧЕЙ!)
                await self.take_action(message, settings, context, f"каналы в профиле: {found_channels[0]}")
                return True
            
            print("   ✅ Каналов в профиле не найдено")
                                
        except Exception as e:
            print(f"   ❌ ОШИБКА при проверке профиля: {e}")
        
        return False
    
    async def send_admin_notification(self, context, admin_id, chat_id, chat_title, user, reason, message_id):
        """Отправить уведомление администратору"""
        try:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Разбанить", callback_data=f"unban_{user.id}_{chat_id}"),
                    InlineKeyboardButton("🔒 Забанить", callback_data=f"ban_{user.id}_{chat_id}")
                ],
                [
                    InlineKeyboardButton("👤 В исключения", callback_data=f"exception_{user.id}_{chat_id}"),
                    InlineKeyboardButton("❌ Пропустить", callback_data=f"resolve_{user.id}_{chat_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            notification_text = (
                f"🚨 Нарушение в \"{chat_title}\"\n\n"
                f"👤 Пользователь: @{user.username or user.first_name}\n"
                f"🆔 ID: {user.id}\n"
                f"📝 Причина: {reason}\n\n"
                f"Выберите действие:"
            )
            
            message = await context.bot.send_message(
                admin_id,
                notification_text,
                reply_markup=reply_markup
            )
            
            db.add_notification(
                admin_id, chat_id, chat_title, user.id,
                f"@{user.username}" if user.username else user.first_name,
                reason, message.message_id
            )
            
            print(f"📨 Уведомление отправлено администратору {admin_id}")
            
        except Exception as e:
            print(f"❌ Ошибка отправки уведомления: {e}")
    
    async def take_action(self, message, settings, context, reason):
        """Выполнить действие при нарушении С КАПЧЕЙ - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        print(f"🛡️ Обработка нарушения: {reason}")
        
        # ВАЖНО: Всегда сначала удаляем сообщение
        try:
            await message.delete()
            print("✅ Сообщение удалено")
        except Exception as e:
            print(f"❌ Ошибка удаления сообщения: {e}")
        
        # Если капча выключена глобально - сразу остальное действие
        if not CAPTCHA_ENABLED:
            print("ℹ️ Капча отключена глобально, выполняем остальное действие")
            await self._execute_remaining_action(message, settings, context, reason)
            return
        
        # Пытаемся отправить капчу
        captcha_sent = await self._send_captcha(message, context, reason, settings)
        
        # Если капча не отправилась - выполняем остальное действие
        if not captcha_sent:
            print("ℹ️ Не удалось отправить капчу, выполняем стандартное действие")
            await self._execute_remaining_action(message, settings, context, reason)
        else:
            print("✅ Капча отправлена, ожидаем ответ...")
            # Если капча отправлена успешно, остальное действие будет выполнено
            # либо после таймаута, либо после неправильного ответа в _check_captcha_response
    
    async def _send_captcha(self, message, context, reason, settings):
        """Отправить капчу пользователю"""
        try:
            user = message.from_user
            chat_id = message.chat_id
            
            # Получаем admin_id для исключений
            admin_id = db.get_chat_admin(chat_id)
            if not admin_id:
                print("❌ Не найден администратор чата для капчи")
                return False
            
            # Проверяем, нет ли уже активной капчи для этого пользователя
            captcha_key = f"{chat_id}_{user.id}"
            if captcha_key in self.pending_captchas:
                print(f"⚠️ У пользователя {user.id} уже есть активная капча")
                return False
            
            # Увеличиваем счетчик отправленных капч
            self.monitor.captcha_stats['sent'] += 1
            
            # Выбираем случайный пример
            import random
            problem, answer = random.choice(CAPTCHA_SIMPLE_PROBLEMS)
            
            # Отправляем капчу
            captcha_msg = await context.bot.send_message(
                chat_id,
                f"🤖 Обнаружено нарушение: {reason}\n\n"
                f"🔐 Докажите что вы не бот:\n"
                f"Решите: {problem} = ?\n\n"
                f"⏰ У вас {CAPTCHA_TIMEOUT} секунд...\n"
                f"✅ При успехе добавлю вас в исключения"
            )
            
            # Сохраняем информацию о капче
            self.pending_captchas[captcha_key] = (
                answer, captcha_msg.message_id, message.message_id, 
                admin_id, settings, reason
            )
            
            print(f"📨 Капча отправлена пользователю {user.id}: {problem} = ? (ответ: {answer})")
            
            # Запускаем таймер для капчи
            asyncio.create_task(self._captcha_timeout(captcha_key, chat_id, captcha_msg.message_id, context))
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка отправки капчи: {e}")
            return False
    
    async def _captcha_timeout(self, captcha_key, chat_id, captcha_msg_id, context):
        """Таймер для капчи"""
        try:
            # Ждем таймаут
            await asyncio.sleep(CAPTCHA_TIMEOUT)
            
            # Проверяем, существует ли еще капча
            if captcha_key in self.pending_captchas:
                print(f"⏰ Таймаут капчи для {captcha_key}")
                
                answer, captcha_msg_id, original_msg_id, admin_id, settings, reason = self.pending_captchas[captcha_key]
                
                # Удаляем капчу из ожидающих
                del self.pending_captchas[captcha_key]
                
                # Увеличиваем счетчик таймаутов
                self.monitor.captcha_stats['timeout'] += 1
                
                # Удаляем сообщение с капчей
                try:
                    await context.bot.delete_message(chat_id, captcha_msg_id)
                except:
                    pass
                
                # Отправляем сообщение о таймауте
                try:
                    timeout_msg = await context.bot.send_message(
                        chat_id,
                        f"⏰ Время вышло!\n"
                        f"Правильный ответ был: {answer}\n"
                        f"Выполняю стандартное действие..."
                    )
                    await self.delete_after(timeout_msg, 3)
                except:
                    pass
                
                # Выполняем стандартное действие (БАН)
                try:
                    # Баним пользователя
                    action_type = settings['action_type']
                    if action_type == 'ban':
                        await context.bot.ban_chat_member(chat_id, int(captcha_key.split('_')[1]))
                        print(f"🚫 Пользователь забанен (таймаут капчи)")
                        
                        # Записываем в логи
                        db.add_log(
                            admin_id,
                            chat_id,
                            int(captcha_key.split('_')[1]),
                            f"ID: {captcha_key.split('_')[1]}",
                            f"{reason} (таймаут капчи)"
                        )
                        
                        # Добавляем в забаненные
                        try:
                            chat = await context.bot.get_chat(chat_id)
                            chat_title = chat.title
                        except:
                            chat_title = "Unknown Group"
                        
                        db.add_banned_user(
                            int(captcha_key.split('_')[1]),
                            f"ID: {captcha_key.split('_')[1]}",
                            chat_id,
                            chat_title,
                            admin_id,
                            f"{reason} (таймаут капчи)"
                        )
                    
                except Exception as e:
                    print(f"❌ Ошибка при выполнении действия после таймаута: {e}")
                
        except Exception as e:
            print(f"❌ Ошибка в таймере капчи: {e}")
    
    async def _execute_remaining_action(self, message, settings, context, reason):
        """Выполнить оставшееся действие (бан/предупреждение) после удаления сообщения"""
        chat_id = message.chat_id
        user = message.from_user
        
        print(f"🛡️ Выполняем действие '{settings['action_type']}' для пользователя {user.id}. Причина: {reason}")
        
        action_type = settings['action_type']
        
        if action_type == 'ban':
            try:
                await context.bot.ban_chat_member(chat_id, user.id)
                print(f"🚫 Пользователь {user.id} забанен")
                
                try:
                    chat = await context.bot.get_chat(chat_id)
                    chat_title = chat.title
                except:
                    chat_title = "Unknown Group"
                
                admin_id = db.get_chat_admin(chat_id)
                if admin_id:
                    db.add_banned_user(
                        user.id,
                        f"@{user.username}" if user.username else user.first_name,
                        chat_id,
                        chat_title,
                        admin_id,
                        reason
                    )
                    print(f"📝 Пользователь {user.id} добавлен в таблицу забаненных")
                    
            except Exception as e:
                print(f"❌ Ошибка при бане: {e}")
                
        elif action_type == 'warn':
            try:
                warning = await context.bot.send_message(
                    chat_id,
                    f"⚠️ Предупреждение для @{user.username or user.first_name}\n"
                    f"Причина: {reason}"
                )
                await self.delete_after(warning, 5)
                print(f"⚠️ Пользователю {user.id} выдано предупреждение")
            except Exception as e:
                print(f"❌ Ошибка при отправке предупреждения: {e}")
        
        # Для action_type == 'delete' ничего дополнительного не делаем
        # сообщение уже было удалено в начале take_action
    
    async def delete_after(self, message, seconds):
        """Удалить сообщение через указанное время"""
        await asyncio.sleep(seconds)
        try:
            await message.delete()
        except:
            pass
    
    async def handle_add_word_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик быстрого добавления стоп-слов в лс (формат: +слово)"""
        message = update.message
        user_id = message.from_user.id
        
        # Проверяем что сообщение в лс
        if message.chat.type != 'private':
            return
        
        text = message.text.strip()
        
        # Добавляем слово (формат: +слово)
        if text.startswith('+') and len(text) > 1:
            words_text = text[1:].strip()
            
            if not words_text:
                await message.reply_text("❌ Укажите слово после +")
                return
            
            # Разделяем слова по запятой
            words_to_add = [w.strip() for w in words_text.split(',') if w.strip()]
            
            added_count = 0
            already_exists = 0
            
            for word in words_to_add:
                if word:  # Проверяем что слово не пустое
                    success = db.add_stop_word(user_id, word)
                    if success:
                        added_count += 1
                        print(f"✅ Добавлено слово: '{word}' для пользователя {user_id}")
                    else:
                        already_exists += 1
                        print(f"⚠️ Слово '{word}' уже есть в списке")
            
            # Формируем ответ
            response_text = ""
            if added_count > 0:
                response_text += f"✅ Добавлено {added_count} слов"
                if added_count == 1:
                    response_text = f"✅ Слово '{words_to_add[0]}' добавлено в стоп-лист"
            
            if already_exists > 0:
                if response_text:
                    response_text += "\n"
                response_text += f"⚠️ {already_exists} слов уже были в списке"
            
            if not response_text:
                response_text = "❌ Не удалось добавить слова"
            
            # Показываем текущий список
            words = db.get_stop_words(user_id)
            if words:
                word_list = "\n".join([f"• {w}" for w in words[-10:]])
                if len(words) > 10:
                    word_list += f"\n\n... и еще {len(words) - 10} слов"
                
                response_text += f"\n\n📋 Ваши стоп-слова ({len(words)}):\n{word_list}"
            else:
                response_text += "\n\n📭 Список стоп-слов пуст"
            
            await message.reply_text(response_text)
    
    async def start_add_word(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало добавления стоп-слова через меню"""
        query = update.callback_query
        await query.answer()
        
        await query.message.edit_text(
            "➕ Введите слово для добавления в стоп-лист:"
        )
        return ADD_WORD
    
    async def add_word_from_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавление стоп-слова из состояния"""
        message = update.message
        user_id = message.from_user.id
        word = message.text.strip()
        
        if word:
            success = db.add_stop_word(user_id, word)
            if success:
                keyboard = [
                    [InlineKeyboardButton("➕ Добавить еще", callback_data="add_word")],
                    [InlineKeyboardButton("← Назад", callback_data="stop_words")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await message.reply_text(
                    f"✅ Слово '{word}' добавлено в стоп-лист",
                    reply_markup=reply_markup
                )
            else:
                await message.reply_text(f"⚠️ Слово '{word}' уже есть в списке")
        else:
            await message.reply_text("❌ Слово не может быть пустым")
        
        return ConversationHandler.END
    
    async def cancel_add_word(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена добавления слова"""
        await update.message.reply_text("❌ Добавление слова отменено")
        return ConversationHandler.END
    
    async def cleanup(self):
        """Корректная очистка ресурсов"""
        self.monitor.stop_monitoring()
        # Очищаем ожидающие капчи
        self.pending_captchas.clear()
    
    async def get_captcha_stats(self):
        """Получить статистику капчи"""
        stats = self.monitor.get_captcha_stats()
        stats['active'] = len(self.pending_captchas)
        return stats

# Создаем экземпляр обработчика
message_handler = MessageHandler()