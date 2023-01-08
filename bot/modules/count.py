from time import time

from telegram.ext import CommandHandler

from bot import dispatcher
from bot.helper.ext_utils.bot_utils import (get_readable_time, is_gdrive_link,
                                            new_thread)
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (anno_checker,
                                                      deleteMessage,
                                                      sendMessage)


@new_thread
def countNode(update, context):
    message = update.message
    if message.from_user.id in [1087968824, 136817688]:
        message.from_user.id = anno_checker(message)
        if not message.from_user.id:
            return
    reply_to = message.reply_to_message
    link = ''
    if len(context.args) == 1:
        link = context.args[0].strip()
        if message.from_user.username:
            tag = f"@{message.from_user.username}"
        else:
            tag = message.from_user.mention_html(message.from_user.first_name)
    elif reply_to:
        if len(context.args) == 0:
            link = reply_to.text.split(maxsplit=1)[0].strip()
        if reply_to.from_user.username:
            tag = f"@{reply_to.from_user.username}"
        else:
            tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)
    if is_gdrive_link(link):
        msg = sendMessage(f"Counting: <code>{link}</code>", context.bot, message)
        gd = GoogleDriveHelper()
        result = gd.count(link)
        deleteMessage(context.bot, msg)
        cc = f'\n\n<b>#cc</b>: {tag} | <b>Elapsed</b>: {get_readable_time(time() - message.date.timestamp())}'
        sendMessage(result + cc, context.bot, message)
    else:
        msg = 'Send Gdrive link along with command or by replying to the link by command'
        sendMessage(msg, context.bot, message)


count_handler = CommandHandler(BotCommands.CountCommand, countNode,
                               filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
dispatcher.add_handler(count_handler)
