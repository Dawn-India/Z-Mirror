from re import match as re_match, findall as re_findall
from threading import Thread, Event
from time import time
from math import ceil
from html import escape
from requests import head as rhead
from urllib.request import urlopen
from bot import download_dict, download_dict_lock, STATUS_LIMIT, botStartTime, DOWNLOAD_DIR, WEB_PINCODE, BASE_URL
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
import shutil
import psutil
from psutil import virtual_memory, cpu_percent, disk_usage
from telegram import InlineKeyboardMarkup
from telegram.error import RetryAfter
from telegram.ext import CallbackQueryHandler
from telegram.message import Message
from telegram.update import Update
from bot import *

MAGNET_REGEX = r"magnet:\?xt=urn:btih:[a-zA-Z0-9]*"

URL_REGEX = r"(?:(?:https?|ftp):\/\/)?[\w/\-?=%.]+\.[\w/\-?=%.]+"

COUNT = 0
PAGE_NO = 1

class MirrorStatus:
    STATUS_UPLOADING = "Uploading"
    STATUS_DOWNLOADING = "Downloading"
    STATUS_CLONING = "Cloning"
    STATUS_WAITING = "Queued"
    STATUS_PAUSED = "Paused"
    STATUS_ARCHIVING = "Archiving"
    STATUS_EXTRACTING = "Extracting"
    STATUS_SPLITTING = "Splitting"
    STATUS_CHECKING = "CheckingUp"
    STATUS_SEEDING = "Seeding"

class EngineStatus:
    STATUS_ARIA = "Aria2c"
    STATUS_GD = "Google Api"
    STATUS_MEGA = "Mega Api"
    STATUS_QB = "Bittorrent"
    STATUS_TG = "Pyrogram"
    STATUS_YT = "YT-dlp"
    STATUS_EXT = "pExtract"
    STATUS_SPLIT = "FFmpeg"
    STATUS_ZIP = "p7zip"

SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

class setInterval:
    def __init__(self, interval, action):
        self.interval = interval
        self.action = action
        self.stopEvent = Event()
        thread = Thread(target=self.__setInterval)
        thread.start()

    def __setInterval(self):
        nextTime = time() + self.interval
        while not self.stopEvent.wait(nextTime - time()):
            nextTime += self.interval
            self.action()

    def cancel(self):
        self.stopEvent.set()

def get_readable_file_size(size_in_bytes) -> str:
    if size_in_bytes is None:
        return '0B'
    index = 0
    while size_in_bytes >= 1024:
        size_in_bytes /= 1024
        index += 1
    try:
        return f'{round(size_in_bytes, 2)}{SIZE_UNITS[index]}'
    except IndexError:
        return 'File too large'

def getDownloadByGid(gid):
    with download_dict_lock:
        for dl in list(download_dict.values()):
            status = dl.status()
            if dl.gid() == gid:
                return dl
    return None

def getAllDownload(req_status: str):
    with download_dict_lock:
        for dl in list(download_dict.values()):
            status = dl.status()
            if req_status in ['all', status]:
                return dl
    return None

def bt_selection_buttons(id_: str):
    gid = id_[:12] if len(id_) > 20 else id_
    pincode = ""
    for n in id_:
        if n.isdigit():
            pincode += str(n)
        if len(pincode) == 4:
            break

    buttons = ButtonMaker()
    if WEB_PINCODE:
        buttons.buildbutton("Select Files", f"{BASE_URL}/app/files/{id_}")
        buttons.sbutton("Pincode", f"btsel pin {gid} {pincode}")
    else:
        buttons.buildbutton("Select Files", f"{BASE_URL}/app/files/{id_}?pin_code={pincode}")
    buttons.sbutton("Done Selecting", f"btsel done {gid} {id_}")
    return InlineKeyboardMarkup(buttons.build_menu(2))

def get_progress_bar_string(status):
    completed = status.processed_bytes() / 8
    total = status.size_raw() / 8
    p = 0 if total == 0 else round(completed * 100 / total)
    p = min(max(p, 0), 100)
    cFull = p // 8
    p_str = '⬢' * cFull
    p_str += '⬡' * (12 - cFull)
    p_str = f"{p_str}"
    return p_str

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

def auto_delete_message(bot, cmd_message: Message, bot_message: Message):
    if AUTO_DELETE_MESSAGE_DURATION != -1:
        sleep(AUTO_DELETE_MESSAGE_DURATION)
        try:
            deleteMessage(bot, cmd_message)
            deleteMessage(bot, bot_message)
        except AttributeError:
            pass

