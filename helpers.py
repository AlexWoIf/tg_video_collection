def get_button_for_serial(serial):
    name_rus, name_eng, counter, serial_id = serial
    if counter % 10 == 1 and counter % 100 != 11:
            counter_part = f'{counter} серия'
    elif counter % 10 in [2, 3, 4] and counter % 100 not in [12, 13, 14]:
        counter_part =  f'{counter} серии'
    else:
        counter_part =  f'{counter} серий'
    counter_part = f'[{counter_part}]'

    name_part = f'{name_rus}({name_eng})'
    if len(name_part) > 64 - len(counter_part):
        name_part = f'{name_part[:64 - len(counter_part) - 3]}...'

    return {'text': f'{name_part}{counter_part}', 
            'callback_data': f'details:{serial_id}'}
