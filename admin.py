import logging

from collections import defaultdict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from helpers import format_numeric
from kinopoiskapiunofficial import KinopoiskApi
from queries import (get_episodes_by_serial_id, get_serial_by_id,
                     insert_kp_episode, insert_kp_serial, )


async def handle_add_command(update, context):
    args = context.args
    # with context.application.database.session() as db:
    # text, markup = format_alphabet_message(letters)
    await update.effective_chat.send_message(text=str(args))


async def handle_get_command(update, context):
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
        f'Вы можете этот объект в наш бот командой /add {kp_id}',
    )


async def handle_update_command(update, context):
    args = context.args
    serial_id = args and args[0].isdigit() and int(args[0])
    if not serial_id:
        await update.effective_chat.send_message(
            'Укажите корректный номер сериала в нашей базе')
        return
    
    with context.application.database.session() as db:
        my_episodes = get_episodes_by_serial_id(db, serial_id)
        serial = get_serial_by_id(db, serial_id)
    my_seasons = defaultdict(lambda: defaultdict(list))
    for episode in my_episodes:
        my_seasons[episode.season][episode.episode] = episode.name, episode.id

    api = KinopoiskApi(context.application.parameters.get('kp_api_key'))
    kp_id = serial.kp_id
    kp_episodes = await api.get_seasons_info(kp_id)
    added = 0
    text = ''
    keyboard = []
    for season in kp_episodes.get('items', []):
        for episode in season.get('episodes', []):
            season_number = episode.get('seasonNumber')
            episode_number = episode.get('episodeNumber')
            if my_seasons[season_number][episode_number]:
                continue
            name = episode.get('nameEn', f'Episode {episode_number}')
            name_rus = episode.get('nameRu')
            if name_rus:
                name = f'{name_rus} ({name})'
            # with context.application.database.session() as db:
            #     insert_new_episode(db, serial_id, season_number, episode_number, name)
            # text += f'❌ [{season_number}x{episode_number}] {name}\n'
            added += 1
            keyboard.append(
                [InlineKeyboardButton(
                    text=f'❌ [{season_number}x{episode_number}] {name}',
                    callback_data=f'exclude_{season_number}_{episode_number}')]
            )
    keyboard = keyboard[:90]
    keyboard.append([
            InlineKeyboardButton(text='✅ Добавить все', callback_data='add_'),
            InlineKeyboardButton(text='❌ Удалить все', callback_data='delete_'),
    ])
    text = f'Можем добавить {format_numeric(added, 'эпизод')}\n'
    await update.effective_chat.send_message(text, 
        reply_markup=InlineKeyboardMarkup(keyboard))
    # while True:
    #     if len(text) > 4095:
    #         index = text.rfind('\n', 0, 4096)
    #         await update.effective_chat.send_message(text[:index])
    #         text = text[index+1:]
    #     else:
    #         await update.effective_chat.send_message(text)
    #         break
