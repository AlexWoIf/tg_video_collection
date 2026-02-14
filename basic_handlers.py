import logging
import re

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from telegram import error as tg_error

from helpers import get_search_text
from messages import (format_alphabet_message, format_details_message,
                      format_episodes_message, format_help_message,
                      format_history_message, format_play_message,
                      format_random_serials_message, format_rating_message,
                      format_search_message, format_seasons_message)
from queries import (create_new_movie_request, get_aggregated_view_history,
                     get_alphabet_counts, get_episode_by_id,
                     get_episodes_by_serial_and_season, get_next_episode,
                     get_random_serials, get_seasons_by_serial_id,
                     get_serial_by_id, get_serial_by_search_key,
                     get_serials_by_namepart, get_serials_rating,
                     insert_episode_view_record, insert_new_user)


async def handle_alphabet_callback(update, context):
    callback_query = update.callback_query
    _, language = callback_query.data.split('_')
    context.args = [language,]
    await handle_alphabet_command(update, context)
    await handle_delete_callback(update, context)


async def handle_alphabet_command(update, context):
    is_english = context.args and context.args[0].lower().startswith('en')
    language = 'ENG' if is_english else 'RUS'
    with context.application.database.session() as db:
        letters = get_alphabet_counts(db, language)
    text, markup = format_alphabet_message(letters)
    await update.effective_chat.send_message(text=text, reply_markup=markup, )

async def handle_delete_callback(update, context):
    try:
        await update.callback_query.delete_message()
        await update.callback_query.answer()
    except tg_error.BadRequest:
        logging.error('Delete: BadRequest')
        await update.callback_query.answer(
            'Старые сообщения не могут быть удалены ботом')


async def handle_details_callback(update, context):
    callback_query = update.callback_query
    _, serial_id = callback_query.data.split('_')
    context.args = [serial_id,]
    await handle_details_command(update, context)
    await handle_delete_callback(update, context)


async def handle_details_command(update, context):
    serial_id = context.args and context.args[0].isdigit() and int(context.args[0]) # noqa E501
    if not serial_id:
        await handle_help_command(update, context)
        return
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


async def handle_episodes_callback(update, context):
    callback_query = update.callback_query
    _, serial_id, season, page = callback_query.data.split('_')
    current_page = int(page)
    page_length = context.application.parameters.get('page_length')
    user_id = update.effective_sender.id
    with context.application.database.session() as db:
        try:
            serial = get_serial_by_id(db, serial_id)
            episodes, total_lines, current_page = get_episodes_by_serial_and_season(
                db, serial_id, season, user_id, page_length,
                (current_page - 1) * page_length
            )
        except(NoResultFound, MultipleResultsFound) as e:
            await callback_query.answer(f'Ошибка {e} при загрузке сериала {serial_id}') # noqa E501
            raise
    text, markup = format_episodes_message(
        serial, season, episodes, total_lines, current_page, page_length)
    await update.effective_chat.send_photo(
        photo=serial.file_id,
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
    _, episode_id, file_id = callback_query.data.split('_')
    with context.application.database.session() as db:
        try:
            files = get_episode_by_id(db, episode_id)
            next_episode = get_next_episode(db, files[0])
        except(NoResultFound, MultipleResultsFound) as e:
            await callback_query.answer(
                f'Ошибка {e} при загрузке сериала {episode_id}') 
            raise
        insert_episode_view_record(db, update.effective_sender.id, episode_id)
    text, markup, current_file = format_play_message(
        context.bot.username, files, int(file_id), next_episode, )
    kwargs = {'parse_mode': 'HTML', 'caption': text, 'reply_markup': markup, }
    if context.application.parameters.get('debug', False):
        await update.effective_chat.send_photo(photo=serial.poster_file_id, 
                                               **kwargs)
    else:
        await update.effective_chat.send_video(
            video=current_file.tg_file_id, **kwargs)
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
    try:
        search_text = get_search_text(update.effective_message.text)
    except (ValueError, AttributeError):
        await update.effective_chat.send_message(
            'Результаты поиска устарели.\n'
            'Введите строку для поиска заново.'
            f'\n"{update.effective_message.text}"'
        )
        return
    context.args = [search_text, page]
    await handle_search_command(update, context)
    await handle_delete_callback(update, context)
    return


async def handle_search_command(update, context):
    if not context.args:
        await update.effective_chat.send_message(
            'Введите строку для поиска сериала')
        return
    search_text = context.args.pop(0)
    page = context.args.pop(0) if context.args else 1
    page_length = context.application.parameters.get('page_length')
    namepart = f'%{search_text}%' if len(search_text) > 2 else f'{search_text}%' # noqa E501
    with context.application.database.session() as db:
        serials, num_lines = get_serials_by_namepart(
            db, namepart, page_length, page)
        if not serials:
            await update.effective_chat.send_message(
                'По вашему запросу ничего не найдено в нашем каталоге. '
                'Попробуйте найти сериал на kinopoisk.ru или imdb.com и '
                'пришлите нам ссылку на его страницу. Мы постараемся '
                'добавить его при наличии технической возможности.'
            )
            return
        text, markup = format_search_message(
            search_text, serials, num_lines, page, page_length)
    await update.effective_chat.send_message(
        parse_mode='HTML',
        text=text,
        reply_markup = markup,
    )


async def handle_search_text(update, context):
    search_text = f'{update.message.text.lower()}'
    page = 1
    context.args = [search_text, page]
    await handle_search_command(update, context)


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
        photo=serial.file_id,
        parse_mode='HTML',
        caption=text,
        reply_markup=markup,
    )
    await handle_delete_callback(update, context)


