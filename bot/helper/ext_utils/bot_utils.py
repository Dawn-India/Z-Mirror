from asyncio import (create_subprocess_exec, create_subprocess_shell,
                     run_coroutine_threadsafe, sleep)
from asyncio.subprocess import PIPE
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from html import escape
from re import match
from time import time
from urllib.request import urlopen

from psutil import cpu_percent, disk_usage, virtual_memory
from pyrogram.types import BotCommand
from requests import head as rhead

from bot import (bot_loop, botStartTime, config_dict, download_dict,
                 download_dict_lock, extra_buttons, user_data)
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker

MAGNET_REGEX = r'magnet:\?xt=urn:(btih|btmh):[a-zA-Z0-9]*\s*'

URL_REGEX = r'^(?!\/)(rtmps?:\/\/|mms:\/\/|rtsp:\/\/|https?:\/\/|ftp:\/\/)?([^\/:]+:[^\/@]+@)?(www\.)?(?=[^\/:\s]+\.[^\/:\s]+)([^\/:\s]+\.[^\/:\s]+)(:\d+)?(\/[^#\s]*[\s\S]*)?(\?[^#\s]*)?(#.*)?$'

SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

STATUS_START = 0
PAGES = 1
PAGE_NO = 1

class MirrorStatus:
    STATUS_UPLOADING = "Uploading"
    STATUS_DOWNLOADING = "Downloading"
    STATUS_CLONING = "Cloneing"
    STATUS_QUEUEDL = "Queue Dn"
    STATUS_QUEUEUP = "Queue Up"
    STATUS_PAUSED = "Paused"
    STATUS_ARCHIVING = "Archiving"
    STATUS_EXTRACTING = "Extracting"
    STATUS_SPLITTING = "Spliting"
    STATUS_CHECKING = "CheckingUp"
    STATUS_SEEDING = "Seeding"
    STATUS_CONVERTING = "Converting"

status_labels = {
    MirrorStatus.STATUS_DOWNLOADING: "Downloaded",
    MirrorStatus.STATUS_UPLOADING: "Uploaded",
    MirrorStatus.STATUS_CLONING: "Cloned",
    MirrorStatus.STATUS_ARCHIVING: "Archived",
    MirrorStatus.STATUS_EXTRACTING: "Extracted",
    MirrorStatus.STATUS_SPLITTING: "Splitted",
    MirrorStatus.STATUS_CHECKING: "Checked",
}

class setInterval:
    def __init__(self, interval, action):
        self.interval = interval
        self.action = action
        self.task = bot_loop.create_task(self.__set_interval())

    async def __set_interval(self):
        while True:
            await sleep(self.interval)
            await self.action()

    def cancel(self):
        self.task.cancel()


def get_readable_file_size(size_in_bytes):
    if size_in_bytes is None:
        return '0B'
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return f'{size_in_bytes:.2f}{SIZE_UNITS[index]}' if index > 0 else f'{size_in_bytes}B'


async def getDownloadByGid(gid):
    async with download_dict_lock:
        return next((dl for dl in download_dict.values() if dl.gid() == gid), None)


async def getAllDownload(req_status, user_id=None):
    dls = []
    async with download_dict_lock:
        for dl in list(download_dict.values()):
            if user_id and user_id != dl.message.from_user.id:
                continue
            status = dl.status()
            if req_status in ['all', status]:
                dls.append(dl)
    return dls


def bt_selection_buttons(id_, isCanCncl=True):
    gid = id_[:12] if len(id_) > 20 else id_
    pincode = ''.join([n for n in id_ if n.isdigit()][:4])
    buttons = ButtonMaker()
    BASE_URL = config_dict['BASE_URL']
    if config_dict['WEB_PINCODE']:
        buttons.ubutton("Select Files", f"{BASE_URL}/app/files/{id_}")
        buttons.ibutton("Pincode", f"btsel pin {gid} {pincode}")
    else:
        buttons.ubutton(
            "Select Files", f"{BASE_URL}/app/files/{id_}?pin_code={pincode}")
    if isCanCncl:
        buttons.ibutton("Cancel", f"btsel rm {gid} {id_}")
    buttons.ibutton("Done Selecting", f"btsel done {gid} {id_}")
    return buttons.build_menu(2)


