#!/usr/bin/env python3
from asyncio import create_subprocess_exec, create_subprocess_shell, sleep, gather
from collections import OrderedDict
from functools import partial
from io import BytesIO
from os import environ, getcwd
from time import time

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import remove, rename
from aioshutil import rmtree as aiormtree
from dotenv import load_dotenv
from pyrogram.filters import command, create, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from bot import (DATABASE_URL, GLOBAL_EXTENSION_FILTER, IS_PREMIUM_USER,
                 LOGGER, MAX_SPLIT_SIZE, Interval, aria2, aria2_options,
                 aria2c_global, bot, categories_dict, config_dict,
                 download_dict, extra_buttons, get_client, list_drives_dict,
                 qbit_options, shorteneres_list, status_reply_dict_lock,
                 user_data)
from bot.helper.ext_utils.bot_utils import (get_readable_file_size, new_thread,
                                            set_commands, setInterval,
                                            sync_to_async)
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.task_manager import start_from_queued
from bot.helper.mirror_utils.rclone_utils.serve import rclone_serve_booter
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (editMessage, sendFile,
                                                      sendMessage,
                                                      update_all_messages)
from bot.modules.rss import addJob
from bot.modules.torrent_search import initiate_search_tools

START = 0
STATE = 'view'
handler_dict = {}
default_values = {'AUTO_DELETE_MESSAGE_DURATION': 120,
                  'DOWNLOAD_DIR': '/usr/src/app/downloads/',
                  'LEECH_SPLIT_SIZE': MAX_SPLIT_SIZE,
                  'RSS_DELAY': 900,
                  'STATUS_UPDATE_INTERVAL': 15,
                  'SEARCH_LIMIT': 0,
                  'UPSTREAM_REPO': 'https://github.com/Dawn-India/Z-Mirror',
                  'UPSTREAM_BRANCH': 'main',
                  'TORRENT_TIMEOUT': '600'}


