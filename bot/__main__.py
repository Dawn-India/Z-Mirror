from aiofiles import open as aiopen
from aiofiles.os import (
    path as aiopath,
    remove
)
from asyncio import (
    create_subprocess_exec,
    gather
)
from nekozee.filters import command
from nekozee.handlers import MessageHandler
from os import execl as osexecl
from signal import (
    SIGINT,
    signal
)
from sys import executable
from time import time

from bot import (
    LOGGER,
    bot,
    config_dict,
    intervals,
    sabnzbd_client,
    scheduler,
)
from .helper.ext_utils.bot_utils import (
    create_help_buttons,
    new_task,
    set_commands,
    sync_to_async
)
from .helper.ext_utils.db_handler import database
from .helper.ext_utils.files_utils import (
    clean_all,
    exit_clean_up
)
from .helper.ext_utils.jdownloader_booter import jdownloader
from .helper.ext_utils.telegraph_helper import telegraph
from .helper.listeners.aria2_listener import start_aria2_listener
from .helper.task_utils.rclone_utils.serve import rclone_serve_booter
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.message_utils import (
    auto_delete_message,
    edit_message,
    send_file,
    send_message
)
from .modules import (
    anonymous,
    authorize,
    bot_settings,
    cancel_task,
    clone,
    exec,
    force_start,
    file_selector,
    gd_count,
    gd_delete,
    gd_search,
    help,
    leech_del,
    mirror_leech,
    rmdb,
    shell,
    status,
    users_settings,
    ytdlp,
)


@new_task
async def restart(_, message):
    intervals["stopAll"] = True
    restart_message = await send_message(
        message,
        "Restarting..."
    )
    if scheduler.running:
        scheduler.shutdown(wait=False)
    if qb := intervals["qb"]:
        qb.cancel()
    if jd := intervals["jd"]:
        jd.cancel()
    if nzb := intervals["nzb"]:
        nzb.cancel()
    if st := intervals["status"]:
        for intvl in list(st.values()):
            intvl.cancel()
    await sync_to_async(clean_all)
    if sabnzbd_client.LOGGED_IN:
        await gather(
            sabnzbd_client.pause_all(),
            sabnzbd_client.purge_all(True),
            sabnzbd_client.delete_history(
                "all",
                delete_files=True
            ),
        )
    proc1 = await create_subprocess_exec(
        "pkill",
        "-9",
        "-f",
        "gunicorn|aria2c|qbittorrent-nox|ffmpeg|rclone|java|sabnzbdplus"
    )
    proc2 = await create_subprocess_exec(
        "python3",
        "update.py"
    )
    await gather(
        proc1.wait(),
        proc2.wait()
    )
    async with aiopen(
        ".restartmsg",
        "w"
    ) as f:
        await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n") # type: ignore
    osexecl(
        executable,
        executable,
        "-m",
        "bot"
    )


@new_task
async def ping(_, message):
    start_time = int(round(time() * 1000))
    reply = await send_message(
        message,
        "Starting Ping"
    )
    end_time = int(round(time() * 1000))
    await edit_message(
        reply,
        f"{end_time - start_time} ms"
    )


@new_task
async def log(_, message):
    await send_file(
        message,
        "Zee_Logs.txt"
    )


help_string = f"""
<b>NOTE: Click on any CMD to see more detalis.</b>

<b>Use Mirror commands for uploading to Cloud Drive:</b>
/{BotCommands.MirrorCommand[0]} or /{BotCommands.MirrorCommand[1]}: Start mirroring to cloud.
/{BotCommands.QbMirrorCommand[0]} or /{BotCommands.QbMirrorCommand[1]}: Start Mirroring to cloud using qBittorrent.
/{BotCommands.JdMirrorCommand[0]} or /{BotCommands.JdMirrorCommand[1]}: Start Mirroring to cloud using JDownloader.
/{BotCommands.NzbMirrorCommand[0]} or /{BotCommands.NzbMirrorCommand[1]}: Start Mirroring to cloud using Sabnzbd.
/{BotCommands.YtdlCommand[0]} or /{BotCommands.YtdlCommand[1]}: Mirror yt-dlp supported link.

<b>Use Leech commands for uploading to Telegram:</b>
/{BotCommands.LeechCommand[0]} or /{BotCommands.LeechCommand[1]}: Start leeching to Telegram.
/{BotCommands.QbLeechCommand[0]} or /{BotCommands.QbLeechCommand[1]}: Start leeching using qBittorrent.
/{BotCommands.JdLeechCommand[0]} or /{BotCommands.JdLeechCommand[1]}: Start leeching using JDownloader.
/{BotCommands.NzbLeechCommand[0]} or /{BotCommands.NzbLeechCommand[1]}: Start leeching using Sabnzbd.
/{BotCommands.YtdlLeechCommand[0]} or /{BotCommands.YtdlLeechCommand[1]}: Leech yt-dlp supported link.

<b>Gdrive only commands:</b>
/{BotCommands.CloneCommand} [drive_url]: Copy file/folder to Google Drive.
/{BotCommands.CountCommand} [drive_url]: Count file/folder of Google Drive.
/{BotCommands.ListCommand} [query]: Search in Google Drive(s).
/{BotCommands.DeleteCommand} [drive_url]: Delete file/folder from Google Drive (Only Owner & Sudo).

<b>Settings:</b>
/{BotCommands.UserSetCommand[0]} or /{BotCommands.UserSetCommand[1]} [query]: Users settings.
/{BotCommands.BotSetCommand[0]} or /{BotCommands.BotSetCommand[1]} [query]: Bot settings.
/{BotCommands.UsersCommand}: show users settings (Only Owner & Sudo).

<b>Cancel Tasks:</b>
/{BotCommands.CancelTaskCommand[0]} or /{BotCommands.CancelTaskCommand[1]} [gid]: Cancel task by gid or reply.
/{BotCommands.CancelAllCommand} [query]: Cancel all [status] tasks.

/{BotCommands.SelectCommand}: Select files from torrents or nzb by gid or reply.
/{BotCommands.SearchCommand} [query]: Search for torrents with API.
/{BotCommands.PingCommand[0]}: Check how long it takes to Ping the Bot (Only Owner & Sudo).
/{BotCommands.ForceStartCommand[0]} or /{BotCommands.ForceStartCommand[1]} [gid]: Force start task by gid or reply.

/{BotCommands.StatusCommand[0]}: Shows a status of all the downloads.
/{BotCommands.StatsCommand[0]}: Show stats of the machine where the bot is hosted in.

<b>Authentication:</b>
/{BotCommands.AuthorizeCommand}: Authorize a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.UnAuthorizeCommand}: Unauthorize a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.AddSudoCommand}: Add sudo user (Only Owner).
/{BotCommands.RmSudoCommand}: Remove sudo users (Only Owner).

<b>Maintainance:</b>
/{BotCommands.RestartCommand[0]}: Restart and update the bot (Only Owner & Sudo).
/{BotCommands.LogCommand}: Get a log file of the bot. Handy for getting crash reports (Only Owner & Sudo).
/{BotCommands.ShellCommand}: Run shell commands (Only Owner).
/{BotCommands.AExecCommand}: Exec async functions (Only Owner).
/{BotCommands.ExecCommand}: Exec sync functions (Only Owner).
/{BotCommands.ClearLocalsCommand}: Clear {BotCommands.AExecCommand} or {BotCommands.ExecCommand} locals (Only Owner).

/{BotCommands.RssCommand}: RSS Menu.
"""