async def get_telegraph_list(telegraph_content):
    path = [(await telegraph.create_page(title='Z Drive Search', content=content))["path"] for content in telegraph_content]
    if len(path) > 1:
        await telegraph.edit_telegraph(path, telegraph_content)
    buttons = ButtonMaker()
    buttons.ubutton("🔎 VIEW", f"https://graph.org/{path[0]}", 'header')
    buttons = extra_btns(buttons)
    return buttons.build_menu(1)


def get_progress_bar_string(pct):
    pct = float(pct.strip('%'))
    p = min(max(pct, 0), 100)
    cFull = int(p // 8)
    p_str = '⬢' * cFull
    p_str += '⬡' * (12 - cFull)
    return f"{p_str}"


def get_readable_message():
    msg = ""
    button = None
    STATUS_LIMIT = config_dict['STATUS_LIMIT']
    tasks = len(download_dict)
    globals()['PAGES'] = (tasks + STATUS_LIMIT - 1) // STATUS_LIMIT
    if PAGE_NO > PAGES and PAGES != 0:
        globals()['STATUS_START'] = STATUS_LIMIT * (PAGES - 1)
        globals()['PAGE_NO'] = PAGES
    for download in list(download_dict.values())[STATUS_START:STATUS_LIMIT+STATUS_START]:
        tag = download.message.from_user.username if download.message.from_user.username is not None else {escape(download.message.from_user.first_name)}
        tag = f"<a href='https://t.me/{tag}'>{tag}</a>"
        if config_dict['DM_MODE']:
            msg += f"Hey {tag}, Please wait!\n<b>{download.status()}</b> "
            msg += f"Your Task [<a href='{download.message.link}'>{download.extra_details['mode']}</a>]"
        else:
            msg += f"\n<b>{download.status()}:</b> <code>{escape(f'{download.name()}')}</code>"
        if download.status() not in [MirrorStatus.STATUS_SEEDING, MirrorStatus.STATUS_CONVERTING,
                                     MirrorStatus.STATUS_QUEUEDL, MirrorStatus.STATUS_QUEUEUP, 
                                     MirrorStatus.STATUS_PAUSED]:
            msg += f"\n{get_progress_bar_string(download.progress())} {download.progress()}"
            status_label = status_labels.get(download.status(), "")
            msg += f"\n<b>{status_label}:</b> "
            msg += f"<code>{download.processed_bytes()}</code> of <code>{download.size()}</code>"
            msg += f"\n<b>Speed</b>: <code>{download.speed()}</code> | "
            msg += f"<b>Elapsed:</b> <code>{get_readable_time(time() - download.extra_details['startTime'])}</code>"
            msg += f"\n<b>ETA</b>: <code>{download.eta()}</code> | <b>Eng</b>: <code>{download.engine}</code>"
            if hasattr(download, 'playList'):
                try:
                    if playlist:=download.playList():
                        msg += f"\n<b>Playlist Downloaded</b>: {playlist}"
                except:
                    pass
            if not config_dict['DM_MODE']:
                msg += f"\n<b>Task</b>: <a href='{download.message.link}'>{download.extra_details['mode']}</a>"
                msg += f" | <b>By</b>: {tag}"
            if hasattr(download, 'seeders_num'):
                try:
                    msg += f"\n<b>Seeders</b>: {download.seeders_num()}"
                    msg += f" | <b>Leechers</b>: {download.leechers_num()}"
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
        msg += f"\n⚠️ <code>/{BotCommands.CancelMirror[0]} {download.gid()}</code>\n\n"
    if len(msg) == 0:
        return None, None
    def convert_speed_to_bytes_per_second(spd):
        if 'K' in spd:
            return float(spd.split('K')[0]) * 1024
        elif 'M' in spd:
            return float(spd.split('M')[0]) * 1048576
        else:
            return 0

    dl_speed = 0
    up_speed = 0
    for download in download_dict.values():
        tstatus = download.status()
        spd = download.speed() if tstatus != MirrorStatus.STATUS_SEEDING else download.upload_speed()
        speed_in_bytes_per_second = convert_speed_to_bytes_per_second(spd)
        if tstatus == MirrorStatus.STATUS_DOWNLOADING:
            dl_speed += speed_in_bytes_per_second
        elif tstatus == MirrorStatus.STATUS_UPLOADING or tstatus == MirrorStatus.STATUS_SEEDING:
            up_speed += speed_in_bytes_per_second
    if tasks > STATUS_LIMIT:
        buttons = ButtonMaker()
        buttons.ibutton("⫷", "status pre")
        buttons.ibutton(f"{PAGE_NO}/{PAGES}", "status ref")
        buttons.ibutton("⫸", "status nex")
        button = buttons.build_menu(3)
    msg += "_____________________________"
    msg += f"\n<b>FREE</b>: <code>{get_readable_file_size(disk_usage(config_dict['DOWNLOAD_DIR']).free)}</code>"
    msg += f" | <b>UPTM</b>: <code>{get_readable_time(time() - botStartTime)}</code>"
    msg += f"\n<b>DL</b>: <code>{get_readable_file_size(dl_speed)}/s</code>"
    msg += f" | <b>UL</b>: <code>{get_readable_file_size(up_speed)}/s</code>"
    return msg, button


def extra_btns(buttons):
    if extra_buttons:
        for btn_name, btn_url in extra_buttons.items():
            buttons.ubutton(btn_name, btn_url)
    return buttons


async def turn_page(data):
    STATUS_LIMIT = config_dict['STATUS_LIMIT']
    global STATUS_START, PAGE_NO, PAGES
    async with download_dict_lock:
        if data[1] == "nex" and PAGE_NO == PAGES:
            PAGE_NO = 1
        elif data[1] == "nex" and PAGE_NO < PAGES:
            PAGE_NO += 1
        elif data[1] == "pre" and PAGE_NO == 1:
            PAGE_NO = PAGES
        elif data[1] == "pre" and PAGE_NO > 1:
            PAGE_NO -= 1
        STATUS_START = (PAGE_NO - 1) * STATUS_LIMIT


async def check_user_tasks(user_id, maxtask):
    if tasks := await getAllDownload(MirrorStatus.STATUS_DOWNLOADING, user_id):
        return len(tasks) >= maxtask


def get_readable_time(seconds):
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)}{period_name}'
    return result


