#!/usr/bin/env python3
from time import time

from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from bot import LOGGER, bot
from bot.helper.ext_utils.bot_utils import (checking_access, get_readable_time,
                                            get_telegraph_list, new_task,
                                            sync_to_async)
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (anno_checker, delete_links,
                                                      editMessage, isAdmin,
                                                      auto_delete_message,
                                                      request_limiter,
                                                      sendMessage)


async def list_buttons(user_id, isRecursive=True):
    buttons = ButtonMaker()
    buttons.ibutton("Folders", f"list_types {user_id} folders {isRecursive}")
    buttons.ibutton("Files", f"list_types {user_id} files {isRecursive}")
    buttons.ibutton("Both", f"list_types {user_id} both {isRecursive}")
    buttons.ibutton(f"Recursive: {isRecursive}",
                    f"list_types {user_id} rec {isRecursive}")
    buttons.ibutton("Cancel", f"list_types {user_id} cancel")
    return buttons.build_menu(2)


async def _list_drive(key, message, item_type, isRecursive):
    LOGGER.info(f"Searching for: {key}")
    start_time = time()
    gdrive = GoogleDriveHelper()
    telegraph_content, contents_no = await sync_to_async(
        gdrive.drive_list, key, isRecursive=isRecursive, itemType=item_type)
    Elapsed = get_readable_time(time() - start_time)
    tag = message.from_user.mention
    msg = ''
    if telegraph_content:
        try:
            button = await get_telegraph_list(telegraph_content)
        except Exception as e:
            await editMessage(message, e)
            return
        msg += f'<b>Found {contents_no} result for <i>{key}</i></b>\n\n'
        msg += f'<b>Type</b>: {item_type} | <b>Recursive list</b>: {isRecursive}\n'
        msg += f'<b>Elapsed</b>: {Elapsed}\n\ncc: {tag}'
        await editMessage(message, msg, button)
    else:
        msg += f'No result found for <i>{key}</i>\n\n'
        msg += f'<b>Type</b>: {item_type} | <b>Recursive list</b>: {isRecursive}\n'
        msg += f'<b>Elapsed</b>: {Elapsed}\n\ncc: {tag}'
        await editMessage(message, msg)
    if msg:
        await delete_links(message.reply_to_message)
        await auto_delete_message(message)


@new_task
async def select_type(_, query):
    user_id = query.from_user.id
    message = query.message
    key = message.reply_to_message.text.split(maxsplit=1)[1].strip()
    data = query.data.split()
    if user_id != int(data[1]):
        return await query.answer(text="Not Yours!", show_alert=True)
    elif data[2] == 'rec':
        await query.answer()
        isRecursive = not bool(eval(data[3]))
        buttons = await list_buttons(user_id, isRecursive)
        return await editMessage(message, 'Choose list options:', buttons)
    elif data[2] == 'cancel':
        await query.answer()
        gdmsg = await editMessage(message, "list has been canceled!")
        await delete_links(message.reply_to_message)
        await auto_delete_message(message, gdmsg)
        return
    await query.answer()
    item_type = data[2]
    isRecursive = eval(data[3])
    await editMessage(message, f"<b>Searching for <i>{key}</i></b>")
    await _list_drive(key, message, item_type, isRecursive)


async def drive_list(_, message):
    if len(message.text.split()) == 1:
        gdmsg = await sendMessage(message, 'Send a search key along with command')
        await delete_links(message)
        await auto_delete_message(message, gdmsg)
        return
    if not message.from_user:
        message.from_user = await anno_checker(message)
    if not message.from_user:
        return
    if sender_chat := message.sender_chat:
        tag = sender_chat.title
    elif username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention
    if reply_to := message.reply_to_message:
        if len(link) == 0:
            link = reply_to.text.split('\n', 1)[0].strip()
        if sender_chat := reply_to.sender_chat:
            tag = sender_chat.title
        elif not reply_to.from_user.is_bot:
            if username := reply_to.from_user.username:
                tag = f"@{username}"
            else:
                tag = reply_to.from_user.mention
    user_id = message.from_user.id
    if not await isAdmin(message, user_id):
        if await request_limiter(message):
            return
        if message.chat.type != message.chat.type.PRIVATE:
            msg, btn = await checking_access(user_id)
            if msg is not None:
                msg += f'\n\n<b>User</b>: {tag}'
                gdmsg = await sendMessage(message, msg, btn.build_menu(1))
                await auto_delete_message(message, gdmsg)
                return
    buttons = await list_buttons(user_id)
    await sendMessage(message, 'Choose list options:', buttons)

bot.add_handler(MessageHandler(drive_list, filters=command(BotCommands.ListCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(select_type, filters=regex("^list_types")))
