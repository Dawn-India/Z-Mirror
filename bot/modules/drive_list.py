from time import time

from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from bot import LOGGER, bot, bot_loop
from bot.helper.ext_utils.bot_utils import (get_readable_time, new_task,
                                            sync_to_async)
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
    buttons.ibutton("Folders", f"types folders {msg_id}")
    buttons.ibutton("Files", f"types files {msg_id}")
    buttons.ibutton("Both", f"types both {msg_id}")
    buttons.ibutton(f"Recurive: {isRecur}", f"types recur {msg_id}")
    buttons.ibutton("Cancel", f"types cancel {msg_id}")
    return buttons.build_menu(3)

async def list_buttons(client, message):
    if len(message.command) == 1:
        return await sendMessage(message, 'Send a search key along with command')
    if not message.from_user:
        tag = 'Anonymous'
        message.from_user = await anno_checker(message)
    elif username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention
    if not message.from_user:
        return
    user_id = message.from_user.id
    msg_id = message.id
    isRecur = False
    button = common_btn(isRecur, msg_id)
    query = message.text.split(" ", maxsplit=1)[1]
    list_listener[msg_id] = [user_id, query, isRecur, tag]
    await sendMessage(message, 'Choose option to list.', button)

async def _list_drive(key, message, item_type):
    LOGGER.info(f"listing: {key}")
    msg, button = await sync_to_async(GoogleDriveHelper().drive_list, key, isRecursive=True, itemType=item_type)
    if button:
        await editMessage(message, msg, button)
    else:
        await editMessage(message, f'No result found for <i>{key}</i>')


@new_task
async def select_type(client, query):
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    listener_id = int(data[-1])
    if not (listener_info := list_listener[listener_id]):
        return await editMessage(message, "This is an old message")
    if listener_info[0] != user_id:
        return await query.answer(text="You are not allowed to do this!", show_alert=True)
    elif data[1] == 'cancel':
        await query.answer()
        return await editMessage(message, "list has been canceled!")
    elif data[1] == 'recur':
        await query.answer()
        listener_info[2] = not listener_info[2]
        button = common_btn(listener_info[2], listener_id)
        return await editMessage(message, 'Choose option to list.', button)
    await query.answer()
    item_type = data[1]
    await editMessage(message, f"<b>Searching for <i>{listener_info[1]}</i></b>\n\n<b>Type</b>: {item_type} | <b>Recursive list</b>: {listener_info[2]}")
    bot_loop.create_task(_list_drive(listener_info, message, item_type))
    del list_listener[listener_id]


async def _list_drive(listener, bmsg, item_type):
    query = listener[1]
    isRecur = listener[2]
    tag = listener[3]
    LOGGER.info(f"listing: {query}")
    start_time = time()
    msg, button = await sync_to_async(GoogleDriveHelper().drive_list, query, isRecursive=isRecur, itemType=item_type)
    Elapsed = get_readable_time(time() - start_time)
    await deleteMessage(bmsg)
    if button:
        msg = f'{msg}\n\n<b>Type</b>: {item_type} | <b>Recursive list</b>: {isRecur}\n#list: {tag}\n<b>Elapsed</b>: {Elapsed}'
        await sendMessage(bmsg.reply_to_message, msg, button)
    else:
        await sendMessage(bmsg.reply_to_message, f'No result found for <i>{query}</i>\n\n<b>Type</b>: {item_type} | <b>Recursive list</b>: {isRecur}\n#list: {tag}\n<b>Elapsed</b>: {Elapsed}')

bot.add_handler(MessageHandler(list_buttons, filters=command(BotCommands.ListCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(select_type, filters=regex("^types")))