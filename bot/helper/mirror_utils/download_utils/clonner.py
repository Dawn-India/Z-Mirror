from random import SystemRandom
from string import ascii_letters, digits

from bot import LOGGER, config_dict, download_dict, download_dict_lock
from bot.helper.ext_utils.bot_utils import (get_readable_file_size,
                                            sync_to_async)
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import (delete_links, deleteMessage,
                                                      sendMessage,
                                                      sendStatusMessage)


async def start_clone(link, listener):
    gd = GoogleDriveHelper(listener=listener)
    res, size, name, files = await sync_to_async(gd.helper, link)
    if res != "":
        return await listener.onDownloadError(res)
    if config_dict['STOP_DUPLICATE'] and not listener.select:
        LOGGER.info('Checking File/Folder if already in Drive...')
        smsg, button = await sync_to_async(gd.drive_list, name, True)
        if smsg:
            await delete_links(listener.message)
            msg = "File/Folder is already available in Drive.\nHere are the search results:"
            return await listener.onDownloadError(msg, button)
    if CLONE_LIMIT := config_dict['CLONE_LIMIT']:
        limit = CLONE_LIMIT * 1024**3
        if size > limit:
            await delete_links(listener.message)
            msg2 = f'Failed, Clone limit is {get_readable_file_size(limit)}.\nYour File/Folder size is {get_readable_file_size(size)}.'
            return await listener.onDownloadError(msg2)
    await listener.onDownloadStart()
    drive_id = listener.drive_id or config_dict['GDRIVE_ID']
    if files <= 20:
        msg = await sendMessage(listener.message, f"Cloning: <code>{link}</code>")
        await sync_to_async(gd.clone, link, drive_id)
        await deleteMessage(msg)
    else:
        gd.name = name
        gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
        async with download_dict_lock:
            download_dict[listener.uid] = CloneStatus(gd, size, listener, gid)
        await sendStatusMessage(listener.message)
        await sync_to_async(gd.clone, link, drive_id)
