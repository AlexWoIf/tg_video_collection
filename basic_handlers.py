import logging

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from telegram import (
    error as tg_error,
)

from helpers import (
    add_episodes_markup_footer,
    get_button_text_for_episode,
    get_button_text_for_serial,
    get_default_episode_markup,
    get_paginated_markup,
    get_seasons_markup,
    get_serial_detail_markup,
)
from queries import (
    get_aggregated_view_history,
    get_episode_by_id,
    get_episodes_by_serial_id,
    get_next_episode_id,
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
        history, total_lines = get_aggregated_view_history(
            db, user_id, page_length, offset)
        if not history:
            reply_text = 'История просмотров пуста'
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=reply_text
            )
            return
        total_pages = total_lines // page_length
        total_pages += 1 if total_lines % page_length else 0
    buttons_callbacks = [get_button_text_for_serial(serial) for serial in history] # noqa E501
    reply_text=(
        'Вот последние просмотренные Вами сериалы.\n'
        'Сверху - самый последний из просмотренных и далее по хронологии.\n'
        'В квадратных скобках указано количество просмотров эпизодов.'
        f'Страница {page} из {total_pages}'
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=reply_text,
        reply_markup = get_paginated_markup(
            buttons_callbacks, 'history', page, total_pages),
    )


async def handle_history_callback(update, context):
    callback_query = update.callback_query
    _, page = callback_query.data.split('_')
    context.args = [page,]
    await handle_history_command(update, context)
    await handle_delete_callback(update, context)


async def handle_details_callback(update, context):
    callback_query = update.callback_query
    _, serial_id = callback_query.data.split('_')
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
    _, serial_id = callback_query.data.split('_')
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
            reply_markup = get_seasons_markup(serial_id, seasons)
        )
    await handle_delete_callback(update, context)


async def handle_episodes_callback(update, context):
    callback_query = update.callback_query
    _, serial_id, season, page = callback_query.data.split('_')
    current_page = int(page)
    page_length = context.application.parameters.get('page_length')
    user_id = update.effective_sender.id
    with context.application.database.session() as db:
        try:
            serial = get_serial_by_id(db, serial_id)
            episodes, total_lines = get_episodes_by_serial_id(
                db,
                serial_id,
                season,
                user_id,
                page_length,
                (current_page - 1) * page_length)
        except(NoResultFound, MultipleResultsFound) as e:
            await callback_query.answer(f'Ошибка {e} при загрузке сериала {serial_id}') # noqa E501
            raise
        logging.debug(episodes)
        buttons_callbacks = [get_button_text_for_episode(episode) for episode in episodes] # noqa E501
        logging.debug(buttons_callbacks)
        total_pages = total_lines // page_length
        total_pages += 1 if total_lines % page_length else 0
        reply_markup = get_paginated_markup(
                buttons_callbacks, 
                f'episodes_{serial_id}_{season}', 
                current_page, 
                total_pages)
        reply_markup = add_episodes_markup_footer(reply_markup, serial_id)
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo = POSTERS_URL.format(serial_id),
            parse_mode='HTML',
            caption=f'<b>{serial.name_rus}({serial.name_eng})</b>\n'
                    f'Выберите нужный эпизод из сезона {season}:\n'
                    '✅ - вы уже запрашивали этот эпизод\n' \
                    f'Страница {current_page} из {total_pages}',
            reply_markup=reply_markup,
        )
    await handle_delete_callback(update, context)


async def handle_play_callback(update, context):
    callback_query = update.callback_query
    _, episode_id = callback_query.data.split('_')
    with context.application.database.session() as db:
        try:
            episode = get_episode_by_id(db, episode_id)
            next_episode_id = get_next_episode_id(db, episode)
        except(NoResultFound, MultipleResultsFound) as e:
            await callback_query.answer(f'Ошибка {e} при загрузке сериала {episode_id}') # noqa E501
            raise
        caption = (
            f'<a href="https://t.me/KinoSpisokBot/start={episode.serial_id}">'
            f'<b>{episode.name_rus} ({episode.name_eng})</b></a>\n'
            f'<u>Episode:</u>[{episode.season}x{episode.episode}]\n'
            f'<i>{episode.name}</i>\n'
            f'<a href="https://t.me/KinoSpisokBot">Еще больше сериалов в @KinoSpisokBot</a>' # noqa E501
        )
        kwargs = {
            'chat_id': update.effective_chat.id,
            'parse_mode': 'HTML',
            'caption': caption,
            'reply_markup': get_default_episode_markup(episode, next_episode_id), # noqa E501
        }
        if context.application.parameters.get('debug', False):
            await context.bot.send_photo(
                photo=POSTERS_URL.format(episode.serial_id), **kwargs)
        else:
            await context.bot.send_video(video=episode.file_id, **kwargs)
                
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