def editMessage(text: str, message: Message, reply_markup=None):
    try:
        bot.editMessageText(text=text, message_id=message.message_id,
                              chat_id=message.chat.id,reply_markup=reply_markup,
                              parse_mode='HTMl', disable_web_page_preview=True)
    except RetryAfter as r:
        LOGGER.warning(str(r))
        sleep(r.retry_after * 1.5)
        return editMessage(text, message, reply_markup)
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)

def deleteMessage(bot, message: Message):
    try:
        bot.deleteMessage(chat_id=message.chat.id,
                           message_id=message.message_id)
    except Exception as e:
        LOGGER.error(str(e))

def delete_all_messages():
    with status_reply_dict_lock:
        for data in list(status_reply_dict.values()):
            try:
                deleteMessage(bot, data[0])
                del status_reply_dict[data[0].chat.id]
            except Exception as e:
                LOGGER.error(str(e))

def update_all_messages(force=False):
    with status_reply_dict_lock:
        if not force and (not status_reply_dict or not Interval or time() - list(status_reply_dict.values())[0][1] < 3):
            return
        for chat_id in status_reply_dict:
            status_reply_dict[chat_id][1] = time()

    msg, buttons = get_readable_message()
    if msg is None:
        return
    with status_reply_dict_lock:
        for chat_id in status_reply_dict:
            if status_reply_dict[chat_id] and msg != status_reply_dict[chat_id][0].text:
                if buttons == "":
                    rmsg = editMessage(msg, status_reply_dict[chat_id][0])
                else:
                    rmsg = editMessage(msg, status_reply_dict[chat_id][0], buttons)
                if rmsg == "Message to edit not found":
                    del status_reply_dict[chat_id]
                    return
                status_reply_dict[chat_id][0].text = msg
                status_reply_dict[chat_id][1] = time()

ONE, TWO, THREE = range(3)

def refresh(update, context):
    query = update.callback_query
    query.edit_message_text(text="Refreshing Status...⏳")
    sleep(5)
    update_all_messages()

def close(update, context):
    chat_id = update.effective_chat.id
    user_id = update.callback_query.from_user.id
    bot = context.bot
    query = update.callback_query
    admins = bot.get_chat_member(chat_id, user_id).status in [
        "creator",
        "administrator",
    ] or user_id in [OWNER_ID]
    if admins:
        delete_all_messages()
    else:
        query.answer(text="Sorry, only Admins can close !", show_alert=True)

def pop_up_stats(update, context):
    query = update.callback_query
    stats = bot_sys_stats()
    query.answer(text=stats, show_alert=True)

def bot_sys_stats():
    currentTime = get_readable_time(time() - botStartTime)
    total, used, free, disk = disk_usage('/')
    disk_t = get_readable_file_size(total)
    disk_f = get_readable_file_size(free)
    memory = virtual_memory()
    mem_p = memory.percent
    recv = get_readable_file_size(psutil.net_io_counters().bytes_recv)
    sent = get_readable_file_size(psutil.net_io_counters().bytes_sent)
    cpuUsage = cpu_percent(interval=1)
    return f"""
BOT SYSTEM STATS
CPU:  {progress_bar(cpuUsage)} {cpuUsage}%
RAM: {progress_bar(mem_p)} {mem_p}%
DISK: {progress_bar(disk)} {disk}%
T: {disk_t}GB | F: {disk_f}GB
Working For: {currentTime}
T-DL: {recv} | T-UL: {sent}
Made with ❤️ by Dawn
"""

#---Thanks for deleting my name ❤️ Appreciate it---#
#---Remove this line too, who cares---#

dispatcher.add_handler(CallbackQueryHandler(refresh, pattern=f"^{str(ONE)}$"))
dispatcher.add_handler(CallbackQueryHandler(close, pattern=f"^{str(TWO)}$"))
dispatcher.add_handler(CallbackQueryHandler(pop_up_stats, pattern=f"^{str(THREE)}$"))

