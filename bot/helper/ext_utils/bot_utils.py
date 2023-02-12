from html import escape
from math import ceil
from re import findall, match
from threading import Event, Thread
from time import time
from urllib.parse import urlparse
from urllib.request import urlopen

import psutil
from psutil import cpu_percent, disk_usage, virtual_memory
from requests import request

from bot import (dispatcher, DOWNLOAD_DIR, botStartTime, config_dict, download_dict,
                 download_dict_lock, extra_buttons, user_data)
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
    STATUS_CLONING = "Cloneing"
    STATUS_QUEUEDL = "QueueDl"
    STATUS_QUEUEUP = "QueueUl"
    STATUS_PAUSED = "Paused"
    STATUS_ARCHIVING = "Archiving"
    STATUS_EXTRACTING = "Extracting"
    STATUS_SPLITTING = "Spliting"
    STATUS_CHECKING = "CheckUp"
    STATUS_SEEDING = "Seeding"
    STATUS_CONVERTING = "Converting"

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
            self.action()
            nextTime = time() + self.interval

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

def getAllDownload(req_status: str, user_id: int = None, onece: bool = True):
    dls = []
    with download_dict_lock:
        for dl in list(download_dict.values()):
            if user_id and user_id != dl.message.from_user.id:
                continue
            status = dl.status()
            if req_status in ['all', status]:
                if onece:
                    return dl
                else:
                    dls.append(dl)
    return None if onece else dls

def bt_selection_buttons(id_: str, isCanCncl: bool = True):
    gid = id_[:12] if len(id_) > 20 else id_
    pincode = ""
    for n in id_:
        if n.isdigit():
            pincode += str(n)
        if len(pincode) == 4:
            break

    buttons = ButtonMaker()
    if config_dict['WEB_PINCODE']:
        buttons.buildbutton("Select Files", f"{config_dict['BASE_URL']}/app/files/{id_}")
        buttons.sbutton("Pincode", f"btsel pin {gid} {pincode}")
    else:
        buttons.buildbutton("Select Files", f"{config_dict['BASE_URL']}/app/files/{id_}?pin_code={pincode}")
    buttons.sbutton("Done Selecting", f"btsel done {gid} {id_}")
    if isCanCncl:
        buttons.sbutton("Cancel", f"btsel rm {gid} {id_}")
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

def _get_readable_message_btns(msg, bmsg):
    buttons = ButtonMaker()
    buttons.sbutton("PREV", "status pre")
    buttons.sbutton(f"{PAGE_NO}/{PAGES}", str(THREE))
    buttons.sbutton("NEXT", "status nex")
    button = buttons.build_menu(3)
    return msg + bmsg, button

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

#----Thanks for deleting my name ❤️ Appreciate it----#
#----------Remove this line too, who cares----------#

dispatcher.add_handler(CallbackQueryHandler(pop_up_stats, pattern=f"^{str(THREE)}$"))

