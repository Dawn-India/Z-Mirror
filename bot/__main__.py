from os import execl, path, remove
from signal import SIGINT, signal
from subprocess import check_output, run
from sys import executable
from time import time

from psutil import (boot_time, cpu_count, cpu_percent, cpu_freq, disk_usage,
                    net_io_counters, swap_memory, virtual_memory)
from telegram.ext import CommandHandler

from bot import (DATABASE_URL, IGNORE_PENDING_REQUESTS,
                 INCOMPLETE_TASK_NOTIFIER, LOGGER, STOP_DUPLICATE_TASKS,
                 Interval, QbInterval, app, bot, botStartTime, config_dict,
                 dispatcher, main_loop, updater)
from bot.helper.ext_utils.bot_utils import (get_readable_file_size,
                                            get_readable_time, set_commands)
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.fs_utils import (clean_all, exit_clean_up,
                                           start_cleanup)
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (editMessage, sendLogFile, sendMessage)
from bot.modules import (authorize, bot_settings, bt_select, cancel_mirror,
                         category_select, count, delete, drive_list,
                         eval, mirror_leech, mirror_status, rmdb, rss,
                         save_message, search, shell, users_settings, ytdlp, anonymous)

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

def stats(update, context):
    if path.exists('.git'):
        last_commit = check_output(["git log -1 --date=short --pretty=format:'%cr \n<b>Version: </b> %cd'"], shell=True).decode()
    else:
        last_commit = 'No UPSTREAM_REPO'
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
            f'<b>Total:</b> <code>{total}</code> | <b>Free:</b> <code>{free}</code>\n' \
            f'<b>T-UL:</b> <code>{sent}</code> | <b>T-DL:</b> <code>{recv}</code>\n'
    sendMessage(stats, context.bot, update.message)

def start(update, context):
    if config_dict['DM_MODE']:
        start_string = 'Welcome | Z BOT is ready for you.\n' \
                       'Thanks for starting me in DM.\n' \
                       'Now I can send all of your files and links here.\n'
    else:
        start_string = 'Hey, Welcome dear. \n' \
                       'I can Mirror all your links To Google Drive! \n' \
                       'Unfortunately you are not authorized!\n' \
                       'Please deploy your own BOT!' \
                       'Created With Love by @Z_Mirror . \n' \
                       'Thank You!'
    sendMessage(start_string, context.bot, update.message)

def restart(update, context):
    restart_message = sendMessage("Restarting...", context.bot, update.message)
    if Interval:
        Interval[0].cancel()
        Interval.clear()
    if QbInterval:
        QbInterval[0].cancel()
        QbInterval.clear()
    clean_all()
    run(["pkill", "-9", "-f", "gunicorn|aria2c|qbittorrent-nox|ffmpeg"])
    run(["python3", "update.py"])
    with open(".restartmsg", "w") as f:
        f.truncate(0)
        f.write(f"{restart_message.chat.id}\n{restart_message.message_id}\n")
    execl(executable, executable, "-m", "bot")


def ping(update, context):
    start_time = int(round(time() * 1000))
    reply = sendMessage("Starting Ping", context.bot, update.message)
    end_time = int(round(time() * 1000))
    editMessage(f'{end_time - start_time} ms', reply)


