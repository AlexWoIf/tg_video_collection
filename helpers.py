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


def get_button_for_serial(serial, max_length=40):
    name_rus, name_eng, counter, serial_id = serial
    counter_part = f'[{counter}]'

    name_part = f'{name_rus}({name_eng})'
    if len(name_part) > (max_length - len(counter_part)):
        name_part = f'{name_part[:max_length - len(counter_part) - 3]}...'

    return {'text': f'{name_part}{counter_part}', 
            'callback_data': f'details:{serial_id}'}