def get_readable_message():
    with download_dict_lock:
        msg = f"Powered By <b>{TITLE_NAME}</b>"
        if STATUS_LIMIT is not None:
            tasks = len(download_dict)
            global pages
            pages = ceil(tasks/STATUS_LIMIT)
            if PAGE_NO > pages and pages != 0:
                globals()['COUNT'] -= STATUS_LIMIT
                globals()['PAGE_NO'] -= 1
        for index, download in enumerate(list(download_dict.values())[COUNT:], start=1):
            msg += f"\n\n<b>File Name:</b> <code>{escape(str(download.name()))}</code>"
            msg += f"\n\n<b>Status:</b> <code>{download.status()}</code> <b>Using:</b> <code>{download.eng()}</code>"
            if download.status() not in [MirrorStatus.STATUS_SEEDING]:
                msg += f"\n{get_progress_bar_string(download)} ↣ {download.progress()}"
                if download.status() in [MirrorStatus.STATUS_DOWNLOADING,
                                         MirrorStatus.STATUS_WAITING,
                                         MirrorStatus.STATUS_PAUSED]:
                    msg += f"\n\n<b>Downloaded:</b> <code>{get_readable_file_size(download.processed_bytes())}</code> of <code>{download.size()}</code> at: <code>{download.speed()}</code>"
                elif download.status() == MirrorStatus.STATUS_UPLOADING:
                    msg += f"\n\n<b>Uploaded:</b> <code>{get_readable_file_size(download.processed_bytes())}</code> of <code>{download.size()}</code> at: <code>{download.speed()}</code>"
                elif download.status() == MirrorStatus.STATUS_CLONING:
                    msg += f"\n\n<b>Cloned:</b> <code>{get_readable_file_size(download.processed_bytes())}</code> of <code>{download.size()}</code> at: <code>{download.speed()}</code>"
                elif download.status() == MirrorStatus.STATUS_ARCHIVING:
                    msg += f"\n\n<b>Archived:</b> <code>{get_readable_file_size(download.processed_bytes())}</code> of <code>{download.size()}</code> at: <code>{download.speed()}</code>"
                elif download.status() == MirrorStatus.STATUS_EXTRACTING:
                    msg += f"\n\n<b>Extracted:</b> <code>{get_readable_file_size(download.processed_bytes())}</code> of <code>{download.size()}</code> at: <code>{download.speed()}</code>"
                elif download.status() == MirrorStatus.STATUS_SPLITTING:
                    msg += f"\n\n<b>Splitted:</b> <code>{get_readable_file_size(download.processed_bytes())}</code> of <code>{download.size()}</code> at: <code>{download.speed()}</code>"
                msg += f"\n<b>ETA:</b> <code>{download.eta()}</code> <b>Elapsed:</b> <code>{get_readable_time(time() - download.message.date.timestamp())}</code>"
                msg += f'\n\n<b>Task By:</b> <a href="https://t.me/c/{str(download.message.chat.id)[4:]}/{download.message.message_id}">{download.message.from_user.first_name}</a>'
                try:
                    msg += f"\n<b>Seeders:</b> <code>{download.aria_download().num_seeders}</code>" \
                           f" | <b>Peers:</b> <code>{download.aria_download().connections}</code>"
                    msg += f"\n<b>To Select:</b> <code>/{BotCommands.BtSelectCommand} {download.gid()}</code>"
                except:
                    pass
                try:
                    msg += f"\n<b>Seeders:</b> <code>{download.torrent_info().num_seeds}</code>" \
                           f" | <b>Leechers:</b> <code>{download.torrent_info().num_leechs}</code>"
                    msg += f"\n<b>To Select:</b> <code>/{BotCommands.BtSelectCommand} {download.gid()}</code>"
                except:
                    pass

            elif download.status() == MirrorStatus.STATUS_SEEDING:
                msg += f"\n<b>Size:</b> {download.size()}"
                msg += f"\n<b>Engine:</b> <code>qBittorrent v4.4.2</code>"
                msg += f"\n<b>Speed:</b> {get_readable_file_size(download.torrent_info().upspeed)}/s"
                msg += f" | <b>Uploaded:</b> {get_readable_file_size(download.torrent_info().uploaded)}"
                msg += f"\n<b>Ratio:</b> {round(download.torrent_info().ratio, 3)}"
                msg += f" | <b>Time:</b> {get_readable_time(download.torrent_info().seeding_time)}"
            else:
                msg += f"\n<b>Size:</b>n{download.size()}"
                msg += f"\n<b>Engine:</b> {download.eng()}"
            msg += f"\n<b>To Cancel:</b> <code>/{BotCommands.CancelMirror} {download.gid()}</code>"
            msg += f"\n"
            if STATUS_LIMIT is not None and index == STATUS_LIMIT:
                break
        if len(msg) == 0:
            return None, None
        bmsg = f"\n<b>___________________________________</b>"
        bmsg += f"\n<b>Disk:</b> <code>{get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)}</code>"
        bmsg += f"<b> | UPTM:</b> <code>{get_readable_time(time() - botStartTime)}</code>"
        dlspeed_bytes = 0
        upspeed_bytes = 0
        for download in list(download_dict.values()):
            spd = download.speed()
            if download.status() == MirrorStatus.STATUS_DOWNLOADING:
                if 'K' in spd:
                    dlspeed_bytes += float(spd.split('K')[0]) * 1024
                elif 'M' in spd:
                    dlspeed_bytes += float(spd.split('M')[0]) * 1048576
            elif download.status() == MirrorStatus.STATUS_UPLOADING:
                if 'KB/s' in spd:
                    upspeed_bytes += float(spd.split('K')[0]) * 1024
                elif 'MB/s' in spd:
                    upspeed_bytes += float(spd.split('M')[0]) * 1048576
        bmsg += f"\n<b>DL:</b> <code>{get_readable_file_size(dlspeed_bytes)}/s</code><b> | UL:</b> <code>{get_readable_file_size(upspeed_bytes)}/s</code>"

        buttons = ButtonMaker()
        buttons.sbutton("Refresh", str(ONE))
        buttons.sbutton("Close", str(TWO))
        buttons.sbutton("Statistics", str(THREE))
        sbutton = InlineKeyboardMarkup(buttons.build_menu(2))

        if STATUS_LIMIT is not None and tasks > STATUS_LIMIT:
            msg += f"\n<b>Total Tasks:</b> {tasks}\n"
            buttons = ButtonMaker()
            buttons.sbutton("Prev", "status pre")
            buttons.sbutton(f"{PAGE_NO}/{pages}", str(THREE))
            buttons.sbutton("Next", "status nex")
            buttons.sbutton("Refresh", str(ONE))
            buttons.sbutton("Close", str(TWO))
            button = InlineKeyboardMarkup(buttons.build_menu(3))

            return msg + bmsg, button
        return msg + bmsg, sbutton

