from telegram.ext import Application, MessageHandler, filters, CallbackQueryHandler, CommandHandler, ChatMemberHandler, ConversationHandler
from telegram import Update, BotCommand
from config import TOKEN
import logging
import sys
import os
import signal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from handlers.start_handler import start, handle_all_messages, register_chat
from handlers.menu_handlers import menu_handlers
from handlers.message_handler import message_handler, ADD_WORD
from handlers.admin_handlers import admin_handlers

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def track_bot_added(update: Update, context):
    """Отслеживаем когда бота добавляют в группу"""
    if update.my_chat_member:
        chat_member = update.my_chat_member.new_chat_member
        chat = update.my_chat_member.chat
        user = update.my_chat_member.from_user
        
        print(f"🤖 Событие изменения статуса бота: {chat_member.status} в чате {chat.id} ({chat.title})")
        
        if chat_member.status == 'administrator':
            from database import db
            
            existing_admin = db.get_chat_admin(chat.id)
            if existing_admin:
                print(f"ℹ️ Чат {chat.id} уже зарегистрирован для администратора {existing_admin}")
                db.add_bot_chat(chat.id, chat.title, user.id)
                print(f"✅ Информация о чате обновлена для пользователя {user.id}")
            else:
                db.add_bot_chat(chat.id, chat.title, user.id)
                print(f"✅ Бот добавлен в группу: {chat.title} (ID: {chat.id}) администратором {user.id}")
            
            try:
                await context.bot.send_message(
                    user.id,
                    f"✅ Бот добавлен в группу: {chat.title}\n\n"
                    f"Автоматическая модерация активирована!\n"
                    f"Настройте параметры через /start\n\n"
                    f"💡 Теперь группа отобразится в разделе '💬 Мои чаты'"
                )
                print(f"📨 Сообщение отправлено администратору {user.id}")
            except Exception as e:
                print(f"❌ Не удалось отправить сообщение администратору: {e}")
        
        elif chat_member.status == 'kicked':
            print(f"🗑️ Бот удален из группы: {chat.title} (ID: {chat.id})")

async def post_init(application):
    """Установка команд бота"""
    await application.bot.set_my_commands([
        BotCommand("start", "Перезапустить бота"),
        BotCommand("menu", "Главное меню"),
        BotCommand("register", "Зарегистрировать чат")
    ])

