from pyrogram.filters import (
    command,
    regex
)
from pyrogram.handlers import (
    MessageHandler,
    CallbackQueryHandler
)
from time import time
from datetime import datetime as dt
from bot.helper.z_utils import def_media
from httpx import AsyncClient as xclient
from aiofiles.os import path as aiopath

from psutil import (
    boot_time,
    cpu_count,
    cpu_freq,
    cpu_percent,
    disk_usage,
    swap_memory,
    virtual_memory,
    net_io_counters
)

from bot import (
    BASE,
    config_dict,
    LOGGER,
    task_dict_lock,
    status_dict,
    task_dict,
    botStartTime,
    DOWNLOAD_DIR,
    Intervals,
    bot,
)
from bot.helper.ext_utils.bot_utils import (
    cmd_exec,
    new_task,
    sync_to_async
)
from bot.helper.ext_utils.status_utils import (
    MirrorStatus,
    get_progress_bar_string,
    get_readable_file_size,
    get_readable_time,
    getSpecificTasks,
    speed_string_to_bytes,
)
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    isAdmin,
    request_limiter,
    sendMessage,
    deleteMessage,
    auto_delete_message,
    sendStatusMessage,
    update_status_message,
)
from bot.helper.telegram_helper.button_build import ButtonMaker


@new_task
async def mirror_status(_, message):
    async with task_dict_lock:
        count = len(task_dict)
    if count == 0:
        currentTime = get_readable_time(time() - botStartTime) # type: ignore
        free = get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)
        msg = "Stop it! Get some help!\n\nNo Active Tasks!\n\n"
        msg += f"Each user can get status for his tasks by adding me or user_id after cmd: /{BotCommands.StatusCommand[0]} me\n\n"
        msg += (
            f"\n<b>CPU:</b> {cpu_percent()}% | <b>FREE:</b> {free}"
            f"\n<b>RAM:</b> {virtual_memory().percent}% | <b>UPTIME:</b> {currentTime}"
        )
        reply_message = await sendMessage(
            message,
            msg
        )
        await auto_delete_message(
            message,
            reply_message
        )
    else:
        text = message.text.split()
        if len(text) > 1:
            user_id = (
                message.from_user.id
                if text[1] == "me"
                else int(text[1])
            )
        else:
            user_id = 0
            sid = message.chat.id
            if obj := Intervals["status"].get(sid):
                obj.cancel()
                del Intervals["status"][sid]
        await sendStatusMessage(
            message,
            user_id
        )
        await deleteMessage(message)


