from asyncio import sleep
from secrets import token_urlsafe

from bot import (
    LOGGER,
    aria2_options,
    aria2c_global,
    task_dict,
    task_dict_lock
)
from ...ext_utils.bot_utils import sync_to_async
from ...ext_utils.status_utils import get_readable_file_size
from ...ext_utils.task_manager import (
    check_running_tasks,
    limit_checker,
    stop_duplicate_check
)
from ...listeners.direct_listener import DirectListener
from ...task_utils.status_utils.direct_status import DirectStatus
from ...task_utils.status_utils.queue_status import QueueStatus
from ...telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    send_message,
    send_status_message
)


async def add_direct_download(listener, path):
    details = listener.link
    if not (contents := details.get("contents")):
        await listener.on_download_error("There is nothing to download!")
        return
    listener.size = details["total_size"]

    if not listener.name:
        listener.name = details["title"]
    path = f"{path}/{listener.name}"

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
    await sleep(1)
    if limit_exceeded := await limit_checker(listener):
        LOGGER.info(f"Direct Limit Exceeded: {listener.name} | {get_readable_file_size(listener.size)}")
        amsg = await send_message(
            listener.message,
            limit_exceeded
        )
        await delete_links(listener.message)
        await auto_delete_message(
            listener.message,
            amsg
        )
        return

    gid = token_urlsafe(10).replace(
        "-",
        ""
    )
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

    a2c_opt = {**aria2_options}
    [
        a2c_opt.pop(k)
        for k
        in aria2c_global
        if k in aria2_options
    ]
    if header := details.get("header"):
        a2c_opt["header"] = header
    a2c_opt["follow-torrent"] = "false"
    a2c_opt["follow-metalink"] = "false"
    directListener = DirectListener(
        path,
        listener,
        a2c_opt
    )

    async with task_dict_lock:
        task_dict[listener.mid] = DirectStatus(
            listener,
            directListener,
            gid
        )

    if add_to_queue:
        LOGGER.info(f"Start Queued Download from Direct Download: {listener.name}")
    else:
        LOGGER.info(f"Download from Direct Download: {listener.name}")
        await listener.on_download_start()
        if listener.multi <= 1:
            await send_status_message(listener.message)

    await sync_to_async(
        directListener.download,
        contents
    )
