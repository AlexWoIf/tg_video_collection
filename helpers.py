import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.helpers import create_deep_linked_url


DELETE = '\u274c Удалить'
#LISTEPISODES = '🎞️ Вернуться к списку эпизодов'
LISTEPISODES = '👈 Вернуться к списку эпизодов'
#LISTSEASONS = '🎬 Список сезонов'
LISTSEASONS = '🗂️ Список сезонов'
SERIALDETAILS = '\u2139 Информация о сериале'
COMPLAIN = '⚠ Сообщить о проблеме'
SUPPORT_LINK = 'tg://resolve?domain=AlexWolf_kornet'


def format_numeric(number, keyword):
    words = {
         'просмотр': ['просмотр', 'просмотра', 'просмотров'],
         'серия': ['серия', 'серии', 'серий'],
         'сериал': ['сериал', 'сериала', 'сериалов'],
         'эпизод': ['эпизод', 'эпизода', 'эпизодов'],
         'фильм': ['фильм', 'фильма', 'фильмов'],
         'минута': ['минута', 'минуты', 'минут'],
    }
    word_forms = words.get(keyword)
    if not word_forms:
        return f'{number} {keyword}'
    if number % 10 == 1 and number % 100 != 11:
        return f'{number} {word_forms[0]}'
    elif number % 10 in [2, 3, 4] and number % 100 not in [12, 13, 14]:
        return f'{number} {word_forms[1]}'
    else:
        return f'{number} {word_forms[2]}'


def get_search_text(text):
    match = re.search(r'"%*(?P<text>.*)%*"', text)
    if match:
        return match.group('text')
    else:
        raise ValueError


def get_deep_link(bot_name, callback_data):
    return create_deep_linked_url(bot_name, callback_data)

def get_button_text_for_serial(serial, max_length=40, counter=True):
    if counter:
        name_rus, name_eng, counter, serial_id = serial
        counter_part = f'[{counter}]'
    else:
        name_rus, name_eng, serial_id = serial
        counter_part = ''
    name_part = f'{name_rus} ({name_eng})'
    if len(name_part) > (max_length - len(counter_part)):
        name_part = f'{name_part[:max_length - len(counter_part) - 3]}...'

    return {'text': f'{name_part}{counter_part}', 
            'callback_data': f'details_{serial_id}'}


def get_button_text_for_episode(episode, max_length=40):
    season, episode, name, episode_id, file_id, views = episode
    return {
        'text': f'{"✅" if views else ""}[{season}x{episode}]{name}',
        'callback_data': f'play_{episode_id}_{file_id}'
    }


def get_alphabet_markup(letters):
    buttons = [{'text': '{}[{}]'.format(*letter), 
                'callback_data': f'text_{letter.letter}'}
               for letter in letters]
    row_length = 6
    keyboard = [
        list(map(lambda button: InlineKeyboardButton(**button), 
        buttons[i:i+row_length]))
        for i in range(0, len(buttons), row_length)
    ]
    keyboard.append([
        InlineKeyboardButton('RUS', callback_data='alphabet_RUS'),
        InlineKeyboardButton('ENG', callback_data='alphabet_ENG'),
    ])
    return InlineKeyboardMarkup(keyboard)


def get_paginated_markup(buttons_callbacks, list_type, current_page=1, total_pages=1, ): # noqa: E501
    keyboard = [
        [InlineKeyboardButton(**button_callback)]
        for button_callback in buttons_callbacks
    ]
    if total_pages == 1:
        return InlineKeyboardMarkup(keyboard)
    keyboard.append([
        InlineKeyboardButton(
            text='1⏮️',
            callback_data=f'{list_type}_1' if current_page>1 else '-'),
        InlineKeyboardButton(
            text='◀️',
            callback_data=f'{list_type}_{current_page - 1}' 
                            if current_page>1 else '-'),
        InlineKeyboardButton(f'{current_page}', callback_data='-'),
        InlineKeyboardButton(
            text='▶️', 
            callback_data=f'{list_type}_{current_page+1}' 
                            if current_page<total_pages else '-'),
        InlineKeyboardButton(
            text=f'⏭️{total_pages}',
            callback_data=f'{list_type}_{total_pages}' 
                            if current_page<total_pages else '-'),
    ])
    return InlineKeyboardMarkup(keyboard)

def get_serial_detail_markup(serial):
    keyboard = [
        [
            InlineKeyboardButton(
                text=LISTSEASONS,
                callback_data=f'seasons_{serial.id}'),
            InlineKeyboardButton(
                text=DELETE,
                callback_data='delete_')]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_seasons_markup(serial_id, seasons):
    keyboard = []
    for i in range(0, len(seasons), 2):
        keyboard.append(
            [InlineKeyboardButton(
                text=f'Сезон {season}[{episodes}]',
                callback_data=f'episodes_{serial_id}_{season}_1')
            for season, episodes in seasons[i:i+2]]
        )
    keyboard.append([
        InlineKeyboardButton(
            text=SERIALDETAILS,
            callback_data=f'details_{serial_id}')
    ])
    keyboard.append([
        InlineKeyboardButton(COMPLAIN, url=SUPPORT_LINK),
        InlineKeyboardButton(DELETE, callback_data='delete_')])
    return InlineKeyboardMarkup(keyboard)


def add_episodes_markup_footer(reply_markup, serial_id):
    keyboard = reply_markup.inline_keyboard
    keyboard += (
        [InlineKeyboardButton(LISTSEASONS, callback_data = f"seasons_{serial_id}"),
         InlineKeyboardButton(SERIALDETAILS, callback_data = f"details_{serial_id}") ],
        [InlineKeyboardButton(COMPLAIN, url = SUPPORT_LINK),
         InlineKeyboardButton(DELETE, callback_data = "delete_"),]
    )
    return InlineKeyboardMarkup(keyboard)


def get_default_episode_markup(episode, episodes, next_episode):
    keyboard = [
        [
            InlineKeyboardButton(
                '👉 Следующий эпизод',
                callback_data=f'play_{next_episode.id}_{next_episode.file_id}',
            )
        ] if next_episode else []
    ]
    keyboard += [
            [InlineKeyboardButton(
                f'[{row.width}x{row.height}] {row.audio}',
                callback_data = f'play_{row.id}_{row.file_id}',
            )]
            for row in episodes
        ]
    keyboard += [
        [
            InlineKeyboardButton(
                LISTEPISODES,
                callback_data = f'episodes_{episode.serial_id}_{episode.season}_1' # noqa E501
            ),
        ],
        [
            InlineKeyboardButton(
                LISTSEASONS, callback_data = f'seasons_{episode.serial_id}'
            ),
            InlineKeyboardButton(
                SERIALDETAILS, callback_data = f'details_{episode.serial_id}'
            ),
        ],
        [
            InlineKeyboardButton(COMPLAIN, url = SUPPORT_LINK),
            InlineKeyboardButton(DELETE, callback_data = "delete_"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
