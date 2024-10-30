from aiofiles.os import (
    remove,
    path as aiopath
)
from asyncio import sleep
from time import time

from bot import (
    LOGGER,
    aria2,
    config_dict,
    intervals,
    task_dict_lock,
    task_dict,
)
from ..ext_utils.bot_utils import (
    bt_selection_buttons,
    loop_thread,
    sync_to_async,
)
from ..ext_utils.files_utils import clean_unwanted
from ..ext_utils.status_utils import (
    get_readable_file_size,
    get_task_by_gid
)
from ..ext_utils.task_manager import (
    limit_checker,
    stop_duplicate_check,
    check_avg_speed
)
from ..task_utils.status_utils.aria2_status import Aria2Status
from ..telegram_helper.message_utils import (
    delete_message,
    send_message,
    update_status_message,
)


@loop_thread
async def _on_download_started(api, gid):
    download = await sync_to_async(
        api.get_download,
        gid
    )
    if download.options.follow_torrent == "false":
        return
    if download.is_metadata:
        LOGGER.info(f"onDownloadStarted: {gid} METADATA")
        await sleep(1)
        if task := await get_task_by_gid(gid):
            task.listener.is_torrent = True
            if task.listener.select:
                metamsg = "Downloading Metadata, wait then you can select files. Use torrent file to avoid this wait."
                meta = await send_message(
                    task.listener.message,
                    metamsg
                )
                while True:
                    await sleep(0.5)
                    if download.is_removed or download.followed_by_ids:
                        await delete_message(meta)
                        break
                    await sync_to_async(download.update)
        return
    else:
        LOGGER.info(f"onAria2DownloadStarted: {download.name} - Gid: {gid}")
        await sleep(1)

    await sleep(2)
    if task := await get_task_by_gid(gid):
        download = await sync_to_async(
            api.get_download,
            gid
        )
        await sync_to_async(download.update)
        task.listener.name = download.name
        task.listener.is_torrent = download.is_torrent
        (
            msg,
            button
        ) = await stop_duplicate_check(task.listener)
        if msg:
            await task.listener.on_download_error(
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
                await task.listener.on_download_error(limit_exceeded)
                await sync_to_async(
                    api.remove,
                    [download],
                    force=True,
                    files=True
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
                await task.listener.on_download_error(min_speed)
                await sync_to_async(
                    api.remove,
                    [download],
                    force=True,
                    files=True
                )


@loop_thread
async def _on_download_complete(api, gid):
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
        if task := await get_task_by_gid(new_gid):
            task.listener.is_torrent = True
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
                await send_message(
                    task.listener.message,
                    msg,
                    SBUTTONS
                )
    elif download.is_torrent:
        if task := await get_task_by_gid(gid):
            task.listener.is_torrent = True
            if hasattr(
                task,
                "seeding"
            ) and task.seeding:
                LOGGER.info(f"Cancelling Seed: {download.name} on_download_complete")
                await task.listener.on_upload_error(
                    f"Seeding stopped with Ratio: {task.ratio()} and Time: {task.seeding_time()}"
                )
                await sync_to_async(
                    api.remove,
                    [download],
                    force=True,
                    files=True
                )
    else:
        LOGGER.info(f"on_download_complete: {download.name} - Gid: {gid}")
        if task := await get_task_by_gid(gid):
            await task.listener.on_download_complete()
            if intervals["stopAll"]:
                return
            await sync_to_async(
                api.remove,
                [download],
                force=True,
                files=True
            )

@loop_thread
async def _on_bt_download_complete(api, gid):
    seed_start_time = time()
    await sleep(1)
    download = await sync_to_async(
        api.get_download,
        gid
    )
    LOGGER.info(f"on_bt_download_complete: {download.name} - Gid: {gid}")
    if task := await get_task_by_gid(gid):
        task.listener.is_torrent = True
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
        await task.listener.on_download_complete()
        if intervals["stopAll"]:
            return
        await sync_to_async(download.update)
        if (
            task.listener.seed
            and download.is_complete
            and await get_task_by_gid(gid)
        ):
            LOGGER.info(f"Cancelling Seed: {download.name}")
            await task.listener.on_upload_error(
                f"Seeding stopped with Ratio: {task.ratio()} and Time: {task.seeding_time()}"
            )
            await sync_to_async(
                api.remove,
                [download],
                force=True,
                files=True
            )
        elif (
            task.listener.seed
            and download.is_complete
            and not await get_task_by_gid(gid)
        ):
            pass
        elif (
            task.listener.seed
            and not task.listener.is_cancelled
        ):
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


@loop_thread
async def _on_download_stopped(api, gid):
    await sleep(4)
    if task := await get_task_by_gid(gid):
        await task.listener.on_download_error("Dead torrent!")


@loop_thread
async def _on_download_error(api, gid):
    await sleep(1)
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
    if task := await get_task_by_gid(gid):
        await task.listener.on_download_error(error)


def start_aria2_listener():
    aria2.listen_to_notifications(
        threaded=False,
        on_download_start=_on_download_started,
        on_download_error=_on_download_error,
        on_download_stop=_on_download_stopped,
        on_download_complete=_on_download_complete,
        on_bt_download_complete=_on_bt_download_complete,
        timeout=60,
    )
