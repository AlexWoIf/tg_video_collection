import logging

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ConversationHandler, MessageHandler, filters)

from admin import (handle_add_command, handle_exclude_callback,
                   handle_get_command, handle_include_callback,
                   handle_update_callback, handle_update_command)
from basic_handlers import (handle_alphabet_callback, handle_alphabet_command,
                            handle_delete_callback, handle_details_callback,
                            handle_details_command, handle_episodes_callback,
                            handle_help_command, handle_history_callback,
                            handle_history_command, handle_play_callback,
                            handle_rating_callback, handle_rating_command,
                            handle_search_callback, handle_search_command,
                            handle_search_text, handle_seasons_callback,
                            handle_serial_command, handle_start_command,
                            handle_text_callback, handle_unknown_callback,
                            handle_urls)
from config import Config
from db import Database

BASIC_MODE, = range(1)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def error_handler(update, context):
    """
        Handle errors thrown by the dispatcher. Log them and send a message
        to the bot admin.
    """
    logger = logging.getLogger(__name__)
    logger.error(msg="Error during message processing.",
                 exc_info=context.error)

    if not sentry_sdk.Hub.current.client:
        logger.error("Не задан ключ для Sentry/GlitchTip)!")
    else:
        with sentry_sdk.isolation_scope() as scope:
            if isinstance(update, Update):
                if update.effective_user:
                    sentry_sdk.set_user({
                        "id": str(update.effective_user.id),
                        "username": update.effective_user.username,
                        "name": update.effective_user.full_name
                    })

                if update.effective_chat:
                    scope.set_tag("chat_id", str(update.effective_chat.id))
                    scope.set_tag("chat_type", update.effective_chat.type)

                if update.message and update.message.text:
                    scope.set_extra("user_message", update.message.text)
                elif update.callback_query and update.callback_query.data:
                    scope.set_extra("callback_data",
                                    update.callback_query.data)

            sentry_sdk.capture_exception(context.error)

    message = ('Возникло исключение при обработке сообщения.\n')
    chat_id = context.bot_data.get('storage_chat_id', '382219005')
    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode=ParseMode.HTML)


async def log_update(update: Update, _):
    logger = logging.getLogger(__name__)
    logger.info(f"📨 Processing update: {update.update_id}")
    logger.info(f"📊 Update content: {update.to_dict()}")
    # Логируем тип обновления
    if update.message:
        logger.info(f"💬 Message text: {update.message.text}")
    if update.callback_query:
        logger.info(f"🔘 Callback data: {update.callback_query.data}")


def main():
    """Run the bot."""
    app_config = Config()

    if app_config.sentry_dsn:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR,
        )
        sentry_sdk.init(
            dsn=app_config.sentry_dsn,
            environment=app_config.environment,
            enable_logs=True,
            auto_session_tracking=False,
            integrations=[sentry_logging],
        )

    logging.getLogger().setLevel(
        logging.DEBUG if app_config.parameters['debug'] else logging.INFO
    )

    conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', handle_start_command),
            CommandHandler('alphabet', handle_alphabet_command),
            CommandHandler('details', handle_details_command),
            CommandHandler('help', handle_help_command),
            CommandHandler('history', handle_history_command),
            CommandHandler('rating', handle_rating_command),
            CommandHandler('search', handle_search_command),
            CommandHandler('serial', handle_serial_command),
            CommandHandler(
                'add', handle_add_command,
                filters.Chat(app_config.parameters.get('storage_chat_id')),),
            CommandHandler(
                'get', handle_get_command,
                filters.Chat(app_config.parameters.get('storage_chat_id')),),
            CommandHandler(
                'update', handle_update_command,
                filters.Chat(app_config.parameters.get('storage_chat_id')),),
            MessageHandler(
                filters.TEXT & (~filters.COMMAND) &
                (filters.Entity("url") | filters.Entity("text_link")),
                handle_urls),
            MessageHandler(
                filters.TEXT & (~filters.COMMAND) & (~filters.Entity("url"))
                & (~filters.Entity("text_link")), handle_search_text, ),
            CallbackQueryHandler(handle_alphabet_callback, r'alphabet_'),
            CallbackQueryHandler(handle_delete_callback, r'delete_'),
            CallbackQueryHandler(handle_details_callback, r'details_'),
            CallbackQueryHandler(handle_episodes_callback, r'episodes_'),
            CallbackQueryHandler(handle_exclude_callback, r'exclude_'),
            CallbackQueryHandler(handle_include_callback, r'include_'),
            CallbackQueryHandler(handle_play_callback, r'play_'),
            CallbackQueryHandler(handle_rating_callback, r'rating_'),
            CallbackQueryHandler(handle_search_callback, r'search_'),
            CallbackQueryHandler(handle_seasons_callback, r'seasons_'),
            CallbackQueryHandler(handle_text_callback, r'text_'),
            CallbackQueryHandler(handle_history_callback, r'history_'),
            CallbackQueryHandler(handle_update_callback, r'update_'),
            CallbackQueryHandler(handle_unknown_callback),
        ],
        states={
            BASIC_MODE: [],
        },
        fallbacks=[],
        name='main_conversation',
        persistent=False,
    )

    # persistence = PicklePersistence(filepath='persistence.pickle')
    # Для включения добавить в инициализацию    .persistence(persistence)
    application = Application.builder() \
        .token(app_config.tg_bot_token) \
        .base_url(app_config.tg_base_url) \
        .build()

    application.database = Database(app_config.db_url, )
    application.parameters = app_config.parameters

    application.add_handler(MessageHandler(filters.ALL, log_update), group=-1)
    application.add_handler(CallbackQueryHandler(log_update), group=-1)

    application.add_handler(conversation_handler)
    application.add_error_handler(error_handler)

    if app_config.tg_webhook_port and app_config.tg_webhook_url:
        application.run_webhook(
            listen='0.0.0.0',
            port=app_config.tg_webhook_port,
            secret_token='ASecretTokenIHaveChangedByNow',
            webhook_url=app_config.tg_webhook_url,
        )
    else:
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
