from asyncio import create_subprocess_exec, gather
from os import execl as osexecl
from signal import SIGINT, signal
from sys import executable
from time import time, sleep, monotonic

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import remove as aioremove
from psutil import (boot_time, cpu_count, cpu_percent, cpu_freq, disk_usage,
                    net_io_counters, swap_memory, virtual_memory)
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from uuid import uuid4
from bot import (DATABASE_URL, INCOMPLETE_TASK_NOTIFIER, LOGGER,
                 STOP_DUPLICATE_TASKS, Interval, QbInterval, bot, botStartTime,
                 user_data, config_dict, scheduler)
from bot.helper.listeners.aria2_listener import start_aria2_listener

from .helper.ext_utils.bot_utils import (cmd_exec, get_readable_file_size,
                                         get_readable_time, set_commands,
                                         sync_to_async, get_progress_bar_string)
from .helper.ext_utils.db_handler import DbManger
from .helper.ext_utils.fs_utils import clean_all, exit_clean_up, start_cleanup
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.message_utils import (editMessage, sendFile,
                                                   sendMessage, auto_delete_message)
from .modules import (anonymous, authorize, bot_settings, cancel_mirror,
                      category_select, clone, eval, gd_count, gd_delete,
                      gd_list, leech_del, mirror_leech, rmdb, rss,
                      shell, status, torrent_search,
                      torrent_select, users_settings, ytdlp)

start_aria2_listener()

async def stats(_, message):
    if await aiopath.exists('.git'):
        last_commit = (await cmd_exec("git log -1 --date=short --pretty=format:'%cr'", True))[0]
        version = (await cmd_exec("git describe --abbrev=0 --tags", True))[0]
        change_log = (await cmd_exec("git log -1 --pretty=format:'%s'", True))[0]
    else:
        last_commit = 'No UPSTREAM_REPO'
        version = 'N/A'
        change_log = 'N/A'

    sysTime = get_readable_time(time() - boot_time())
    botTime = get_readable_time(time() - botStartTime)
    total, used, free, disk= disk_usage('/')
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(net_io_counters().bytes_sent)
    recv = get_readable_file_size(net_io_counters().bytes_recv)
    cpuUsage = cpu_percent(interval=1)
    v_core = cpu_count(logical=True) - cpu_count(logical=False)
    memory = virtual_memory()
    swap = swap_memory()
    mem_p = memory.percent

    DIR = 'Unlimited' if config_dict['DIRECT_LIMIT'] == '' else config_dict['DIRECT_LIMIT']
    YTD = 'Unlimited' if config_dict['YTDLP_LIMIT'] == '' else config_dict['YTDLP_LIMIT']
    GDL = 'Unlimited' if config_dict['GDRIVE_LIMIT'] == '' else config_dict['GDRIVE_LIMIT']
    TOR = 'Unlimited' if config_dict['TORRENT_LIMIT'] == '' else config_dict['TORRENT_LIMIT']
    CLL = 'Unlimited' if config_dict['CLONE_LIMIT'] == '' else config_dict['CLONE_LIMIT']
    MGA = 'Unlimited' if config_dict['MEGA_LIMIT'] == '' else config_dict['MEGA_LIMIT']
    TGL = 'Unlimited' if config_dict['LEECH_LIMIT'] == '' else config_dict['LEECH_LIMIT']
    UMT = 'Unlimited' if config_dict['USER_MAX_TASKS'] == '' else config_dict['USER_MAX_TASKS']
    BMT = 'Unlimited' if config_dict['QUEUE_ALL'] == '' else config_dict['QUEUE_ALL']

    stats = f'<b><i><u>Zee Bot Statistics</u></i></b>\n\n'\
            f'<b><i><u>Repo Info</u></i></b>\n' \
            f'<b>Updated:</b> <code>{last_commit}</code>\n' \
            f'<b>Version:</b> <code>{version}</code>\n' \
            f'<b>Change Log:</b> <code>{change_log}</code>\n\n' \
            f'<b><i><u>Bot Info</u></i></b>\n' \
            f'<b>SYS UPTM:</b> <code>{sysTime}</code>\n' \
            f'<b>BOT UPTM:</b> <code>{botTime}</code>\n\n' \
            f'<b>CPU:</b> <code>{get_progress_bar_string(cpuUsage)} {cpuUsage}%</code>\n' \
            f'<b>CPU Total Core(s):</b> <code>{cpu_count(logical=True)}</code>\n' \
            f'<b>P-Core(s):</b> <code>{cpu_count(logical=False)}</code> | <b>V-Core(s):</b> <code>{v_core}</code>\n' \
            f'<b>Frequency:</b> <code>{cpu_freq(percpu=False).current / 1000:.2f} GHz</code>\n\n' \
            f'<b>RAM:</b> <code>{get_progress_bar_string(mem_p)} {mem_p}%</code>\n' \
            f'<b>RAM In Use:</b> <code>{get_readable_file_size(memory.used)}</code> [{mem_p}%]\n' \
            f'<b>Total:</b> <code>{get_readable_file_size(memory.total)}</code> | <b>Free:</b> <code>{get_readable_file_size(memory.available)}</code>\n\n' \
            f'<b>SWAP:</b> <code>{get_progress_bar_string(swap.percent)} {swap.percent}%</code>\n' \
            f'<b>SWAP In Use:</b> <code>{get_readable_file_size(swap.used)}</code> [{swap.percent}%]\n' \
            f'<b>Allocated</b> <code>{get_readable_file_size(swap.total)}</code> | <b>Free:</b> <code>{get_readable_file_size(swap.free)}</code>\n\n' \
            f'<b>DISK:</b> <code>{get_progress_bar_string(disk)} {disk}%</code>\n' \
            f'<b>Drive In Use:</b> <code>{used}</code> [{disk}%]\n' \
            f'<b>Total:</b> <code>{total}</code> | <b>Free:</b> <code>{free}</code>\n\n' \
            f'<b>UL:</b> <code>{sent}</code> | <b>DL:</b> <code>{recv}</code>\n\n' \
            f'<b><i><u>Bot Limits</u></i></b>\n' \
            f'<code>Torrent   : {TOR}</code> <b>GB</b>\n' \
            f'<code>G-Drive   : {GDL}</code> <b>GB</b>\n' \
            f'<code>Yt-Dlp    : {YTD}</code> <b>GB</b>\n' \
            f'<code>Direct    : {DIR}</code> <b>GB</b>\n' \
            f'<code>Clone     : {CLL}</code> <b>GB</b>\n' \
            f'<code>Leech     : {TGL}</code> <b>GB</b>\n' \
            f'<code>MEGA      : {MGA}</code> <b>GB</b>\n' \
            f'<code>User Tasks: {UMT}</code>\n' \
            f'<code>Bot Tasks : {BMT}</code>'
    reply_message = await sendMessage(message, stats)
    await auto_delete_message(message, reply_message)


