from threading import Thread
from time import time

from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import LOGGER, dispatcher
from bot.helper.ext_utils.bot_utils import get_readable_time
from bot.helper.ext_utils.rate_limiter import ratelimiter
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (anno_checker,
                                                      deleteMessage,
                                                      editMessage, sendMessage)

list_listener = {}

def common_btn(isRecur, msg_id):
    buttons = ButtonMaker()
    buttons.sbutton("Folders", f"types folders {msg_id}")
    buttons.sbutton("Files", f"types files {msg_id}")
    buttons.sbutton("Both", f"types both {msg_id}")
    buttons.sbutton(f"Recurive: {isRecur}", f"types recur {msg_id}")
    buttons.sbutton("Cancel", f"types cancel {msg_id}")
    return buttons.build_menu(3)

@ratelimiter
def list_buttons(update, context):
    message = update.message
    if message.from_user.id in [1087968824, 136817688]:
        message.from_user.id = anno_checker(message)
        if not message.from_user.id:
            return
    user_id = message.from_user.id
    msg_id = message.message_id
    if len(context.args) == 0:
        return sendMessage('Send a search key along with command', context.bot, message)
    isRecur = False
    button = common_btn(isRecur, msg_id)
    query = message.text.split(" ", maxsplit=1)[1]
    list_listener[msg_id] = [user_id, query, isRecur]
    sendMessage('Choose option to list.', context.bot, message, button)

@ratelimiter
def select_type(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    listener_id = int(data[-1])
    try:
        listener_info = list_listener[listener_id]
    except:
        return editMessage("This is an old message", message)
    if listener_info[0] != user_id:
        return query.answer(text="You are not allowed to do this!", show_alert=True)
    elif data[1] == 'cancel':
        query.answer()
        return editMessage("list has been canceled!", message)
    elif data[1] == 'recur':
        query.answer()
        listener_info[2] = not listener_info[2]
        button = common_btn(listener_info[2], listener_id)
        return editMessage('Choose option to list.', message, button)
    query.answer()
    item_type = data[1]
    editMessage(f"<b>Searching for <i>{listener_info[1]}</i></b>\n\n<b>Type</b>: {item_type} | <b>Recursive list</b>: {listener_info[2]}",  message)
    Thread(target=_list_drive, args=(listener_info, message, item_type, context.bot)).start()
    del list_listener[listener_id]

def _list_drive(listener, bmsg, item_type, bot):
    query = listener[1]
    isRecur = listener[2]
    LOGGER.info(f"listing: {query}")
    gdrive = GoogleDriveHelper()
    start_time = time()
    msg, button = gdrive.drive_list(query, isRecursive=isRecur, itemType=item_type)
    if bmsg.reply_to_message.from_user.username:
        tag = f"@{bmsg.reply_to_message.from_user.username}"
    else:
        tag = bmsg.reply_to_message.from_user.mention_html(bmsg.reply_to_message.from_user.first_name)
    Elapsed = get_readable_time(time() - start_time)
    deleteMessage(bot, bmsg)
    if button:
        msg = f'{msg}\n\n<b>Type</b>: {item_type} | <b>Recursive list</b>: {isRecur}\n#list: {tag}\n<b>Elapsed</b>: {Elapsed}'
        sendMessage(msg, bot, bmsg.reply_to_message, button)
    else:
        sendMessage(f'No result found for <i>{query}</i>\n\n<b>Type</b>: {item_type} | <b>Recursive list</b>: {isRecur}\n#list: {tag}\n<b>Elapsed</b>: {Elapsed}', bot, bmsg.reply_to_message)

list_handler = CommandHandler(BotCommands.ListCommand, list_buttons,
                              filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
list_type_handler = CallbackQueryHandler(select_type, pattern="types")

dispatcher.add_handler(list_handler)
dispatcher.add_handler(list_type_handler)