@new_task
async def status_pages(_, query):
    user_id = query.from_user.id
    spam = (
        not await isAdmin(
            query.message,
            user_id
        )
        and await request_limiter(query=query)
    )
    if spam:
        return
    if (
        not await isAdmin(
            query.message,
            user_id
        )
        and user_id
        and not await sync_to_async(
            getSpecificTasks,
            "All",
            user_id
        )
    ):
        await query.answer(
            "You don't have any active tasks",
            show_alert=True
        )
        return
    data = query.data.split()
    if data[2] == "stats":
        bstats = bot_sys_stats()
        await query.answer(
            bstats,
            show_alert=True
        )
    key = int(data[1])
    if data[2] == "ref":
        await query.answer()
        await update_status_message(
            key,
            force=True
        )
    elif data[2] in [
        "nex",
        "pre"
    ]:
        await query.answer()
        async with task_dict_lock:
            if data[2] == "nex":
                status_dict[key]["page_no"] += status_dict[key]["page_step"]
            else:
                status_dict[key]["page_no"] -= status_dict[key]["page_step"]
        await update_status_message(
            key,
            force=True
        )
    elif data[2] == "ps":
        await query.answer()
        async with task_dict_lock:
            status_dict[key]["page_step"] = int(data[3])
    elif data[2] == "st":
        await query.answer()
        async with task_dict_lock:
            status_dict[key]["status"] = data[3]
        await update_status_message(
            key,
            force=True
        )
    elif data[2] == "ov":
        tasks = {
            "Download": 0,
            "Upload": 0,
            "Seed": 0,
            "Archive": 0,
            "Extract": 0,
            "Split": 0,
            "QueueDl": 0,
            "QueueUp": 0,
            "Clone": 0,
            "CheckUp": 0,
            "Pause": 0,
            "SamVid": 0,
            "ConvertMedia": 0,
        }
        dl_speed = 0
        up_speed = 0
        seed_speed = 0
        async with task_dict_lock:
            for download in task_dict.values():
                match await sync_to_async(download.status):
                    case MirrorStatus.STATUS_DOWNLOADING:
                        tasks["Download"] += 1
                        dl_speed += speed_string_to_bytes(download.speed())
                    case MirrorStatus.STATUS_UPLOADING:
                        tasks["Upload"] += 1
                        up_speed += speed_string_to_bytes(download.speed())
                    case MirrorStatus.STATUS_SEEDING:
                        tasks["Seed"] += 1
                        seed_speed += speed_string_to_bytes(download.seed_speed())
                    case MirrorStatus.STATUS_ARCHIVING:
                        tasks["Archive"] += 1
                    case MirrorStatus.STATUS_EXTRACTING:
                        tasks["Extract"] += 1
                    case MirrorStatus.STATUS_SPLITTING:
                        tasks["Split"] += 1
                    case MirrorStatus.STATUS_QUEUEDL:
                        tasks["QueueDl"] += 1
                    case MirrorStatus.STATUS_QUEUEUP:
                        tasks["QueueUp"] += 1
                    case MirrorStatus.STATUS_CLONING:
                        tasks["Clone"] += 1
                    case MirrorStatus.STATUS_PAUSED:
                        tasks["Pause"] += 1
                    case MirrorStatus.STATUS_SAMVID:
                        tasks["SamVid"] += 1
                    case MirrorStatus.STATUS_CONVERTING:
                        tasks["ConvertMedia"] += 1
                    case _:
                        tasks["Download"] += 1
                        dl_speed += speed_string_to_bytes(download.speed())

        msg = (
            f"DL: {tasks['Download']} | "
            f"UP: {tasks['Upload']} | "
            f"SD: {tasks['Seed']} | "
            f"EX: {tasks['Extract']} | "
            f"SP: {tasks['Split']} | "
            f"AR: {tasks['Archive']}\n"
            f"QU: {tasks['QueueUp']} | "
            f"QD: {tasks['QueueDl']} | "
            f"PA: {tasks['Pause']} | "
            f"SV: {tasks['SamVid']} | "
            f"CM: {tasks['ConvertMedia']} | "
            f"CL: {tasks['Clone']}\n\n"

            f"DL: {get_readable_file_size(dl_speed)}/s | " # type: ignore
            f"UL: {get_readable_file_size(up_speed)}/s | " # type: ignore
            f"SD: {get_readable_file_size(seed_speed)}/s" # type: ignore
        )
        await query.answer(
            msg,
            show_alert=True
        )


def bot_sys_stats():
    cpup = cpu_percent(interval=0.1)
    ramp = virtual_memory().percent
    swap = swap_memory().percent
    disk = disk_usage(config_dict["DOWNLOAD_DIR"]).percent
    traf = get_readable_file_size(net_io_counters().bytes_sent + net_io_counters().bytes_recv)
    bmsg = f"C: {cpup}% | "
    bmsg += f"R: {ramp}% | "
    bmsg += f"S: {swap}% | "
    bmsg += f"D: {disk}%\n\n"
    bmsg += f"Bandwidth Used: {traf}\n"
    bmsg += f"{def_media(BASE.encode()).decode()}"
    return bmsg


