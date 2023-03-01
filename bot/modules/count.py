from time import time

from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import bot
from bot.helper.ext_utils.bot_utils import (get_readable_time, is_gdrive_link,
                                            new_task, sync_to_async)
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (anno_checker,
                                                      deleteMessage,
                                                      sendMessage)


@new_task
async def countNode(client, message):
    args = message.text.split()
    link = ''
    if len(args) > 1:
        link = args[1]
        if username := message.from_user.username:
            tag = f"@{username}"
        else:
            tag = message.from_user.mention
    if reply_to := message.reply_to_message:
        if len(link) == 0:
            link = reply_to.text.split(maxsplit=1)[0].strip()
        if not reply_to.from_user.is_bot:
            if username := reply_to.from_user.username:
                tag = f"@{username}"
            else:
                tag = reply_to.from_user.mention
    if not message.from_user:
        message.from_user = await anno_checker(message)
    if not message.from_user:
        return
    if is_gdrive_link(link):
        msg = await sendMessage(message, f"Counting: <code>{link}</code>")
        startTime = time()
        gd = GoogleDriveHelper()
        result = await sync_to_async(gd.count, link)
        await deleteMessage(msg)
        cc = f'\n\n<b>#cc</b>: {tag} | <b>Elapsed</b>: {get_readable_time(time() - startTime)}'
        await sendMessage(message, result + cc)
    else:
        msg = 'Send Gdrive link along with command or by replying to the link by command'
        await sendMessage(message, msg)


bot.add_handler(MessageHandler(countNode, filters=command(BotCommands.CountCommand) & CustomFilters.authorized))