def is_magnet(url):
    return bool(match(MAGNET_REGEX, url))


def is_url(url):
    return bool(match(URL_REGEX, url))


def is_gdrive_link(url):
    return "drive.google.com" in url


def is_share_link(url: str):
    if 'gdtot' in url:
        regex = r'(https?:\/\/.+\.gdtot\..+\/file\/\d+)'
    else:
        regex = r'(https?:\/\/(\S+)\..+\/file\/\S+)'
    return bool(match(regex, url))


def is_mega_link(url):
    return "mega.nz" in url or "mega.co.nz" in url


def is_rclone_path(path):
    return bool(match(r'^(mrcc:)?(?!magnet:)(?![- ])[a-zA-Z0-9_\. -]+(?<! ):(?!.*\/\/).*$|^rcl$', path))


def get_mega_link_type(url):
    return "folder" if "folder" in url or "/#F!" in url else "file"


def get_content_type(link):
    try:
        res = rhead(link, allow_redirects=True, timeout=5,
                    headers={'user-agent': 'Wget/1.12'})
        content_type = res.headers.get('content-type')
    except:
        try:
            res = urlopen(link, timeout=5)
            content_type = res.info().get_content_type()
        except:
            content_type = None
    return content_type


def update_user_ldata(id_, key, value):
    if not key and not value:
        user_data[id_] = {}
        return
    user_data.setdefault(id_, {})
    user_data[id_][key] = value


async def cmd_exec(cmd, shell=False):
    if shell:
        proc = await create_subprocess_shell(cmd, stdout=PIPE, stderr=PIPE)
    else:
        proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await proc.communicate()
    stdout = stdout.decode().strip()
    stderr = stderr.decode().strip()
    return stdout, stderr, proc.returncode


def new_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return bot_loop.create_task(func(*args, **kwargs))
    return wrapper


async def sync_to_async(func, *args, wait=True, **kwargs):
    pfunc = partial(func, *args, **kwargs)
    with ThreadPoolExecutor() as pool:
        future = bot_loop.run_in_executor(pool, pfunc)
        return await future if wait else future


def async_to_sync(func, *args, wait=True, **kwargs):
    future = run_coroutine_threadsafe(func(*args, **kwargs), bot_loop)
    return future.result() if wait else future


def new_thread(func):
    @wraps(func)
    def wrapper(*args, wait=False, **kwargs):
        future = run_coroutine_threadsafe(func(*args, **kwargs), bot_loop)
        return future.result() if wait else future
    return wrapper


