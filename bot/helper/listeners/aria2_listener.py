from aiofiles.os import (
    remove,
    path as aiopath
)
from asyncio import sleep
from time import time

from bot import (
    aria2,
    config_dict,
    Intervals,
    LOGGER,
    task_dict_lock,
    task_dict,
)
from bot.helper.ext_utils.bot_utils import (
    new_thread,
    bt_selection_buttons,
    sync_to_async,
)
from bot.helper.ext_utils.files_utils import clean_unwanted
from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,
    getTaskByGid
)
from bot.helper.ext_utils.task_manager import (
    limit_checker,
    stop_duplicate_check,
    check_avg_speed
)
from bot.helper.task_utils.status_utils.aria2_status import Aria2Status
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    sendMessage,
    deleteMessage,
    update_status_message,
)


@new_thread
async def _onDownloadStarted(api, gid):
    download = await sync_to_async(
        api.get_download,
        gid
    )
    if download.options.follow_torrent == "false":
        return
    if download.is_metadata:
        LOGGER.info(f"onDownloadStarted: {gid} METADATA")
        await sleep(1)
        if task := await getTaskByGid(gid):
            task.listener.isTorrent = True
            if task.listener.select:
                metamsg = "Downloading Metadata, wait then you can select files. Use torrent file to avoid this wait."
                meta = await sendMessage(
                    task.listener.message,
                    metamsg
                )
                while True:
                    await sleep(0.5)
                    if download.is_removed or download.followed_by_ids:
                        await deleteMessage(meta)
                        break
                    await sync_to_async(download.update)
        return
    else:
        LOGGER.info(f"onAria2DownloadStarted: {download.name} - Gid: {gid}")
        await sleep(1)

    if task := await getTaskByGid(gid):
        download = await sync_to_async(
            api.get_download,
            gid
        )
        await sleep(2)
        await sync_to_async(download.update)
        task.listener.name = download.name
        task.listener.isTorrent = download.is_torrent
        msg, button = await stop_duplicate_check(task.listener)
        if msg:
            await task.listener.onDownloadError(
                msg,
                button
            )
            await sync_to_async(
                api.remove,
                [download],
                force=True,
                files=True
            )
            return
        if download.total_length == 0:
            start_time = time()
            while time() - start_time <= 15:
                await sleep(5)
                download = await sync_to_async(
                    api.get_download,
                    gid
                )
                await sync_to_async(download.update)
                if download.followed_by_ids:
                    download = await sync_to_async(
                        api.get_download,
                        download.followed_by_ids[0]
                    )
                    await sync_to_async(download.update)
                if download.total_length > 0:
                    break
        task.listener.size = download.total_length
        if not task.listener.select:
            if limit_exceeded := await limit_checker(task.listener):
                LOGGER.info(f"Aria2 Limit Exceeded: {task.listener.name} | {get_readable_file_size(task.listener.size)}")
                amsg = await task.listener.onDownloadError(limit_exceeded)
                await sync_to_async(
                    api.remove,
                    [download],
                    force=True,
                    files=True
                )
                await delete_links(task.listener.message)
                await auto_delete_message(
                    task.listener.message,
                    amsg
                )
        if config_dict["AVG_SPEED"]:
            start_time = time()
            total_speed = 0
            count = 0
            while time() - start_time < 1800:
                await sync_to_async(download.update)
                dl_speed = download.download_speed
                total_speed += dl_speed
                count += 1
                await sleep(10)
            if min_speed := await check_avg_speed(
                total_speed,
                count
            ):
                LOGGER.info(
                    f"Task is slower than minimum download speed: {task.listener.name} | {get_readable_file_size(dl_speed)}ps"
                )
                smsg = await task.listener.onDownloadError(min_speed)
                await sync_to_async(
                    api.remove,
                    [download],
                    force=True,
                    files=True
                )
                await delete_links(task.listener.message)
                await auto_delete_message(
                    task.listener.message,
                    smsg
                )