async def start(_, message):
    if len(message.command) > 1:
        userid = message.from_user.id
        input_token = message.command[1]
        if userid not in user_data:
            return await sendMessage(message, 'This token is not yours!\n\nKindly generate your own.')
        data = user_data[userid]
        if 'token' not in data or data['token'] != input_token:
            return await sendMessage(message, 'Token already used!\n\nKindly generate a new one.')
        data['token'] = str(uuid4())
        data['time'] = time()
        user_data[userid].update(data)
        msg = 'Token refreshed successfully!\n\n'
        msg += f'Validity: {get_readable_time(int(config_dict["TOKEN_TIMEOUT"]))}'
        return await sendMessage(message, msg)
    elif config_dict['DM_MODE']:
        start_string = 'Bot Started.\n' \
                       'Now I can send your stuff here.\n' \
                       'Use me here: @Z_Mirror'
    else:
        start_string = 'Sorry, you cant use me here!\n' \
                       'Join @Z_Mirror to use me.\n' \
                       'Thank You'
    await sendMessage(message, start_string)


async def restart(_, message):
    restart_message = await sendMessage(message, "Restarting...")
    if scheduler.running:
        scheduler.shutdown(wait=False)
    for interval in [QbInterval, Interval]:
        if interval:
            interval[0].cancel()
    await sync_to_async(clean_all)
    proc1 = await create_subprocess_exec('pkill', '-9', '-f', 'gunicorn|aria2c|qbittorrent-nox|ffmpeg|rclone')
    proc2 = await create_subprocess_exec('python3', 'update.py')
    await gather(proc1.wait(), proc2.wait())
    async with aiopen(".restartmsg", "w") as f:
        await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    osexecl(executable, executable, "-m", "bot")