async def load_config():

    BOT_TOKEN = environ.get('BOT_TOKEN', '')
    if len(BOT_TOKEN) == 0:
        BOT_TOKEN = config_dict['BOT_TOKEN']

    TELEGRAM_API = environ.get('TELEGRAM_API', '')
    if len(TELEGRAM_API) == 0:
        TELEGRAM_API = config_dict['TELEGRAM_API']
    else:
        TELEGRAM_API = int(TELEGRAM_API)

    TELEGRAM_HASH = environ.get('TELEGRAM_HASH', '')
    if len(TELEGRAM_HASH) == 0:
        TELEGRAM_HASH = config_dict['TELEGRAM_HASH']

    OWNER_ID = environ.get('OWNER_ID', '')
    OWNER_ID = config_dict['OWNER_ID'] if len(OWNER_ID) == 0 else int(OWNER_ID)

    DATABASE_URL = environ.get('DATABASE_URL', '')
    if len(DATABASE_URL) == 0:
        DATABASE_URL = ''

    DOWNLOAD_DIR = environ.get('DOWNLOAD_DIR', '')
    if len(DOWNLOAD_DIR) == 0:
        DOWNLOAD_DIR = '/usr/src/app/downloads/'
    elif not DOWNLOAD_DIR.endswith("/"):
        DOWNLOAD_DIR = f'{DOWNLOAD_DIR}/'

    GDRIVE_ID = environ.get('GDRIVE_ID', '')
    if len(GDRIVE_ID) == 0:
        GDRIVE_ID = ''

    RCLONE_PATH = environ.get('RCLONE_PATH', '')
    if len(RCLONE_PATH) == 0:
        RCLONE_PATH = ''

    DEFAULT_UPLOAD = environ.get('DEFAULT_UPLOAD', '')
    if DEFAULT_UPLOAD != 'rc':
        DEFAULT_UPLOAD = 'gd'

    RCLONE_FLAGS = environ.get('RCLONE_FLAGS', '')
    if len(RCLONE_FLAGS) == 0:
        RCLONE_FLAGS = ''

    AUTHORIZED_CHATS = environ.get('AUTHORIZED_CHATS', '')
    if len(AUTHORIZED_CHATS) != 0:
        aid = AUTHORIZED_CHATS.split()
        for id_ in aid:
            user_data[int(id_.strip())] = {'is_auth': True}

    SUDO_USERS = environ.get('SUDO_USERS', '')
    if len(SUDO_USERS) != 0:
        aid = SUDO_USERS.split()
        for id_ in aid:
            user_data[int(id_.strip())] = {'is_sudo': True}

    EXTENSION_FILTER = environ.get('EXTENSION_FILTER', '')
    if len(EXTENSION_FILTER) > 0:
        fx = EXTENSION_FILTER.split()
        GLOBAL_EXTENSION_FILTER.clear()
        GLOBAL_EXTENSION_FILTER.extend(['aria2', '!qB'])
        for x in fx:
            if x.strip().startswith('.'):
                x = x.lstrip('.')
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())

    MEGA_EMAIL = environ.get('MEGA_EMAIL', '')
    MEGA_PASSWORD = environ.get('MEGA_PASSWORD', '')
    if len(MEGA_EMAIL) == 0 or len(MEGA_PASSWORD) == 0:
        MEGA_EMAIL = ''
        MEGA_PASSWORD = ''

    FILELION_API = environ.get('FILELION_API', '')
    if len(FILELION_API) == 0:
        FILELION_API = ''

    STREAMWISH_API = environ.get('STREAMWISH_API', '')
    if len(STREAMWISH_API) == 0:
        STREAMWISH_API = ''

    JIODRIVE_ACCESS_TOKEN = environ.get('JIODRIVE_ACCESS_TOKEN', '')
    if len(JIODRIVE_ACCESS_TOKEN) == 0:
        JIODRIVE_ACCESS_TOKEN = ''

    INDEX_URL = environ.get('INDEX_URL', '').rstrip("/")
    if len(INDEX_URL) == 0:
        INDEX_URL = ''

    SEARCH_API_LINK = environ.get('SEARCH_API_LINK', '').rstrip("/")
    if len(SEARCH_API_LINK) == 0:
        SEARCH_API_LINK = ''

    LEECH_FILENAME_PREFIX = environ.get('LEECH_FILENAME_PREFIX', '')
    if len(LEECH_FILENAME_PREFIX) == 0:
        LEECH_FILENAME_PREFIX = ''

    LEECH_REMOVE_UNWANTED = environ.get('LEECH_REMOVE_UNWANTED', '')
    if len(LEECH_REMOVE_UNWANTED) == 0:
        LEECH_REMOVE_UNWANTED = ''

    SEARCH_PLUGINS = environ.get('SEARCH_PLUGINS', '')
    if len(SEARCH_PLUGINS) == 0:
        SEARCH_PLUGINS = ''

    MAX_SPLIT_SIZE = 4194304000 if IS_PREMIUM_USER else 2097152000

    LEECH_SPLIT_SIZE = environ.get('LEECH_SPLIT_SIZE', '')
    if len(LEECH_SPLIT_SIZE) == 0 or int(LEECH_SPLIT_SIZE) > MAX_SPLIT_SIZE:
        LEECH_SPLIT_SIZE = MAX_SPLIT_SIZE
    else:
        LEECH_SPLIT_SIZE = int(LEECH_SPLIT_SIZE)

    STATUS_UPDATE_INTERVAL = environ.get('STATUS_UPDATE_INTERVAL', '')
    if len(STATUS_UPDATE_INTERVAL) == 0:
        STATUS_UPDATE_INTERVAL = 15
    else:
        STATUS_UPDATE_INTERVAL = int(STATUS_UPDATE_INTERVAL)
    if len(download_dict) != 0:
        async with status_reply_dict_lock:
            if Interval:
                Interval[0].cancel()
                Interval.clear()
                Interval.append(setInterval(
                    STATUS_UPDATE_INTERVAL, update_all_messages))

    AUTO_DELETE_MESSAGE_DURATION = environ.get(
        'AUTO_DELETE_MESSAGE_DURATION', '')
    if len(AUTO_DELETE_MESSAGE_DURATION) == 0:
        AUTO_DELETE_MESSAGE_DURATION = 120
    else:
        AUTO_DELETE_MESSAGE_DURATION = int(AUTO_DELETE_MESSAGE_DURATION)

    YT_DLP_OPTIONS = environ.get('YT_DLP_OPTIONS', '')
    if len(YT_DLP_OPTIONS) == 0:
        YT_DLP_OPTIONS = ''

    SEARCH_LIMIT = environ.get('SEARCH_LIMIT', '')
    SEARCH_LIMIT = 0 if len(SEARCH_LIMIT) == 0 else int(SEARCH_LIMIT)

    DUMP_CHAT_ID = environ.get('DUMP_CHAT_ID', '')
    DUMP_CHAT_ID = '' if len(DUMP_CHAT_ID) == 0 else int(DUMP_CHAT_ID)

    USER_DUMP = environ.get('USER_DUMP', '')
    USER_DUMP = '' if len(USER_DUMP) == 0 else USER_DUMP
    if USER_DUMP.isdigit() or USER_DUMP.startswith('-'):
        USER_DUMP = int(USER_DUMP)

    STATUS_LIMIT = environ.get('STATUS_LIMIT', '')
    STATUS_LIMIT = 5 if len(STATUS_LIMIT) == 0 else int(STATUS_LIMIT)

    RSS_CHAT_ID = environ.get('RSS_CHAT_ID', '')
    RSS_CHAT_ID = '' if len(RSS_CHAT_ID) == 0 else RSS_CHAT_ID
    if RSS_CHAT_ID.isdigit() or RSS_CHAT_ID.startswith('-'):
        RSS_CHAT_ID = int(RSS_CHAT_ID)

    RSS_DELAY = environ.get('RSS_DELAY', '')
    RSS_DELAY = 900 if len(RSS_DELAY) == 0 else int(RSS_DELAY)

    CMD_SUFFIX = environ.get('CMD_SUFFIX', '')

    USER_SESSION_STRING = environ.get('USER_SESSION_STRING', '')

    TORRENT_TIMEOUT = environ.get('TORRENT_TIMEOUT', '')
    downloads = aria2.get_downloads()
    if len(TORRENT_TIMEOUT) == 0:
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(aria2.client.change_option, download.gid, {'bt-stop-timeout': '0'})
                except Exception as e:
                    LOGGER.error(e)
        aria2_options['bt-stop-timeout'] = '0'
        if DATABASE_URL:
            await DbManager().update_aria2('bt-stop-timeout', '0')
        TORRENT_TIMEOUT = ''
    else:
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(aria2.client.change_option, download.gid, {'bt-stop-timeout': TORRENT_TIMEOUT})
                except Exception as e:
                    LOGGER.error(e)
        aria2_options['bt-stop-timeout'] = TORRENT_TIMEOUT
        if DATABASE_URL:
            await DbManager().update_aria2('bt-stop-timeout', TORRENT_TIMEOUT)
        TORRENT_TIMEOUT = int(TORRENT_TIMEOUT)

    QUEUE_ALL = environ.get('QUEUE_ALL', '')
    QUEUE_ALL = '' if len(QUEUE_ALL) == 0 else int(QUEUE_ALL)

    QUEUE_DOWNLOAD = environ.get('QUEUE_DOWNLOAD', '')
    QUEUE_DOWNLOAD = '' if len(QUEUE_DOWNLOAD) == 0 else int(QUEUE_DOWNLOAD)

    QUEUE_UPLOAD = environ.get('QUEUE_UPLOAD', '')
    QUEUE_UPLOAD = '' if len(QUEUE_UPLOAD) == 0 else int(QUEUE_UPLOAD)

    INCOMPLETE_TASK_NOTIFIER = environ.get('INCOMPLETE_TASK_NOTIFIER', '')
    INCOMPLETE_TASK_NOTIFIER = INCOMPLETE_TASK_NOTIFIER.lower() == 'true'
    if not INCOMPLETE_TASK_NOTIFIER and DATABASE_URL:
        await DbManager().trunc_table('tasks')

    STOP_DUPLICATE = environ.get('STOP_DUPLICATE', '')
    STOP_DUPLICATE = STOP_DUPLICATE.lower() == 'true'

    IS_TEAM_DRIVE = environ.get('IS_TEAM_DRIVE', '')
    IS_TEAM_DRIVE = IS_TEAM_DRIVE.lower() == 'true'

    USE_SERVICE_ACCOUNTS = environ.get('USE_SERVICE_ACCOUNTS', '')
    USE_SERVICE_ACCOUNTS = USE_SERVICE_ACCOUNTS.lower() == 'true'

    WEB_PINCODE = environ.get('WEB_PINCODE', '')
    WEB_PINCODE = WEB_PINCODE.lower() == 'true'

    AS_DOCUMENT = environ.get('AS_DOCUMENT', '')
    AS_DOCUMENT = AS_DOCUMENT.lower() == 'true'

    EQUAL_SPLITS = environ.get('EQUAL_SPLITS', '')
    EQUAL_SPLITS = EQUAL_SPLITS.lower() == 'true'

    MEDIA_GROUP = environ.get('MEDIA_GROUP', '')
    MEDIA_GROUP = MEDIA_GROUP.lower() == 'true'

    BASE_URL_PORT = environ.get('BASE_URL_PORT', '')
    BASE_URL_PORT = 80 if len(BASE_URL_PORT) == 0 else int(BASE_URL_PORT)

    RCLONE_SERVE_URL = environ.get('RCLONE_SERVE_URL', '')
    if len(RCLONE_SERVE_URL) == 0:
        RCLONE_SERVE_URL = ''

    RCLONE_SERVE_PORT = environ.get('RCLONE_SERVE_PORT', '')
    RCLONE_SERVE_PORT = 8080 if len(
        RCLONE_SERVE_PORT) == 0 else int(RCLONE_SERVE_PORT)

    RCLONE_SERVE_USER = environ.get('RCLONE_SERVE_USER', '')
    if len(RCLONE_SERVE_USER) == 0:
        RCLONE_SERVE_USER = ''

    RCLONE_SERVE_PASS = environ.get('RCLONE_SERVE_PASS', '')
    if len(RCLONE_SERVE_PASS) == 0:
        RCLONE_SERVE_PASS = ''

    await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
    BASE_URL = environ.get('BASE_URL', '').rstrip("/")
    if len(BASE_URL) == 0:
        BASE_URL = ''
    else:
        await create_subprocess_shell(f"gunicorn web.wserver:app --bind 0.0.0.0:{BASE_URL_PORT} --worker-class gevent")

    UPSTREAM_REPO = environ.get('UPSTREAM_REPO', '')
    if len(UPSTREAM_REPO) == 0:
        UPSTREAM_REPO = 'https://github.com/Dawn-India/Z-Mirror'

    UPSTREAM_BRANCH = environ.get('UPSTREAM_BRANCH', '')
    if len(UPSTREAM_BRANCH) == 0:
        UPSTREAM_BRANCH = 'main'

    LOG_CHAT_ID = environ.get('LOG_CHAT_ID', '')
    if LOG_CHAT_ID.startswith('-100'):
        LOG_CHAT_ID = int(LOG_CHAT_ID)
    elif LOG_CHAT_ID.startswith('@'):
        LOG_CHAT_ID = LOG_CHAT_ID.removeprefix('@')
    else:
        LOG_CHAT_ID = ''

    USER_MAX_TASKS = environ.get('USER_MAX_TASKS', '')
    USER_MAX_TASKS = '' if len(USER_MAX_TASKS) == 0 else int(USER_MAX_TASKS)

    STORAGE_THRESHOLD = environ.get('STORAGE_THRESHOLD', '')
    STORAGE_THRESHOLD = '' if len(
        STORAGE_THRESHOLD) == 0 else float(STORAGE_THRESHOLD)

    TORRENT_LIMIT = environ.get('TORRENT_LIMIT', '')
    TORRENT_LIMIT = '' if len(TORRENT_LIMIT) == 0 else float(TORRENT_LIMIT)

    DIRECT_LIMIT = environ.get('DIRECT_LIMIT', '')
    DIRECT_LIMIT = '' if len(DIRECT_LIMIT) == 0 else float(DIRECT_LIMIT)

    YTDLP_LIMIT = environ.get('YTDLP_LIMIT', '')
    YTDLP_LIMIT = '' if len(YTDLP_LIMIT) == 0 else float(YTDLP_LIMIT)

    PLAYLIST_LIMIT = environ.get('PLAYLIST_LIMIT', '')
    PLAYLIST_LIMIT = '' if len(PLAYLIST_LIMIT) == 0 else int(PLAYLIST_LIMIT)

    GDRIVE_LIMIT = environ.get('GDRIVE_LIMIT', '')
    GDRIVE_LIMIT = '' if len(GDRIVE_LIMIT) == 0 else float(GDRIVE_LIMIT)

    CLONE_LIMIT = environ.get('CLONE_LIMIT', '')
    CLONE_LIMIT = '' if len(CLONE_LIMIT) == 0 else float(CLONE_LIMIT)

    RCLONE_LIMIT = environ.get('RCLONE_LIMIT', '')
    RCLONE_LIMIT = '' if len(RCLONE_LIMIT) == 0 else float(RCLONE_LIMIT)

    MEGA_LIMIT = environ.get('MEGA_LIMIT', '')
    MEGA_LIMIT = '' if len(MEGA_LIMIT) == 0 else float(MEGA_LIMIT)

    LEECH_LIMIT = environ.get('LEECH_LIMIT', '')
    LEECH_LIMIT = '' if len(LEECH_LIMIT) == 0 else float(LEECH_LIMIT)

    ENABLE_RATE_LIMIT = environ.get('ENABLE_RATE_LIMIT', '')
    ENABLE_RATE_LIMIT = ENABLE_RATE_LIMIT.lower() == 'true'

    ENABLE_MESSAGE_FILTER = environ.get('ENABLE_MESSAGE_FILTER', '')
    ENABLE_MESSAGE_FILTER = ENABLE_MESSAGE_FILTER.lower() == 'true'

    STOP_DUPLICATE_TASKS = environ.get('STOP_DUPLICATE_TASKS', '')
    STOP_DUPLICATE_TASKS = STOP_DUPLICATE_TASKS.lower() == 'true'

    if not STOP_DUPLICATE_TASKS and DATABASE_URL:
        await DbManager().clear_download_links()

    DISABLE_DRIVE_LINK = environ.get('DISABLE_DRIVE_LINK', '')
    DISABLE_DRIVE_LINK = DISABLE_DRIVE_LINK.lower() == 'true'

    DISABLE_BULK = environ.get('DISABLE_BULK', '')
    DISABLE_BULK = DISABLE_BULK.lower() == 'true'

    DISABLE_MULTI = environ.get('DISABLE_MULTI', '')
    DISABLE_MULTI = DISABLE_MULTI.lower() == 'true'

    DISABLE_SEED = environ.get('DISABLE_SEED', '')
    DISABLE_SEED = DISABLE_SEED.lower() == 'true'

    DISABLE_LEECH = environ.get('DISABLE_LEECH', '')
    DISABLE_LEECH = DISABLE_LEECH.lower() == 'true'

    SET_COMMANDS = environ.get('SET_COMMANDS', '')
    SET_COMMANDS = SET_COMMANDS.lower() == 'true'

    REQUEST_LIMITS = environ.get('REQUEST_LIMITS', '')
    REQUEST_LIMITS = '' if len(
        REQUEST_LIMITS) == 0 else max(int(REQUEST_LIMITS), 5)

    DM_MODE = environ.get('DM_MODE', '')
    DM_MODE = DM_MODE.lower() if DM_MODE.lower() in [
        'leech', 'mirror', 'all'] else ''

    DELETE_LINKS = environ.get('DELETE_LINKS', '')
    DELETE_LINKS = DELETE_LINKS.lower() == 'true'

    FSUB_IDS = environ.get('FSUB_IDS', '')
    if len(FSUB_IDS) == 0:
        FSUB_IDS = ''

    TOKEN_TIMEOUT = environ.get('TOKEN_TIMEOUT', '')
    if TOKEN_TIMEOUT.isdigit():
        TOKEN_TIMEOUT = int(TOKEN_TIMEOUT)
    else:
        TOKEN_TIMEOUT = ''

    list_drives_dict.clear()
    categories_dict.clear()

    if GDRIVE_ID:
        list_drives_dict['Main'] = {
            "drive_id": GDRIVE_ID, "index_link": INDEX_URL}
        categories_dict['Root'] = {
            "drive_id": GDRIVE_ID, "index_link": INDEX_URL}

    if await aiopath.exists('list_drives.txt'):
        async with aiopen('list_drives.txt', 'r+') as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                name = temp[0].replace("_", " ")
                if name.casefold() == "Main":
                    name = "Main Custom"
                tempdict = {}
                tempdict['drive_id'] = temp[1]
                if len(temp) > 2:
                    tempdict['index_link'] = temp[2]
                else:
                    tempdict['index_link'] = ''
                list_drives_dict[name] = tempdict

    if await aiopath.exists('categories.txt'):
        async with aiopen('categories.txt', 'r+') as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                name = temp[0].replace("_", " ")
                if name.casefold() == "Root":
                    name = "Root Custom"
                tempdict = {}
                tempdict['drive_id'] = temp[1]
                if len(temp) > 2:
                    tempdict['index_link'] = temp[2]
                else:
                    tempdict['index_link'] = ''
                categories_dict[name] = tempdict

    extra_buttons.clear()
    if await aiopath.exists('buttons.txt'):
        async with aiopen('buttons.txt', 'r+') as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                if len(extra_buttons.keys()) == 4:
                    break
                if len(temp) == 2:
                    extra_buttons[temp[0].replace("_", " ")] = temp[1]

    shorteneres_list.clear()
    if await aiopath.exists('shorteners.txt'):
        async with aiopen('shorteners.txt', 'r+') as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                if len(temp) == 2:
                    shorteneres_list.append({'domain': temp[0],'api_key': temp[1]})

    if await aiopath.exists('accounts.zip'):
        if await aiopath.exists('accounts'):
            await aiormtree('accounts')
        await (await create_subprocess_exec("7z", "x", "-o.", "-aoa", "accounts.zip", "accounts/*.json")).wait()
        await (await create_subprocess_exec("chmod", "-R", "777", "accounts")).wait()
        await remove("accounts.zip")
    if not await aiopath.exists('accounts'):
        USE_SERVICE_ACCOUNTS = False

    config_dict.update({'AS_DOCUMENT': AS_DOCUMENT,
                        'AUTHORIZED_CHATS': AUTHORIZED_CHATS,
                        'AUTO_DELETE_MESSAGE_DURATION': AUTO_DELETE_MESSAGE_DURATION,
                        'BASE_URL': BASE_URL,
                        'BASE_URL_PORT': BASE_URL_PORT,
                        'BOT_TOKEN': BOT_TOKEN,
                        'CMD_SUFFIX': CMD_SUFFIX,
                        'CLONE_LIMIT': CLONE_LIMIT,
                        'DATABASE_URL': DATABASE_URL,
                        'DEFAULT_UPLOAD': DEFAULT_UPLOAD,
                        'DOWNLOAD_DIR': DOWNLOAD_DIR,
                        'DUMP_CHAT_ID': DUMP_CHAT_ID,
                        'DIRECT_LIMIT': DIRECT_LIMIT,
                        'DISABLE_DRIVE_LINK': DISABLE_DRIVE_LINK,
                        'DISABLE_LEECH': DISABLE_LEECH,
                        'DISABLE_BULK': DISABLE_BULK,
                        'DISABLE_MULTI': DISABLE_MULTI,
                        'DISABLE_SEED': DISABLE_SEED,
                        'DM_MODE': DM_MODE,
                        'DELETE_LINKS': DELETE_LINKS,
                        'EQUAL_SPLITS': EQUAL_SPLITS,
                        'EXTENSION_FILTER': EXTENSION_FILTER,
                        'ENABLE_RATE_LIMIT': ENABLE_RATE_LIMIT,
                        'ENABLE_MESSAGE_FILTER': ENABLE_MESSAGE_FILTER,
                        'FSUB_IDS': FSUB_IDS,
                        'FILELION_API': FILELION_API,
                        'GDRIVE_ID': GDRIVE_ID,
                        'GDRIVE_LIMIT': GDRIVE_LIMIT,
                        'INCOMPLETE_TASK_NOTIFIER': INCOMPLETE_TASK_NOTIFIER,
                        'INDEX_URL': INDEX_URL,
                        'IS_TEAM_DRIVE': IS_TEAM_DRIVE,
                        'JIODRIVE_ACCESS_TOKEN': JIODRIVE_ACCESS_TOKEN,
                        'LEECH_FILENAME_PREFIX': LEECH_FILENAME_PREFIX,
                        'LEECH_REMOVE_UNWANTED': LEECH_REMOVE_UNWANTED,
                        'LEECH_SPLIT_SIZE': LEECH_SPLIT_SIZE,
                        'LOG_CHAT_ID': LOG_CHAT_ID,
                        'LEECH_LIMIT': LEECH_LIMIT,
                        'MEGA_LIMIT': MEGA_LIMIT,
                        'MEDIA_GROUP': MEDIA_GROUP,
                        'MEGA_EMAIL': MEGA_EMAIL,
                        'MEGA_PASSWORD': MEGA_PASSWORD,
                        'OWNER_ID': OWNER_ID,
                        'QUEUE_ALL': QUEUE_ALL,
                        'QUEUE_DOWNLOAD': QUEUE_DOWNLOAD,
                        'QUEUE_UPLOAD': QUEUE_UPLOAD,
                        'RCLONE_FLAGS': RCLONE_FLAGS,
                        'RCLONE_LIMIT': RCLONE_LIMIT,
                        'RCLONE_PATH': RCLONE_PATH,
                        'RCLONE_SERVE_URL': RCLONE_SERVE_URL,
                        'RCLONE_SERVE_PORT': RCLONE_SERVE_PORT,
                        'RCLONE_SERVE_USER': RCLONE_SERVE_USER,
                        'RCLONE_SERVE_PASS': RCLONE_SERVE_PASS,
                        'RSS_CHAT_ID': RSS_CHAT_ID,
                        'RSS_DELAY': RSS_DELAY,
                        'REQUEST_LIMITS': REQUEST_LIMITS,
                        'SEARCH_API_LINK': SEARCH_API_LINK,
                        'SEARCH_LIMIT': SEARCH_LIMIT,
                        'SEARCH_PLUGINS': SEARCH_PLUGINS,
                        'STATUS_LIMIT': STATUS_LIMIT,
                        'STATUS_UPDATE_INTERVAL': STATUS_UPDATE_INTERVAL,
                        'STOP_DUPLICATE': STOP_DUPLICATE,
                        'STREAMWISH_API': STREAMWISH_API,
                        'SUDO_USERS': SUDO_USERS,
                        'STORAGE_THRESHOLD': STORAGE_THRESHOLD,
                        'STOP_DUPLICATE_TASKS': STOP_DUPLICATE_TASKS,
                        'SET_COMMANDS': SET_COMMANDS,
                        'TELEGRAM_API': TELEGRAM_API,
                        'TELEGRAM_HASH': TELEGRAM_HASH,
                        'TORRENT_TIMEOUT': TORRENT_TIMEOUT,
                        'TORRENT_LIMIT': TORRENT_LIMIT,
                        'TOKEN_TIMEOUT': TOKEN_TIMEOUT,
                        'UPSTREAM_BRANCH': UPSTREAM_BRANCH,
                        'UPSTREAM_REPO': UPSTREAM_REPO,
                        'USER_MAX_TASKS': USER_MAX_TASKS,
                        'USER_DUMP': USER_DUMP,
                        'USER_SESSION_STRING': USER_SESSION_STRING,
                        'USE_SERVICE_ACCOUNTS': USE_SERVICE_ACCOUNTS,
                        'WEB_PINCODE': WEB_PINCODE,
                        'YTDLP_LIMIT': YTDLP_LIMIT,
                        'PLAYLIST_LIMIT': PLAYLIST_LIMIT,
                        'YT_DLP_OPTIONS': YT_DLP_OPTIONS})

    if DATABASE_URL:
        await DbManager().update_config(config_dict)
    await gather(initiate_search_tools(), start_from_queued(), rclone_serve_booter())