def log(update, context):
    sendLogFile(context.bot, update.message)

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
/{BotCommands.UserSetCommand} : Users settings.
/{BotCommands.BotSetCommand} : Bot settings.
/{BotCommands.BtSelectCommand}: Select files from torrents by gid or reply.
/{BotCommands.CategorySelect}: Change upload category for Google Drive.
/{BotCommands.CancelMirror}: Cancel task by gid or reply.
/{BotCommands.CancelAllCommand[0]} : Cancel all tasks which added by you {BotCommands.CancelAllCommand[1]} to in bots.
/{BotCommands.ListCommand} [query]: Search in Google Drive(s).
/{BotCommands.SearchCommand} [query]: Search for torrents with API.
/{BotCommands.StatusCommand[0]} or /{BotCommands.StatusCommand[1]}: Shows a status of all the downloads.
/{BotCommands.StatsCommand}: Show stats of the machine where the bot is hosted in.
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
/{BotCommands.RssListCommand[0]} or /{BotCommands.RssListCommand[1]}: List all subscribed rss feed info (Only Owner & Sudo).
/{BotCommands.RssGetCommand[0]} or /{BotCommands.RssGetCommand[1]}: Force fetch last N links (Only Owner & Sudo).
/{BotCommands.RssSubCommand[0]} or /{BotCommands.RssSubCommand[1]}: Subscribe new rss feed (Only Owner & Sudo).
/{BotCommands.RssUnSubCommand[0]} or /{BotCommands.RssUnSubCommand[1]}: Unubscribe rss feed by title (Only Owner & Sudo).
/{BotCommands.RssSettingsCommand[0]} or /{BotCommands.RssSettingsCommand[1]} [query]: Rss Settings (Only Owner & Sudo).
/{BotCommands.RmdbCommand}: Remove task from the database.
'''

def bot_help(update, context):
    sendMessage(help_string, context.bot, update.message)

def main():
    set_commands(bot)
    start_cleanup()
    if DATABASE_URL and STOP_DUPLICATE_TASKS:
        DbManger().clear_download_links()
    if INCOMPLETE_TASK_NOTIFIER and DATABASE_URL:
        if notifier_dict:= DbManger().get_incomplete_tasks():
            for cid, data in notifier_dict.items():
                if path.isfile(".restartmsg"):
                    with open(".restartmsg") as f:
                        chat_id, msg_id = map(int, f)
                    msg = 'Restarted Successfully!'
                else:
                    msg = 'Bot Restarted!'
                for tag, links in data.items():
                    msg += f"\n\n{tag}: "
                    for index, link in enumerate(links, start=1):
                        msg += f" <a href='{link}'>{index}</a> |"
                        if len(msg.encode()) > 4000:
                            if 'Restarted Successfully!' in msg and cid == chat_id:
                                try:
                                    bot.editMessageText('Restarted Successfully!', chat_id, msg_id)
                                    bot.sendMessage(chat_id, msg, reply_to_message_id=msg_id)
                                except:
                                    pass
                                remove(".restartmsg")
                            else:
                                try:
                                    bot.sendMessage(cid, msg)
                                except Exception as e:
                                    LOGGER.error(e)
                            msg = ''
                if 'Restarted Successfully!' in msg and cid == chat_id:
                    try:
                        bot.editMessageText('Restarted Successfully!', chat_id, msg_id)
                        bot.sendMessage(chat_id, msg, reply_to_message_id=msg_id)
                    except:
                        pass
                    remove(".restartmsg")
                else:
                    try:
                        bot.sendMessage(cid, msg)
                    except Exception as e:
                        LOGGER.error(e)
    if path.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        try:
            bot.edit_message_text("Restarted Successfully!", chat_id, msg_id)
        except:
            pass
        remove(".restartmsg")

    start_handler = CommandHandler(BotCommands.StartCommand, start)
    log_handler = CommandHandler(BotCommands.LogCommand, log,
                                        filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
    restart_handler = CommandHandler(BotCommands.RestartCommand, restart,
                                        filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
    ping_handler = CommandHandler(BotCommands.PingCommand, ping,
                               filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
    help_handler = CommandHandler(BotCommands.HelpCommand, bot_help,
                               filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
    stats_handler = CommandHandler(BotCommands.StatsCommand, stats,
                               filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(ping_handler)
    dispatcher.add_handler(restart_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(stats_handler)
    dispatcher.add_handler(log_handler)

    updater.start_polling(drop_pending_updates=IGNORE_PENDING_REQUESTS)
    LOGGER.info("Bot Started Successfully!")
    signal(SIGINT, exit_clean_up)

app.start()
main()
main_loop.run_forever()