async def ping(_, message):
    start_time = monotonic()
    reply = await sendMessage(message, "Starting Ping")
    end_time = monotonic()
    ping_time = int((end_time - start_time) * 1000)
    await editMessage(reply, f'{ping_time} ms')

async def log(_, message):
    await sendFile(message, 'Z_Logs.txt')

help_string = f'''
<b>NOTE: Click on any CMD to see more detalis.</b>

/{BotCommands.MirrorCommand[0]} or /{BotCommands.MirrorCommand[1]}: Upload to Cloud Drive.
/{BotCommands.ZipMirrorCommand[0]} or /{BotCommands.ZipMirrorCommand[1]}: Upload as zip.
/{BotCommands.UnzipMirrorCommand[0]} or /{BotCommands.UnzipMirrorCommand[1]}: Unzip before upload.

<b>Use qBit commands for torrents only:</b>
/{BotCommands.QbMirrorCommand[0]} or /{BotCommands.QbMirrorCommand[1]}: Download using qBittorrent and Upload to Cloud Drive.
/{BotCommands.QbZipMirrorCommand[0]} or /{BotCommands.QbZipMirrorCommand[1]}: Download using qBittorrent and upload as zip.
/{BotCommands.QbUnzipMirrorCommand[0]} or /{BotCommands.QbUnzipMirrorCommand[1]}: Download using qBittorrent and unzip before upload.

/{BotCommands.BtSelectCommand}: Select files from torrents by gid or reply.
/{BotCommands.CategorySelect}: Change upload category for Google Drive.

<b>Use Yt-Dlp commands for YouTube or any videos:</b>
/{BotCommands.YtdlCommand[0]} or /{BotCommands.YtdlCommand[1]}: Mirror yt-dlp supported link.
/{BotCommands.YtdlZipCommand[0]} or /{BotCommands.YtdlZipCommand[1]}: Mirror yt-dlp supported link as zip.

<b>Use Leech commands for upload to Telegram:</b>
/{BotCommands.LeechCommand[0]} or /{BotCommands.LeechCommand[1]}: Upload to Telegram.
/{BotCommands.ZipLeechCommand[0]} or /{BotCommands.ZipLeechCommand[1]}: Upload to Telegram as zip.
/{BotCommands.UnzipLeechCommand[0]} or /{BotCommands.UnzipLeechCommand[1]}: Unzip before upload to Telegram.
/{BotCommands.QbLeechCommand[0]} or /{BotCommands.QbLeechCommand[1]}: Download using qBittorrent and upload to Telegram(For torrents only).
/{BotCommands.QbZipLeechCommand[0]} or /{BotCommands.QbZipLeechCommand[1]}: Download using qBittorrent and upload to Telegram as zip(For torrents only).
/{BotCommands.QbUnzipLeechCommand[0]} or /{BotCommands.QbUnzipLeechCommand[1]}: Download using qBittorrent and unzip before upload to Telegram(For torrents only).
/{BotCommands.YtdlLeechCommand[0]} or /{BotCommands.YtdlLeechCommand[1]}: Download using Yt-Dlp(supported link) and upload to telegram.
/{BotCommands.YtdlZipLeechCommand[0]} or /{BotCommands.YtdlZipLeechCommand[1]}: Download using Yt-Dlp(supported link) and upload to telegram as zip.

/leech{BotCommands.DeleteCommand} [telegram_link]: Delete replies from telegram (Only Owner & Sudo).

<b>G-Drive commands:</b>
/{BotCommands.CloneCommand}: Copy file/folder to Cloud Drive.
/{BotCommands.CountCommand} [drive_url]: Count file/folder of Google Drive.
/{BotCommands.DeleteCommand} [drive_url]: Delete file/folder from Google Drive (Only Owner & Sudo).

<b>Cancel Tasks:</b>
/{BotCommands.CancelMirror[0]} or /{BotCommands.CancelMirror[1]}: Cancel task by gid or reply.
/{BotCommands.CancelAllCommand[0]} : Cancel all tasks which added by you /{BotCommands.CancelAllCommand[1]} to in bots.

<b>Torrent/Drive Search:</b>
/{BotCommands.ListCommand} [query]: Search in Google Drive(s).
/{BotCommands.SearchCommand} [query]: Search for torrents with API.

<b>Bot Settings:</b>
/{BotCommands.UserSetCommand}: Open User settings.
/{BotCommands.UsersCommand}: show users settings (Only Owner & Sudo).
/{BotCommands.BotSetCommand}: Open Bot settings (Only Owner & Sudo).

<b>Authentication:</b>
/{BotCommands.AuthorizeCommand}: Authorize a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.UnAuthorizeCommand}: Unauthorize a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.AddSudoCommand}: Add sudo user (Only Owner).
/{BotCommands.RmSudoCommand}: Remove sudo users (Only Owner).

<b>Bot Stats:</b>
/{BotCommands.StatusCommand[0]} or /{BotCommands.StatusCommand[1]}: Shows a status of all active tasks.
/{BotCommands.StatsCommand[0]} or /{BotCommands.StatsCommand[1]}: Show server stats.
/{BotCommands.PingCommand[0]} or /{BotCommands.PingCommand[1]}: Check how long it takes to Ping the Bot.

<b>Maintainance:</b>
/{BotCommands.RestartCommand[0]}: Restart and update the bot (Only Owner & Sudo).
/{BotCommands.RestartCommand[1]}: Restart and update all bots (Only Owner & Sudo).
/{BotCommands.LogCommand}: Get a log file of the bot. Handy for getting crash reports (Only Owner & Sudo).

<b>Extras:</b>
/{BotCommands.ShellCommand}: Run shell commands (Only Owner).
/{BotCommands.EvalCommand}: Run Python Code Line | Lines (Only Owner).
/{BotCommands.ExecCommand}: Run Commands In Exec (Only Owner).
/{BotCommands.ClearLocalsCommand}: Clear {BotCommands.EvalCommand} or {BotCommands.ExecCommand} locals (Only Owner).

<b>RSS Feed:</b>
/{BotCommands.RssCommand}: Open RSS Menu.

<b>Attention: Read the first line again!</b>
'''