def signal_handler(signum, frame):
    """Обработчик сигналов завершения"""
    print(f"\n🛑 Получен сигнал завершения ({signum})...")
    
    try:
        message_handler.monitor.stop_monitoring()
        print("🔍 Мониторинг сообщений остановлен")
    except Exception as e:
        print(f"❌ Ошибка при остановке мониторинга: {e}")
    
    print("👋 Бот завершает работу")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    application = Application.builder().token(TOKEN).build()
    
    application.post_init = post_init

    # 1. Обработчик добавления бота в группы (самый высокий приоритет)
    application.add_handler(ChatMemberHandler(track_bot_added, ChatMemberHandler.MY_CHAT_MEMBER), group=0)

    # 2. Обработчики команд в лс
    application.add_handler(CommandHandler("start", start), group=1)
    application.add_handler(CommandHandler("menu", start), group=1)
    application.add_handler(CommandHandler("register", register_chat), group=1)
    application.add_handler(CommandHandler("admin", admin_handlers.handle_admin), group=1)
    
    # 3. ConversationHandler для добавления стоп-слов (личные сообщения)
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(message_handler.start_add_word, pattern="^add_word$")],
        states={
            ADD_WORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler.add_word_from_state)]
        },
        fallbacks=[CommandHandler("cancel", message_handler.cancel_add_word)]
    )
    application.add_handler(conv_handler, group=2)
    
    # 4. Обработчики меню в лс (ОСНОВНЫЕ)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_settings, pattern="^settings$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_stop_words, pattern="^stop_words$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_profile_check, pattern="^profile_check$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_my_chats, pattern="^my_chats$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_logs, pattern="^logs$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_banned_users, pattern="^banned_users$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_exceptions, pattern="^exceptions$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_notifications, pattern="^notifications$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_help, pattern="^help$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_back, pattern="^back$"), group=3)
    
    # 5. Обработчики капчи
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_captcha_settings, pattern="^captcha_settings$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_captcha_stats, pattern="^captcha_stats$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_toggle_captcha_global, pattern="^toggle_captcha_global$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_toggle_captcha, pattern="^toggle_captcha$"), group=3)
    
    # 6. Обработчики действий в меню
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_toggle_automod, pattern="^toggle_automod$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_toggle_profile_check, pattern="^toggle_profile_check$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_toggle_media_check, pattern="^toggle_media_check$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_toggle_notifications, pattern="^toggle_notifications$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_change_action, pattern="^change_action$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_action_select, pattern="^(ban|delete|warn)$"), group=3)

    # 7. Обработчики исключений
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_show_exceptions, pattern="^show_exceptions$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_remove_exception, pattern="^remove_exception_"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_add_exception, pattern="^add_exception$"), group=3)
    
    # 8. Обработчики стоп-слов
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_show_words, pattern="^show_words$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_clear_words, pattern="^clear_words$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_remove_word, pattern="^remove_"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_popular_words, pattern="^popular_words$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_add_popular_word, pattern="^add_popular_"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_add_multiple_popular, pattern="^add_multiple_popular$"), group=3)
    
    # 9. Обработчики логов
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_recent_logs, pattern="^recent_logs$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_month_stats, pattern="^month_stats$"), group=3)
    
    # 10. Обработчики забаненных пользователей
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_show_banned, pattern="^show_banned$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_unban_user, pattern="^unban_"), group=3)
    
    # 11. Обработчики уведомлений
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_show_notifications, pattern="^show_notifications$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_resolve_notification, pattern="^resolve_"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_ban_from_notification, pattern="^ban_"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_exception_from_notification, pattern="^exception_"), group=3)
    
    # 12. Обработчики чатов
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_show_chats, pattern="^show_chats$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_add_chat, pattern="^add_chat$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_refresh_chats, pattern="^refresh_chats$"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_chat_detail, pattern="^chat_"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_remove_chat, pattern="^remove_chat_"), group=3)
    application.add_handler(CallbackQueryHandler(menu_handlers.handle_toggle_chat_automod, pattern="^toggle_chat_"), group=3)
    
    # 13. Обработчики админ-панели
    application.add_handler(CallbackQueryHandler(admin_handlers.handle_admin_stats, pattern="^admin_stats$"), group=3)
    application.add_handler(CallbackQueryHandler(admin_handlers.handle_admin_users, pattern="^admin_users$"), group=3)
    application.add_handler(CallbackQueryHandler(admin_handlers.handle_admin_chats, pattern="^admin_chats$"), group=3)
    application.add_handler(CallbackQueryHandler(admin_handlers.handle_admin_violators, pattern="^admin_violators$"), group=3)
    application.add_handler(CallbackQueryHandler(admin_handlers.handle_admin_monitoring, pattern="^admin_monitoring$"), group=3)
    application.add_handler(CallbackQueryHandler(admin_handlers.handle_admin_clear_monitoring, pattern="^admin_clear_monitoring$"), group=3)
    application.add_handler(CallbackQueryHandler(admin_handlers.handle_admin_system, pattern="^admin_system$"), group=3)
    application.add_handler(CallbackQueryHandler(admin_handlers.handle_admin_cleanup_logs, pattern="^admin_cleanup_logs$"), group=3)
    application.add_handler(CallbackQueryHandler(admin_handlers.handle_admin_search, pattern="^admin_search$"), group=3)
    application.add_handler(CallbackQueryHandler(admin_handlers.handle_admin_back, pattern="^admin_back$"), group=3)
    
    # 14. ВАЖНО: ГРУППОВЫЕ ХЕНДЛЕРЫ (отдельная группа для сообщений в группах)
    
    # 14.1. Обработчик медиа в группах
    application.add_handler(MessageHandler(
        (filters.PHOTO | filters.VIDEO) & filters.ChatType.GROUPS,
        message_handler.handle_media_message
    ), group=4)
    
    # 14.2. УНИВЕРСАЛЬНЫЙ обработчик ВСЕХ сообщений в группах
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & ~filters.COMMAND,
        handle_all_messages
    ), group=4)
    
    # 15. Обработчик добавления слова в ЛС (формат: +слово) - ЛИЧНЫЕ СООБЩЕНИЯ
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^\+') & filters.ChatType.PRIVATE, 
        message_handler.handle_add_word_message
    ), group=5)

    print("=" * 60)
    print("🤖 Бот запускается...")
    print("=" * 60)
    
    # Показываем статус капчи
    from config import CAPTCHA_ENABLED, CAPTCHA_TIMEOUT
    captcha_status = "✅ ВКЛЮЧЕНА" if CAPTCHA_ENABLED else "❌ ВЫКЛЮЧЕНА"
    print(f"🔐 Система капчи: {captcha_status}")
    if CAPTCHA_ENABLED:
        print(f"⏰ Время на ответ: {CAPTCHA_TIMEOUT} секунд")
        print("🧮 Примеры: 2+3=?, 5-2=?, 4*2=? и т.д.")
        print("✅ При успехе: пользователь добавляется в исключения")
        print("❌ При неудаче/таймауте: пользователь банится")
        print("💡 Сообщение удаляется ВСЕГДА, независимо от капчи")
    
    print("=" * 60)
    print("✅ Универсальный обработчик активирован")
    print("✅ Отслеживание обычных и отредактированных сообщений")
    print("✅ Мониторинг сообщений: 10 минут, проверка каждые 10 секунд")
    print("✅ Правильный порядок хендлеров")
    print("=" * 60)
    
    try:
        application.run_polling()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
    finally:
        try:
            message_handler.monitor.stop_monitoring()
        except:
            pass
        print("👋 Бот завершил работу")

if __name__ == '__main__':
    main()