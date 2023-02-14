from random import SystemRandom
from string import ascii_letters, digits

from bot import LOGGER, config_dict, download_dict, download_dict_lock
from bot.helper.ext_utils.bot_utils import get_readable_file_size
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import (deleteMessage, delete_links,
                                                      sendMessage,
                                                      sendStatusMessage)


def start_clone(link, listener):
    gd = GoogleDriveHelper(listener=listener)
    res, size, name, files = gd.helper(link)
    if res != "":
        return listener.onDownloadError(res)
    if config_dict['STOP_DUPLICATE'] and not listener.select:
        LOGGER.info('Checking File/Folder if already in Drive...')
        smsg, button = gd.drive_list(name, True)
        if smsg:
            delete_links(listener.bot, listener.message)
            msg = "File/Folder is already available in Drive.\nHere are the search results:"
            return listener.onDownloadError(msg, button)
    if CLONE_LIMIT := config_dict['CLONE_LIMIT']:
        limit = CLONE_LIMIT * 1024**3
        if size > limit:
            msg2 = f'Failed, Clone limit is {get_readable_file_size(limit)}.\nYour File/Folder size is {get_readable_file_size(size)}.'
            return listener.onDownloadError(msg2)
    listener.onDownloadStart()
    if files <= 20:
        msg = sendMessage(f"Cloning: <code>{link}</code>", listener.bot, listener.message)
        gd.clone(link, listener.drive_id or config_dict['GDRIVE_ID'])
        deleteMessage(listener.bot, msg)
    else:
        gd.name = name
        gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
        clone_status = CloneStatus(gd, size, listener, gid)
        with download_dict_lock:
            download_dict[listener.uid] = clone_status
        sendStatusMessage(listener.message, listener.bot)
        gd.clone(link, listener.drive_id or config_dict['GDRIVE_ID'])
