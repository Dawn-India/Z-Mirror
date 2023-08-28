#!/usr/bin/env python3
from hashlib import sha1
from os import path, remove
from re import search

from bencoding import bdecode, bencode

from bot import DATABASE_URL, LOGGER, config_dict
from bot.helper.ext_utils.bot_utils import (check_user_tasks, checking_access,
                                            is_gdrive_link, is_magnet)
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import (delete_links, forcesub,
                                                      auto_delete_message,
                                                      message_filter,
                                                      sendMessage)


async def extract_link(link, shouldDel=False):
    try:
        if link and is_magnet(link):
            raw_link = search(r'(?<=xt=urn:(btih|btmh):)[a-zA-Z0-9]+', link).group(0).lower()
        elif is_gdrive_link(link):
            raw_link = GoogleDriveHelper.getIdFromUrl(link)
        elif path.exists(link):
            with open(link, "rb") as f:
                decodedDict = bdecode(f.read())
            raw_link = str(sha1(bencode(decodedDict[b'info'])).hexdigest())
            if shouldDel:
                remove(link)
        else:
            raw_link = link
    except Exception as e:
        LOGGER.error(e)
        raw_link = link
    return raw_link


async def stop_duplicate_tasks(message, link, file_=None):
    if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS']:
        raw_url = file_.file_unique_id if file_ else await extract_link(link)
        exist = await DbManager().check_download(raw_url)
        if exist:
            _msg = f'<b>Download is already added by {exist["tag"]}</b>\n'
            _msg += f'Check the download status in @{exist["botname"]}\n\n'
            _msg += f'<b>Link</b>: <code>{exist["_id"]}</code>'
            reply_message = await sendMessage(message, _msg)
            await auto_delete_message(message, reply_message)
            await delete_links(message)
            return 'duplicate_tasks'
        return raw_url


async def none_admin_utils(message, isLeech=False):
    msg = []
    if isLeech and config_dict['DISABLE_LEECH']:
        msg.append('Leech is disabled on this bot.\n💡Use other bots;)')
    if filtered := await message_filter(message):
        msg.append(filtered)
    if (maxtask := config_dict['USER_MAX_TASKS']) and await check_user_tasks(message.from_user.id, maxtask):
        msg.append(f"Your tasks limit exceeded!\n💡Use other bots.\n\nTasks limit: {maxtask}")
    button = None
    if message.chat.type != message.chat.type.PRIVATE:
        token_msg, button = await checking_access(message.from_user.id, button)
        if token_msg is not None:
            msg.append(token_msg)
        if ids := config_dict['FSUB_IDS']:
            _msg, button = await forcesub(message, ids, button)
            if _msg:
                msg.append(_msg)
    await delete_links(message)
    return msg, button
