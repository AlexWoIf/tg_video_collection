from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


def format_numeric(number, keyword):
    words = {
         'просмотр': ['просмотр', 'просмотра', 'просмотров'],
         'серия': ['серия', 'серии', 'серий'],
         'сериал': ['сериал', 'сериала', 'сериалов'],
         'эпизод': ['эпизод', 'эпизода', 'эпизодов'],
         'фильм': ['фильм', 'фильма', 'фильмов'],
         'минута': ['минута', 'минуты', 'минут'],
    }
    word_forms = words.get(word)
    if not word_forms:
        return f'{number} {word}'
    if number % 10 == 1 and number % 100 != 11:
        return f'{number} {word_forms[0]}'
    elif number % 10 in [2, 3, 4] and number % 100 not in [12, 13, 14]:
        return f'{number} {word_forms[1]}'
    else:
        return f'{number} {word_forms[2]}'


def get_button_text_for_serial(serial, max_length=40):
    name_rus, name_eng, counter, serial_id = serial
    counter_part = f'[{counter}]'

    name_part = f'{name_rus}({name_eng})'
    if len(name_part) > (max_length - len(counter_part)):
        name_part = f'{name_part[:max_length - len(counter_part) - 3]}...'

    return {'text': f'{name_part}{counter_part}', 
            'callback_data': f'details:{serial_id}'}


def get_paginated_markup(serials, current_page, total_pages):
    keyboard = [
        [InlineKeyboardButton(**get_button_text_for_serial(serial))]
        for serial in serials
    ]
    if total_pages == 1:
        return InlineKeyboardMarkup(keyboard)
    keyboard.append([
        InlineKeyboardButton(
            text='1⏮️',
            callback_data=f'page:1' if current_page>1 else '-'),
        InlineKeyboardButton(
            text='◀️',
            callback_data=f'page:{current_page - 1}' if current_page>1 else '-'), # noqa E501
        InlineKeyboardButton(f'{current_page}', callback_data='-'),
        InlineKeyboardButton(
            text='▶️', 
            callback_data=f'page:{current_page+1}' if current_page<total_pages
                            else '-'),
        InlineKeyboardButton(
            text=f'⏭️{total_pages}',
            callback_data=f'page:{total_pages}' if current_page<total_pages
                            else '-'),
    ])
    return InlineKeyboardMarkup(keyboard)