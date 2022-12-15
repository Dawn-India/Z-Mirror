from re import findall as re_findall, match as re_match
from threading import Thread, Event
from time import time
from math import ceil
from html import escape
import psutil
from psutil import *
from requests import head as rhead
from urllib.request import urlopen
from bot import *
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from telegram.ext import CallbackQueryHandler

MAGNET_REGEX = r"magnet:\?xt=urn:btih:[a-zA-Z0-9]*"

URL_REGEX = r"(?:(?:https?|ftp):\/\/)?[\w/\-?=%.]+\.[\w/\-?=%.]+"

COUNT = 0
PAGE_NO = 1
PAGES = 0

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
    STATUS_ARIA = "Aria2p"
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
    return buttons.build_menu(2)

def get_progress_bar_string(status):
    completed = status.processed_bytes() / 8
    total = status.size_raw() / 8
    p = 0 if total == 0 else round(completed * 100 / total)
    p = min(max(p, 0), 100)
    cFull = p // 8
    p_str = '⬢' * cFull
    p_str += '⬡' * (12 - cFull)
    return f"[{p_str}]"

def progress_bar(percentage):
    p_used = '⬢'
    p_total = '⬡'
    if isinstance(percentage, str):
        return '-'
    try:
        percentage=int(percentage)
    except:
        percentage = 0
    return ''.join(
        p_used if i <= percentage // 10 else p_total for i in range(1, 11)
    )

ONE, TWO, THREE = range(3)

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
T: {disk_t} | F: {disk_f}

Working For: {currentTime}
T-DL: {recv} | T-UL: {sent}

