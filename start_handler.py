from telegram import Update
from telegram.ext import ContextTypes
from database import db
from keyboards import get_main_menu
from handlers.message_handler import message_handler

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start и /menu"""
    
    if update.message:
        user = update.message.from_user
        chat = update.message.chat
        
        # Бот работает только в личных сообщениях
        if chat.type != 'private':
            await update.message.reply_text(
                "🤖 Я работаю только в личных сообщениях!\n\n"
                "Напишите мне в лс для настройки модерации ваших групп."
            )
            return
        
        user_id = user.id
        
        # Приветственное сообщение
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            f"🤖 Я бот-модератор для ваших групп.\n\n"
            f"📋 Что я умею:\n"
            f"• Автоматически модерировать сообщения\n"
            f"• Проверять профили на каналы\n"
            f"• Блокировать спамеров\n\n"
            f"💡 Чтобы начать:\n"
            f"1. Добавьте меня в группу как администратора\n"
            f"2. Назначьте права на удаление сообщений и бан\n"
            f"3. Используйте команду /register в группе\n"
            f"4. Или настройте через меню ниже\n\n"
            f"⚙️ Настройте модерацию для ваших групп:",
            reply_markup=get_main_menu()
        )

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик сообщений в группах (только модерация)"""
    # Проверяем что это сообщение
    if not update.message:
        return
    
    message = update.message
    
    # Проверяем что сообщение в группе или супергруппе
    if message.chat.type not in ['group', 'supergroup']:
        return
    
    chat_id = message.chat_id
    user = message.from_user
    
    print(f"🔍 [start_handler] Получено сообщение в чате {chat_id} от {user.id}")
    
    # Пропускаем сообщения от самого бота
    if user.id == context.bot.id:
        return
    
    # Ищем администратора этого чата
    admin_id = db.get_chat_admin(chat_id)
    
    if not admin_id:
        print(f"❌ [start_handler] Администратор чата {chat_id} не найден")
        return
    
    # Получаем настройки администратора
    settings = db.get_user_settings(admin_id)
    
    # Получаем настройки конкретного чата
    chat_settings = db.get_chat_settings(chat_id)
    
    # Проверяем и глобальные настройки И настройки чата
    if not settings or not settings['automod_enabled']:
        print(f"❌ [start_handler] Глобальная автомодерация отключена для {admin_id}")
        return
    
    if not chat_settings or not chat_settings['automod_enabled']:
        print(f"❌ [start_handler] Модерация отключена для чата {chat_id}")
        return
    
    # Проверяем исключения для этого пользователя
    if db.is_user_exception(user.id, chat_id):
        print(f"✅ [start_handler] Пользователь {user.id} в исключениях")
        return
    
    # Проверяем, является ли отправитель администратором
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user.id)
        if chat_member.status in ['administrator', 'creator']:
            print(f"✅ [start_handler] Пользователь {user.id} администратор - пропускаем")
            return
    except Exception as e:
        print(f"❌ [start_handler] Ошибка проверки прав: {e}")
        return
    
    # Передаем обработку в основной обработчик
    print(f"✅ [start_handler] Передаем сообщение от {user.id} в message_handler")
    await message_handler.handle_message(update, context)

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Универсальный обработчик ВСЕХ типов сообщений в группах"""
    print(f"🔥 [ALL] Обновление получено: update_id={update.update_id}")
    
    # Обычное сообщение
    if update.message:
        print(f"📨 [ALL] Обычное сообщение от {update.message.from_user.id}: {update.message.text[:50] if update.message.text else 'без текста'}")
        await handle_group_message(update, context)
    
    # Отредактированное сообщение
    elif update.edited_message:
        print(f"✏️ [ALL] ОТРЕДАКТИРОВАННОЕ сообщение от {update.edited_message.from_user.id}: {update.edited_message.text[:50] if update.edited_message.text else 'без текста'}")
        await message_handler.handle_edited_message(update, context)
    
    else:
        print(f"❓ [ALL] Неизвестный тип обновления: {update}")

async def register_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительная регистрация чата в базе"""
    if update.message:
        user = update.message.from_user
        chat = update.message.chat
        
        # Только в группах
        if chat.type == 'private':
            await update.message.reply_text("Эта команда работает только в группах!")
            return
        
        chat_id = chat.id
        
        try:
            # Проверяем что бот администратор
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            if bot_member.status not in ['administrator', 'creator']:
                await update.message.reply_text(
                    "❌ Бот не является администратором этой группы!\n\n"
                    "Добавьте бота как администратора с правами:\n"
                    "• Удаление сообщений\n"
                    "• Блокировка пользователей"
                )
                return
            
            # Проверяем что пользователь администратор
            user_member = await context.bot.get_chat_member(chat_id, user.id)
            if user_member.status not in ['administrator', 'creator']:
                await update.message.reply_text("❌ Вы не являетесь администратором этой группы!")
                return
            
            # Проверяем, не зарегистрирован ли уже чат
            existing_admin = db.get_chat_admin(chat_id)
            if existing_admin:
                if existing_admin == user.id:
                    await update.message.reply_text(
                        f"ℹ️ Группа '{chat.title}' уже зарегистрирована!\n\n"
                        f"Бот уже модерирует эту группу с вашими настройками.\n"
                        f"Настройте параметры через /start в личных сообщениях бота."
                    )
                else:
                    await update.message.reply_text(
                        f"⚠️ Эта группа уже зарегистрирована другим администратором!\n\n"
                        f"Только один пользователь может управлять настройками модерации для группы."
                    )
                return
            
            # Регистрируем чат
            db.add_bot_chat(chat_id, chat.title, user.id)
            await update.message.reply_text(
                f"✅ Группа '{chat.title}' зарегистрирована!\n\n"
                f"Теперь бот будет модерировать эту группу с вашими настройками.\n"
                f"Настройте параметры через /start в личных сообщениях бота.\n\n"
                f"💡 Группа появится в разделе '💬 Мои чаты'"
            )
            print(f"✅ Чат {chat_id} зарегистрирован для пользователя {user.id}")
            
            # Отправляем сообщение в ЛС пользователю
            try:
                await context.bot.send_message(
                    user.id,
                    f"✅ Группа зарегистрирована!\n\n"
                    f"💬 {chat.title}\n\n"
                    f"Теперь вы можете управлять настройками модерации для этой группы "
                    f"в разделе '💬 Мои чаты'"
                )
            except Exception as e:
                print(f"❌ Не удалось отправить сообщение в ЛС: {e}")
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка регистрации: {e}\n\n"
                f"Убедитесь, что:\n"
                f"• Бот добавлен как администратор\n"
                f"• У бота есть права на удаление сообщений и бан\n"
                f"• Вы являетесь администратором группы"
            )
            print(f"❌ Ошибка регистрации чата: {e}")