async def stats(_, message, edit_mode=False):
    buttons = ButtonMaker()
    sysTime = get_readable_time(time() - boot_time()) # type: ignore
    botTime = get_readable_time(time() - botStartTime) # type: ignore
    total, used, free, disk = disk_usage("/")
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(net_io_counters().bytes_sent)
    recv = get_readable_file_size(net_io_counters().bytes_recv)
    tb = get_readable_file_size(net_io_counters().bytes_sent + net_io_counters().bytes_recv)
    cpuUsage = cpu_percent(interval=0.1)
    v_core = cpu_count(logical=True) - cpu_count(logical=False)
    freq_info = cpu_freq(percpu=False)
    if freq_info is not None:
        frequency = freq_info.current / 1000
    else:
        frequency = "-_-"
    memory = virtual_memory()
    mem_p = memory.percent
    swap = swap_memory()

    bot_stats = f"<b><i><u>Zee Bot Statistics</u></i></b>\n\n"\
                f"<code>CPU  : </code>{get_progress_bar_string(cpuUsage)} {cpuUsage}%\n" \
                f"<code>RAM  : </code>{get_progress_bar_string(mem_p)} {mem_p}%\n" \
                f"<code>SWAP : </code>{get_progress_bar_string(swap.percent)} {swap.percent}%\n" \
                f"<code>DISK : </code>{get_progress_bar_string(disk)} {disk}%\n\n" \
                f"<code>Bot Uptime      : </code> {botTime}\n" \
                f"<code>Uploaded        : </code> {sent}\n" \
                f"<code>Downloaded      : </code> {recv}\n" \
                f"<code>Total Bandwidth : </code> {tb}"

    sys_stats = f"<b><i><u>Zee System Statistics</u></i></b>\n\n"\
                f"<b>System Uptime:</b> <code>{sysTime}</code>\n" \
                f"<b>CPU:</b> {get_progress_bar_string(cpuUsage)}<code> {cpuUsage}%</code>\n" \
                f"<b>CPU Total Core(s):</b> <code>{cpu_count(logical=True)}</code>\n" \
                f"<b>P-Core(s):</b> <code>{cpu_count(logical=False)}</code> | " \
                f"<b>V-Core(s):</b> <code>{v_core}</code>\n" \
                f"<b>Frequency:</b> <code>{frequency} GHz</code>\n\n" \
                f"<b>RAM:</b> {get_progress_bar_string(mem_p)}<code> {mem_p}%</code>\n" \
                f"<b>Total:</b> <code>{get_readable_file_size(memory.total)}</code> | " \
                f"<b>Free:</b> <code>{get_readable_file_size(memory.available)}</code>\n\n" \
                f"<b>SWAP:</b> {get_progress_bar_string(swap.percent)}<code> {swap.percent}%</code>\n" \
                f"<b>Total</b> <code>{get_readable_file_size(swap.total)}</code> | " \
                f"<b>Free:</b> <code>{get_readable_file_size(swap.free)}</code>\n\n" \
                f"<b>DISK:</b> {get_progress_bar_string(disk)}<code> {disk}%</code>\n" \
                f"<b>Total:</b> <code>{total}</code> | <b>Free:</b> <code>{free}</code>"

    buttons.ibutton(
        "Sys Stats",
        "show_sys_stats"
    )
    buttons.ibutton(
        "Repo Stats",
        "show_repo_stats"
    )
    buttons.ibutton(
        "Bot Limits",
        "show_bot_limits"
    )
    buttons.ibutton(
        "Close",
        "close_signal"
    )
    sbtns = buttons.build_menu(2)
    if not edit_mode:
        await message.reply(
            bot_stats,
            reply_markup=sbtns
        )
    return bot_stats, sys_stats


async def send_bot_stats(_, query):
    buttons = ButtonMaker()
    (
        bot_stats,
        _
    ) = await stats(
        _,
        query.message,
        edit_mode=True
    )
    buttons.ibutton(
        "Sys Stats",
        "show_sys_stats"
    )
    buttons.ibutton(
        "Repo Stats",
        "show_repo_stats"
    )
    buttons.ibutton(
        "Bot Limits",
        "show_bot_limits"
    )
    buttons.ibutton(
        "Close",
        "close_signal"
    )
    sbtns = buttons.build_menu(2)
    await query.answer()
    await query.message.edit_text(
        bot_stats,
        reply_markup=sbtns
    )


async def send_sys_stats(_, query):
    buttons = ButtonMaker()
    (
        _,
        sys_stats
    ) = await stats(
        _,
        query.message,
        edit_mode=True
    )
    buttons.ibutton(
        "Bot Stats",
        "show_bot_stats"
    )
    buttons.ibutton(
        "Repo Stats",
        "show_repo_stats"
    )
    buttons.ibutton(
        "Bot Limits",
        "show_bot_limits"
    )
    buttons.ibutton(
        "Close",
        "close_signal"
    )
    sbtns = buttons.build_menu(2)
    await query.answer()
    await query.message.edit_text(
        sys_stats,
        reply_markup=sbtns
    )


