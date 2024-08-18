from aiofiles.os import (
    remove,
    path as aiopath
)
from asyncio import sleep
from time import time

from bot import (
    task_dict,
    task_dict_lock,
    Intervals,
    qbittorrent_client,
    config_dict,
    QbTorrents,
    qb_listener_lock,
    LOGGER,
    bot_loop,
)
from bot.helper.ext_utils.bot_utils import (
    new_task,
    sync_to_async
)
from bot.helper.ext_utils.files_utils import clean_unwanted
from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,
    get_readable_time,
    getTaskByGid
)
from bot.helper.ext_utils.task_manager import (
    check_avg_speed,
    limit_checker,
    stop_duplicate_check
)
from bot.helper.task_utils.status_utils.qbit_status import QbittorrentStatus
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    update_status_message
)


async def _remove_torrent(hash_, tag):
    await sync_to_async(
        qbittorrent_client.torrents_delete,
        torrent_hashes=hash_,
        delete_files=True
    )
    async with qb_listener_lock:
        if tag in QbTorrents:
            del QbTorrents[tag]
    await sync_to_async(
        qbittorrent_client.torrents_delete_tags,
        tags=tag
    )


@new_task
async def _onDownloadError(err, tor, button=None):
    LOGGER.info(f"Cancelling Download: {tor.name}")
    ext_hash = tor.hash
    if task := await getTaskByGid(ext_hash[:12]):
        await task.listener.onDownloadError(
            err,
            button
        )
    await sync_to_async(
        qbittorrent_client.torrents_pause,
        torrent_hashes=ext_hash
    )
    await sleep(0.3)
    await _remove_torrent(
        ext_hash,
        tor.tags
    )


@new_task
async def _onSeedFinish(tor):
    ext_hash = tor.hash
    LOGGER.info(f"Cancelling Seed: {tor.name}")
    if task := await getTaskByGid(ext_hash[:12]):
        msg = f"Seeding stopped with Ratio: {round(tor.ratio, 3)} and Time: {get_readable_time(tor.seeding_time)}"
        await task.listener.onUploadError(msg)
    await _remove_torrent(
        ext_hash,
        tor.tags
    )


@new_task
async def _stop_duplicate(tor):
    if task := await getTaskByGid(tor.hash[:12]):
        if task.listener.stopDuplicate: # type: ignore
            task.listener.name = tor.content_path.rsplit( # type: ignore
                "/",
                1
            )[-1].rsplit(
                ".!qB",
                1
            )[0]
            (
                msg,
                button
            ) = await stop_duplicate_check(task.listener) # type: ignore
            if msg:
                _onDownloadError(
                    msg,
                    tor,
                    button
                ) # type: ignore


@new_task
async def _size_checked(tor):
    if task := await getTaskByGid(tor.hash[:12]):
        task.listener.size = tor.size # type: ignore
        if limit_exceeded := await limit_checker(
            task.listener, # type: ignore
            isTorrent=True
        ):
            LOGGER.info(
                f"qBit Limit Exceeded: {task.listener.name} | {get_readable_file_size(task.listener.size)}" # type: ignore
            )
            qmsg = _onDownloadError(
                limit_exceeded,
                tor
            )
            await delete_links(task.listener.message) # type: ignore
            await auto_delete_message(
                task.listener.message, # type: ignore
                qmsg
            )


@new_task
async def _avg_speed_check(tor):
    if task := await getTaskByGid(tor.hash[:12]):
        if config_dict["AVG_SPEED"]:
            start_time = time()
            total_speed = 0
            count = 0
            while time() - start_time < 1800:
                live_dl = await sync_to_async(
                    qbittorrent_client.torrents_info,
                    torrent_hashes=tor.hash
                )
                try:
                    dl_speed = live_dl[0].dlspeed
                except:
                    dl_speed = 0
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
                qmsg = _onDownloadError(
                    min_speed,
                    tor
                )
                await delete_links(task.listener.message) # type: ignore
                await auto_delete_message(
                    task.listener.message, # type: ignore
                    qmsg
                )