def get_readable_message():
    cDl = 0
    cUl = 0
    cQdl = 0
    cQul = 0
    cQu = 0
    with download_dict_lock:
        for c in list(download_dict.values()):
            if c.status() == MirrorStatus.STATUS_DOWNLOADING:
                cDl += 1
            if c.status() == MirrorStatus.STATUS_UPLOADING:
                cUl += 1
            if c.status() == MirrorStatus.STATUS_QUEUEDL:
                cQdl += 1
            if c.status() == MirrorStatus.STATUS_QUEUEUP:
                cQul += 1
            cQu = cQdl + cQul
        tasks = len(download_dict)
        msg = f"<b>Tasks</b> ➜ <b>DL:</b> <code>{cDl}</code>  <b>UL:</b> <code>{cUl}</code>  <b>Queued:</b> <code>{cQu}</code>  <b>Total:</b> <code>{tasks}</code>\n<code>--------------------------------</code>\n"
        if STATUS_LIMIT := config_dict['STATUS_LIMIT']:
            globals()['PAGES'] = ceil(tasks/STATUS_LIMIT)
            if PAGE_NO > PAGES and PAGES != 0:
                globals()['COUNT'] -= STATUS_LIMIT
                globals()['PAGE_NO'] -= 1
        for index, download in enumerate(list(download_dict.values())[COUNT:], start=1):
            if config_dict['DM_MODE']:
                msg += f"Hey <b><i>@{download.message.from_user.username}</i></b>, Please wait!\n<b>{download.status()}</b> Your Task [<a href='{download.message.link}'>{download.mode}</a>]"
            else:
                msg += f'\n<b>{download.status()}:</b> <code>{escape(str(download.name()))}</code>'
            if download.status() not in [MirrorStatus.STATUS_SEEDING, MirrorStatus.STATUS_CONVERTING]:
                msg += f"\n{get_progress_bar_string(download)} {download.progress()}"
                if download.status() in [MirrorStatus.STATUS_DOWNLOADING,
                                         MirrorStatus.STATUS_QUEUEDL,
                                         MirrorStatus.STATUS_QUEUEUP,
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
                msg += f"\n<b>Speed</b>: <code>{download.speed()}</code> | <b>Elapsed:</b> <code>{get_readable_time(time() - download.startTime)}</code>"
                msg += f"\n<b>ETA</b>: <code>{download.eta()}</code> | <b>Eng</b>: <code>{download.engine}</code>"
                if not config_dict['DM_MODE']:
                    msg += f"\n<b>Task</b>: <a href='{download.message.link}'>{download.mode()}</a> | <b>By</b>: {download.source}"
                if hasattr(download, 'seeders_num'):
                    try:
                        msg += f"\n<b>Seeders</b>: {download.seeders_num()} | <b>Leechers</b>: {download.leechers_num()}"
                    except:
                        pass
            elif download.status() == MirrorStatus.STATUS_SEEDING:
                msg += f"\n<b>Size</b>: {download.size()}"
                msg += f"\n<b>Speed</b>: {download.upload_speed()}"
                msg += f" | <b>Uploaded</b>: {download.uploaded_bytes()}"
                msg += f"\n<b>Ratio</b>: {download.ratio()}"
                msg += f" | <b>Time</b>: {download.seeding_time()}"
            else:
                msg += f"\n<b>Size</b>: {download.size()}"
            if hasattr(download, 'playList'):
                try:
                    if playlist:=download.playList():
                        msg += f"\n<b>Playlist</b>: {playlist}"
                except:
                    pass
            if download.status() != MirrorStatus.STATUS_CONVERTING:
                msg += f"\n🛑 <code>/{BotCommands.CancelMirror} {download.gid()}</code>"
            msg += "\n\n"
            if STATUS_LIMIT and index == STATUS_LIMIT:
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
        bmsg = f"<b>FREE:</b> <code>{get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)}</code><b> | UPTM:</b> <code>{get_readable_time(time() - botStartTime)}</code>"
        bmsg += f"\n<b>DL:</b> <code>{get_readable_file_size(dl_speed)}/s</code><b> | UL:</b> <code>{get_readable_file_size(up_speed)}/s</code>"
        buttons = ButtonMaker()
        buttons.sbutton("Bot SYS Statistics", str(THREE))
        button = buttons.build_menu(1)
        if STATUS_LIMIT and tasks > STATUS_LIMIT:
            return _get_readable_message_btns(msg, bmsg)
        return msg + bmsg, button


def extra_btns(buttons):
    if extra_buttons:
        for btn_name, btn_url in extra_buttons.items():
            buttons.buildbutton(btn_name, btn_url)
    return buttons

def turn(data):
    STATUS_LIMIT = config_dict['STATUS_LIMIT']
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

def check_user_tasks(user_id, maxtask):
    if tasks:= getAllDownload(MirrorStatus.STATUS_DOWNLOADING, user_id, False):
        return len(tasks) >= maxtask

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
    url = findall(URL_REGEX, url)
    return bool(url)

def is_gdrive_link(url: str):
    return "drive.google.com" in urlparse(url).netloc

def is_Sharerlink(url: str):
    if 'gdtot' in url:
        regex = r'(https?:\/\/.+\.gdtot\..+\/file\/\d+)'
    else:
        regex = r'(https?:\/\/(\S+)\..+\/file\/\S+)'
    return bool(match(regex, url))

def is_mega_link(url: str):
    url_ = urlparse(url)
    return any(x in url_.netloc for x in ['mega.nz', 'mega.co.nz'])

def get_mega_link_type(url: str):
    if "folder" in url:
        return "folder"
    elif "file" in url:
        return "file"
    elif "/#F!" in url:
        return "folder"
    return "file"

def is_magnet(url: str):
    magnet = findall(MAGNET_REGEX, url)
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
        res = request('HEAD', link, allow_redirects=True, timeout=5, headers = {'user-agent': 'Wget/1.12'})
        content_type = res.headers.get('content-type')
    except:
        try:
            res = urlopen(link, timeout=5)
            info = res.info()
            content_type = info.get_content_type()
        except:
            content_type = None
    return content_type

def update_user_ldata(id_, key, value):
    if id_ in user_data:
        user_data[id_][key] = value
    else:
        user_data[id_] = {key: value}

def set_commands(bot):
    if config_dict['SET_COMMANDS']:
        bot.set_my_commands([
        (f'{BotCommands.MirrorCommand[0]}', f'or /{BotCommands.MirrorCommand[1]} Mirror'),
        (f'{BotCommands.LeechCommand[0]}', f'or /{BotCommands.LeechCommand[1]} Leech'),
        (f'{BotCommands.ZipMirrorCommand[0]}', f'or /{BotCommands.ZipMirrorCommand[1]} Mirror and upload as zip'),
        (f'{BotCommands.ZipLeechCommand[0]}', f'or /{BotCommands.ZipLeechCommand[1]} Leech and upload as zip'),
        (f'{BotCommands.UnzipMirrorCommand[0]}', f'or /{BotCommands.UnzipMirrorCommand[1]} Mirror and extract files'),
        (f'{BotCommands.UnzipLeechCommand[0]}', f'or /{BotCommands.UnzipLeechCommand[1]} Leech and extract files'),
        (f'{BotCommands.QbMirrorCommand[0]}', f'or /{BotCommands.QbMirrorCommand[1]} Mirror torrent using qBittorrent'),
        (f'{BotCommands.QbLeechCommand[0]}', f'or /{BotCommands.QbLeechCommand[1]} Leech torrent using qBittorrent'),
        (f'{BotCommands.QbZipMirrorCommand[0]}', f'or /{BotCommands.QbZipMirrorCommand[1]} Mirror torrent and upload as zip using qb'),
        (f'{BotCommands.QbZipLeechCommand[0]}', f'or /{BotCommands.QbZipLeechCommand[1]} Leech torrent and upload as zip using qb'),
        (f'{BotCommands.QbUnzipMirrorCommand[0]}', f'or /{BotCommands.QbUnzipMirrorCommand[1]} Mirror torrent and extract files using qb'),
        (f'{BotCommands.QbUnzipLeechCommand[0]}', f'or /{BotCommands.QbUnzipLeechCommand[1]} Leech torrent and extract using qb'),
        (f'{BotCommands.YtdlCommand[0]}', f'or /{BotCommands.YtdlCommand[1]} Mirror yt-dlp supported link'),
        (f'{BotCommands.YtdlLeechCommand[0]}', f'or /{BotCommands.YtdlLeechCommand[1]} Leech through yt-dlp supported link'),
        (f'{BotCommands.YtdlZipCommand[0]}', f'or /{BotCommands.YtdlZipCommand[1]} Mirror yt-dlp supported link as zip'),
        (f'{BotCommands.YtdlZipLeechCommand[0]}', f'or /{BotCommands.YtdlZipLeechCommand[1]} Leech yt-dlp support link as zip'),
        (f'{BotCommands.CloneCommand}', 'Copy file/folder to Drive'),
        (f'{BotCommands.StatusCommand[0]}', f'or /{BotCommands.StatusCommand[1]} Get mirror status message'),
        (f'{BotCommands.StatsCommand}', 'Check bot stats'),
        (f'{BotCommands.BtSelectCommand}', 'Select files to download only torrents'),
        (f'{BotCommands.CategorySelect}', 'Select category to upload only mirror'),
        (f'{BotCommands.CancelMirror}', 'Cancel a Task'),
        (f'{BotCommands.CancelAllCommand[0]}', f'Cancel all tasks which added by you or {BotCommands.CancelAllCommand[1]} to in bots.'),
        (f'{BotCommands.ListCommand}', 'Search in Drive'),
        (f'{BotCommands.SearchCommand}', 'Search in Torrent'),
        (f'{BotCommands.UserSetCommand}', 'Users settings'),
        (f'{BotCommands.HelpCommand}', 'Get detailed help'),
            ])
