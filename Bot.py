import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, ConversationHandler, Filters, MessageHandler

import config
from db_handlers import *

aid = None
is_authorized = False #Заменить на false и написать процедуру авторизации пользователя через токен


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


def auth(update: Update, context: CallbackContext) -> str:
    update.message.reply_text("Отправте мне токен из личного кабинета, чтобы подтвердить личность!")
    return 'verify'


def verify_token(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Ищем вас в базе данных...")
    global aid
    aid = get_aid_by_token(update.message.text.lower())
    if aid is not None:
        global is_authorized
        is_authorized = True
        update.effective_message.reply_text("Вы успешно вошли, для продолжения введите - /start")

    else:
        update.effective_message.reply_text("Ошибка авторизации, для повтора введите - /start")
    return ConversationHandler.END


def start(update: Update, context: CallbackContext) -> None:
    # global is_authorized
    # if not is_authorized:
    #     print(is_authorized)
    #     return 'auth'
    keyboard = [
        [
            InlineKeyboardButton("Офис.Навигатор", callback_data='navigator'),
            InlineKeyboardButton("Офис.Находки", callback_data='lostnfound'),
            InlineKeyboardButton("Офис.Люди", callback_data='people'),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Выберите приложение:', reply_markup=reply_markup)


def navigator_main(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    keyboard = [
        [
            InlineKeyboardButton("Посмотреть план этажа", callback_data='navigator_plan'),
            InlineKeyboardButton("Проложить маршрут", callback_data='navigator_road'),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.answer()
    query.edit_message_text(text="Вы хотите: ", reply_markup=reply_markup)


def navigator_plan(update: Update, context: CallbackContext) -> None:
    ncols = 4
    print(get_floors_count())
    nrows = int(get_floors_count() / ncols)
    print(nrows)
    query = update.callback_query
    keyboard = []
    floor = 1
    for i in range(1, nrows + 1):
        row = []
        for j in range(ncols):
            row.append(InlineKeyboardButton(str(floor), callback_data='floor_{}'.format(floor)))
            floor += 1
        keyboard.append(row)

    print(keyboard)

    reply_markup = InlineKeyboardMarkup(keyboard)

    query.answer()
    query.edit_message_text(text="Выберите этаж: ", reply_markup=reply_markup)


def navigator_plan_floor(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    floor_img = query.data.lower() + '.png'
    floor = query.data.lower().split('_')[1]
    photo = open(os.path.join(config.FLOORS_DIR, floor_img), 'rb')
    update.effective_chat.send_photo(photo=photo, caption='{} этаж'.format(floor))
    update.effective_chat.send_message("Для продолжения введите - /start")


def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    query.edit_message_text(text=query.data)


def lostnfound(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    keyboard = [    
        [
            InlineKeyboardButton("Потеряли что-то?", callback_data='lost'),
            InlineKeyboardButton("Нашли что-то?", callback_data='found'),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.answer()
    query.edit_message_text(text="Что случилось: ", reply_markup=reply_markup)


def lost(update: Update, context: CallbackContext) -> None:
    data = load_lost_data()
    if len(data) == 0:
        update.effective_message.reply_text('К сожалению сегодня ничего не находили!')
    else:
        for e in data:
            update.effective_message.reply_text("{} {} Оставил сообщение о находке: \"{}\"".format(e[8], e[6], e[1]))
    update.effective_message.reply_text("Введите - /start для продолжения общения")


def found(update: Update, context: CallbackContext) -> str:
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Отправте мне фото вещи или её описание, и как владелец сможет забрать ее.")
    return 'found'


def founded_item(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    save_lost_data(update.message.text, aid)
    update.message.reply_text('Спасибо за помощь! Надеюсь, вещь найдет владельца.')

    return ConversationHandler.END


def end(update: Update, context: CallbackContext) -> None:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over"""
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Всегда рад вам!")


def main():
    # Create the Updater and pass it your bot's token.
    global is_authorized
    global aid

    print(aid)
    print(is_authorized)
    updater = Updater(config.token)
    # conv_handler = ConversationHandler(
    #     entry_points=[CommandHandler('start', start)],
    #     states={
    #         'navigator': [
    #             CallbackQueryHandler(lost, pattern='^lost$'),
    #             CallbackQueryHandler(found, pattern='^found$'),
    #             CallbackQueryHandler(end, pattern='^back$'),
    #         ],
    #         'lostnfound': [
    #             CallbackQueryHandler(lost, pattern='^lost$'),
    #             CallbackQueryHandler(found, pattern='^found$'),
    #             CallbackQueryHandler(end, pattern='^back$'),
    #         ],
    #         'people': []
    #     },
    #     fallbacks=[CommandHandler('start', start)],
    # )   

    auth_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(auth, pattern='^auth$')],
        states={
            'verify': [
                MessageHandler(Filters.text & ~Filters.command, verify_token)
            ]
        },
        fallbacks=[CommandHandler('start', start)]
    )

    lnf_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(found, pattern='^found$')],
        states={
            'found': [
                MessageHandler(Filters.text & ~Filters.command, founded_item)
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    updater.dispatcher.add_handler(auth_handler)

    updater.dispatcher.add_handler(CommandHandler('start', start))

    updater.dispatcher.add_handler(CallbackQueryHandler(navigator_main, pattern='^navigator$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(navigator_plan, pattern='^navigator_plan$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(navigator_plan_floor, pattern='^floor_[0-9]*$'))


    updater.dispatcher.add_handler(CallbackQueryHandler(lostnfound, pattern='^lostnfound$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(lost, pattern='^lost$'))
    updater.dispatcher.add_handler(lnf_handler)
    updater.dispatcher.add_handler(CallbackQueryHandler(end, pattern='^back$'))

    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    # updater.dispatcher.add_handler(conv_handler)
    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == '__main__':
    main()