async def bot_help(_, message):
    reply_message = await sendMessage(message, help_string)
    await auto_delete_message(message, reply_message)


async def restart_notification():
    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
    else:
        chat_id, msg_id = 0, 0

    async def send_incompelete_task_message(cid, msg):
        try:
            if msg.startswith('Restarted Successfully!'):
                await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text='Restarted Successfully!')
                await bot.send_message(chat_id, msg, disable_web_page_preview=True, reply_to_message_id=msg_id)
                await aioremove(".restartmsg")
            else:
                await bot.send_message(chat_id=cid, text=msg, disable_web_page_preview=True,
                                       disable_notification=True)
        except Exception as e:
            LOGGER.error(e)
    if DATABASE_URL:
        if INCOMPLETE_TASK_NOTIFIER and (notifier_dict := await DbManger().get_incomplete_tasks()):
            for cid, data in notifier_dict.items():
                msg = 'Restarted Successfully!' if cid == chat_id else 'Bot Restarted!'
                for tag, links in data.items():
                    msg += f"\n\n👤 {tag} Do your tasks again. \n"
                    for index, link in enumerate(links, start=1):
                        msg += f" {index}: {link} \n"
                        if len(msg.encode()) > 4000:
                            await send_incompelete_task_message(cid, msg)
                            msg = ''
                if msg:
                    await send_incompelete_task_message(cid, msg)

        if STOP_DUPLICATE_TASKS:
            await DbManger().clear_download_links()


    if await aiopath.isfile(".restartmsg"):
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text='Restarted Successfully!')
        except:
            pass
        await aioremove(".restartmsg")


async def main():
    await gather(start_cleanup(), torrent_search.initiate_search_tools(), restart_notification(), set_commands(bot))

    bot.add_handler(MessageHandler(
        start, filters=command(BotCommands.StartCommand)))
    bot.add_handler(MessageHandler(log, filters=command(
        BotCommands.LogCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(restart, filters=command(
        BotCommands.RestartCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(ping, filters=command(
        BotCommands.PingCommand) & CustomFilters.authorized))
    bot.add_handler(MessageHandler(bot_help, filters=command(
        BotCommands.HelpCommand) & CustomFilters.authorized))
    bot.add_handler(MessageHandler(stats, filters=command(
        BotCommands.StatsCommand) & CustomFilters.authorized))
    LOGGER.info("Congratulations, Bot Started Successfully!")
    signal(SIGINT, exit_clean_up)

bot.loop.run_until_complete(main())
bot.loop.run_forever()