Made with ❤️ by Dawn
"""

#---Thanks for deleting my name ❤️ Appreciate it---#
#----------Remove this line too, who cares----------#

dispatcher.add_handler(CallbackQueryHandler(pop_up_stats, pattern=f"^{str(THREE)}$"))

def get_readable_message():
    with download_dict_lock:
        msg = ""
        if STATUS_LIMIT is not None:
            tasks = len(download_dict)
            globals()['PAGES'] = ceil(tasks/STATUS_LIMIT)
            if PAGE_NO > PAGES and PAGES != 0:
                globals()['COUNT'] -= STATUS_LIMIT
                globals()['PAGE_NO'] -= 1
        for index, download in enumerate(list(download_dict.values())[COUNT:], start=1):
            msg += f'\n\n<b>File Name:</b> <a href="https://t.me/c/{str(download.message.chat.id)[4:]}/{download.message.message_id}">{escape(str(download.name()))}</a>'
            msg += f"\n\n<b>Status:</b> <code>{download.status()}</code> <b>Using:</b> <code>{download.eng()}</code>"
            if download.status() not in [MirrorStatus.STATUS_SEEDING]:
                msg += f"\n{get_progress_bar_string(download)} ↣ {download.progress()}"
                if download.status() in [MirrorStatus.STATUS_DOWNLOADING,
                                         MirrorStatus.STATUS_WAITING,
                                         MirrorStatus.STATUS_PAUSED]:
                    msg += f"\n<b>Downloaded:</b> <code>{get_readable_file_size(download.processed_bytes())}</code> of <code>{download.size()}</code>"
                elif download.status() == MirrorStatus.STATUS_UPLOADING:
                    msg += f"\n<b>Uploaded:</b> <code>{get_readable_file_size(download.processed_bytes())}</code> of <code>{download.size()}</code>"
                elif download.status() == MirrorStatus.STATUS_CLONING:
                    msg += f"\n<b>Cloned:</b> <code>{get_readable_file_size(download.processed_bytes())}</code> of <code>{download.size()}</code>"
                elif download.status() == MirrorStatus.STATUS_ARCHIVING:
                    msg += f"\n<b>Archived:</b> <code>{get_readable_file_size(download.processed_bytes())}</code> of <code>{download.size()}</code>"
                elif download.status() == MirrorStatus.STATUS_EXTRACTING:
                    msg += f"\n<b>Extracted:</b> <code>{get_readable_file_size(download.processed_bytes())}</code> of <code>{download.size()}</code>"
                elif download.status() == MirrorStatus.STATUS_SPLITTING:
                    msg += f"\n<b>Splitted:</b> <code>{get_readable_file_size(download.processed_bytes())}</code> of <code>{download.size()}</code>"
                msg += f"\n<b>ETA:</b> <code>{download.eta()}</code> <b>Elapsed:</b> <code>{get_readable_time(time() - download.message.date.timestamp())}</code>"
                msg += f'\n<b>Speed:</b> <code>{download.speed()}</code> <b>Task By:</b> {download.message.from_user.mention_html(download.message.from_user.first_name)}'
                if hasattr(download, 'seeders_num'):
                    try:
                        msg += f"\n<b>Seeders:</b> {download.seeders_num()} | <b>Leechers:</b> {download.leechers_num()}"
                        msg += f"\n<b>To Select:</b> <code>/{BotCommands.BtSelectCommand} {download.gid()}</code>"
                    except:
                        pass
            elif download.status() == MirrorStatus.STATUS_SEEDING:
                msg += f"\n<b>Size: </b>{download.size()}"
                msg += f"\n<b>Speed: </b>{download.upload_speed()}"
                msg += f" | <b>Uploaded: </b>{download.uploaded_bytes()}"
                msg += f"\n<b>Ratio: </b>{download.ratio()}"
                msg += f" | <b>Time: </b>{download.seeding_time()}"
            msg += f"\n<b>To Cancel:</b> <code>/{BotCommands.CancelMirror} {download.gid()}</code>"
            msg += f"\n"
            if STATUS_LIMIT is not None and index == STATUS_LIMIT:
                break
        if len(msg) == 0:
            return None, None
        dl_speed = 0
        up_speed = 0
        for download in list(download_dict.values()):
            if download.status() == MirrorStatus.STATUS_DOWNLOADING:
                spd = download.speed()
                if 'K' in spd:
                    dl_speed += float(spd.split('K')[0]) * 1024
                elif 'M' in spd:
                    dl_speed += float(spd.split('M')[0]) * 1048576
            elif download.status() == MirrorStatus.STATUS_UPLOADING:
                spd = download.speed()
                if 'KB/s' in spd:
                    up_speed += float(spd.split('K')[0]) * 1024
                elif 'MB/s' in spd:
                    up_speed += float(spd.split('M')[0]) * 1048576
            elif download.status() == MirrorStatus.STATUS_SEEDING:
                spd = download.upload_speed()
                if 'K' in spd:
                    up_speed += float(spd.split('K')[0]) * 1024
                elif 'M' in spd:
                    up_speed += float(spd.split('M')[0]) * 1048576
        bmsg = f"\n<b>___________________________________</b>"
        bmsg += f"\n<b>FREE:</b> <code>{get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)}</code><b> | UPTM:</b> <code>{get_readable_time(time() - botStartTime)}</code>"
        bmsg += f"\n<b>DL:</b> <code>{get_readable_file_size(dl_speed)}/s</code><b> | UL:</b> <code>{get_readable_file_size(up_speed)}/s</code>"
        buttons = ButtonMaker()
        buttons.sbutton("Bot SYS Statistics", str(THREE))
        button = buttons.build_menu(1)
        if STATUS_LIMIT is not None and tasks > STATUS_LIMIT:
            msg += f"\n<b>Total Tasks:</b> {tasks}\n"
            buttons = ButtonMaker()
            buttons.sbutton("Previous", "status pre")
            buttons.sbutton(f"{PAGE_NO}/{PAGES}", str(THREE))
            buttons.sbutton("Next", "status nex")
            button = buttons.build_menu(3)
            return msg + bmsg, button
        return msg + bmsg, button

def turn(data):
    try:
        global COUNT, PAGE_NO
        with download_dict_lock:
            if data[1] == "nex":
                if PAGE_NO == PAGES:
                    COUNT = 0
                    PAGE_NO = 1
                else:
                    COUNT += STATUS_LIMIT
                    PAGE_NO += 1
            elif data[1] == "pre":
                if PAGE_NO == 1:
                    COUNT = STATUS_LIMIT * (PAGES - 1)
                    PAGE_NO = PAGES
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

def is_filepress_link(url: str):
    url = re_match(r'https?://(filepress|filebee)\.\S+', url)
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
def is_appdrive_link(url: str):
    url = re_match(r'https?://(?:\S*\.)?(?:appdrive|driveapp)\.\S+', url)
    return bool(url)
def is_gdtot_link(url: str):
    url = re_match(r'https?://.+\.gdtot\.\S+', url)
    return bool(url)
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
