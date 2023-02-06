from telegram.ext import CallbackQueryHandler

from bot import LOGGER, btn_listener, dispatcher
from bot.helper.telegram_helper.message_utils import (deleteMessage,
                                                      editMessage, isAdmin)


def verifyAnno(update, context):
    query = update.callback_query
    message = query.message
    data = query.data.split()
    msg_id = int(data[2])
    if msg_id not in btn_listener:
        return editMessage('<b>Old Verification Message</b>', message)
    user = query.from_user
    if (
        data[1] == 'admin'
        and isAdmin(message, user.id)
        or data[1] != 'admin'
        and data[1] == 'channel'
    ):
        query.answer(f'Username: {user.username}\nYour userid : {user.id}')
        btn_listener[msg_id][1] = user.id
        btn_listener[msg_id][0] = False
        LOGGER.info(f'Verification Success by ({user.username}){user.id}')
        deleteMessage(message.bot, message)
    elif data[1] == 'admin' and not isAdmin(message, user.id):
        query.answer('You are not really admin')
    else:
        query.answer()
        btn_listener[msg_id][0] = False
        editMessage('<b>Cancel Verification</b>', message)

anno_handler = CallbackQueryHandler(verifyAnno, pattern="verify")
dispatcher.add_handler(anno_handler)