@new_task
async def bot_help(_, message):
    hmsg = await send_message(
        message,
        help_string
    )
    await auto_delete_message(
        message,
        hmsg
    )



async def restart_notification():
    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            (
                chat_id,
                msg_id
            ) = map(
                int,
                f
            )
    else:
        (
            chat_id,
            msg_id
        ) = (
            0,
            0
        )

    async def send_incomplete_task_message(cid, msg):
        try:
            if msg.startswith("Restarted Successfully!"):
                await bot.edit_message_text( # type: ignore
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=msg
                )
                await remove(".restartmsg")
            else:
                await bot.send_message( # type: ignore
                    chat_id=cid,
                    text=msg,
                    disable_web_page_preview=True,
                    disable_notification=True,
                )
        except Exception as e:
            LOGGER.error(e)

    if config_dict["INCOMPLETE_TASK_NOTIFIER"] and config_dict["DATABASE_URL"]:
        if notifier_dict := await database.get_incomplete_tasks():
            for cid, data in notifier_dict.items():
                msg = (
                    "Restarted Successfully!"
                    if cid == chat_id
                    else "Bot Restarted!"
                )
                for tag, links in data.items():
                    msg += f"\n\n👤 {tag} Do your tasks again. \n"
                    for index, link in enumerate(
                        links,
                        start=1
                    ):
                        msg += f" {index}: {link} \n"
                        if len(msg.encode()) > 4000:
                            await send_incomplete_task_message(
                                cid,
                                msg
                            )
                            msg = ""
                if msg:
                    await send_incomplete_task_message(
                        cid,
                        msg
                    )
        if config_dict["STOP_DUPLICATE_TASKS"]:
            await database.clear_download_links()

    if await aiopath.isfile(".restartmsg"):
        try:
            await bot.edit_message_text( # type: ignore
                chat_id=chat_id,
                message_id=msg_id,
                text="Restarted Successfully!"
            )
        except:
            pass
        await remove(".restartmsg")


async def main():
    if config_dict["DATABASE_URL"]:
        await database.db_load()
    await gather(
        jdownloader.boot(),
        sync_to_async(clean_all),
        bot_settings.initiate_search_tools(),
        restart_notification(),
        telegraph.create_account(),
        rclone_serve_booter(),
        sync_to_async(
            start_aria2_listener,
            wait=False
        ),
        set_commands(bot),
    )
    create_help_buttons()

    bot.add_handler( # type: ignore
        MessageHandler(
            log,
            filters=command(
                BotCommands.LogCommand,
                case_sensitive=True
            ) & CustomFilters.sudo
        )
    )
    bot.add_handler( # type: ignore
        MessageHandler(
            restart,
            filters=command(
                BotCommands.RestartCommand,
                case_sensitive=True
            ) & CustomFilters.sudo
        )
    )
    bot.add_handler( # type: ignore
        MessageHandler(
            ping,
            filters=command(
                BotCommands.PingCommand,
                case_sensitive=True
            ) & CustomFilters.sudo
        )
    )
    bot.add_handler( # type: ignore
        MessageHandler(
            bot_help,
            filters=command(
                BotCommands.HelpCommand,
                case_sensitive=True
            ) & CustomFilters.authorized,
        )
    )
    LOGGER.info("Bot Started Successfully!")
    signal(
        SIGINT,
        exit_clean_up
    )


bot.loop.run_until_complete(main()) # type: ignore
bot.loop.run_forever() # type: ignore
