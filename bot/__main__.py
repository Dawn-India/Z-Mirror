from asyncio import create_subprocess_exec
from os import execl as osexecl
from signal import SIGINT, signal
from sys import executable
from time import time

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import remove as aioremove
from psutil import (boot_time, cpu_count, cpu_percent, cpu_freq, disk_usage,
                    net_io_counters, swap_memory, virtual_memory)
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import (DATABASE_URL, INCOMPLETE_TASK_NOTIFIER, LOGGER,
                 STOP_DUPLICATE_TASKS, Interval, QbInterval, bot, botStartTime,
                 config_dict, scheduler)

from .helper.ext_utils.bot_utils import (cmd_exec, get_readable_file_size,
                                         get_readable_time, set_commands,
                                         sync_to_async)
from .helper.ext_utils.db_handler import DbManger
from .helper.ext_utils.fs_utils import clean_all, exit_clean_up, start_cleanup
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.message_utils import (editMessage, sendFile,
                                                   sendMessage)
from .modules import (anonymous, authorize, bot_settings, bt_select,
                      cancel_mirror, category_select, count, delete,
                      drive_list, eval, mirror_leech, mirror_status, rmdb, rss,
                      search, shell, users_settings, ytdlp)

def progress_bar(percentage):
    p_used = '⬢'
    p_total = '⬡'
    if isinstance(percentage, str):
        return 'NaN'
    try:
        percentage=int(percentage)
    except:
        percentage = 0
    return ''.join(
        p_used if i <= percentage // 10 else p_total for i in range(1, 11)
    )

async def stats(client, message):
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
    if await aiopath.exists('.git'):
        last_commit = await cmd_exec("git log -1 --date=short --pretty=format:'%cr \n<b>Version: </b> %cd'", True)
        last_commit = last_commit[0]
    else:
        last_commit = 'No UPSTREAM_REPO'
    stats = f'<b><i><u>Bot Statistics</u></i></b>\n\n'\
            f'<code>CPU  :{progress_bar(cpuUsage)} {cpuUsage}%</code>\n' \
            f'<code>RAM  :{progress_bar(mem_p)} {mem_p}%</code>\n' \
            f'<code>SWAP :{progress_bar(swap.percent)} {swap.percent}%</code>\n' \
            f'<code>DISK :{progress_bar(disk)} {disk}%</code>\n\n' \
            f'<b>Updated:</b> {last_commit}\n' \
            f'<b>SYS Uptime:</b> <code>{sysTime}</code>\n' \
            f'<b>BOT Uptime:</b> <code>{botTime}</code>\n\n' \
            f'<b>CPU Total Core(s):</b> <code>{cpu_count(logical=True)}</code>\n' \
            f'<b>P-Core(s):</b> <code>{cpu_count(logical=False)}</code> | <b>V-Core(s):</b> <code>{v_core}</code>\n' \
            f'<b>Frequency:</b> <code>{cpu_freq(percpu=False).current} Mhz</code>\n\n' \
            f'<b>RAM In Use:</b> <code>{get_readable_file_size(memory.used)}</code> [{mem_p}%]\n' \
            f'<b>Total:</b> <code>{get_readable_file_size(memory.total)}</code> | <b>Free:</b> <code>{get_readable_file_size(memory.available)}</code>\n\n' \
            f'<b>SWAP In Use:</b> <code>{get_readable_file_size(swap.used)}</code> [{swap.percent}%]\n' \
            f'<b>Allocated</b> <code>{get_readable_file_size(swap.total)}</code> | <b>Free:</b> <code>{get_readable_file_size(swap.free)}</code>\n\n' \
            f'<b>Drive In Use:</b> <code>{used}</code> [{disk}%]\n' \
            f'<b>Total:</b> <code>{total}</code> | <b>Free:</b> <code>{free}</code>\n\n' \
            f'<b>Total Upload:</b> <code>{sent}</code>\n<b>Total Download:</b> <code>{recv}</code>\n'
    await sendMessage(message, stats)

async def start(client, message):
    if config_dict['DM_MODE']:
        start_string = 'Bot Started.\n' \
                    'Now I will send your files or links here.\n'
    else:
        start_string = 'Hey, Welcome dear. \n' \
                       'I can Mirror all your links To Google Drive! \n' \
                       'Unfortunately you are not authorized!\n' \
                       'Please deploy your own BOT!' \
                       'Created With Love by @Z_Mirror . \n' \
                       'Thank You!'
    await sendMessage(message, start_string)