async def get_buttons(key=None, edit_type=None):
    buttons = ButtonMaker()
    if key is None:
        if DATABASE_URL:
            buttons.ibutton('Fetch Config', "botset fetch")
        buttons.ibutton('Config Variables', "botset var")
        buttons.ibutton('Private Files', "botset private")
        buttons.ibutton('Qbit Settings', "botset qbit")
        buttons.ibutton('Aria2c Settings', "botset aria")
        buttons.ibutton('Close', "botset close")
        msg = 'Bot Settings:'
    elif key == 'var':
        for k in list(config_dict.keys())[START:10+START]:
            buttons.ibutton(k, f"botset editvar {k}")
        if STATE == 'view':
            buttons.ibutton('Edit', "botset edit var")
        else:
            buttons.ibutton('View', "botset view var")
        buttons.ibutton('Back', "botset back")
        buttons.ibutton('Close', "botset close")
        for x in range(0, len(config_dict), 10):
            buttons.ibutton(
                f'{int(x/10)}', f"botset start var {x}", position='footer')
        msg = f'Config Variables | Page: {int(START/10)} | State: {STATE}'
    elif key == 'private':
        buttons.ibutton('Back', "botset back")
        buttons.ibutton('Close', "botset close")
        msg = '''Send private file: config.env, token.pickle, accounts.zip, list_drives.txt, cookies.txt, terabox.txt, categories.txt, shorteners.txt, buttons.txt, .netrc or any other file!
To delete private file send only the file name as text message.
Note: Changing .netrc will not take effect for aria2c until restart.
Timeout: 60 sec'''
    elif key == 'aria':
        for k in list(aria2_options.keys())[START:10+START]:
            buttons.ibutton(k, f"botset editaria {k}")
        if STATE == 'view':
            buttons.ibutton('Edit', "botset edit aria")
        else:
            buttons.ibutton('View', "botset view aria")
        buttons.ibutton('Add new key', "botset editaria newkey")
        buttons.ibutton('Back', "botset back")
        buttons.ibutton('Close', "botset close")
        for x in range(0, len(aria2_options), 10):
            buttons.ibutton(
                f'{int(x/10)}', f"botset start aria {x}", position='footer')
        msg = f'Aria2c Options | Page: {int(START/10)} | State: {STATE}'
    elif key == 'qbit':
        for k in list(qbit_options.keys())[START:10+START]:
            buttons.ibutton(k, f"botset editqbit {k}")
        if STATE == 'view':
            buttons.ibutton('Edit', "botset edit qbit")
        else:
            buttons.ibutton('View', "botset view qbit")
        buttons.ibutton('Back', "botset back")
        buttons.ibutton('Close', "botset close")
        for x in range(0, len(qbit_options), 10):
            buttons.ibutton(
                f'{int(x/10)}', f"botset start qbit {x}", position='footer')
        msg = f'Qbittorrent Options | Page: {int(START/10)} | State: {STATE}'
    elif edit_type == 'editvar':
        msg = ''
        buttons.ibutton('Back', "botset back var")
        if key not in ['TELEGRAM_HASH', 'TELEGRAM_API', 'OWNER_ID', 'BOT_TOKEN']:
            buttons.ibutton('Default', f"botset resetvar {key}")
        buttons.ibutton('Close', "botset close")
        if key in ['SUDO_USERS', 'CMD_SUFFIX', 'OWNER_ID', 'USER_SESSION_STRING', 'TELEGRAM_HASH',
                   'TELEGRAM_API', 'AUTHORIZED_CHATS', 'DATABASE_URL', 'BOT_TOKEN', 'DOWNLOAD_DIR']:
            msg += 'Restart required for this edit to take effect!\n\n'
        msg += f'Send a valid value for {key}. Timeout: 60 sec'
    elif edit_type == 'editaria':
        buttons.ibutton('Back', "botset back aria")
        if key != 'newkey':
            buttons.ibutton('Default', f"botset resetaria {key}")
            buttons.ibutton('Empty String', f"botset emptyaria {key}")
        buttons.ibutton('Close', "botset close")
        if key == 'newkey':
            msg = 'Send a key with value. Example: https-proxy-user:value'
        else:
            msg = f'Send a valid value for {key}. Timeout: 60 sec'
    elif edit_type == 'editqbit':
        buttons.ibutton('Back', "botset back qbit")
        buttons.ibutton('Empty String', f"botset emptyqbit {key}")
        buttons.ibutton('Close', "botset close")
        msg = f'Send a valid value for {key}. Timeout: 60 sec'
    button = buttons.build_menu(1) if key is None else buttons.build_menu(2)
    return msg, button


