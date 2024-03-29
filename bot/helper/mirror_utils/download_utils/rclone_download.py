#!/usr/bin/env python3
from asyncio import gather
from json import loads
from secrets import token_urlsafe

from bot import (LOGGER, download_dict, download_dict_lock, non_queued_dl,
                 queue_dict_lock)
from bot.helper.ext_utils.bot_utils import cmd_exec
from bot.helper.ext_utils.task_manager import is_queued, stop_duplicate_check, limit_checker
from bot.helper.mirror_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.telegram_helper.message_utils import (sendMessage, delete_links,
                                                      sendStatusMessage, auto_delete_message)


async def add_rclone_download(rc_path, config_path, path, name, listener):
    remote, rc_path = rc_path.split(':', 1)
    rc_path = rc_path.strip('/')

    cmd1 = f'rclone lsjson --fast-list --stat --no-mimetype --no-modtime --config {config_path} "{remote}:{rc_path}"'
    cmd2 = f'rclone size --fast-list --json --config {config_path} "{remote}:{rc_path}"'
    res1, res2 = await gather(cmd_exec(cmd1, shell=True), cmd_exec(cmd2, shell=True))
    if res1[2] != res2[2] != 0:
        if res1[2] != -9:
            err = res1[1] or res2[1]
            msg = f'Error: While getting rclone stat/size. Path: {remote}:{rc_path}. Stderr: {err[:4000]}'
            rmsg = await sendMessage(listener.message, msg)
            await delete_links(listener.message)
            await auto_delete_message(listener.message, rmsg)
        return
    try:
        rstat = loads(res1[0])
        rsize = loads(res2[0])
    except Exception as err:
        rmsg = await sendMessage(listener.message, f'RcloneDownload JsonLoad: {err}')
        await delete_links(listener.message)
        await auto_delete_message(listener.message, rmsg)
        return
    if rstat['IsDir']:
        if not name:
            name = rc_path.rsplit('/', 1)[-1] if rc_path else remote
        path += name
    else:
        name = rc_path.rsplit('/', 1)[-1]
    size = rsize['bytes']
    gid = token_urlsafe(6)
    gid = gid.replace('-', '')

    msg, button = await stop_duplicate_check(name, listener)
    if msg:
        rmsg = await sendMessage(listener.message, msg, button)
        await delete_links(listener.message)
        await auto_delete_message(listener.message, rmsg)
        return
    if limit_exceeded := await limit_checker(size, listener, isRclone=True):
        rmsg = await sendMessage(listener.message, limit_exceeded)
        await delete_links(listener.message)
        await auto_delete_message(listener.message, rmsg)
        return

    added_to_queue, event = await is_queued(listener.uid)
    if added_to_queue:
        LOGGER.info(f"Added to Queue/Download: {name}")
        async with download_dict_lock:
            download_dict[listener.uid] = QueueStatus(name, size, gid, listener, 'dl')
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
        await event.wait()
        async with download_dict_lock:
            if listener.uid not in download_dict:
                return
        from_queue = True
    else:
        from_queue = False

    RCTransfer = RcloneTransferHelper(listener, name)
    async with download_dict_lock:
        download_dict[listener.uid] = RcloneStatus(RCTransfer, listener.message, gid, 'dl', listener.extra_details)
    async with queue_dict_lock:
        non_queued_dl.add(listener.uid)

    if from_queue:
        LOGGER.info(f'Start Queued Download with rclone: {rc_path}')
    else:
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
        LOGGER.info(f"Download with rclone: {rc_path}")

    await RCTransfer.download(remote, rc_path, config_path, path)
