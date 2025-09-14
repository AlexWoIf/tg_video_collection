from helpers import (
    get_button_text_for_serial,
    get_paginated_markup,
)


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
