from pyrogram.filters import regex
from pyrogram.handlers import CallbackQueryHandler

from bot import LOGGER, bot, btn_listener
from bot.helper.telegram_helper.message_utils import (deleteMessage,
                                                      editMessage, isAdmin)


async def verifyAnno(client, query):
    message = query.message
    data = query.data.split()
    msg_id = int(data[2])
    if msg_id not in btn_listener:
        return await editMessage(message, '<b>Old Verification Message</b>')
    user = query.from_user
    is_admin = await isAdmin(message, user.id)
    if data[1] == 'admin' and is_admin:
        await query.answer(f'Username: {user.username}\nYour userid : {user.id}')
        btn_listener[msg_id] = user
        LOGGER.info(f'Verification Success by ({user.username}) {user.id}')
        await deleteMessage(message)
    elif data[1] == 'admin':
        await query.answer('You are not an admin')
    else:
        await query.answer()
        await editMessage(message, '<b>Cancel Verification</b>')

bot.add_handler(CallbackQueryHandler(verifyAnno, filters=regex("^verify")))
