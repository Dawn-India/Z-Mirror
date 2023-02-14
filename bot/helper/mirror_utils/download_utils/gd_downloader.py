from random import SystemRandom
from string import ascii_letters, digits

from bot import (LOGGER, config_dict, download_dict, download_dict_lock,
                 non_queued_dl, non_queued_up, queue_dict_lock, queued_dl)
from bot.helper.ext_utils.bot_utils import get_readable_file_size
from bot.helper.ext_utils.fs_utils import (check_storage_threshold,
                                           get_base_name)
from bot.helper.mirror_utils.status_utils.gd_download_status import GdDownloadStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import (sendMessage, delete_links,
                                                      sendStatusMessage)


def add_gd_download(link, path, listener, newname, from_queue=False):
    drive = GoogleDriveHelper()
    res, size, name, _ = drive.helper(link)
    if res != "":
        return sendMessage(res, listener.bot, listener.message)
    if newname:
        name = newname
    if not listener.isLeech and config_dict['STOP_DUPLICATE'] and not listener.select:
        LOGGER.info('Checking File/Folder if already in Drive...')
        if listener.isZip:
            gname = f"{name}.zip"
        elif listener.extract:
            try:
                gname = get_base_name(name)
            except:
                gname = None
        if gname:
            gmsg, button = GoogleDriveHelper().drive_list(gname, True)
            if gmsg:
                delete_links(listener.bot, listener.message)
                msg = "File/Folder is already available in Drive.\nHere are the search results:"
                return sendMessage(msg, listener.bot, listener.message, button)
    limit_exceeded = ''
    if not limit_exceeded and (STORAGE_THRESHOLD:= config_dict['STORAGE_THRESHOLD']):
        limit = STORAGE_THRESHOLD * 1024**3
        arch = any([listener.extract, listener.isZip])
        acpt = check_storage_threshold(size, limit, arch)
        if not acpt:
            limit_exceeded = f'You must leave {get_readable_file_size(limit)} free storage.'
    if not limit_exceeded and (GDRIVE_LIMIT:= config_dict['GDRIVE_LIMIT']):
        limit = GDRIVE_LIMIT * 1024**3
        if size > limit:
            limit_exceeded = f'Google drive limit is {get_readable_file_size(limit)}'
    if not limit_exceeded and (LEECH_LIMIT:= config_dict['LEECH_LIMIT']) and listener.isLeech:
        limit = LEECH_LIMIT * 1024**3
        if size > limit:
            limit_exceeded = f'Leech limit is {get_readable_file_size(limit)}'
    if limit_exceeded:
        return sendMessage(f'{limit_exceeded}.\nYour File/Folder size is {get_readable_file_size(size)}.', listener.bot, listener.message)
    gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
    all_limit = config_dict['QUEUE_ALL']
    dl_limit = config_dict['QUEUE_DOWNLOAD']
    if all_limit or dl_limit:
        added_to_queue = False
        with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            if (all_limit and dl + up >= all_limit and (not dl_limit or dl >= dl_limit)) or (dl_limit and dl >= dl_limit):
                added_to_queue = True
                queued_dl[listener.uid] = ['gd', link, path, listener, newname]
        if added_to_queue:
            LOGGER.info(f"Added to Queue/Download: {name}")
            with download_dict_lock:
                download_dict[listener.uid] = QueueStatus(name, size, gid, listener, 'Dl')
            listener.onDownloadStart()
            sendStatusMessage(listener.message, listener.bot)
            return
    drive = GoogleDriveHelper(name, path, size, listener)
    with download_dict_lock:
        download_dict[listener.uid] = GdDownloadStatus(drive, size, listener, gid)
    with queue_dict_lock:
        non_queued_dl.add(listener.uid)
    if not from_queue:
        LOGGER.info(f"Download from GDrive: {name}")
        listener.onDownloadStart()
        sendStatusMessage(listener.message, listener.bot)
    else:
        LOGGER.info(f'Start Queued Download from GDrive: {name}')
    drive.download(link)
