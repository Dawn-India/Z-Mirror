#!/usr/bin/env python3
from time import time

from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import bot, LOGGER
from bot.helper.ext_utils.bot_utils import (get_readable_file_size,
                                            get_readable_time, is_gdrive_link,
                                            new_task, sync_to_async)
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (deleteMessage, delete_links, 
                                                     sendMessage, auto_delete_message,
                                                     editMessage)


@new_task
async def countNode(_, message):
    args = message.text.split()
    if sender_chat := message.sender_chat:
        tag = sender_chat.title
    elif username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention

    link = args[1] if len(args) > 1 else ''
    if len(link) == 0 and (reply_to := message.reply_to_message):
        link = reply_to.text.split(maxsplit=1)[0].strip()

    if is_gdrive_link(link):
        start_time = time()
        LOGGER.info(f'Counting {link}')
        mssg = await sendMessage(message, f"Counting: <code>{link}</code>")
        gd = GoogleDriveHelper()
        name, mime_type, size, files, folders = await sync_to_async(gd.count, link)
        elapsed = time() - start_time
        if mime_type is None:
            LOGGER.error(f'Error in counting: {name}')
            msg = f'Sorry {tag}!\nYour count has been stopped.'
            msg += f'\n\n<code>Reason : </code>{name}'
            msg += f'\n<code>Elapsed: </code>{get_readable_time(elapsed)}'
            await editMessage(mssg, msg)
            await delete_links(message)
            await auto_delete_message(message, mssg)
            return
        await deleteMessage(mssg)
        msg = f'<b>File Name</b>: <code>{name}</code>'
        msg += f'\n\n<b>Size</b>: {get_readable_file_size(size)}'
        msg += f'\n<b>Type</b>: {mime_type}'
        if mime_type == 'Folder':
            msg += f'\n<b>SubFolders</b>: {folders}'
            msg += f'\n<b>Files</b>: {files}'
        msg += f'\n<b>Elapsed</b>: {get_readable_time(elapsed)}'
        msg += f'\n\n<b>cc</b>: {tag}'
        msg += f'\nThanks For Using <b>@Z_Mirror</b>'
        
    else:
        msg = f'Send Gdrive link along with command or by replying to the link by command\n\n<b>cc</b>: {tag}'
    gdmsg = await sendMessage(message, msg)
    await delete_links(message)
    await auto_delete_message(message, gdmsg)


bot.add_handler(MessageHandler(countNode, filters=command(BotCommands.CountCommand) & CustomFilters.authorized))