async def update_buttons(message, key=None, edit_type=None):
    msg, button = await get_buttons(key, edit_type)
    await editMessage(message, msg, button)


async def edit_variable(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if key == 'RSS_DELAY':
        addJob()
    elif key == 'DOWNLOAD_DIR':
        if not value.endswith('/'):
            value += '/'
    elif key in ['DUMP_CHAT_ID', 'RSS_CHAT_ID', 'LOG_CHAT_ID', 'USER_DUMP']:
        if value.isdigit() or value.startswith('-'):
            value = int(value)
    elif key == 'STATUS_UPDATE_INTERVAL':
        value = int(value)
        if len(download_dict) != 0:
            async with status_reply_dict_lock:
                if Interval:
                    Interval[0].cancel()
                    Interval.clear()
                    Interval.append(setInterval(value, update_all_messages))
    elif key == 'TORRENT_TIMEOUT':
        value = int(value)
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option,
                        download.gid,
                        {'bt-stop-timeout': f'{value}'}
                    )
                except Exception as e:
                    LOGGER.error(e)
        aria2_options['bt-stop-timeout'] = f'{value}'
    elif key == 'DM_MODE':
        value = value.lower() if value.lower() in [
            'leech', 'mirror', 'all'] else ''
    elif key == 'REQUEST_LIMITS':
        value = max(int(value), 5)
    elif key == 'LEECH_SPLIT_SIZE':
        value = min(int(value), MAX_SPLIT_SIZE)
    elif key == 'BASE_URL_PORT':
        value = int(value)
        if config_dict['BASE_URL']:
            await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
            await create_subprocess_shell(f"gunicorn web.wserver:app --bind 0.0.0.0:{value} --worker-class gevent")
    elif key == 'EXTENSION_FILTER':
        fx = value.split()
        GLOBAL_EXTENSION_FILTER.clear()
        GLOBAL_EXTENSION_FILTER.extend(['aria2', '!qB'])
        for x in fx:
            if x.strip().startswith('.'):
                x = x.lstrip('.')
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())
    elif key == 'GDRIVE_ID':
        list_drives_dict['Main'] = {"drive_id": value,
                                    "index_link": config_dict['INDEX_URL']}
        categories_dict['Root'] = {"drive_id": value,
                                   "index_link": config_dict['INDEX_URL']}
    elif key == 'INDEX_URL':
        if GDRIVE_ID := config_dict['GDRIVE_ID']:
            list_drives_dict['Main'] = {
                "drive_id": GDRIVE_ID, "index_link": value}
            categories_dict['Root'] = {
                "drive_id": GDRIVE_ID, "index_link": value}
    elif key not in ['SEARCH_LIMIT', 'STATUS_LIMIT', 'PLAYLIST_LIMIT'] and key.endswith(('_THRESHOLD', '_LIMIT')):
        value = float(value)
    elif value.isdigit() and key != 'FSUB_IDS':
        value = int(value)
    elif value.lower() == 'true':
        value = True
    elif value.lower() == 'false':
        value = False
        if key == 'INCOMPLETE_TASK_NOTIFIER' and DATABASE_URL:
            await DbManager().trunc_table('tasks')
    config_dict[key] = value
    await update_buttons(pre_message, 'var')
    await message.delete()
    if DATABASE_URL:
        await DbManager().update_config({key: value})
    if key in ['SEARCH_PLUGINS', 'SEARCH_API_LINK']:
        await initiate_search_tools()
    elif key in ['QUEUE_ALL', 'QUEUE_DOWNLOAD', 'QUEUE_UPLOAD']:
        await start_from_queued()
    elif key in ['RCLONE_SERVE_URL', 'RCLONE_SERVE_PORT', 'RCLONE_SERVE_USER', 'RCLONE_SERVE_PASS']:
        await rclone_serve_booter()
    elif key == 'SET_COMMANDS':
        await set_commands(client)


