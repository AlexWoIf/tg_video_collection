import logging

from telegram import (
    error as tg_error,
)

from helpers import (
    get_paginated_markup,
)
from queries import (
    get_aggregated_view_history,
)


async def handle_help_command(update, context):
    reply_text='''
        Бот для просмотра сериалов прямо в телеграме
        Список доступных команд:
        \u25cf  для поиска сериала введите несколько букв его названия (не меньше 3х)
        \u25cf  /help - справка о доступных командах
        \u25cf  /serial - получить 10 случайных сериалов
        \u25cf  /history -  последние запрошенные Вами эпизоды
        \u25cf  /rating -  самые популярные сериалы
        Замечания и предложения присылайте на @AlexWolf_kornet
    '''
    await update.message.reply_text(reply_text)


async def handle_start_command(update, context):
    if not context.args:
        await handle_help_command(update, context)
        return
    reply_text = f'"{'", "'.join(context.args)}"'
    await update.message.reply_text(reply_text)


async def handle_history_command(update, context):
    logging.debug(f'{update.effective_sender=}')
    user_id = update.effective_sender.id
    page = int(context.args[0]) if context.args else 1
    page_length = context.application.parameters.get('page_length')
    offset = (page - 1) * page_length
    with context.application.database.session() as db:
        history = get_aggregated_view_history(db, user_id, page_length, offset)
        if not history:
            reply_text = 'История просмотров пуста'
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=reply_text
            )
            return
        if len(history) < page_length and page == 1:
            total_pages = 1
        else:
            total_pages = get_aggregated_view_history(db, user_id, 0, ) // page_length + 1 # noqa E501
    reply_markup = get_paginated_markup(history, page, total_pages)
    reply_text=(
        'Вот последние просмотренные Вами сериалы.\n'
        'Сверху - самый последний из просмотренных и далее по хронологии.\n'
        'В квадратных скобках указано количество просмотров эпизодов.'
        f'Страница{page} из {total_pages}'
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=reply_text,
        reply_markup = reply_markup,
    )


async def handle_history_callback(update, context):
    callback_query = update.callback_query
    _, page = callback_query.data.split(':')
    context.args = [page,]
    await handle_history_command(update, context)
    try:
        await callback_query.delete_message()
        await callback_query.answer()
    except tg_error.BadRequest:
        logging.error("Delete: BadRequest")
        await callback_query.answer("Старые сообщения не могут быть удалены")


async def handle_unknown_callback(update, context):
    await update.callback_query.answer()
