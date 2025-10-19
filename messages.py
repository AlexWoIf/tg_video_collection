from helpers import (
    add_episodes_markup_footer,
    get_alphabet_markup,
    get_button_text_for_episode,
    get_button_text_for_serial,
    get_deep_link,
    get_default_episode_markup,
    get_paginated_markup,
    get_serial_detail_markup,
    get_seasons_markup,
)


def format_alphabet_message(letters):
    text = 'Выбарите начальную букву сериала.\n' \
           'В квадратных скобках указано количество сериалов.\n'
    markup = get_alphabet_markup(letters)
    return text, markup


def format_help_message():
    return '''
        Бот для просмотра сериалов прямо в телеграме
        Список доступных команд:
        ●  для поиска сериала введите несколько букв его названия
        ●  /help - справка о доступных командах
        ●  /serial - получить 10 случайных сериалов
        ●  /history -  последние запрошенные Вами эпизоды
        ●  /rating -  самые популярные сериалы
        Замечания и предложения присылайте на @AlexWolf_kornet
    '''


def format_details_message(serial):
    text = (f'<b>{serial.name_rus}({serial.name_eng})</b>\n'
        f'<u>Формат серий:</u><i> {serial.format}</i>\n' 
        f'<u>Описание:</u>\n{serial.descr}')
    markup = get_serial_detail_markup(serial)
    return text, markup


def format_episodes_message(serial, season, episodes, total_lines,
                            current_page, page_length):
    total_pages = total_lines // page_length
    total_pages += 1 if total_lines % page_length else 0
    buttons = [get_button_text_for_episode(episode) for episode in episodes]
    text = f'<b>{serial.name_rus}({serial.name_eng})</b>\n' \
        f'Выберите нужный эпизод из сезона {season}:\n' \
        '✅ - вы уже запрашивали этот эпизод\n' \
        f'Страница {current_page} из {total_pages}'
    markup = get_paginated_markup(
        buttons, f'episodes_{serial.id}_{season}', current_page, total_pages)
    markup = add_episodes_markup_footer(markup, serial.id)
    return text, markup


def format_history_message(serials, total_lines, page, page_length):
    total_pages = total_lines // page_length
    total_pages += 1 if total_lines % page_length else 0
    buttons = [get_button_text_for_serial(serial) for serial in serials]
    text=(
        'Вот последние просмотренные Вами сериалы.\n'
        'Сверху - самый последний из просмотренных и далее по хронологии.\n'
        'В квадратных скобках указано количество просмотров эпизодов.'
        f'Страница {page} из {total_pages}'
    )
    markup = get_paginated_markup(buttons, 'history', page, total_pages)

    return text, markup


def format_play_message(bot_name, files, file_id, next_episode_id):
    for row, file in enumerate(files):
        if file.file_id == file_id:
            episode = files.pop(row)
            break
    text = (
        f'<a href="{get_deep_link(bot_name, f'{episode.serial_id}')}">'
        f'<b>{episode.name_rus} ({episode.name_eng})</b></a>\n'
        f'<u>Episode:</u>[{episode.season}x{episode.episode}]\n'
        f'<i>{episode.name}</i>\n'
        f'<a href="{get_deep_link(bot_name, 'serial')}">'
        'Еще больше сериалов в @KinoSpisokBot</a>'
    )
    if files:
        text += f'\n[{episode.width}x{episode.height}] {episode.audio}'
    markup = get_default_episode_markup(episode, files, next_episode_id)
    return text, markup, episode


def format_random_serials_message(serials, ):
    text=('10 случайных сериалов]":')
    buttons = [get_button_text_for_serial(serial, counter=False)
               for serial in serials]
    markup = get_paginated_markup(buttons, 'random', )
    return text, markup


def format_rating_message(serials, total_lines, page, page_length):
    total_pages = total_lines // page_length
    total_pages += 1 if total_lines % page_length else 0
    text=(
        'Самые популярные сериалы:\n'
        'В квадратных скобках указано количество пользователей смотревших сериал.\n' # noqa E501
        f'Страница {page} из {total_pages}'
    )
    buttons = [get_button_text_for_serial(serial) for serial in serials]
    markup = get_paginated_markup(buttons, 'rating', page, total_pages)
    return text, markup


def format_search_message(namepart, serials, total_lines, page, page_length):
    total_pages = total_lines // page_length
    total_pages += 1 if total_lines % page_length else 0
    text=(
        f'Результаты поиска по запросу "<i>{namepart}</i>":\n'
        'Выберите сериал из списка ниже или введите новую строку для поиска\n'
        f'Страница {page} из {total_pages}'
    )
    buttons = [get_button_text_for_serial(serial, counter=False)
               for serial in serials]
    markup = get_paginated_markup(buttons, 'search', page, total_pages)
    return text, markup


def format_seasons_message(serial, seasons):
    text = (f'<b>{serial.name_rus}({serial.name_eng})</b>\n'
        'Выберите сезон из списка ниже.'
        'В квадратных скобках количество серий')
    markup = get_seasons_markup(serial.id, seasons)
    return text, markup