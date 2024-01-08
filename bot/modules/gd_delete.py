#!/usr/bin/env python3
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import LOGGER, bot
from bot.helper.ext_utils.bot_utils import (is_gdrive_link, new_task,
                                            sync_to_async)
from bot.helper.mirror_utils.gdrive_utils.delete import gdDelete
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (auto_delete_message, delete_links,
                                                      sendMessage)


@new_task
async def deletefile(_, message):
    args = message.text.split()
    if sender_chat := message.sender_chat:
        tag = sender_chat.title
    elif username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention

    if len(args) > 1:
        link = args[1]
    elif reply_to := message.reply_to_message:
        link = reply_to.text.split(maxsplit=1)[0].strip()
    else:
        link = ''
    if is_gdrive_link(link):
        LOGGER.info(link)
        msg = await sync_to_async(gdDelete().deletefile, link)
    else:
        msg = f'Send Gdrive link along with command or by replying to the link by command\n\n<b>cc</b>: {tag}'
    gdmge = await sendMessage(message, msg)
    await delete_links(message)
    await auto_delete_message(message, gdmge)


bot.add_handler(MessageHandler(deletefile, filters=command(BotCommands.DeleteCommand) & CustomFilters.sudo))
