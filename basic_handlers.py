async def handle_history_command(update, context):
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
        await handle_history_command(update, context)
        return
    reply_text = f'"{'", "'.join(context.args)}"'
    await update.message.reply_text(reply_text)
