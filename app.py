import json
import html
import logging
import traceback

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

from basic_handlers import (
    handle_delete_callback,
    handle_details_callback,
    handle_episodes_callback,
    handle_history_callback,
    handle_history_command,
    handle_help_command,
    handle_play_callback,
    handle_rating_command,
    handle_rating_callback,
    handle_seasons_callback,
    handle_search_callback,
    handle_search_text,
    handle_start_command,
    handle_unknown_callback,
)
from db import Database
from config import Config


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logging.getLogger("httpx").setLevel(logging.WARNING)

BASIC_MODE, = range(1)


async def error_handler(update, context):
    """
        Handle errors thrown by the dispatcher. Log them and send a message
        to the bot admin.
    """
    logger = logging.getLogger(__name__)
    logger.error(msg="Error during message processing.",
                 exc_info=context.error)

    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) \
        else str(update)
    messages = (
        f'Возникло исключение при обработке сообщения.\n'
        f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))[:4085]}</pre>', # noqa: E501
        f'<pre>context.bot_data = {html.escape(str(context.bot_data))}</pre>\n\n', # noqa: E501
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n', # noqa: E501
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n', # noqa: E501
        f'<pre>{html.escape(tb_string)[:4085]}</pre>'
    )
    chat_id = context.bot_data.get('storage_chat_id', '382219005')
    for message in messages:
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML)


def main():
    """Run the bot."""
    app_config = Config()
    logging.getLogger().setLevel(
        logging.DEBUG if app_config.parameters['debug'] else logging.INFO
    )

    # persistence = PicklePersistence(filepath='persistence.pickle')
    # Для включения добавить в инициализацию    .persistence(persistence)
    application = Application.builder() \
                    .token(app_config.tg_bot_token) \
                    .base_url(app_config.tg_base_url) \
                    .build()

    application.database = Database(app_config.db_url, )
    application.parameters = app_config.parameters

    conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', handle_start_command),
            CommandHandler('help', handle_help_command),
            CommandHandler('history', handle_history_command),
            CommandHandler('rating', handle_rating_command),
            MessageHandler(
                filters.TEXT & (~filters.COMMAND) & (~filters.Entity("url"))
                & (~filters.Entity("text_link")), handle_search_text, ),
            CallbackQueryHandler(handle_delete_callback, r'delete_'),
            CallbackQueryHandler(handle_details_callback, r'details_'),
            CallbackQueryHandler(handle_episodes_callback, r'episodes_'),
            CallbackQueryHandler(handle_play_callback, r'play_'),
            CallbackQueryHandler(handle_rating_callback, r'rating_'),
            CallbackQueryHandler(handle_search_callback, r'search_'),
            CallbackQueryHandler(handle_seasons_callback, r'seasons_'),
            CallbackQueryHandler(handle_history_callback, r'history_'),
            CallbackQueryHandler(handle_unknown_callback),
        ],
        states={
            BASIC_MODE: [],
        },
        fallbacks=[],
        name='main_conversation',
        persistent=False,
    )

    application.add_handler(conversation_handler)
    application.add_error_handler(error_handler)

    # application.run_polling(allowed_updates=Update.ALL_TYPES)
    application.run_webhook(
        listen='0.0.0.0',
        port=app_config.tg_webhook_port,
        secret_token='ASecretTokenIHaveChangedByNow',
        webhook_url=app_config.tg_webhook_url,
    )


if __name__ == '__main__':
    main()
