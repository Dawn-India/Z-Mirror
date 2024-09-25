from aiofiles.os import (
    path as aiopath,
    remove
)

from nekozee.filters import (
    command,
    regex
)
from nekozee.handlers import (
    CallbackQueryHandler,
    MessageHandler
)

from bot import (
    LOGGER,
    OWNER_ID,
    aria2,
    bot,
    config_dict,
    qbittorrent_client,
    sabnzbd_client,
    task_dict,
    task_dict_lock,
    user_data
)
from ..helper.ext_utils.bot_utils import (
    bt_selection_buttons,
    new_task,
    sync_to_async
)
from ..helper.ext_utils.status_utils import (
    get_readable_file_size,
    get_task_by_gid,
    MirrorStatus
)
from ..helper.ext_utils.task_manager import limit_checker
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    delete_message,
    send_message,
    send_status_message
)


@new_task
async def select(_, message):
    if not config_dict["BASE_URL"]:
        smsg = await send_message(
            message,
            "Base URL not defined!"
        )
        await auto_delete_message(
            message,
            smsg
        )
        return
    user_id = message.from_user.id
    msg = message.text.split()
    if len(msg) > 1:
        gid = msg[1]
        task = await get_task_by_gid(gid)
        if task is None:
            smsg = await send_message(
                message,
                f"GID: <code>{gid}</code> Not Found."
            )
            await auto_delete_message(
                message,
                smsg
            )
            return
    elif reply_to_id := message.reply_to_message_id:
        async with task_dict_lock:
            task = task_dict.get(reply_to_id)
        if task is None:
            smsg = await send_message(
                message,
                "This is not an active task!"
            )
            await auto_delete_message(
                message,
                smsg
            )
            return
    elif len(msg) == 1:
        msg = (
            "Reply to an active /cmd which was used to start the download or add gid along with cmd\n\n"
            + "This command mainly for selection incase you decided to select files from already added torrent/nzb. "
            + "But you can always use /cmd with arg `s` to select files before download start."
        )
        smsg = await send_message(
            message,
            msg
        )
        await auto_delete_message(
            message,
            smsg
        )
        return

    if (
        OWNER_ID != user_id
        and task.listener.user_id != user_id
        and (
            user_id not in user_data
            or not user_data[user_id].get("is_sudo")
        )
    ):
        smsg = await send_message(
            message,
            "This task is not for you!"
        )
        await auto_delete_message(
            message,
            smsg
        )
        return
    if await sync_to_async(task.status) not in [
        MirrorStatus.STATUS_DOWNLOADING,
        MirrorStatus.STATUS_PAUSED,
        MirrorStatus.STATUS_QUEUEDL,
    ]:
        smsg = await send_message(
            message,
            "Task should be in download or pause (incase message deleted by wrong) or queued status (incase you have used torrent or nzb file)!",
        )
        await auto_delete_message(
            message,
            smsg
        )
        return
    if (
        task.name().startswith("[METADATA]") or
        task.name().startswith("Trying")
    ):
        smsg = await send_message(
            message,
            "Try after downloading metadata finished!"
        )
        await auto_delete_message(
            message,
            smsg
        )
        return

    try:
        id_ = task.gid()
        if not task.queued:
            if task.listener.is_nzb:
                await sabnzbd_client.pause_job(id_)
            elif task.listener.is_qbit:
                await sync_to_async(task.update)
                id_ = task.hash()
                await sync_to_async(
                    qbittorrent_client.torrents_pause,
                    torrent_hashes=id_
                )
            else:
                await sync_to_async(task.update)
                try:
                    await sync_to_async(
                        aria2.client.force_pause,
                        id_
                    )
                except Exception as e:
                    LOGGER.error(
                        f"{e} Error in pause, this mostly happens after abuse aria2"
                    )
        task.listener.select = True
    except:
        smsg = await send_message(
            message,
            "This is not a bittorrent or sabnzbd task!"
        )
        await auto_delete_message(
            message,
            smsg
        )
        return

    SBUTTONS = bt_selection_buttons(id_)
    msg = "Your download paused. Choose files then press Done Selecting button to resume downloading."
    await send_message(
        message,
        msg,
        SBUTTONS
    )


@new_task
async def get_confirm(_, query):
    user_id = query.from_user.id
    data = query.data.split()
    message = query.message
    task = await get_task_by_gid(data[2])
    if task is None:
        await query.answer(
            "This task has been cancelled!",
            show_alert=True
        )
        await delete_message(message)
        return
    if user_id != task.listener.user_id:
        await query.answer(
            "This task is not for you!",
            show_alert=True
        )
    elif data[1] == "pin":
        await query.answer(
            data[3],
            show_alert=True
        )
    elif data[1] == "done":
        await query.answer()
        id_ = data[3]
        if hasattr(
            task,
            "seeding"
        ):
            if task.listener.is_qbit:
                tor_info = (
                    await sync_to_async(
                        qbittorrent_client.torrents_info,
                        torrent_hash=id_
                    )
                )[0]
                path = tor_info.content_path.rsplit(
                    "/",
                    1
                )[0]
                res = await sync_to_async(
                    qbittorrent_client.torrents_files,
                    torrent_hash=id_
                )
                for f in res:
                    if f.priority == 0:
                        f_paths = [
                            f"{path}/{f.name}",
                            f"{path}/{f.name}.!qB"
                        ]
                        for f_path in f_paths:
                            if await aiopath.exists(f_path):
                                try:
                                    await remove(f_path)
                                except:
                                    pass
                if not task.queued:
                    await sync_to_async(
                        qbittorrent_client.torrents_resume,
                        torrent_hashes=id_
                    )
            else:
                res = await sync_to_async(
                    aria2.client.get_files,
                    id_
                )
                task.listener.size = sum(
                    int(file['length'])
                    for file in res
                    if file['selected'] == 'true'
                )
                LOGGER.info(f"Total size after selection: {get_readable_file_size(task.listener.size)}")
                if limit_exceeded := await limit_checker(task.listener):
                    LOGGER.info(f"Aria2 Limit Exceeded: {task.listener.name} | {get_readable_file_size(task.listener.size)}")
                    amsg = await task.listener.on_download_error(limit_exceeded)
                    await sync_to_async(
                        aria2.client.remove,
                        id_
                    )
                    await delete_links(task.listener.message)
                    await auto_delete_message(
                        task.listener.message,
                        amsg
                    )
                    return
                for f in res:
                    if (
                        f["selected"] == "false" and
                        await aiopath.exists(f["path"])
                    ):
                        try:
                            await remove(f["path"])
                        except:
                            pass
                if not task.queued:
                    try:
                        await sync_to_async(aria2.client.unpause, id_)
                    except Exception as e:
                        LOGGER.error(
                            f"{e} Error in resume, this mostly happens after abuse aria2. Try to use select cmd again!"
                        )
        elif task.listener.is_nzb:
            await sabnzbd_client.resume_job(id_)
        await send_status_message(message)
        await delete_message(message)
    else:
        await delete_message(message)
        await task.cancel_task()


bot.add_handler( # type: ignore
    MessageHandler(
        select,
        filters=command(
            BotCommands.SelectCommand,
            case_sensitive=True
        ) & CustomFilters.authorized
    )
)
bot.add_handler( # type: ignore
    CallbackQueryHandler(
        get_confirm,
        filters=regex("^sel")
    )
)