async def handle_serial_command(update, context):
    with context.application.database.session() as db:
        serials = get_random_serials(db, )
    text, markup = format_random_serials_message(serials)
    await update.effective_chat.send_message(text=text, reply_markup=markup, )


async def handle_start_command(update, context):
    with context.application.database.session() as db:
        insert_new_user(db, update.effective_sender)
    if not context.args:
        await handle_help_command(update, context)
        return
    await handle_details_command(update, context)


async def handle_text_callback(update, context):
    callback_query = update.callback_query
    _, search_text = callback_query.data.split('_')
    page = 1
    context.args = [search_text, page]
    await handle_search_command(update, context)
    await handle_delete_callback(update, context)


async def handle_unknown_callback(update, context):
    await update.callback_query.answer()


async def handle_urls(update, context):
    search = re.search(r'(imdb\.com|kinopoisk\.ru)/[^/]+/([^/]+)', update.message.text)
    if not search:
        await update.effective_chat.send_message(
            'Ваша ссылка нераспознана. '
            'Попробуйте найти сериал на kinopoisk.ru или imdb.com и '
            'пришлите нам ссылку на его страницу. Мы постараемся '
            'добавить его при наличии технической возможности.'
        )
        return
    search_key = 'imdb' if search.group(1) == 'imdb.com' else 'kp_id'
    search_value = search.group(2)
    with context.application.database.session() as db:
        try:
            serial = get_serial_by_search_key(db, search_key, search_value)
        except NoResultFound:
            user_id = update.effective_sender.id
            create_new_movie_request(db, user_id, update.message.text,
                                    **{search_key: search_value})
            web_url = re.sub(r'(imdb\.com|kinopoisk\.ru)', 'kinospisok.ru', 
                                update.message.text)
            await update.effective_chat.send_message(
                'В нашем каталоге такого контента пока нет.\n'
                'Пока мы работаем над его добавлением, попробуйте посмотреть '
                f'его на этом ресурсе: {web_url}')
            return
    text, markup = format_details_message(serial)
    await update.effective_chat.send_message(
        text=text, parse_mode='HTML', reply_markup=markup, )