async def restart(client, message):
    restart_message = await sendMessage(message, "Restarting...")
    if scheduler.running:
        scheduler.shutdown(wait=False)
    if Interval:
        Interval[0].cancel()
        Interval.clear()
    if QbInterval:
        QbInterval[0].cancel()
        QbInterval.clear()
    await sync_to_async(clean_all)
    await (await create_subprocess_exec('pkill', '-9', '-f', '-e', 'gunicorn|aria2c|qbittorrent-nox|ffmpeg')).wait()
    await (await create_subprocess_exec('python3', 'update.py')).wait()
    async with aiopen(".restartmsg", "w") as f:
        await f.truncate(0)
        await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    osexecl(executable, executable, "-m", "bot")

async def ping(client, message):
    start_time = int(round(time() * 1000))
    reply = await sendMessage(message, "Starting Ping")
    end_time = int(round(time() * 1000))
    await editMessage(reply, f'{end_time - start_time} ms')

async def log(client, message):
    await sendFile(message, 'log.txt')

help_string = f'''
NOTE: Try each command without any argument to see more detalis.
/{BotCommands.MirrorCommand[0]} or /{BotCommands.MirrorCommand[1]}: Start mirroring to Google Drive.
/{BotCommands.ZipMirrorCommand[0]} or /{BotCommands.ZipMirrorCommand[1]}: Start mirroring and upload the file/folder compressed with zip extension.
/{BotCommands.UnzipMirrorCommand[0]} or /{BotCommands.UnzipMirrorCommand[1]}: Start mirroring and upload the file/folder extracted from any archive extension.
/{BotCommands.QbMirrorCommand[0]} or /{BotCommands.QbMirrorCommand[1]}: Start Mirroring to Google Drive using qBittorrent.
/{BotCommands.QbZipMirrorCommand[0]} or /{BotCommands.QbZipMirrorCommand[1]}: Start mirroring using qBittorrent and upload the file/folder compressed with zip extension.
/{BotCommands.QbUnzipMirrorCommand[0]} or /{BotCommands.QbUnzipMirrorCommand[1]}: Start mirroring using qBittorrent and upload the file/folder extracted from any archive extension.
/{BotCommands.YtdlCommand[0]} or /{BotCommands.YtdlCommand[1]}: Mirror yt-dlp supported link.
/{BotCommands.YtdlZipCommand[0]} or /{BotCommands.YtdlZipCommand[1]}: Mirror yt-dlp supported link as zip.
/{BotCommands.LeechCommand[0]} or /{BotCommands.LeechCommand[1]}: Start leeching to Telegram.
/{BotCommands.ZipLeechCommand[0]} or /{BotCommands.ZipLeechCommand[1]}: Start leeching and upload the file/folder compressed with zip extension.
/{BotCommands.UnzipLeechCommand[0]} or /{BotCommands.UnzipLeechCommand[1]}: Start leeching and upload the file/folder extracted from any archive extension.
/{BotCommands.QbLeechCommand[0]} or /{BotCommands.QbLeechCommand[1]}: Start leeching using qBittorrent.
/{BotCommands.QbZipLeechCommand[0]} or /{BotCommands.QbZipLeechCommand[1]}: Start leeching using qBittorrent and upload the file/folder compressed with zip extension.
/{BotCommands.QbUnzipLeechCommand[0]} or /{BotCommands.QbUnzipLeechCommand[1]}: Start leeching using qBittorrent and upload the file/folder extracted from any archive extension.
/{BotCommands.YtdlLeechCommand[0]} or /{BotCommands.YtdlLeechCommand[1]}: Leech yt-dlp supported link.
/{BotCommands.YtdlZipLeechCommand[0]} or /{BotCommands.YtdlZipLeechCommand[1]}: Leech yt-dlp supported link as zip.
/{BotCommands.CloneCommand} [drive_url]: Copy file/folder to Google Drive.
/{BotCommands.CountCommand} [drive_url]: Count file/folder of Google Drive.
/{BotCommands.DeleteCommand} [drive_url]: Delete file/folder from Google Drive (Only Owner & Sudo).
/leech{BotCommands.DeleteCommand} [telegram_link]: Delete replies from telegram (Only Owner & Sudo).
/{BotCommands.UserSetCommand} [query]: Users settings.
/{BotCommands.BotSetCommand} [query]: Bot settings.
/{BotCommands.BtSelectCommand}: Select files from torrents by gid or reply.
/{BotCommands.CategorySelect}: Change upload category for Google Drive.
/{BotCommands.CancelMirror} : Cancel task by gid or reply.
/{BotCommands.CancelAllCommand[0]} : Cancel all tasks which added by you {BotCommands.CancelAllCommand[1]} to in bots.
/{BotCommands.ListCommand} [query]: Search in Google Drive(s).
/{BotCommands.SearchCommand} [query]: Search for torrents with API.
/{BotCommands.StatusCommand[0]} or /{BotCommands.StatusCommand[1]}: Shows a status of all the downloads.
/{BotCommands.StatsCommand[0]} or /{BotCommands.StatsCommand[1]}: Show stats of the machine where the bot is hosted in.
/{BotCommands.PingCommand[0]} or /{BotCommands.PingCommand[1]}: Check how long it takes to Ping the Bot (Only Owner & Sudo).
/{BotCommands.AuthorizeCommand}: Authorize a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.UnAuthorizeCommand}: Unauthorize a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.UsersCommand}: show users settings (Only Owner & Sudo).
/{BotCommands.AddSudoCommand}: Add sudo user (Only Owner).
/{BotCommands.RmSudoCommand}: Remove sudo users (Only Owner).
/{BotCommands.RestartCommand[0]}: Restart and update the bot (Only Owner & Sudo).
/{BotCommands.RestartCommand[1]}: Restart all bots and update the bot (Only Owner & Sudo).
/{BotCommands.LogCommand}: Get a log file of the bot. Handy for getting crash reports (Only Owner & Sudo).
/{BotCommands.ShellCommand}: Run shell commands (Only Owner).
/{BotCommands.EvalCommand}: Run Python Code Line | Lines (Only Owner).
/{BotCommands.ExecCommand}: Run Commands In Exec (Only Owner).
/{BotCommands.ClearLocalsCommand}: Clear {BotCommands.EvalCommand} or {BotCommands.ExecCommand} locals (Only Owner).
/{BotCommands.RssCommand}: RSS Menu.
'''

