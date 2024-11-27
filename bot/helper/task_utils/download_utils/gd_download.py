from secrets import token_urlsafe

from bot import (
    LOGGER,
    task_dict,
    task_dict_lock,
)
from ...ext_utils.bot_utils import sync_to_async
from ...ext_utils.status_utils import get_readable_file_size
from ...ext_utils.task_manager import (
    check_running_tasks,
    limit_checker,
    stop_duplicate_check
)
from ...task_utils.gdrive_utils.count import GoogleDriveCount
from ...task_utils.gdrive_utils.download import GoogleDriveDownload
from ...task_utils.status_utils.gdrive_status import GoogleDriveStatus
from ...task_utils.status_utils.queue_status import QueueStatus
from ...telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    send_message,
    send_status_message
)


async def add_gd_download(listener, path):
    drive = GoogleDriveCount()
    (
        name,
        mime_type,
        listener.size,
        _,
        _
    ) = await sync_to_async(
        drive.count,
        listener.link,
        listener.user_id
    )
    if mime_type is None:
        await listener.on_download_error(name)
        return

    listener.name = listener.name or name
    gid = token_urlsafe(12).replace(
        "-",
        ""
    )

    (
        msg,
        button
    ) = await stop_duplicate_check(listener)
    if msg:
        await listener.on_download_error(
            msg,
            button
        )
        return
    if limit_exceeded := await limit_checker(
        listener,
        is_drive_link=True
    ):
        LOGGER.info(f"GDrive Limit Exceeded: {listener.name} | {get_readable_file_size(listener.size)}")
        gmsg = await send_message(
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
        await listener.on_download_start()
        if listener.multi <= 1:
            await send_status_message(listener.message)
        await event.wait() # type: ignore
        if listener.is_cancelled:
            return

    drive = GoogleDriveDownload(
        listener,
        path
    )
    async with task_dict_lock:
        task_dict[listener.mid] = GoogleDriveStatus(
            listener,
            drive,
            gid,
            "dl",
        )

    if add_to_queue:
        LOGGER.info(f"Start Queued Download from GDrive: {listener.name}")
    else:
        LOGGER.info(f"Download from GDrive: {listener.name}")
        await listener.on_download_start()
        if listener.multi <= 1:
            await send_status_message(listener.message)

    await sync_to_async(drive.download)