async def set_commands(client):
    if config_dict['SET_COMMANDS']:
        await client.set_bot_commands([
        BotCommand(f'{BotCommands.MirrorCommand[0]}', f'or /{BotCommands.MirrorCommand[1]} Mirror'),
        BotCommand(f'{BotCommands.LeechCommand[0]}', f'or /{BotCommands.LeechCommand[1]} Leech'),
        BotCommand(f'{BotCommands.ZipMirrorCommand[0]}', f'or /{BotCommands.ZipMirrorCommand[1]} Mirror and upload as zip'),
        BotCommand(f'{BotCommands.ZipLeechCommand[0]}', f'or /{BotCommands.ZipLeechCommand[1]} Leech and upload as zip'),
        BotCommand(f'{BotCommands.UnzipMirrorCommand[0]}', f'or /{BotCommands.UnzipMirrorCommand[1]} Mirror and extract files'),
        BotCommand(f'{BotCommands.UnzipLeechCommand[0]}', f'or /{BotCommands.UnzipLeechCommand[1]} Leech and extract files'),
        BotCommand(f'{BotCommands.QbMirrorCommand[0]}', f'or /{BotCommands.QbMirrorCommand[1]} Mirror torrent using qBittorrent'),
        BotCommand(f'{BotCommands.QbLeechCommand[0]}', f'or /{BotCommands.QbLeechCommand[1]} Leech torrent using qBittorrent'),
        BotCommand(f'{BotCommands.QbZipMirrorCommand[0]}', f'or /{BotCommands.QbZipMirrorCommand[1]} Mirror torrent and upload as zip using qb'),
        BotCommand(f'{BotCommands.QbZipLeechCommand[0]}', f'or /{BotCommands.QbZipLeechCommand[1]} Leech torrent and upload as zip using qb'),
        BotCommand(f'{BotCommands.QbUnzipMirrorCommand[0]}', f'or /{BotCommands.QbUnzipMirrorCommand[1]} Mirror torrent and extract files using qb'),
        BotCommand(f'{BotCommands.QbUnzipLeechCommand[0]}', f'or /{BotCommands.QbUnzipLeechCommand[1]} Leech torrent and extract using qb'),
        BotCommand(f'{BotCommands.YtdlCommand[0]}', f'or /{BotCommands.YtdlCommand[1]} Mirror yt-dlp supported link'),
        BotCommand(f'{BotCommands.YtdlLeechCommand[0]}', f'or /{BotCommands.YtdlLeechCommand[1]} Leech through yt-dlp supported link'),
        BotCommand(f'{BotCommands.YtdlZipCommand[0]}', f'or /{BotCommands.YtdlZipCommand[1]} Mirror yt-dlp supported link as zip'),
        BotCommand(f'{BotCommands.YtdlZipLeechCommand[0]}', f'or /{BotCommands.YtdlZipLeechCommand[1]} Leech yt-dlp support link as zip'),
        BotCommand(f'{BotCommands.CloneCommand}', 'Copy file/folder to Drive'),
        BotCommand(f'{BotCommands.CountCommand}', '[drive_url]: Count file/folder of Google Drive.'),
        BotCommand(f'{BotCommands.StatusCommand[0]}', f'or /{BotCommands.StatusCommand[1]} Get mirror status message'),
        BotCommand(f'{BotCommands.StatsCommand[0]}', f'{BotCommands.StatsCommand[1]} Check bot stats'),
        BotCommand(f'{BotCommands.BtSelectCommand}', 'Select files to download only torrents'),
        BotCommand(f'{BotCommands.CategorySelect}', 'Select category to upload only mirror'),
        BotCommand(f'{BotCommands.CancelMirror[0]}', f'or {BotCommands.CancelMirror[1]} Cancel a Task'),
        BotCommand(f'{BotCommands.CancelAllCommand[0]}', f'Cancel all tasks which added by you or {BotCommands.CancelAllCommand[1]} to in bots.'),
        BotCommand(f'{BotCommands.ListCommand}', 'Search in Drive'),
        BotCommand(f'{BotCommands.SearchCommand}', 'Search in Torrent'),
        BotCommand(f'{BotCommands.UserSetCommand}', 'Users settings'),
        BotCommand(f'{BotCommands.HelpCommand}', 'Get detailed help'),
            ])
