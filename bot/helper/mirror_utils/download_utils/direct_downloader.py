#!/usr/bin/env python3
from asyncio import sleep
from secrets import token_urlsafe

from bot import (config_dict, LOGGER, aria2_options, aria2c_global, download_dict,
                 download_dict_lock, non_queued_dl, queue_dict_lock)
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.task_manager import is_queued, stop_duplicate_check, limit_checker
from bot.helper.listeners.direct_listener import DirectListener
from bot.helper.mirror_utils.status_utils.direct_status import DirectStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import (delete_links, sendMessage,
                                                      sendStatusMessage,
                                                      auto_delete_message)


async def add_direct_download(details, path, listener, foldername):
    if not (contents:= details.get('contents')):
        await sendMessage(listener.message, 'There is nothing to download!')
        return
    size = details['total_size']

    if not foldername:
        foldername = details['title']
    path = f'{path}/{foldername}'
    if config_dict['STOP_DUPLICATE']:
        msg, button = await stop_duplicate_check(foldername, listener)
        if msg:
            dmsg = await sendMessage(listener.message, msg, button)
            await delete_links(listener.message)
            await auto_delete_message(listener.message, dmsg)
            return
    if any([config_dict['DIRECT_LIMIT'],
            config_dict['LEECH_LIMIT'],
            config_dict['STORAGE_THRESHOLD']]):
        await sleep(1)
        if limit_exceeded := await limit_checker(size, listener):
            LOGGER.info(f"Limit Exceeded: {foldername} | {size}")
            amsg = await sendMessage(listener.message, limit_exceeded)
            await delete_links(listener.message)
            await auto_delete_message(listener.message, amsg)
            return

    gid = token_urlsafe(6)
    gid = gid.replace('-', '')
    added_to_queue, event = await is_queued(listener.uid)
    if added_to_queue:
        LOGGER.info(f"Added to Queue/Download: {foldername}")
        async with download_dict_lock:
            download_dict[listener.uid] = QueueStatus(foldername, size, gid, listener, 'dl')
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
        await event.wait()
        async with download_dict_lock:
            if listener.uid not in download_dict:
                return
        from_queue = True
    else:
        from_queue = False
    
    a2c_opt = {**aria2_options}
    [a2c_opt.pop(k) for k in aria2c_global if k in aria2_options]
    if header:= details.get('header'):
        a2c_opt['header'] = header
    a2c_opt['follow-torrent'] = 'false'
    a2c_opt['follow-metalink'] = 'false'
    directListener = DirectListener(foldername, size, path, listener, a2c_opt)
    async with download_dict_lock:
        download_dict[listener.uid] = DirectStatus(directListener, gid, listener)

    async with queue_dict_lock:
        non_queued_dl.add(listener.uid)

    if from_queue:
        LOGGER.info(f'Start Queued Download from Direct Download: {foldername}')
    else:
        LOGGER.info(f"Download from Direct Download: {foldername}")
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)

    await sync_to_async(directListener.download, contents)