async def bot_help(client, message):
    await sendMessage(message, help_string)

async def main():
    await set_commands(bot)
    await start_cleanup()
    await search.initiate_search_tools()
    if DATABASE_URL and STOP_DUPLICATE_TASKS:
        await DbManger().clear_download_links()
    if INCOMPLETE_TASK_NOTIFIER and DATABASE_URL:
        if notifier_dict := await DbManger().get_incomplete_tasks():
            for cid, data in notifier_dict.items():
                if await aiopath.isfile(".restartmsg"):
                    with open(".restartmsg") as f:
                        chat_id, msg_id = map(int, f)
                    msg = 'Restarted Successfully!'
                else:
                    msg = 'Bot Restarted!'
                for tag, links in data.items():
                    msg += f"\n\n👤 {tag} Do your tasks again. \n"
                    for index, link in enumerate(links, start=1):
                        msg += f" {index}: {link} \n"
                        if len(msg.encode()) > 4000:
                            if 'Restarted Successfully!' in msg and cid == chat_id:
                                try:
                                    await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text='Restarted Successfully!')
                                    await bot.send_message(chat_id, msg, disable_web_page_preview=True, reply_to_message_id=msg_id)
                                except:
                                    pass
                                await aioremove(".restartmsg")
                            else:
                                try:
                                    await bot.send_message(chat_id=cid, text=msg, disable_web_page_preview=True,
                                                           disable_notification=True)
                                except Exception as e:
                                    LOGGER.error(e)
                            msg = ''
                if 'Restarted Successfully!' in msg and cid == chat_id:
                    try:
                        await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text='Restarted Successfully!\n')
                        await bot.send_message(chat_id, msg, disable_web_page_preview=True, reply_to_message_id=msg_id)
                    except:
                        pass
                    await aioremove(".restartmsg")
                else:
                    try:
                        await bot.send_message(chat_id=cid, text=msg, disable_web_page_preview=True,
                                         disable_notification=True)
                    except Exception as e:
                        LOGGER.error(e)

    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="Restarted Successfully!")
        except:
            pass
        await aioremove(".restartmsg")

    bot.add_handler(MessageHandler(start, filters=command(BotCommands.StartCommand)))
    bot.add_handler(MessageHandler(log, filters=command(BotCommands.LogCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(restart, filters=command(BotCommands.RestartCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(ping, filters=command(BotCommands.PingCommand)))
    bot.add_handler(MessageHandler(bot_help, filters=command(BotCommands.HelpCommand)))
    bot.add_handler(MessageHandler(stats, filters=command(BotCommands.StatsCommand)))
    LOGGER.info("Bot Started Successfully!")
    signal(SIGINT, exit_clean_up)

bot.loop.run_until_complete(main())
bot.loop.run_forever()