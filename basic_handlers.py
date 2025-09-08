import logging

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from telegram import (
    error as tg_error,
)

from helpers import (
    get_paginated_markup,
    get_seasons_markup,
    get_serial_detail_markup,
)
from queries import (
    get_aggregated_view_history,
    get_seasons_by_serial_id,
    get_serial_by_id,
)


POSTERS_URL = "https://alexwolf.ru/ksb/covers/{}.jpg"


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
    reply_text=(
        'Вот последние просмотренные Вами сериалы.\n'
        'Сверху - самый последний из просмотренных и далее по хронологии.\n'
        'В квадратных скобках указано количество просмотров эпизодов.'
        f'Страница{page} из {total_pages}'
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=reply_text,
        reply_markup = get_paginated_markup(history, page, total_pages),
    )


async def handle_history_callback(update, context):
    callback_query = update.callback_query
    _, page = callback_query.data.split(':')
    context.args = [page,]
    await handle_history_command(update, context)
    await handle_delete_callback(update, context)


async def handle_details_callback(update, context):
    callback_query = update.callback_query
    _, serial_id = callback_query.data.split(':')
    with context.application.database.session() as db:
        try:
            serial = get_serial_by_id(db, serial_id)
        except (NoResultFound, MultipleResultsFound) as e:
            await callback_query.answer(f'Ошибка {e} при загрузке сериала {serial_id}') # noqa E501
            raise
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            parse_mode='HTML',
            text = f'<b>{serial.name_rus}({serial.name_eng})</b>\n'
                f'<u>Формат серий:</u><i> {serial.format}</i>\n' 
                f'<u>Описание:</u>\n{serial.descr}',
            reply_markup = get_serial_detail_markup(serial),
        )
    await handle_delete_callback(update, context)


async def handle_seasons_callback(update, context):
    callback_query = update.callback_query
    _, serial_id = callback_query.data.split(':')
    with context.application.database.session() as db:
        try:
            serial = get_serial_by_id(db, serial_id)
            seasons = get_seasons_by_serial_id(db, serial_id)
        except(NoResultFound, MultipleResultsFound) as e:
            await callback_query.answer(f'Ошибка {e} при загрузке сериала {serial_id}') # noqa E501
            raise
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=POSTERS_URL.format(serial_id),
            parse_mode='HTML',
            caption = f'<b>{serial.name_rus}({serial.name_eng})</b>\n'
                        'Выберите сезон из списка ниже.'
                        'В квадратных скобках количество серий',
            reply_markup = get_seasons_markup(serial.id, seasons)
        )
    await handle_delete_callback(update, context)


async def handle_delete_callback(update, context):
    try:
        await update.callback_query.delete_message()
        await update.callback_query.answer()
    except tg_error.BadRequest:
        logging.error('Delete: BadRequest')
        await update.callback_query.answer('Старые сообщения не могут быть удалены') # noqa E501
        return
    await update.callback_query.answer()


async def handle_unknown_callback(update, context):
    await update.callback_query.answer()
