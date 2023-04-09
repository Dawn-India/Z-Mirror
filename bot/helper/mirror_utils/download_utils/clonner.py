from random import SystemRandom
from string import ascii_letters, digits

from bot import config_dict, download_dict, download_dict_lock
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.task_manager import (limit_checker,
                                               stop_duplicate_check)
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
        smsg, button = await stop_duplicate_check(name, listener)
        if smsg:
            await sendMessage(listener.message, smsg, button)
            await delete_links(listener.message)
            return
    if limit_exceeded := await limit_checker(size, listener):
        await sendMessage(listener.message, limit_exceeded)
        await delete_links(listener.message)
        return
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
            download_dict[listener.uid] = CloneStatus(gd, size, listener.message, gid, listener.extra_details)
        await sendStatusMessage(listener.message)
        await sync_to_async(gd.clone, link, drive_id)
