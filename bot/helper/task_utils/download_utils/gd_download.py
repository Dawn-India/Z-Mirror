from secrets import token_urlsafe

from bot import (
    LOGGER,
    non_queued_dl,
    queue_dict_lock,
    task_dict,
    task_dict_lock,
)
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.ext_utils.task_manager import (
    check_running_tasks,
    limit_checker,
    stop_duplicate_check
)
from bot.helper.task_utils.gdrive_utils.count import gdCount
from bot.helper.task_utils.gdrive_utils.download import gdDownload
from bot.helper.task_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.task_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    sendMessage,
    sendStatusMessage
)


async def add_gd_download(listener, path):
    drive = gdCount()
    (
        name,
        mime_type,
        listener.size,
        _,
        _
    ) = await sync_to_async(
        drive.count,
        listener.link,
        listener.userId
    )
    if mime_type is None:
        await listener.onDownloadError(name)
        return

    listener.name = listener.name or name
    gid = token_urlsafe(12)

    (
        msg,
        button
    ) = await stop_duplicate_check(listener)
    if msg:
        await listener.onDownloadError(
            msg,
            button
        )
        return
    if limit_exceeded := await limit_checker(
        listener,
        isDriveLink=True
    ):
        LOGGER.info(f"GDrive Limit Exceeded: {listener.name} | {get_readable_file_size(listener.size)}")
        gmsg = await sendMessage(
            listener.message,
            limit_exceeded
        )
        await delete_links(listener.message)
        await auto_delete_message(
            listener.message,
            gmsg
        )
        return

    (
        add_to_queue,
        event
    ) = await check_running_tasks(listener)
    if add_to_queue:
        LOGGER.info(f"Added to Queue/Download: {listener.name}")
        async with task_dict_lock:
            task_dict[listener.mid] = QueueStatus(
                listener,
                gid,
                "dl"
            )
        await listener.onDownloadStart()
        if listener.multi <= 1:
            await sendStatusMessage(listener.message)
        await event.wait() # type: ignore
        if listener.isCancelled:
            return
        async with queue_dict_lock:
            non_queued_dl.add(listener.mid)

    drive = gdDownload(
        listener,
        path
    )
    async with task_dict_lock:
        task_dict[listener.mid] = GdriveStatus(
            listener,
            drive,
            gid,
            "dl",
        )

    if add_to_queue:
        LOGGER.info(f"Start Queued Download from GDrive: {listener.name}")
    else:
        LOGGER.info(f"Download from GDrive: {listener.name}")
        await listener.onDownloadStart()
        if listener.multi <= 1:
            await sendStatusMessage(listener.message)

    await sync_to_async(drive.download)
