from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from helpers import (
    get_button_for_serial,
)
from queries import (
    get_aggregated_view_history,
)


async def handle_help_command(update, context):
    reply_text='''
        Бот для просмотра сериалов прямо в телеграме
        Список доступных команд:
        \u25cf  для поиска сериала введите несколько букв его названия (не меньше 3х)
        \u25cf  /help - справка о доступных командах
        \u25cf  /serial - получить 10 случайных сериалов
        \u25cf  /history -  последние запрошенные Вами эпизоды
        \u25cf  /rating -  самые популярные сериалы
        Замечания и предложения присылайте на @AlexWolf_kornet
    '''
    await update.message.reply_text(reply_text)


async def handle_start_command(update, context):
    if not context.args:
        await handle_help_command(update, context)
        return
    reply_text = f'"{'", "'.join(context.args)}"'
    await update.message.reply_text(reply_text)


async def handle_history_command(update, context):
    user_id=update.message.from_user.id
    db = context.application.database.get_session()
    history = get_aggregated_view_history(db, user_id)
    if not history:
        reply_text = 'История просмотров пуста'
        await update.message.reply_text(reply_text)
        return
    keyboard = [
        [InlineKeyboardButton(**get_button_for_serial(serial))] for serial in history # noqa E501
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_text=(
        'Вот последние просмотренные Вами сериалы.\n'
        'Сверху - самый последний из просмотренных и далее по хронологии.\n'
        'В квадратных скобках указано количество просмотров эпизодов.'
    )

    await update.message.reply_text(
        text=reply_text,
        reply_markup = reply_markup,
    )