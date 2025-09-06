import json
import html
import logging
import traceback

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

from basic_handlers import (
    handle_history_command,
    handle_start_command,
)
from db import Database
from config import Config


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

BASIC_MODE, = range(1)


async def error_handler(update, context):
    """
        Handle errors thrown by the dispatcher. Log them and send a message
        to the bot admin.
    """
    logger.error(msg="Error during mrssage processing:",
                 exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f'Возникло исключение при обработке сообщения.\n'
        f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.bot_data = {html.escape(str(context.bot_data))}</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )

    chat_id = context.bot_data.get('storage_chat_id', '382219005')
    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode=ParseMode.HTML)


def main():
    """Run the bot."""
    app_config = Config()

    persistence = PicklePersistence(filepath="persistence.pickle")
    application = Application.builder() \
                    .token(app_config.tg_bot_token) \
                    .persistence(persistence) \
                    .build()

    application.database = Database(app_config.db_url, )
    application.storage_chat_id = app_config.storage_chat_id

    conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", handle_start_command),
            CommandHandler('help', handle_history_command),
        ],
        states={
            BASIC_MODE: [],
        },
        fallbacks=[],
        name="main_conversation",
        persistent=True,
    )

    application.add_handler(conversation_handler)
    application.add_error_handler(error_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
