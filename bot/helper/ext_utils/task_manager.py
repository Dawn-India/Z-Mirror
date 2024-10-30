from asyncio import Event

from bot import (
    config_dict,
    queued_dl,
    queued_up,
    non_queued_up,
    non_queued_dl,
    queue_dict_lock,
    LOGGER,
)
from .bot_utils import (
    sync_to_async,
    get_telegraph_list,
)
from .files_utils import (
    check_storage_threshold,
    get_base_name
)
from .links_utils import is_gdrive_id
from .status_utils import (
    get_specific_tasks,
    get_readable_file_size
)
from ..task_utils.gdrive_utils.search import GoogleDriveSearch
from ..telegram_helper.message_utils import is_admin


async def stop_duplicate_check(listener):
    if (
        isinstance(
            listener.up_dest,
            int
        )
        or listener.is_leech
        or listener.select
        or not is_gdrive_id(listener.up_dest)
        or (
            listener.up_dest.startswith("mtp:")
            and listener.stop_duplicate
        )
        or not listener.stop_duplicate
        or listener.same_dir
    ):
        return (
            False,
            None
        )

    name = listener.name
    LOGGER.info(f"Checking File/Folder if already in Drive: {name}")

    if listener.compress:
        name = f"{name}.zip"
    elif listener.extract:
        try:
            name = get_base_name(name)
        except:
            name = None

    if name is not None:
        (
            telegraph_content,
            contents_no
        ) = await sync_to_async(
            GoogleDriveSearch(
                stop_dup=True,
                no_multi=listener.is_clone
            ).drive_list,
            name,
            listener.up_dest,
            listener.user_id,
        )
        if telegraph_content:
            msg = f"File/Folder is already available in Drive.\nHere are {contents_no} list results:"
            button = await get_telegraph_list(telegraph_content)
            return msg, button

    return (
        False,
        None
    )


async def check_running_tasks(listener, state="dl"):
    all_limit = config_dict["QUEUE_ALL"]
    state_limit = (
        config_dict["QUEUE_DOWNLOAD"]
        if state == "dl"
        else config_dict["QUEUE_UPLOAD"]
    )
    event = None
    is_over_limit = False
    async with queue_dict_lock:
        if (
            state == "up"
            and listener.mid in non_queued_dl
        ):
            non_queued_dl.remove(listener.mid)
        if (
            (all_limit or state_limit)
            and not listener.force_run
            and not (
                listener.force_upload
                and state == "up"
            )
            and not (
                listener.force_download
                and state == "dl"
            )
        ):
            dl_count = len(non_queued_dl)
            up_count = len(non_queued_up)
            t_count = (
                dl_count
                if state == "dl"
                else up_count
            )
            is_over_limit = (
                all_limit
                and dl_count + up_count >= all_limit
                and (
                    not state_limit
                    or t_count >= state_limit
                )
            ) or (state_limit and t_count >= state_limit)
            if is_over_limit:
                event = Event()
                if state == "dl":
                    queued_dl[listener.mid] = event
                else:
                    queued_up[listener.mid] = event
        if not is_over_limit:
            if state == "up":
                non_queued_up.add(listener.mid)
            else:
                non_queued_dl.add(listener.mid)

    return (
        is_over_limit,
        event
    )


async def start_dl_from_queued(mid: int):
    queued_dl[mid].set()
    del queued_dl[mid]
    non_queued_dl.add(mid)


async def start_up_from_queued(mid: int):
    queued_up[mid].set()
    del queued_up[mid]
    non_queued_up.add(mid)


async def start_from_queued():
    if all_limit := config_dict["QUEUE_ALL"]:
        dl_limit = config_dict["QUEUE_DOWNLOAD"]
        up_limit = config_dict["QUEUE_UPLOAD"]
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            all_ = dl + up
            if all_ < all_limit:
                f_tasks = all_limit - all_
                if queued_up and (
                    not up_limit
                    or up < up_limit
                ):
                    for (
                        index,
                        mid
                    ) in enumerate(
                        list(queued_up.keys()),
                        start=1
                    ):
                        await start_up_from_queued(mid)
                        f_tasks -= 1
                        if f_tasks == 0 or (
                            up_limit
                            and index >= up_limit - up
                        ):
                            break
                if queued_dl and (
                    not dl_limit
                    or dl < dl_limit
                ) and f_tasks != 0:
                    for index, mid in enumerate(
                        list(queued_dl.keys()),
                        start=1
                    ):
                        await start_dl_from_queued(mid)
                        if (
                            dl_limit
                            and index >= dl_limit - dl
                        ) or index == f_tasks:
                            break
        return

    if up_limit := config_dict["QUEUE_UPLOAD"]:
        async with queue_dict_lock:
            up = len(non_queued_up)
            if (
                queued_up and
                up < up_limit
            ):
                f_tasks = up_limit - up
                for (
                    index,
                    mid
                ) in enumerate(
                    list(queued_up.keys()),
                    start=1
                ):
                    await start_up_from_queued(mid)
                    if index == f_tasks:
                        break
    else:
        async with queue_dict_lock:
            if queued_up:
                for mid in list(queued_up.keys()):
                    await start_up_from_queued(mid)

    if dl_limit := config_dict["QUEUE_DOWNLOAD"]:
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            if (
                queued_dl and
                dl < dl_limit
            ):
                f_tasks = dl_limit - dl
                for (
                    index,
                    mid
                ) in enumerate(
                    list(queued_dl.keys()),
                    start=1
                ):
                    await start_dl_from_queued(mid)
                    if index == f_tasks:
                        break
    else:
        async with queue_dict_lock:
            if queued_dl:
                for mid in list(queued_dl.keys()):
                    await start_dl_from_queued(mid)