async def send_repo_stats(_, query):
    buttons = ButtonMaker()
    commit_date = "Official Repo not available"
    last_commit = "No UPSTREAM_REPO"
    c_log = "N/A"
    d_log = "N/A"
    vtag = "N/A"
    version = "N/A"
    sha = "N/A"
    change_log = "N/A"
    update_info = ""
    async with xclient() as client:
        c_url = "https://api.github.com/repos/Dawn-India/Z-Mirror/commits"
        v_url = "https://api.github.com/repos/Dawn-India/Z-Mirror/tags"
        res = await client.get(c_url)
        pns = await client.get(v_url)
        if res.status_code == 200 and pns.status_code == 200:
            commits = res.json()
            tags = pns.json()
            if commits:
                latest_commit = commits[0]
                commit_date = latest_commit["commit"]["committer"]["date"]
                commit_date = dt.strptime(
                    commit_date,
                    "%Y-%m-%dT%H:%M:%SZ"
                )
                commit_date = commit_date.strftime("%d/%m/%Y at %I:%M %p")
                logs = latest_commit["commit"]["message"].split("\n\n")
                c_log = logs[0]
                d_log = (
                    "N/A"
                    if len(logs) < 2
                    else logs[1]
                )
                sha = latest_commit["sha"]
            if tags:
                tags = next(
                    (
                        tag for tag in tags
                        if tag["commit"]["sha"] == f"{sha}"
                    ),
                    None
                )
                vtag = (
                    "N/A"
                    if tags is None
                    else tags["name"]
                )
        if await aiopath.exists(".git"):
            last_commit = (
                await cmd_exec(
                    "git log -1 --date=short --pretty=format:'%cr'",
                    True
                )
            )[0]
            version = (
                await cmd_exec(
                    "git describe --abbrev=0 --tags",
                    True
                )
            )[0]
            change_log = (
                await cmd_exec(
                    "git log -1 --pretty=format:'%s'",
                    True
                )
            )[0]
            if version == "":
                version = "N/A"
        if version != "N/A":
            if version != vtag:
                update_info =  f"⚠️ New Version Update Available ⚠️"

    repo_stats = f"<b><i><u>Zee Repository Info</u></i></b> \n\n" \
                 f"<b><i>Official Repository</i></b>        \n"   \
                 f"<code>- Updated   : </code> {commit_date}\n"   \
                 f"<code>- Version   : </code> {vtag}       \n"   \
                 f"<code>- Changelog : </code> {c_log}      \n"   \
                 f"<code>- Desc      : </code> {d_log}      \n\n" \
                 f"<b><i>Bot Repository</i></b>             \n"   \
                 f"<code>- Updated   : </code> {last_commit}\n"   \
                 f"<code>- Version   : </code> {version}    \n"   \
                 f"<code>- Changelog : </code> {change_log} \n\n" \
                 f"<b>{update_info}</b>"

    buttons.ibutton(
        "Bot Stats", 
        "show_bot_stats"
    )
    buttons.ibutton(
        "Sys Stats",
        "show_sys_stats"
    )
    buttons.ibutton(
        "Bot Limits",
        "show_bot_limits"
    )
    buttons.ibutton(
        "Close",
        "close_signal"
    )
    sbtns = buttons.build_menu(2)
    await query.answer()
    await query.message.edit_text(
        repo_stats,
        reply_markup=sbtns
    )


