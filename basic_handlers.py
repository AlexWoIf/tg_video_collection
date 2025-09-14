import logging

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from telegram import error as tg_error

from helpers import get_search_text
from messages import (format_details_message, format_episodes_message,
                      format_help_message, format_history_message,
                      format_play_message, format_rating_message,
                      format_search_message, format_seasons_message)
from queries import (get_aggregated_view_history, get_episode_by_id,
                     get_episodes_by_serial_id, get_next_episode_id,
                     get_seasons_by_serial_id, get_serial_by_id,
                     get_serials_by_namepart, get_serials_rating,
                     insert_episode_view_record, insert_new_user)


POSTERS_URL = "https://alexwolf.ru/ksb/covers/{}.jpg"


async def handle_delete_callback(update, context):
    try:
        await update.callback_query.delete_message()
        await update.callback_query.answer()
    except tg_error.BadRequest:
        logging.error('Delete: BadRequest')
        await update.callback_query.answer(
            'Старые сообщения не могут быть удалены')


async def handle_details_callback(update, context):
    callback_query = update.callback_query
    _, serial_id = callback_query.data.split('_')
    with context.application.database.session() as db:
        try:
            serial = get_serial_by_id(db, serial_id)
        except (NoResultFound, MultipleResultsFound) as e:
            await callback_query.answer(
                f'Ошибка {e} при загрузке сериала {serial_id}')
            raise
    text, markup = format_details_message(serial)
    await update.effective_chat.send_message(
        text=text, parse_mode='HTML', reply_markup=markup, )
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
    text, markup = format_episodes_message(
        serial, season, episodes, total_lines, current_page, page_length)
    await update.effective_chat.send_photo(
        photo = POSTERS_URL.format(serial_id),
        parse_mode='HTML',
        caption=text,
        reply_markup=markup,
    )
    await handle_delete_callback(update, context)


async def handle_help_command(update, context):
    reply_text=format_help_message()
    await update.message.reply_text(reply_text)


async def handle_history_callback(update, context):
    callback_query = update.callback_query
    _, page = callback_query.data.split('_')
    context.args = [int(page),]
    await handle_history_command(update, context)
    await handle_delete_callback(update, context)


async def handle_history_command(update, context):
    user_id = update.effective_sender.id
    page = int(context.args[0]) if context.args else 1
    page_length = context.application.parameters.get('page_length')
    offset = (page - 1) * page_length
    with context.application.database.session() as db:
        history, num_lines = get_aggregated_view_history(
            db, user_id, page_length, offset)
    if not history:
        text = 'История просмотров пуста'
        await update.effective_chat.send_message(text=text)
        return
    text, markup = format_history_message(history, num_lines, page, page_length)
    await update.effective_chat.send_message(text=text, reply_markup=markup, )


async def handle_play_callback(update, context):
    callback_query = update.callback_query
    _, episode_id = callback_query.data.split('_')
    with context.application.database.session() as db:
        try:
            episode = get_episode_by_id(db, episode_id)
            next_episode_id = get_next_episode_id(db, episode)
        except(NoResultFound, MultipleResultsFound) as e:
            await callback_query.answer(
                f'Ошибка {e} при загрузке сериала {episode_id}') 
            raise
        insert_episode_view_record(db, update.effective_sender.id, episode_id)
    text, markup = format_play_message(context.bot.username, episode,
                                       next_episode_id)
    kwargs = {'parse_mode': 'HTML', 'caption': text, 'reply_markup': markup, }
    if context.application.parameters.get('debug', False):
        await update.effective_chat.send_photo(
            photo=POSTERS_URL.format(episode.serial_id), **kwargs)
    else:
        await update.effective_chat.send_video(video=episode.file_id, **kwargs)
    await handle_delete_callback(update, context)


async def handle_rating_callback(update, context):
    callback_query = update.callback_query
    _, page = callback_query.data.split('_')
    context.args = [int(page),]
    await handle_rating_command(update, context)
    await handle_delete_callback(update, context)


async def handle_rating_command(update, context):
    page = int(context.args[0]) if context.args else 1
    page_length = context.application.parameters.get('page_length')
    with context.application.database.session() as db:
        serials, num_lines = get_serials_rating(db, page_length, page)
    text, markup = format_rating_message(serials, num_lines, page, page_length)
    await update.effective_chat.send_message(
        parse_mode='HTML',
        text=text,
        reply_markup = markup,
    )


async def handle_search_callback(update, context):
    callback_query = update.callback_query
    _, page = callback_query.data.split('_')
    page = int(page)
    page_length = context.application.parameters.get('page_length')
    try:
        namepart = get_search_text(update.effective_message.text)
    except (ValueError, AttributeError):
        await update.effective_chat.send_message(
            'Результаты поиска устарели.\n'
            'Введите строку для поиска заново.'
            f'\n"{update.effective_message.text}"'
        )
        return
    search_text = f'%{namepart}%' if len(namepart) > 2 else f'{namepart}%'
    with context.application.database.session() as db:
        serials, num_lines = get_serials_by_namepart(
            db, search_text, page_length, page)
        text, markup = format_search_message(
            namepart, serials, num_lines, page, page_length)
    await update.effective_chat.send_message(
        parse_mode='HTML',
        text=text,
        reply_markup = markup,
    )
    await handle_delete_callback(update, context)


async def handle_search_text(update, context):
    namepart = f'{update.message.text.lower()}'
    page = 1
    page_length = context.application.parameters.get('page_length')
    search_text = f'%{namepart}%' if len(namepart) > 2 else f'{namepart}%'
    with context.application.database.session() as db:
        serials, num_lines = get_serials_by_namepart(
            db, search_text, page_length, page)
        text, markup = format_search_message(
            namepart, serials, num_lines, page, page_length)
    await update.effective_chat.send_message(
        parse_mode='HTML',
        text=text,
        reply_markup = markup,
    )


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
    text, markup = format_seasons_message(serial, seasons)
    await update.effective_chat.send_photo(
        photo=POSTERS_URL.format(serial_id),
        parse_mode='HTML',
        caption=text,
        reply_markup=markup,
    )
    await handle_delete_callback(update, context)


async def handle_start_command(update, context):
    with context.application.database.session() as db:
        insert_new_user(db, update.effective_sender)
    if not context.args:
        reply_text=format_help_message()
        await update.message.reply_text(reply_text)


async def handle_unknown_callback(update, context):
    await update.callback_query.answer()
