from time import time
from aiofiles.os import (
    remove,
    path as aiopath
)
from asyncio import sleep

from bot import (
    LOGGER,
    config_dict,
    non_queued_dl,
    qbittorrent_client,
    queue_dict_lock,
    task_dict,
    task_dict_lock,
)
from ...ext_utils.bot_utils import (
    bt_selection_buttons,
    sync_to_async
)
from ...ext_utils.task_manager import check_running_tasks
from ...listeners.qbit_listener import on_download_start
from ...task_utils.status_utils.qbit_status import QbittorrentStatus
from ...telegram_helper.message_utils import (
    delete_message,
    send_message,
    send_status_message,
)


async def add_qb_torrent(listener, path, ratio, seed_time):
    try:
        url = listener.link
        tpath = None
        if await aiopath.exists(listener.link):
            url = None
            tpath = listener.link
        (
            add_to_queue,
            event
        ) = await check_running_tasks(listener)
        op = await sync_to_async(
            qbittorrent_client.torrents_add,
            url,
            tpath,
            path,
            is_paused=add_to_queue,
            tags=f"{listener.mid}",
            ratio_limit=ratio,
            seeding_time_limit=seed_time
        )

        if op.lower() == "ok.":
            tor_info = await sync_to_async(
                qbittorrent_client.torrents_info,
                tag=f"{listener.mid}"
            )

            if len(tor_info) == 0:
                start_time = time()
                while (time() - start_time) <= 60:
                    if add_to_queue and event.is_set():
                        add_to_queue = False
                    tor_info = await sync_to_async(
                        qbittorrent_client.torrents_info,
                        tag=f"{listener.mid}"
                    )
                    if len(tor_info) > 0:
                        break
                    await sleep(1)
                else:
                    raise Exception("Use torrent file or magnet link incase you have added direct link! Timed Out!")

            tor_info = tor_info[0]
            listener.name = tor_info.name
            ext_hash = tor_info.hash
        else:
            LOGGER.error("Download not started! This Torrent already added or unsupported/invalid link/file.")
            await listener.on_download_error("Download not started!\nThis Torrent already added or unsupported/invalid link/file.")
            return

        async with task_dict_lock:
            task_dict[listener.mid] = QbittorrentStatus(
                listener,
                queued=add_to_queue
            )

        await on_download_start(f"{listener.mid}")

        if add_to_queue:
            LOGGER.info(f"Added to Queue/Download: {tor_info.name} - Hash: {ext_hash}")
        else:
            LOGGER.info(f"QbitDownload started: {tor_info.name} - Hash: {ext_hash}")

        await listener.on_download_start()

        if (
            config_dict["BASE_URL"]
            and listener.select
        ):
            if listener.link.startswith("magnet:"):
                metamsg = "Downloading Metadata, wait then you can select files. Use torrent file to avoid this wait."
                meta = await send_message(
                    listener.message,
                    metamsg
                )
                while True:
                    tor_info = await sync_to_async(
                        qbittorrent_client.torrents_info,
                        tag=f"{listener.mid}"
                    )

                    if len(tor_info) == 0:
                        await delete_message(meta)
                        return
                    try:
                        tor_info = tor_info[0]
                        if tor_info.state not in [
                            "metaDL",
                            "checkingResumeData",
                            "pausedDL",
                        ]:
                            await delete_message(meta)
                            break
                    except:
                        await delete_message(meta)
                        return

            ext_hash = tor_info.hash
            if not add_to_queue:
                await sync_to_async(
                    qbittorrent_client.torrents_pause,
                    torrent_hashes=ext_hash
                )
            SBUTTONS = bt_selection_buttons(ext_hash)
            msg = f"Your download paused. Choose files then press Done Selecting button to start downloading.\n\ncc: {listener.tag}"
            await send_message(
                listener.message,
                msg,
                SBUTTONS
            )

        elif listener.multi <= 1:
            await send_status_message(listener.message)

        if event is not None:
            if not event.is_set():
                await event.wait()
                if listener.is_cancelled:
                    return
                async with task_dict_lock:
                    task_dict[listener.mid].queued = False
                LOGGER.info(f"Start Queued Download from Qbittorrent: {tor_info.name} - Hash: {ext_hash}")
            await sync_to_async(
                qbittorrent_client.torrents_resume,
                torrent_hashes=ext_hash
            )

    except Exception as e:
        LOGGER.error(f"Qbittorrent download error: {e}")
        await listener.on_download_error(f"{e}")
    finally:
        if tpath and await aiopath.exists(tpath):
            await remove(tpath)