@new_thread
async def _onDownloadComplete(api, gid):
    try:
        download = await sync_to_async(
            api.get_download,
            gid
        )
    except:
        return
    if download.options.follow_torrent == "false":
        return
    if download.followed_by_ids:
        new_gid = download.followed_by_ids[0]
        LOGGER.info(f"Gid changed from {gid} to {new_gid}")
        if task := await getTaskByGid(new_gid):
            task.listener.isTorrent = True
            if (
                config_dict["BASE_URL"]
                and task.listener.select
            ):
                if not task.queued:
                    await sync_to_async(
                        api.client.force_pause,
                        new_gid
                    )
                SBUTTONS = bt_selection_buttons(new_gid)
                msg = "Your download paused. Choose files then press Done Selecting button to start downloading."
                await sendMessage(
                    task.listener.message,
                    msg,
                    SBUTTONS
                )
    elif download.is_torrent:
        if task := await getTaskByGid(gid):
            task.listener.isTorrent = True
            if hasattr(
                task,
                "seeding"
            ) and task.seeding:
                LOGGER.info(f"Cancelling Seed: {download.name} onDownloadComplete")
                await task.listener.onUploadError(
                    f"Seeding stopped with Ratio: {task.ratio()} and Time: {task.seeding_time()}"
                )
                await sync_to_async(
                    api.remove,
                    [download],
                    force=True,
                    files=True
                )
    else:
        LOGGER.info(f"onDownloadComplete: {download.name} - Gid: {gid}")
        if task := await getTaskByGid(gid):
            await task.listener.onDownloadComplete()
            if Intervals["stopAll"]:
                return
            await sync_to_async(
                api.remove,
                [download],
                force=True,
                files=True
            )

@new_thread
async def _onBtDownloadComplete(api, gid):
    seed_start_time = time()
    await sleep(1)
    download = await sync_to_async(
        api.get_download,
        gid
    )
    LOGGER.info(f"onBtDownloadComplete: {download.name} - Gid: {gid}")
    if task := await getTaskByGid(gid):
        task.listener.isTorrent = True
        if task.listener.select:
            res = download.files
            for file_o in res:
                f_path = file_o.path
                if (
                    not file_o.selected
                    and await aiopath.exists(f_path)
                ):
                    try:
                        await remove(f_path)
                    except:
                        pass
            await clean_unwanted(download.dir)
        if task.listener.seed:
            try:
                await sync_to_async(
                    api.set_options,
                    {"max-upload-limit": "0"},
                    [download]
                )
            except Exception as e:
                LOGGER.error(
                    f"{e} You are not able to seed because you added global option seed-time=0 without adding specific seed_time for this torrent GID: {gid}"
                )
        else:
            try:
                await sync_to_async(
                    api.client.force_pause,
                    gid
                )
            except Exception as e:
                LOGGER.error(f"{e} GID: {gid}")
        await task.listener.onDownloadComplete()
        if Intervals["stopAll"]:
            return
        await sync_to_async(download.update)
        if task.listener.seed:
            if download.is_complete:
                if await getTaskByGid(gid):
                    LOGGER.info(f"Cancelling Seed: {download.name}")
                    await task.listener.onUploadError(
                        f"Seeding stopped with Ratio: {task.ratio()} and Time: {task.seeding_time()}"
                    )
                    await sync_to_async(
                        api.remove,
                        [download],
                        force=True,
                        files=True
                    )
            elif not task.listener.isCancelled:
                async with task_dict_lock:
                    if task.listener.mid not in task_dict:
                        await sync_to_async(
                            api.remove,
                            [download],
                            force=True,
                            files=True
                        )
                        return
                    task_dict[task.listener.mid] = Aria2Status(
                        task.listener,
                        gid,
                        True
                    )
                    task_dict[task.listener.mid].start_time = seed_start_time
                LOGGER.info(f"Seeding started: {download.name} - Gid: {gid}")
                await update_status_message(task.listener.message.chat.id)
            else:
                await sync_to_async(
                    api.remove,
                    [download],
                    force=True,
                    files=True
                )
        else:
            await sync_to_async(
                api.remove,
                [download],
                force=True,
                files=True
            )


@new_thread
async def _onDownloadStopped(api, gid):
    await sleep(4)
    if task := await getTaskByGid(gid):
        await task.listener.onDownloadError("Dead torrent!")


@new_thread
async def _onDownloadError(api, gid):
    LOGGER.info(f"onDownloadError: {gid}")
    error = "None"
    try:
        download = await sync_to_async(
            api.get_download,
            gid
        )
        if download.options.follow_torrent == "false":
            return
        error = download.error_message
        LOGGER.info(f"Download Error: {error}")
    except:
        pass
    if task := await getTaskByGid(gid):
        await task.listener.onDownloadError(error)


def start_aria2_listener():
    aria2.listen_to_notifications(
        threaded=False,
        on_download_start=_onDownloadStarted,
        on_download_error=_onDownloadError,
        on_download_stop=_onDownloadStopped,
        on_download_complete=_onDownloadComplete,
        on_bt_download_complete=_onBtDownloadComplete,
        timeout=60,
    )