async def check_user_tasks(user_id, maxtask):
    all_tasks = await sync_to_async(
        get_specific_tasks,
        "All",
        user_id
    )
    return len(all_tasks) >= maxtask


async def list_checker(listener):
    try:
        if await is_admin(listener.message):
            return
    except Exception as e:
        LOGGER.error(f"Error while checking if the user is Admin: {e}")
    if listener.is_playlist:
        if PLAYLIST_LIMIT := config_dict["PLAYLIST_LIMIT"]:
            if listener.playlist_count > PLAYLIST_LIMIT:
                return f"Playlist limit is {PLAYLIST_LIMIT}\n⚠ Your Playlist has {listener.playlist_count} items."


async def limit_checker(
        listener,
        is_torrent=False,
        is_mega=False,
        is_drive_link=False,
        is_rclone=False,
        is_jd=False,
        is_nzb=False,
    ):
    try:
        if await is_admin(listener.message):
            return
    except Exception as e:
        LOGGER.error(f"Error while checking if the user is Admin: {e}")

    GB = 1024 ** 3
    limit_exceeded = ""

    def check_limit(limit, size, limit_type):
        limit_bytes = limit * GB
        if size > limit_bytes:
            return f"{limit_type} limit is {get_readable_file_size(limit_bytes)}"
        return ""

    limit_configs = [
        (
            listener.is_ytdlp,
            "YTDLP_LIMIT",
            "Yt-Dlp"
        ),
        (
            listener.is_playlist,
            "PLAYLIST_LIMIT",
            "Yt-Dlp Playlist",
            "playlist_count"
        ),
        (
            listener.is_clone,
            "CLONE_LIMIT",
            "Clone"
        ),
        (
            is_rclone,
            "RCLONE_LIMIT",
            "Rclone"
        ),
        (
            is_jd,
            "JD_LIMIT",
            "Jdownloader"
        ),
        (
            is_mega,
            "MEGA_LIMIT",
            "Mega"
        ),
        (
            is_drive_link,
            "GDRIVE_LIMIT",
            "Google drive"
        ),
        (
            is_nzb,
            "NZB_LIMIT",
            "NZB"
        ),
        (
            is_torrent or listener.is_torrent,
            "TORRENT_LIMIT",
            "Torrent"
        ),
        (
            True,
            "DIRECT_LIMIT",
            "Direct"
        )
    ]

    for (
        condition,
        limit_key,
        limit_type,
        *optional
    ) in limit_configs:
        if condition:
            limit = config_dict.get(limit_key)
            if limit:
                size = getattr(
                    listener,
                    optional[0],
                    listener.size
                ) if optional else listener.size
                limit_exceeded = check_limit(
                    limit,
                    size,
                    limit_type
                )
                if limit_exceeded:
                    break

    if (
        not limit_exceeded
        and listener.is_leech
    ):
        limit = config_dict.get("LEECH_LIMIT")
        if limit:
            limit_exceeded = check_limit(
                limit,
                listener.size,
                "Leech"
            )

    if (
        not limit_exceeded
        and config_dict.get("STORAGE_THRESHOLD")
        and not listener.is_clone
    ):
        arch = any([
            listener.compress,
            listener.extract
        ])
        limit = config_dict["STORAGE_THRESHOLD"] * GB
        acpt = await sync_to_async(
            check_storage_threshold,
            listener.size,
            limit,
            arch
        )
        if not acpt:
            limit_exceeded = f"Don't have enough free space for your task.\nYou must leave {get_readable_file_size(limit)} free storage"

    if limit_exceeded:
        if listener.is_playlist:
            return limit_exceeded
        return f"{limit_exceeded}.\n⚠ Your task size is {get_readable_file_size(listener.size)}"


async def check_avg_speed(total_speed, count):
    if AVG_SPEED := config_dict["AVG_SPEED"]:
        avg_speed = AVG_SPEED * 1024**2
        task_avg_speed = total_speed / count
        if task_avg_speed < avg_speed:
            return(
                f"⚠ Minimum download speed must be above {get_readable_file_size(avg_speed)}ps."
                f"\nYour task's average download speed is {get_readable_file_size(task_avg_speed)}ps."
            )
