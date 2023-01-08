from telegram.ext import CommandHandler

from bot import DATABASE_URL, config_dict, dispatcher
from bot.helper.ext_utils.bot_utils import is_magnet, is_url, new_thread
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.z_utils import extract_link
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage


def _rmdb(message, bot):
    mesg = message.text.split('\n')
    message_args = mesg[0].split(' ', maxsplit=1)
    tfile = False
    file = None
    try:
        link = message_args[1]
    except IndexError:
        link = ''
    tag = None
    reply_to = message.reply_to_message
    if reply_to:
        media_array = [reply_to.document, reply_to.video, reply_to.audio]
        file = next((i for i in media_array if i), None)
        if not reply_to.from_user.is_bot:
            if reply_to.from_user.username:
                tag = f"@{reply_to.from_user.username}"
            else:
                tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)

        if not is_url(link) and not is_magnet(link) and not link:
            if file is None:
                if is_url(reply_to.text) or is_magnet(reply_to.text):
                    link = reply_to.text.strip()
                else:
                    mesg = message.text.split('\n')
                    message_args = mesg[0].split(' ', maxsplit=1)
                    try:
                        link = message_args[1]
                    except IndexError:
                        pass
            elif file.mime_type != "application/x-bittorrent":
                link = file.file_unique_id
            else:
                link = file.get_file().download_url
                tfile = True

    if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS']:
        raw_url = extract_link(link, tfile)
        exist = DbManger().check_download(raw_url)
        if exist:
            DbManger().remove_download(exist['_id'])
            msg = 'Download is removed from database successfully'
            msg += f'\n{exist["tag"]} Your download is removed.'
        else:
            msg = 'This download is not exists in database'
    else:
        msg = 'STOP_DUPLICATE_TASKS feature is not enabled'
    return sendMessage(msg, bot, message)

@new_thread
def rmdbNode(update, context):
    _rmdb(update.message, context.bot)

if DATABASE_URL:
    rmdb_handler = CommandHandler(command=BotCommands.RmdbCommand, callback=rmdbNode, filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
    dispatcher.add_handler(rmdb_handler)
