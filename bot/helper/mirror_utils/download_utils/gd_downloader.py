from random import SystemRandom
from string import ascii_letters, digits

from bot import (LOGGER, config_dict, download_dict, download_dict_lock,
                 non_queued_dl, non_queued_up, queue_dict_lock, queued_dl)
from bot.helper.ext_utils.bot_utils import (get_readable_file_size,
                                            sync_to_async)
from bot.helper.ext_utils.fs_utils import (check_storage_threshold,
                                           get_base_name)
from bot.helper.mirror_utils.status_utils.gd_download_status import GdDownloadStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import (delete_links, sendMessage,
                                                      sendStatusMessage)


async def add_gd_download(link, path, listener, newname, from_queue=False):
    drive = GoogleDriveHelper()
    res, size, name, files = await sync_to_async(drive.helper, link)
    if res != "":
        await sendMessage(listener.message, res)
        return
    if newname:
        name = newname
    if config_dict['STOP_DUPLICATE'] and not listener.isLeech:
        LOGGER.info('Checking File/Folder if already in Drive...')
        if listener.isZip:
            gname = f"{name}.zip"
        elif listener.extract:
            try:
                gname = get_base_name(name)
            except:
                gname = None
        if gname:
            gmsg, button = await sync_to_async(drive.drive_list, gname, True)
            if gmsg:
                await delete_links(listener.message)
                msg = "File/Folder is already available in Drive.\nHere are the search results:"
                return await sendMessage(listener.message, msg, button)
    limit_exceeded = ''
    if not limit_exceeded and (GDRIVE_LIMIT:= config_dict['GDRIVE_LIMIT']):
        limit = GDRIVE_LIMIT * 1024**3
        if size > limit:
            limit_exceeded = f'Google drive limit is {get_readable_file_size(limit)}'
    if not limit_exceeded and (LEECH_LIMIT:= config_dict['LEECH_LIMIT']) and listener.isLeech:
        limit = LEECH_LIMIT * 1024**3
        if size > limit:
            limit_exceeded = f'Leech limit is {get_readable_file_size(limit)}'
    if not limit_exceeded and (STORAGE_THRESHOLD:= config_dict['STORAGE_THRESHOLD']):
        limit = STORAGE_THRESHOLD * 1024**3
        arch = any([listener.extract, listener.isZip])
        acpt = await sync_to_async(check_storage_threshold, size, limit, arch)
        if not acpt:
            limit_exceeded = f'You must leave {get_readable_file_size(limit)} free storage.'
    if limit_exceeded:
        await delete_links(listener.message)
        return await sendMessage(listener.message, f'{limit_exceeded}.\nYour File/Folder size is {get_readable_file_size(size)}.')
    gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
    all_limit = config_dict['QUEUE_ALL']
    dl_limit = config_dict['QUEUE_DOWNLOAD']
    if all_limit or dl_limit:
        added_to_queue = False
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            if (all_limit and dl + up >= all_limit and (not dl_limit or dl >= dl_limit)) or (dl_limit and dl >= dl_limit):
                added_to_queue = True
                queued_dl[listener.uid] = ['gd', link, path, listener, newname]
        if added_to_queue:
            LOGGER.info(f"Added to Queue/Download: {name}")
            async with download_dict_lock:
                download_dict[listener.uid] = QueueStatus(name, size, gid, listener, 'Dl')
            await listener.onDownloadStart()
            await sendStatusMessage(listener.message)
            return
    drive = GoogleDriveHelper(name, path, size, listener)
    async with download_dict_lock:
        download_dict[listener.uid] = GdDownloadStatus(drive, size, listener, gid)
    async with queue_dict_lock:
        non_queued_dl.add(listener.uid)
    if not from_queue:
        LOGGER.info(f"Download from GDrive: {name}")
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
    else:
        LOGGER.info(f'Start Queued Download from GDrive: {name}')
    await sync_to_async(drive.download, link)