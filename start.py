from telegram import Update
from telegram.ext import ContextTypes
from database import db
from keyboards import get_main_menu

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
            f"⚙️ Настройте модерацию для ваших групп:",
            reply_markup=get_main_menu()
        )

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик сообщений в группах (только модерация)"""
    message = update.message
    chat_id = message.chat_id
    user = message.from_user
    
    print(f"🔍 Бот получил сообщение в группе {chat_id} от пользователя {user.id}")
    
    # Пропускаем сообщения от самого бота
    if user.id == context.bot.id:
        return
    
    # Ищем администратора этого чата
    admin_id = db.get_chat_admin(chat_id)
    print(f"👤 Найден администратор чата: {admin_id}")
    
    if not admin_id:
        print("❌ Администратор чата не найден в базе")
        return
    
    # Получаем настройки администратора
    settings = db.get_user_settings(admin_id)
    
    if not settings or not settings['automod_enabled']:
        return
    
    # Проверяем, является ли отправитель администратором
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user.id)
        if chat_member.status in ['administrator', 'creator']:
            return  # Администраторов не проверяем
    except:
        return
    
    # Импортируем здесь чтобы избежать циклического импорта
    from handlers.message_handler import message_handler
    await message_handler.handle_message(update, context)

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
                await update.message.reply_text("❌ Бот не является администратором этой группы!")
                return
            
            # Проверяем что пользователь администратор
            user_member = await context.bot.get_chat_member(chat_id, user.id)
            if user_member.status not in ['administrator', 'creator']:
                await update.message.reply_text("❌ Вы не являетесь администратором этой группы!")
                return
            
            # Регистрируем чат
            db.add_bot_chat(chat_id, chat.title, user.id)
            await update.message.reply_text(
                f"✅ Группа '{chat.title}' зарегистрирована!\n\n"
                f"Теперь бот будет модерировать эту группу с вашими настройками.\n"
                f"Настройте параметры через /start в личных сообщениях бота."
            )
            print(f"✅ Чат {chat_id} зарегистрирован для пользователя {user.id}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")
            print(f"❌ Ошибка регистрации чата: {e}")

# Явно экспортируем все функции
__all__ = ['start', 'handle_group_message', 'register_chat']