async def edit_aria(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if key == 'newkey':
        key, value = [x.strip() for x in value.split(':', 1)]
    elif value.lower() == 'true':
        value = "true"
    elif value.lower() == 'false':
        value = "false"
    if key in aria2c_global:
        await sync_to_async(aria2.set_global_options, {key: value})
    else:
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(aria2.client.change_option, download.gid, {key: value})
                except Exception as e:
                    LOGGER.error(e)
    aria2_options[key] = value
    await update_buttons(pre_message, 'aria')
    await message.delete()
    if DATABASE_URL:
        await DbManager().update_aria2(key, value)


async def edit_qbit(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.lower() == 'true':
        value = True
    elif value.lower() == 'false':
        value = False
    elif key == 'max_ratio':
        value = float(value)
    elif value.isdigit():
        value = int(value)
    await sync_to_async(get_client().app_set_preferences, {key: value})
    qbit_options[key] = value
    await update_buttons(pre_message, 'qbit')
    await message.delete()
    if DATABASE_URL:
        await DbManager().update_qbittorrent(key, value)


async def update_private_file(_, message, pre_message):
    handler_dict[message.chat.id] = False
    if not message.media and (file_name := message.text):
        fn = file_name.rsplit('.zip', 1)[0]
        if await aiopath.isfile(fn) and file_name != 'config.env':
            await remove(fn)
        if fn == 'accounts':
            if await aiopath.exists('accounts'):
                await aiormtree('accounts')
            if await aiopath.exists('rclone_sa'):
                await aiormtree('rclone_sa')
            config_dict['USE_SERVICE_ACCOUNTS'] = False
            if DATABASE_URL:
                await DbManager().update_config({'USE_SERVICE_ACCOUNTS': False})
        elif file_name in ['.netrc', 'netrc']:
            await (await create_subprocess_exec("touch", ".netrc")).wait()
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (await create_subprocess_exec("cp", ".netrc", "/root/.netrc")).wait()
        elif file_name in ['buttons.txt', 'buttons']:
            extra_buttons.clear()
        elif file_name in ['categories.txt', 'categories']:
            categories_dict.clear()
            if GDRIVE_ID := config_dict['GDRIVE_ID']:
                categories_dict['Root'] = {"drive_id": GDRIVE_ID,
                                           "index_link": config_dict['INDEX_URL']}
        elif file_name in ['list_drives.txt', 'list_drives']:
            list_drives_dict.clear()
            if GDRIVE_ID := config_dict['GDRIVE_ID']:
                list_drives_dict['Main'] = {"drive_id": GDRIVE_ID,
                                            "index_link": config_dict['INDEX_URL']}
        elif file_name in ['shorteners.txt', 'shorteners']:
            shorteneres_list.clear()
        await message.delete()
    elif doc := message.document:
        file_name = doc.file_name
        await message.download(file_name=f'{getcwd()}/{file_name}')
        if file_name == 'accounts.zip':
            if await aiopath.exists('accounts'):
                await aiormtree('accounts')
            if await aiopath.exists('rclone_sa'):
                await aiormtree('rclone_sa')
            await (await create_subprocess_exec("7z", "x", "-o.", "-aoa", "accounts.zip", "accounts/*.json")).wait()
            await (await create_subprocess_exec("chmod", "-R", "777", "accounts")).wait()
        elif file_name == 'list_drives.txt':
            list_drives_dict.clear()
            if GDRIVE_ID := config_dict['GDRIVE_ID']:
                list_drives_dict['Main'] = {"drive_id": GDRIVE_ID,
                                            "index_link": config_dict['INDEX_URL']}
            with open('list_drives.txt', 'r+') as f:
                lines = f.readlines()
                for line in lines:
                    temp = line.strip().split()
                    name = temp[0].replace("_", " ")
                    if name.casefold() == "Main":
                        name = "Main Custom"
                    tempdict = {}
                    tempdict['drive_id'] = temp[1]
                    if len(temp) > 2:
                        tempdict['index_link'] = temp[2]
                    else:
                        tempdict['index_link'] = ''
                    list_drives_dict[name] = tempdict
        elif file_name == 'categories.txt':
            categories_dict.clear()
            if GDRIVE_ID := config_dict['GDRIVE_ID']:
                list_drives_dict['Root'] = {"drive_id": GDRIVE_ID,
                                            "index_link": config_dict['INDEX_URL']}
            with open('categories.txt', 'r+') as f:
                lines = f.readlines()
                for line in lines:
                    temp = line.strip().split()
                    name = temp[0].replace("_", " ")
                    if name.casefold() == "Root":
                        name = "Root Custom"
                    tempdict = {}
                    tempdict['drive_id'] = temp[1]
                    if len(temp) > 2:
                        tempdict['index_link'] = temp[2]
                    else:
                        tempdict['index_link'] = ''
                    categories_dict[name] = tempdict
        elif file_name == 'shorteners.txt':
            shorteneres_list.clear()
            with open('shorteners.txt', 'r+') as f:
                lines = f.readlines()
                for line in lines:
                    temp = line.strip().split()
                    if len(temp) == 2:
                        shorteneres_list.append({'domain': temp[0],'api_key': temp[1]})
        elif file_name == 'buttons.txt':
            extra_buttons.clear()
            with open('buttons.txt', 'r+') as f:
                lines = f.readlines()
                for line in lines:
                    temp = line.strip().split()
                    if len(extra_buttons.keys()) == 4:
                        break
                    if len(temp) == 2:
                        extra_buttons[temp[0].replace("_", " ")] = temp[1]
        elif file_name in ['.netrc', 'netrc']:
            if file_name == 'netrc':
                await rename('netrc', '.netrc')
                file_name = '.netrc'
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (await create_subprocess_exec("cp", ".netrc", "/root/.netrc")).wait()
        elif file_name == 'config.env':
            load_dotenv('config.env', override=True)
            await load_config()
        if '@github.com' in config_dict['UPSTREAM_REPO']:
            buttons = ButtonMaker()
            msg = 'Push to UPSTREAM_REPO ?'
            buttons.ibutton('Yes!', f"botset push {file_name}")
            buttons.ibutton('No', "botset close")
            await sendMessage(message, msg, buttons.build_menu(2))
        else:
            await message.delete()
    if file_name == 'rclone.conf':
        await rclone_serve_booter()
    await update_buttons(pre_message)
    if DATABASE_URL and file_name != 'config.env':
        await DbManager().update_private_file(file_name)
    if await aiopath.exists('accounts.zip'):
        await remove('accounts.zip')


async def event_handler(client, query, pfunc, rfunc, document=False):
    chat_id = query.message.chat.id
    handler_dict[chat_id] = True
    start_time = time()

    async def event_filter(_, __, event):
        user = event.from_user or event.sender_chat
        return bool(user.id == query.from_user.id and event.chat.id == chat_id and (event.text or event.document and document))
    handler = client.add_handler(MessageHandler(
        pfunc, filters=create(event_filter)), group=-1)
    while handler_dict[chat_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[chat_id] = False
            await rfunc()
    client.remove_handler(*handler)


@new_thread
async def edit_bot_settings(client, query):
    data = query.data.split()
    message = query.message
    if data[1] == 'close':
        handler_dict[message.chat.id] = False
        await query.answer()
        await message.reply_to_message.delete()
        await message.delete()
    elif data[1] == 'fetch':
        handler_dict[message.chat.id] = False
        await query.answer()
        await DbManager().load_configs()
        await load_config()
        await editMessage(message, 'Fetch config from database success!')
    elif data[1] == 'back':
        handler_dict[message.chat.id] = False
        await query.answer()
        key = data[2] if len(data) == 3 else None
        if key is None:
            globals()['START'] = 0
        await update_buttons(message, key)
    elif data[1] in ['var', 'aria', 'qbit']:
        await query.answer()
        await update_buttons(message, data[1])
    elif data[1] == 'resetvar':
        handler_dict[message.chat.id] = False
        await query.answer()
        value = ''
        if data[2] in default_values:
            value = default_values[data[2]]
            if data[2] == "STATUS_UPDATE_INTERVAL" and len(download_dict) != 0:
                async with status_reply_dict_lock:
                    if Interval:
                        Interval[0].cancel()
                        Interval.clear()
                        Interval.append(setInterval(
                            value, update_all_messages))
        elif data[2] == 'EXTENSION_FILTER':
            GLOBAL_EXTENSION_FILTER.clear()
            GLOBAL_EXTENSION_FILTER.extend(['aria2', '!qB'])
        elif data[2] == 'TORRENT_TIMEOUT':
            downloads = await sync_to_async(aria2.get_downloads)
            for download in downloads:
                if not download.is_complete:
                    try:
                        await sync_to_async(aria2.client.change_option, download.gid, {'bt-stop-timeout': '0'})
                    except Exception as e:
                        LOGGER.error(e)
            aria2_options['bt-stop-timeout'] = '0'
            if DATABASE_URL:
                await DbManager().update_aria2('bt-stop-timeout', '0')
        elif data[2] == 'BASE_URL':
            await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
        elif data[2] == 'BASE_URL_PORT':
            value = 80
            if config_dict['BASE_URL']:
                await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
                await create_subprocess_shell("gunicorn web.wserver:app --bind 0.0.0.0:80 --worker-class gevent")
        elif data[2] == 'GDRIVE_ID':
            if 'Main' in list_drives_dict:
                del list_drives_dict['Main']
            if 'Root' in categories_dict:
                del categories_dict['Root']
        elif data[2] == 'INDEX_URL':
            if (GDRIVE_ID := config_dict['GDRIVE_ID']) and 'Main' in list_drives_dict:
                list_drives_dict['Main'] = {
                    "drive_id": GDRIVE_ID, "index_link": ''}
            if (GDRIVE_ID := config_dict['GDRIVE_ID']) and 'Root' in categories_dict:
                categories_dict['Root'] = {
                    "drive_id": GDRIVE_ID, "index_link": ''}
        elif data[2] == 'INCOMPLETE_TASK_NOTIFIER' and DATABASE_URL:
            await DbManager().trunc_table('tasks')
        elif data[2] == 'STOP_DUPLICATE_TASKS' and DATABASE_URL:
            await DbManager().clear_download_links()
        config_dict[data[2]] = value
        await update_buttons(message, 'var')
        if DATABASE_URL:
            await DbManager().update_config({data[2]: value})
        if data[2] in ['SEARCH_PLUGINS', 'SEARCH_API_LINK']:
            await initiate_search_tools()
        elif data[2] in ['QUEUE_ALL', 'QUEUE_DOWNLOAD', 'QUEUE_UPLOAD']:
            await start_from_queued()
        elif data[2] in ['RCLONE_SERVE_URL', 'RCLONE_SERVE_PORT', 'RCLONE_SERVE_USER', 'RCLONE_SERVE_PASS']:
            await rclone_serve_booter()
    elif data[1] == 'resetaria':
        handler_dict[message.chat.id] = False
        aria2_defaults = await sync_to_async(aria2.client.get_global_option)
        if aria2_defaults[data[2]] == aria2_options[data[2]]:
            await query.answer('Value already same as you added in aria.sh!')
            return
        await query.answer()
        value = aria2_defaults[data[2]]
        aria2_options[data[2]] = value
        await update_buttons(message, 'aria')
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(aria2.client.change_option, download.gid, {data[2]: value})
                except Exception as e:
                    LOGGER.error(e)
        if DATABASE_URL:
            await DbManager().update_aria2(data[2], value)
    elif data[1] == 'emptyaria':
        handler_dict[message.chat.id] = False
        await query.answer()
        aria2_options[data[2]] = ''
        await update_buttons(message, 'aria')
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(aria2.client.change_option, download.gid, {data[2]: ''})
                except Exception as e:
                    LOGGER.error(e)
        if DATABASE_URL:
            await DbManager().update_aria2(data[2], '')
    elif data[1] == 'emptyqbit':
        handler_dict[message.chat.id] = False
        await query.answer()
        await sync_to_async(get_client().app_set_preferences, {data[2]: value})
        qbit_options[data[2]] = ''
        await update_buttons(message, 'qbit')
        if DATABASE_URL:
            await DbManager().update_qbittorrent(data[2], '')
    elif data[1] == 'private':
        handler_dict[message.chat.id] = False
        await query.answer()
        await update_buttons(message, data[1])
        pfunc = partial(update_private_file, pre_message=message)
        rfunc = partial(update_buttons, message)
        await event_handler(client, query, pfunc, rfunc, True)
    elif data[1] == 'editvar' and STATE == 'edit':
        value = config_dict[data[2]]
        if value and data[2] in ['OWNER_ID'] and not await CustomFilters.owner(client, query):
            value = 'Only owner can edit this!'
            await query.answer(f'{value}', show_alert=True)
        else:
            handler_dict[message.chat.id] = False
            await query.answer()
            await update_buttons(message, data[2], data[1])
            pfunc = partial(edit_variable, pre_message=message, key=data[2])
            rfunc = partial(update_buttons, message, 'var')
            await event_handler(client, query, pfunc, rfunc)
    elif data[1] == 'editvar' and STATE == 'view':
        value = config_dict[data[2]]
        if value and data[2] in ['DATABASE_URL', 'TELEGRAM_API', 'TELEGRAM_HASH', 'UPSTREAM_REPO',
                                 'USER_SESSION_STRING', 'MEGA_PASSWORD',
                                 'UPTOBOX_TOKEN'] and not await CustomFilters.owner(client, query):
            value = 'Only owner can see this!'
        elif len(str(value)) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await sendFile(message, out_file)
            return
        elif value and data[2] not in ['SEARCH_LIMIT', 'STATUS_LIMIT'] and data[2].endswith(('_THRESHOLD', '_LIMIT')):
            value = float(value)
            value = get_readable_file_size(value * 1024**3)
        elif not value:
            value = None
        await query.answer(f'{value}', show_alert=True)
    elif data[1] == 'editaria' and (STATE == 'edit' or data[2] == 'newkey'):
        handler_dict[message.chat.id] = False
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_aria, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, 'aria')
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == 'editaria' and STATE == 'view':
        value = aria2_options[data[2]]
        if len(str(value)) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await sendFile(message, out_file)
            return
        elif value == '':
            value = None
        await query.answer(f'{value}', show_alert=True)
    elif data[1] == 'editqbit' and STATE == 'edit':
        handler_dict[message.chat.id] = False
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_qbit, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, 'var')
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == 'editqbit' and STATE == 'view':
        value = qbit_options[data[2]]
        if len(str(value)) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await sendFile(message, out_file)
            return
        elif value == '':
            value = None
        await query.answer(f'{value}', show_alert=True)
    elif data[1] == 'edit':
        await query.answer()
        globals()['STATE'] = 'edit'
        await update_buttons(message, data[2])
    elif data[1] == 'view':
        await query.answer()
        globals()['STATE'] = 'view'
        await update_buttons(message, data[2])
    elif data[1] == 'start':
        await query.answer()
        if START != int(data[3]):
            globals()['START'] = int(data[3])
            await update_buttons(message, data[2])
    elif data[1] == 'push':
        await query.answer()
        filename = data[2].rsplit('.zip', 1)[0]
        if await aiopath.exists(filename):
            await (await create_subprocess_shell(f"git add -f {filename} \
                                                   && git commit -sm botsettings -q \
                                                   && git push origin {config_dict['UPSTREAM_BRANCH']} -qf")).wait()
        else:
            await (await create_subprocess_shell(f"git rm -r --cached {filename} \
                                                   && git commit -sm botsettings -q \
                                                   && git push origin {config_dict['UPSTREAM_BRANCH']} -qf")).wait()
        await message.reply_to_message.delete()
        await message.delete()


async def bot_settings(_, message):
    handler_dict[message.chat.id] = False
    msg, button = await get_buttons()
    globals()['START'] = 0
    await sendMessage(message, msg, button)



bot.add_handler(MessageHandler(bot_settings, filters=command(
    BotCommands.BotSetCommand) & CustomFilters.sudo))
bot.add_handler(CallbackQueryHandler(edit_bot_settings,
                filters=regex("^botset") & CustomFilters.sudo))