def turn(data):
    try:
        with download_dict_lock:
            global COUNT, PAGE_NO
            if data[1] == "nex":
                if PAGE_NO == pages:
                    COUNT = 0
                    PAGE_NO = 1
                else:
                    COUNT += STATUS_LIMIT
                    PAGE_NO += 1
            elif data[1] == "pre":
                if PAGE_NO == 1:
                    COUNT = STATUS_LIMIT * (pages - 1)
                    PAGE_NO = pages
                else:
                    COUNT -= STATUS_LIMIT
                    PAGE_NO -= 1
        return True
    except:
        return False

def get_readable_time(seconds: int) -> str:
    result = ''
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days != 0:
        result += f'{days}d'
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f'{hours}h'
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f'{minutes}m'
    seconds = int(seconds)
    result += f'{seconds}s'
    return result

def is_url(url: str):
    url = re_findall(URL_REGEX, url)
    return bool(url)

def is_gdrive_link(url: str):
    return "drive.google.com" in url

def is_gdtot_link(url: str):
    url = re_match(r'https?://.+\.gdtot\.\S+', url)
    return bool(url)

def is_appdrive_link(url: str):
    url = re_match(r'https?://(?:\S*\.)?(?:appdrive|driveapp)\.info/\S+', url)
    return bool(url)

def is_mega_link(url: str):
    return "mega.nz" in url or "mega.co.nz" in url

def get_mega_link_type(url: str):
    if "folder" in url:
        return "folder"
    elif "file" in url:
        return "file"
    elif "/#F!" in url:
        return "folder"
    return "file"

def is_magnet(url: str):
    magnet = re_findall(MAGNET_REGEX, url)
    return bool(magnet)

def new_thread(fn):
    """To use as decorator to make a function call threaded.
    Needs import
    from threading import Thread"""

    def wrapper(*args, **kwargs):
        thread = Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper

def get_content_type(link: str) -> str:
    try:
        res = rhead(link, allow_redirects=True, timeout=5, headers = {'user-agent': 'Wget/1.12'})
        content_type = res.headers.get('content-type')
    except:
        try:
            res = urlopen(link, timeout=5)
            info = res.info()
            content_type = info.get_content_type()
        except:
            content_type = None
    return content_type