async def send_bot_limits(_, query):
    buttons = ButtonMaker()
    DIR = "Unlimited" if config_dict["DIRECT_LIMIT"] == "" else config_dict["DIRECT_LIMIT"]
    JDL = "Unlimited" if config_dict["JD_LIMIT"] == "" else config_dict["JD_LIMIT"]
    NZB = "Unlimited" if config_dict["NZB_LIMIT"] == "" else config_dict["NZB_LIMIT"]
    YTD = "Unlimited" if config_dict["YTDLP_LIMIT"] == "" else config_dict["YTDLP_LIMIT"]
    YTP = "Unlimited" if config_dict["PLAYLIST_LIMIT"] == "" else config_dict["PLAYLIST_LIMIT"]
    GDL = "Unlimited" if config_dict["GDRIVE_LIMIT"] == "" else config_dict["GDRIVE_LIMIT"]
    TOR = "Unlimited" if config_dict["TORRENT_LIMIT"] == "" else config_dict["TORRENT_LIMIT"]
    CLL = "Unlimited" if config_dict["CLONE_LIMIT"] == "" else config_dict["CLONE_LIMIT"]
    RCL = "Unlimited" if config_dict["RCLONE_LIMIT"] == "" else config_dict["RCLONE_LIMIT"]
    MGA = "Unlimited" if config_dict["MEGA_LIMIT"] == "" else config_dict["MEGA_LIMIT"]
    TGL = "Unlimited" if config_dict["LEECH_LIMIT"] == "" else config_dict["LEECH_LIMIT"]
    UMT = "Unlimited" if config_dict["USER_MAX_TASKS"] == "" else config_dict["USER_MAX_TASKS"]
    BMT = "Unlimited" if config_dict["QUEUE_ALL"] == "" else config_dict["QUEUE_ALL"]

    bot_limit = f"<b><i><u>Zee Bot Limitations</u></i></b>\n" \
                f"<code>Torrent   : {TOR}</code> <b>GB</b>\n" \
                f"<code>G-Drive   : {GDL}</code> <b>GB</b>\n" \
                f"<code>Yt-Dlp    : {YTD}</code> <b>GB</b>\n" \
                f"<code>Playlist  : {YTP}</code> <b>NO</b>\n" \
                f"<code>Direct    : {DIR}</code> <b>GB</b>\n" \
                f"<code>JDownL    : {JDL}</code> <b>GB</b>\n" \
                f"<code>NZB       : {NZB}</code> <b>GB</b>\n" \
                f"<code>Clone     : {CLL}</code> <b>GB</b>\n" \
                f"<code>Rclone    : {RCL}</code> <b>GB</b>\n" \
                f"<code>Leech     : {TGL}</code> <b>GB</b>\n" \
                f"<code>MEGA      : {MGA}</code> <b>GB</b>\n\n" \
                f"<code>User Tasks: {UMT}</code>\n" \
                f"<code>Bot Tasks : {BMT}</code>"

    buttons.ibutton(
        "Bot Stats",
        "show_bot_stats"
    )
    buttons.ibutton(
        "Sys Stats",
        "show_sys_stats"
    )
    buttons.ibutton(
        "Repo Stats",
        "show_repo_stats"
    )
    buttons.ibutton(
        "Close",
        "close_signal"
    )
    sbtns = buttons.build_menu(2)
    await query.answer()
    await query.message.edit_text(
        bot_limit,
        reply_markup=sbtns
    )


async def send_close_signal(_, query):
    await query.answer()
    try:
        await deleteMessage(query.message.reply_to_message)
    except Exception as e:
        LOGGER.error(e)
    await deleteMessage(query.message)


bot.add_handler( # type: ignore
    MessageHandler(
        stats,
        filters=command(
            BotCommands.StatsCommand
        ) & CustomFilters.authorized
    )
)

bot.add_handler( # type: ignore
    CallbackQueryHandler(
        send_close_signal,
        filters=regex(
            "^close_signal"
        )
    )
)

bot.add_handler( # type: ignore
    CallbackQueryHandler(
        send_bot_stats,
        filters=regex(
            "^show_bot_stats"
        )
    )
)

bot.add_handler( # type: ignore
    CallbackQueryHandler(
        send_sys_stats,
        filters=regex(
            "^show_sys_stats"
        )
    )
)

bot.add_handler( # type: ignore
    CallbackQueryHandler(
        send_repo_stats,
        filters=regex(
            "^show_repo_stats"
        )
    )
)

bot.add_handler( # type: ignore
    CallbackQueryHandler(
        send_bot_limits,
        filters=regex(
            "^show_bot_limits"
        )
    )
)

bot.add_handler( # type: ignore
    MessageHandler(
        mirror_status,
        filters=command(
            BotCommands.StatusCommand
        ) & CustomFilters.authorized,
    )
)

bot.add_handler( # type: ignore
    CallbackQueryHandler(
        status_pages,
        filters=regex(
            "^status"
        )
    )
)
