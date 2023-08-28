#!/usr/bin/env python3
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import DATABASE_URL, bot, config_dict
from bot.helper.ext_utils.bot_utils import is_magnet, is_url, new_task
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.z_utils import extract_link
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage


@new_task
async def rmAllTokens(_, message):
    if DATABASE_URL:
        await DbManager().delete_all_access_tokens()
        msg = 'All access tokens have been removed from the database.'
    else:
        msg = 'Database URL not added.'
    return await sendMessage(message, msg)


@new_task
async def rmdbNode(_, message):
    if DATABASE_URL and not config_dict['STOP_DUPLICATE_TASKS']:
        return await sendMessage(message, 'STOP_DUPLICATE_TASKS feature is not enabled')
    mesg = message.text.split('\n')
    message_args = mesg[0].split(' ', maxsplit=1)
    file = None
    shouldDel = False
    try:
        link = message_args[1]
    except IndexError:
        link = ''
    if reply_to := message.reply_to_message:
        media_array = [reply_to.document, reply_to.photo, reply_to.video, reply_to.audio, reply_to.voice, reply_to.video_note, reply_to.sticker, reply_to.animation]
        file = next((i for i in media_array if i), None)
        if not is_url(link) and not is_magnet(link) and not link:
            if not file:
                if is_url(reply_to.text) or is_magnet(reply_to.text):
                    link = reply_to.text.strip()
                else:
                    mesg = message.text.split('\n')
                    message_args = mesg[0].split(' ', maxsplit=1)
                    try:
                        link = message_args[1]
                    except IndexError:
                        pass
            elif file.mime_type == 'application/x-bittorrent':
                link = await reply_to.download()
                shouldDel = True
            else:
                link = file.file_unique_id
    if not link:
        msg = 'Something went wrong!!'
        return await sendMessage(message, msg)
    raw_url = await extract_link(link, shouldDel)
    if exist := await DbManager().check_download(raw_url):
        await DbManager().remove_download(exist['_id'])
        msg = 'Download is removed from database successfully'
        msg += f'\n{exist["tag"]} Your download is removed.'
    else:
        msg = 'This download is not exists in database'
    return await sendMessage(message, msg)


if DATABASE_URL:
    bot.add_handler(MessageHandler(rmdbNode, filters=command(BotCommands.RmdbCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(rmAllTokens, filters=command(BotCommands.RmalltokensCommand) & CustomFilters.sudo))
