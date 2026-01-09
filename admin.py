import logging
import re

from collections import defaultdict

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from telegram import error as tg_error

from helpers import format_numeric
from kinopoiskapiunofficial import KinopoiskApi
from queries import get_episodes_by_serial_id, insert_new_episode

async def handle_add_command(update, context):
    args = context.args
    # with context.application.database.session() as db:
    # text, markup = format_alphabet_message(letters)
    await update.effective_chat.send_message(text=str(args))


async def handle_update_command(update, context):
    if not context.args:
        await update.effective_chat.send_message(
            'Укажите номер сериала в нашей базе')
        return
    args = context.args
    serial_id = int(args[0])

    with context.application.database.session() as db:
        my_episodes = get_episodes_by_serial_id(db, serial_id)
    my_seasons = defaultdict(lambda: defaultdict(list))
    for episode in my_episodes:
        my_seasons[episode.season][episode.episode] = episode.name, episode.id

    api = KinopoiskApi(context.application.parameters.get('kp_api_key'))
    kp_id = my_episodes[0].kp_id
    kp_episodes = await api.get_seasons_info(kp_id)
    added = 0
    text = ''
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
            with context.application.database.session() as db:
                insert_new_episode(db, serial_id, season_number, episode_number, name)
            text += f'Добавили [{season_number}x{episode_number}] {name}\n'
            added += 1
    await update.effective_chat.send_message(
        f'{text}Добавили {format_numeric(added, 'эпизод')}')
