from threading import Thread

from telegram.ext import CommandHandler

from bot import LOGGER, app, dispatcher
from bot.helper.ext_utils.bot_utils import is_gdrive_link
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (auto_delete_message,
                                                      editMessage, sendMessage)


def deletefile(update, context):
    reply_to = update.message.reply_to_message
    if len(context.args) == 1:
        link = context.args[0].strip()
    elif reply_to:
        link = reply_to.text.split(maxsplit=1)[0].strip()
    else:
        link = ''
    if is_gdrive_link(link):
        LOGGER.info(link)
        drive = GoogleDriveHelper()
        msg = drive.deletefile(link)
    else:
        msg = 'Send Gdrive link along with command or by replying to the link by command'
    reply_message = sendMessage(msg, context.bot, update.message)
    Thread(target=auto_delete_message, args=(context.bot, update.message, reply_message)).start()

delete = set()

def delete_leech(update, context):
    reply_to = update.message.reply_to_message
    if len(context.args) == 1:
        link = context.args[0].strip()
    elif reply_to:
        link = reply_to.text.split(maxsplit=1)[0].strip()
    else:
        link = ''
    if not link.startswith('https://t.me/'):
        msg = 'Send telegram message link along with command or by replying to the link by command'
        return sendMessage(msg, context.bot, update.message)
    if len(delete) != 0:
        msg = 'Already deleting in progress'
        return sendMessage(msg, context.bot, update.message)
    msg = f'Okay deleting all replies with {link}'
    link = link.split('/')
    message_id = int(link[-1])
    chat_id = link[-2]
    if chat_id.isdigit():
        chat_id = f'-100{chat_id}'
        chat_id = int(chat_id)
    reply_message = sendMessage(msg, context.bot, update.message)
    Thread(target=deleting, args=(chat_id, message_id, reply_message)).start()
    

def deleting(chat_id, message_id, message):
    delete.add(message_id)
    try:
        msg = app.get_messages(chat_id, message_id, replies=-1)
        replies_ids = []
        while msg:
            replies_ids.append(msg.id)
            if msg.media_group_id:
                media_group = msg.get_media_group()
                media_ids = []
                for media in media_group:
                    media_ids.append(media.id)
                    msg = media.reply_to_message
                    if not msg:
                        msg = app.get_messages(chat_id, media.reply_to_message_id, replies=-1)
                replies_ids.extend(media_ids)
            else:
                msg = msg.reply_to_message
        replies_ids = list(set(replies_ids))
        deleted = app.delete_messages(chat_id, replies_ids)
        editMessage(f'{deleted} message deleted', message)
    except Exception as e:
        editMessage(str(e), message)
    delete.remove(message_id)

delete_handler = CommandHandler(BotCommands.DeleteCommand, deletefile,
                                filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
dispatcher.add_handler(delete_handler)

leech_delete_handler = CommandHandler(f'leech{BotCommands.DeleteCommand}', delete_leech,
                                filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
dispatcher.add_handler(leech_delete_handler)