@new_task
async def _onDownloadComplete(tor):
    ext_hash = tor.hash
    tag = tor.tags
    if task := await getTaskByGid(tor.hash[:12]):
        if not task.listener.seed: # type: ignore
            await sync_to_async(
                qbittorrent_client.torrents_pause,
                torrent_hashes=ext_hash
                )
        if task.listener.select: # type: ignore
            await clean_unwanted(task.listener.dir) # type: ignore
            path = tor.content_path.rsplit(
                "/",
                1
            )[0]
            res = await sync_to_async(
                qbittorrent_client.torrents_files,
                torrent_hash=ext_hash
            )
            for f in res:
                if (
                    f.priority == 0 and
                    await aiopath.exists(f"{path}/{f.name}")
                ):
                    try:
                        await remove(f"{path}/{f.name}")
                    except:
                        pass
        await task.listener.onDownloadComplete() # type: ignore
        if Intervals["stopAll"]:
            return
        if (
            task.listener.seed and not # type: ignore
            task.listener.isCancelled # type: ignore
        ):
            async with task_dict_lock:
                if task.listener.mid in task_dict: # type: ignore
                    removed = False
                    task_dict[task.listener.mid] = QbittorrentStatus( # type: ignore
                        task.listener, # type: ignore
                        True
                    )
                else:
                    removed = True
            if removed:
                await _remove_torrent(
                    ext_hash,
                    tag
                )
            return
        if (
            task.listener.seed and not
            task.listener.isCancelled
        ):
            async with task_dict_lock:
                if task.listener.mid in task_dict:
                    removed = False
                    task_dict[task.listener.mid] = QbittorrentStatus(
                        task.listener,
                        True
                    )
                else:
                    removed = True
            if removed:
                await _remove_torrent(
                    ext_hash,
                    tag
                )
                return
            async with qb_listener_lock:
                if tag in QbTorrents:
                    QbTorrents[tag]["seeding"] = True
                else:
                    return
            await update_status_message(task.listener.message.chat.id)
            LOGGER.info(f"Seeding started: {tor.name} - Hash: {ext_hash}")
        else:
            await _remove_torrent(
                ext_hash,
                tag
            )
    else:
        await _remove_torrent(
            ext_hash,
            tag
        )


async def _qb_listener():
    while True:
        async with qb_listener_lock:
            try:
                torrents = await sync_to_async(qbittorrent_client.torrents_info)
                if len(torrents) == 0:
                    Intervals["qb"] = ""
                    break
                for tor_info in torrents:
                    tag = tor_info.tags
                    if tag not in QbTorrents:
                        continue
                    state = tor_info.state
                    if state == "metaDL":
                        TORRENT_TIMEOUT = config_dict["TORRENT_TIMEOUT"]
                        QbTorrents[tag]["stalled_time"] = time()
                        if (
                            TORRENT_TIMEOUT
                            and time() - tor_info.added_on >= TORRENT_TIMEOUT
                        ):
                            _onDownloadError(
                                "Dead Torrent!",
                                tor_info
                            ) # type: ignore
                        else:
                            await sync_to_async(
                                qbittorrent_client.torrents_reannounce,
                                torrent_hashes=tor_info.hash,
                            )
                    elif state == "downloading":
                        QbTorrents[tag]["stalled_time"] = time()
                        if not QbTorrents[tag]["stop_dup_check"]:
                            QbTorrents[tag]["stop_dup_check"] = True
                            _stop_duplicate(tor_info) # type: ignore
                            _size_checked(tor_info) # type: ignore
                            _avg_speed_check(tor_info) # type: ignore
                    elif state == "stalledDL":
                        TORRENT_TIMEOUT = config_dict["TORRENT_TIMEOUT"]
                        if (
                            not QbTorrents[tag]["rechecked"]
                            and 0.99989999999999999 < tor_info.progress < 1
                        ):
                            msg = f"Force recheck - Name: {tor_info.name} Hash: "
                            msg += f"{tor_info.hash} Downloaded Bytes: {tor_info.downloaded} "
                            msg += f"Size: {tor_info.size} Total Size: {tor_info.total_size}"
                            LOGGER.warning(msg)
                            await sync_to_async(
                                qbittorrent_client.torrents_recheck,
                                torrent_hashes=tor_info.hash,
                            )
                            QbTorrents[tag]["rechecked"] = True
                        elif (
                            TORRENT_TIMEOUT
                            and time() - QbTorrents[tag]["stalled_time"]
                            >= TORRENT_TIMEOUT
                        ):
                            _onDownloadError(
                                "Dead Torrent!",
                                tor_info
                            ) # type: ignore
                        else:
                            await sync_to_async(
                                qbittorrent_client.torrents_reannounce,
                                torrent_hashes=tor_info.hash,
                            )
                    elif state == "missingFiles":
                        await sync_to_async(
                            qbittorrent_client.torrents_recheck,
                            torrent_hashes=tor_info.hash,
                        )
                    elif state == "error":
                        _onDownloadError(
                            "No enough space for this torrent on device",
                            tor_info # type: ignore
                        )
                    elif (
                        tor_info.completion_on != 0
                        and not QbTorrents[tag]["uploaded"]
                        and state
                        not in [
                            "checkingUP",
                            "checkingDL",
                            "checkingResumeData"
                        ]
                    ):
                        QbTorrents[tag]["uploaded"] = True
                        _onDownloadComplete(tor_info) # type: ignore
                    elif (
                        state in [
                            "pausedUP",
                            "pausedDL"
                        ] and QbTorrents[tag]["seeding"]
                    ):
                        QbTorrents[tag]["seeding"] = False
                        _onSeedFinish(tor_info) # type: ignore
                        await sleep(0.5)
            except Exception as e:
                LOGGER.error(str(e))
        await sleep(3)


async def onDownloadStart(tag):
    try:
        async with qb_listener_lock:
            QbTorrents[tag] = {
                "stalled_time": time(),
                "stop_dup_check": False,
                "rechecked": False,
                "uploaded": False,
                "seeding": False,
            }
            if not Intervals["qb"]:
                Intervals["qb"] = bot_loop.create_task(_qb_listener())
    except Exception as e:
            LOGGER.error(str(e))
