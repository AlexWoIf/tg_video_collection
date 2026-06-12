from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from basic_handlers import handle_delete_callback
from helpers import format_numeric
from kinopoiskapiunofficial import KinopoiskApi
from queries import (get_kp_episodes_by_serial_id, ignore_kp_episode,
                     insert_kp_episode, insert_kp_serial)


async def handle_add_command(update, context):
    args = context.args
    # with context.application.database.session() as db:
    # text, markup = format_alphabet_message(letters)
    await update.effective_chat.send_message(text=str(args))


async def handle_get_command(update, context):
    '''
    Get information from kinopoisk.ru and store it in database.
    Usage format:
    /get <kinopoisk-ID>
    '''
    args = context.args
    kp_id = args and args[0].isdigit() and int(args[0])
    if not kp_id:
        await update.effective_chat.send_message(
            'Укажите номер сериала в kinopoisk.ru')
        return
    api = KinopoiskApi(context.application.parameters.get('kp_api_key'))
    serial = await api.get_by_id(kp_id)
    if not serial:
        await update.effective_chat.send_message(
            'Сериал в kinopoisk.ru не найден')
        return
    episodes = await api.get_seasons_info(kp_id)
    with context.application.database.session() as db:
        insert_kp_serial(db, serial, episodes)
    await update.effective_chat.send_message(
        f'Обновлена информация о фильме/сериале "{serial['nameRu']}."'
        f'Вы можете добавить этот объект в наш бот командой /add {kp_id}',
    )


async def handle_exclude_callback(update, context):
    callback_query = update.callback_query
    _, kp_episode, page = callback_query.data.split('_')
    with context.application.database.session() as db:
        serial = ignore_kp_episode(db, kp_episode)
    context.args = [str(serial.id), page, ]
    await handle_update_command(update, context)
    await handle_delete_callback(update, context)


async def handle_include_callback(update, context):
    callback_query = update.callback_query
    _, kp_episode, page = callback_query.data.split('_')
    with context.application.database.session() as db:
        serial = ignore_kp_episode(db, kp_episode)
    context.args = [str(serial.id), page, ]
    await handle_update_command(update, context)
    await handle_delete_callback(update, context)


async def handle_update_callback(update, context):
    callback_query = update.callback_query
    _, serial_id, page = callback_query.data.split('_')
    context.args = [serial_id, page, ]
    await handle_update_command(update, context)
    await handle_delete_callback(update, context)


async def handle_update_command(update, context):
    '''
    Show additional episodes for serial.
    Usage format:
    /update <serial_id> [<page>]
    '''
    if update.effective_chat.id != context.application.parameters.get(
                                                            'storage_chat_id'):
        return
    args = context.args + ['0']
    serial_id = args and args[0].isdigit() and int(args[0]) or 0
    current_page = args and args[1].isdigit() and int(args[1]) or 1
    page_length = context.application.parameters.get('page_length')
    offset = (current_page - 1) * page_length
    with context.application.database.session() as db:
        kp_episodes = get_kp_episodes_by_serial_id(db, serial_id)
    if not kp_episodes:
        await update.effective_chat.send_message(
            f'Сериал с ID {serial_id} не найден, либо для него неизвестны '
            'новые эпизоды')
        return

    total_pages = len(kp_episodes) // page_length
    total_pages += 1 if len(kp_episodes) % page_length else 0
    keyboard = []
    for episode in kp_episodes[offset:offset+page_length]:
        name = f'{episode.name_rus} ({episode.name_eng})' \
            if episode.name_rus else episode.name_eng
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f'➕[{episode.season}x{episode.episode}] {name}',
                    callback_data=f'include_{episode.id}_{current_page}'
                ),
                InlineKeyboardButton(
                    text='❌ Исключить',
                    callback_data=f'exclude_{episode.id}_{current_page}'
                ),
            ]
        )
    if total_pages > 1:
        list_type = f'update_{serial_id}'
        keyboard.append([
            InlineKeyboardButton(
                text='1⏮️',
                callback_data=f'{list_type}_1' if current_page > 1 else '-'),
            InlineKeyboardButton(
                text='◀️',
                callback_data=f'{list_type}_{current_page - 1}'
                              if current_page > 1 else '-'),
            InlineKeyboardButton(f'{current_page}', callback_data='-'),
            InlineKeyboardButton(
                text='▶️',
                callback_data=f'{list_type}_{current_page+1}'
                              if current_page < total_pages else '-'),
            InlineKeyboardButton(
                text=f'⏭️{total_pages}',
                callback_data=f'{list_type}_{total_pages}'
                              if current_page < total_pages else '-'),
        ])
    keyboard.append([
            InlineKeyboardButton(text='✅ Добавить все',
                                 callback_data='include_'),
            InlineKeyboardButton(text='❌ Удалить меню',
                                 callback_data='delete_'),
    ])
    text = f'Можем добавить {format_numeric(len(kp_episodes), 'эпизод')}\n'
    await update.effective_chat.send_message(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
